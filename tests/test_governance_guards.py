"""Planted-violation proofs for G1 governance guards (library + PreToolUse shape)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / ".cursor" / "hooks"
sys.path.insert(0, str(HOOKS))

from governance_guards import (  # noqa: E402
    added_lines_from_texts,
    check_funder_fixture_lines,
    check_harness_import_lines,
    check_protected_write,
    check_secrets_lines,
    evaluate_path_lines,
    load_blocklist,
    run_pretool_guard,
)


@pytest.fixture
def cfg():
    return load_blocklist()


@pytest.fixture(autouse=True)
def _clear_override_env(monkeypatch):
    monkeypatch.delenv("GOVERNANCE_OVERRIDE", raising=False)


def test_funder_string_on_engine_path_denied(cfg):
    path = "app/reports/gap/planted.py"
    lines = ['label = "FCDO Annual Review"']
    hits = check_funder_fixture_lines(path, lines, cfg)
    assert hits
    assert all(h.guard in {"funder_fixture", "sealed_fixture"} for h in hits)
    # No override path — override env must not clear funder hits
    os.environ["GOVERNANCE_OVERRIDE"] = "should-not-matter"
    result = evaluate_path_lines(path, lines, cfg=cfg, check_protected=False)
    assert not result.ok
    del os.environ["GOVERNANCE_OVERRIDE"]


def test_bare_fixture_number_prompt_only(cfg):
    prompt_path = "app/reports/ai/prompts/planted.py"
    non_prompt = "app/reports/services/planted_service.py"
    lines = ["count = 684"]
    assert check_funder_fixture_lines(prompt_path, lines, cfg)
    # Same bare number on non-prompt engine path: allow (Decision 4)
    assert not any(
        "bare fixture number" in v.detail
        for v in check_funder_fixture_lines(non_prompt, lines, cfg)
    )


def test_protected_file_requires_override(cfg, tmp_path, monkeypatch):
    path = "AGENTS.md"
    without = check_protected_write(path, cfg=cfg, layer="test", log=False)
    assert without
    monkeypatch.setenv("GOVERNANCE_OVERRIDE", "g1-proof")
    # Log to a temp file so we don't pollute the real override log during unit tests
    import governance_guards as gg

    log_path = tmp_path / "override_log.jsonl"
    monkeypatch.setattr(gg, "OVERRIDE_LOG_PATH", log_path)
    cleared = check_protected_write(path, cfg=cfg, layer="test", log=True)
    assert cleared == []
    assert log_path.is_file()
    record = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["reason"] == "g1-proof"
    assert record["path"] == "AGENTS.md"


def test_engine_importing_harness_denied(cfg):
    engine = "app/reports/services/planted.py"
    lines = ["from app.reports.eval.gates import gate_faithfulness"]
    assert check_harness_import_lines(engine, lines, cfg)
    assert check_harness_import_lines(
        engine, ["import app.reports.eval as harness"], cfg
    )
    assert check_harness_import_lines(
        engine,
        ['importlib.import_module("app.reports.eval.gates")'],
        cfg,
    )
    # Allowed importers
    assert not check_harness_import_lines(
        "tests/test_planted.py", lines, cfg
    )
    assert not check_harness_import_lines(
        "scripts/audit/planted.py", lines, cfg
    )
    assert not check_harness_import_lines(
        "app/reports/eval/gates.py", lines, cfg
    )


def test_protected_deletion_requires_override(cfg):
    from governance_guards import evaluate_added_map, parse_unified_diff_added

    diff = """\
--- a/AGENTS.md
+++ /dev/null
@@ -1 +0,0 @@
-gone
"""
    added = parse_unified_diff_added(diff)
    assert "AGENTS.md" in added
    result = evaluate_added_map(
        added, layer="test", commit_message="", check_protected=True, log_overrides=False
    )
    assert not result.ok
    assert any(v.guard == "protected_file" for v in result.violations)


def test_fake_secret_denied(cfg):
    lines = ['key = "sk-abcdefghijklmnopqrstuvwxyz0123456789"']
    hits = check_secrets_lines("app/reports/services/x.py", lines, cfg)
    assert hits
    assert hits[0].guard == "secret"


def test_deletion_never_fires(cfg):
    """Removing a blocklisted string produces no funder/fixture / secret / import hits."""
    old = 'label = "FCDO Annual Review"\ncount = 684\nfrom app.reports.eval.gates import x\n'
    new = 'label = "generic"\ncount = 0\npass\n'
    added = added_lines_from_texts(old, new)
    # Added lines are the replacements — "generic", "0", "pass" — none blocklisted
    path = "app/reports/ai/prompts/planted.py"
    assert not check_funder_fixture_lines(path, added, cfg)
    assert not check_harness_import_lines(path, added, cfg)
    assert not check_secrets_lines(path, added, cfg)


def test_harness_path_exempt_from_funder_string(cfg):
    path = "app/reports/eval/gates.py"
    lines = ['x = "FCDO Annual Review"']
    assert not check_funder_fixture_lines(path, lines, cfg)


def test_blocklist_is_protected(cfg):
    assert check_protected_write(
        ".governance/blocklist.json", cfg=cfg, layer="test", log=False
    )


def _run_pretool(tool_name: str, tool_input: dict, which: str, monkeypatch) -> tuple[int, dict]:
    import governance_guards as gg
    import io

    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    code = gg.run_pretool_guard(which=which)
    out = captured.getvalue()
    return code, json.loads(out) if out.strip() else {}


def test_pretool_funder_deny(monkeypatch):
    code, out = _run_pretool(
        "StrReplace",
        {
            "path": "app/reports/gap/planted.py",
            "old_string": "x = 1",
            "new_string": 'x = "FCDO Annual Review"',
        },
        "funder_fixture",
        monkeypatch,
    )
    assert code == 2
    assert out.get("permission") == "deny"
    assert "BOUNDARY" in out.get("user_message", "")


def test_pretool_protected_deny_and_allow(monkeypatch, tmp_path):
    import governance_guards as gg

    monkeypatch.setattr(gg, "OVERRIDE_LOG_PATH", tmp_path / "override_log.jsonl")
    code, out = _run_pretool(
        "Write",
        {"path": "AGENTS.md", "contents": "# temp\n"},
        "protected_file",
        monkeypatch,
    )
    assert code == 2
    assert out.get("permission") == "deny"

    monkeypatch.setenv("GOVERNANCE_OVERRIDE", "g1-pretool-proof")
    code2, out2 = _run_pretool(
        "Write",
        {"path": "AGENTS.md", "contents": "# temp\n"},
        "protected_file",
        monkeypatch,
    )
    assert code2 == 0
    assert out2.get("permission") == "allow"
    assert "Governance override accepted (PreToolUse)" in out2.get("user_message", "")
    assert "g1-pretool-proof" in out2.get("user_message", "")
    assert (tmp_path / "override_log.jsonl").exists()


def test_run_guards_script_help():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "governance" / "run_guards.py"), "-h"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_op_dotted_pattern_caught(cfg):
    path = "app/reports/gap/planted.py"
    lines = [
        'ref = "OP2.3"',
        'template = "logframe_row:opN_N"',
    ]
    hits = check_funder_fixture_lines(path, lines, cfg)
    details = " ".join(h.detail for h in hits)
    assert "op_dotted_indicator" in details
    assert "logframe_row_template_form" in details


def test_secret_denied_on_docs_path(cfg):
    lines = ['key = "sk-abcdefghijklmnopqrstuvwxyz0123456789"']
    hits = check_secrets_lines("docs/artefacts/me_module/audits/_planted.md", lines, cfg)
    assert hits
    assert hits[0].guard == "secret"


def test_proof_suite_is_protected(cfg):
    assert check_protected_write(
        "tests/test_governance_guards.py", cfg=cfg, layer="test", log=False
    )


def test_ci_protected_file_report_mode_scopes_softening_only():
    """Push/schedule: protected-file is report-only; funder/harness/secret still block."""
    import importlib.util

    from governance_guards import Violation

    path = REPO_ROOT / "scripts" / "governance" / "run_guards.py"
    spec = importlib.util.spec_from_file_location("run_guards_mod", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    protected = Violation(
        guard="protected_file", path="AGENTS.md", detail="needs override"
    )
    funder = Violation(
        guard="funder_fixture", path="app/reports/gap/x.py", detail="FCDO"
    )
    harness = Violation(
        guard="harness_import",
        path="app/reports/services/x.py",
        detail="engine imports eval",
    )
    secret = Violation(guard="secret", path="docs/x.md", detail="sk-…")

    # Report mode (push/schedule): protected soft; invariants hard.
    blocking, report_only = mod.partition_ci_violations(
        [protected, funder, harness, secret], protected_file_mode="report"
    )
    assert report_only == [protected]
    assert blocking == [funder, harness, secret]
    assert all(v.guard != "protected_file" for v in blocking)

    # Each invariant alone still blocks under report mode.
    for alone in (funder, harness, secret):
        b, r = mod.partition_ci_violations([alone], protected_file_mode="report")
        assert b == [alone]
        assert r == []

    # Protected alone under report mode does not block.
    b, r = mod.partition_ci_violations([protected], protected_file_mode="report")
    assert b == []
    assert r == [protected]

    # Pull-request / blocking mode: protected still fails the job.
    b, r = mod.partition_ci_violations(
        [protected, funder], protected_file_mode="blocking"
    )
    assert b == [protected, funder]
    assert r == []
