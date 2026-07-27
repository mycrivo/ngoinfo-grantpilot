"""Shared diff-aware governance guards (Cursor + Claude Code + pre-commit + CI)."""

from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
BLOCKLIST_PATH = REPO_ROOT / ".governance" / "blocklist.json"
OVERRIDE_LOG_PATH = REPO_ROOT / ".governance" / "override_log.jsonl"

EDIT_TOOLS = {
    "Write",
    "WriteFile",
    "StrReplace",
    "search_replace",
    "ApplyPatch",
    "EditNotebook",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
}

# Real Python import statements only (start of line). Does not match prose/error text.
HARNESS_IMPORT_RE = re.compile(
    r"^\s*(?:"
    r"from\s+app\.reports\.eval(?:\.\w+)*\s+import\s+\S|"
    r"import\s+app\.reports\.eval(?:\.\w+)*(?:\s+as\s+\w+)?\s*(?:$|#|,)"
    r")",
    re.MULTILINE,
)
# Dynamic import forms that load the harness by string.
HARNESS_DYNAMIC_IMPORT_RE = re.compile(
    r"""(?:import_module|__import__)\s*\(\s*['"]app\.reports\.eval""",
)


@dataclass
class Violation:
    guard: str
    path: str
    detail: str
    line: str = ""


@dataclass
class GuardResult:
    violations: list[Violation] = field(default_factory=list)
    override_used: bool = False
    override_reason: str = ""
    overrides: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def load_blocklist() -> dict:
    with BLOCKLIST_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def path_matches_prefix(path: str, prefixes: Iterable[str]) -> bool:
    normalized = normalize_path(path)
    for prefix in prefixes:
        p = normalize_path(prefix)
        if normalized == p.rstrip("/") or normalized.startswith(p):
            return True
    return False


def is_engine_path(path: str, cfg: dict) -> bool:
    scopes = cfg["path_scopes"]
    if not path_matches_prefix(path, scopes["engine_paths"]):
        return False
    if path_matches_prefix(path, scopes["engine_exempt"]):
        return False
    return True


def is_prompt_component(path: str, cfg: dict) -> bool:
    return path_matches_prefix(path, cfg["path_scopes"]["prompt_component_paths"])


def is_protected_path(path: str, cfg: dict) -> bool:
    return path_matches_prefix(path, cfg["protected_paths"])


def is_sealed_only_path(path: str, cfg: dict) -> bool:
    return path_matches_prefix(path, cfg["path_scopes"]["sealed_only"])


def is_string_scan_excluded(path: str, cfg: dict) -> bool:
    return path_matches_prefix(path, cfg["path_scopes"]["guard_excluded_from_string_scan"])


def added_lines_from_texts(old: str, new: str) -> list[str]:
    if old == new:
        return []
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        lineterm="",
        n=0,
    )
    added: list[str] = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
    return added


def projected_content(path: Path, tool_name: str, tool_input: dict) -> str | None:
    if tool_name in {"Write", "WriteFile"}:
        content = tool_input.get("contents")
        if content is None:
            content = tool_input.get("content")
        return content if isinstance(content, str) else None

    if tool_name in {"StrReplace", "search_replace", "Edit"}:
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        if not isinstance(old, str) or not isinstance(new, str):
            return None
        current = read_text(path)
        if old and old in current:
            return current.replace(old, new, 1)
        if not path.exists() and not old:
            return new
        return None

    if tool_name == "MultiEdit":
        current = read_text(path)
        edits = tool_input.get("edits") or tool_input.get("replacements") or []
        if not isinstance(edits, list):
            return None
        text = current
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            old = edit.get("old_string") or edit.get("old_str") or ""
            new = edit.get("new_string") or edit.get("new_str") or ""
            if isinstance(old, str) and isinstance(new, str) and old in text:
                text = text.replace(old, new, 1)
        return text

    if tool_name == "EditNotebook" or tool_name == "NotebookEdit":
        new = tool_input.get("new_string")
        return new if isinstance(new, str) else None

    if tool_name == "ApplyPatch":
        # Best-effort: cannot reliably apply; treat full projected text unavailable.
        return None

    return None


def added_lines_for_tool(path: Path, tool_name: str, tool_input: dict) -> list[str] | None:
    """Return added lines, or None if the edit cannot be projected (fail closed for protected)."""
    if tool_name in {"StrReplace", "search_replace", "Edit"}:
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        if isinstance(old, str) and isinstance(new, str):
            return added_lines_from_texts(old, new)

    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or tool_input.get("replacements") or []
        added: list[str] = []
        if isinstance(edits, list):
            for edit in edits:
                if not isinstance(edit, dict):
                    continue
                old = edit.get("old_string") or edit.get("old_str") or ""
                new = edit.get("new_string") or edit.get("new_str") or ""
                if isinstance(old, str) and isinstance(new, str):
                    added.extend(added_lines_from_texts(old, new))
        return added

    projected = projected_content(path, tool_name, tool_input)
    if projected is None:
        return None
    old = read_text(path) if path.exists() else ""
    return added_lines_from_texts(old, projected)


def parse_unified_diff_added(diff_text: str) -> dict[str, list[str]]:
    """Map path -> added lines from a unified diff.

    Deleted files (`+++ /dev/null`) are included with an empty added-line list so
    the protected-file guard can still require an override for `git rm`.
    """
    current: str | None = None
    pending_old: str | None = None
    out: dict[str, list[str]] = {}
    for line in diff_text.splitlines():
        if line.startswith("--- "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                pending_old = None
            else:
                if raw.startswith("a/"):
                    raw = raw[2:]
                pending_old = normalize_path(raw)
            continue
        if line.startswith("+++ "):
            raw = line[4:].strip()
            if raw == "/dev/null":
                # Full-file deletion: track path with no added lines.
                if pending_old:
                    out.setdefault(pending_old, [])
                current = None
                pending_old = None
                continue
            if raw.startswith("b/"):
                raw = raw[2:]
            current = normalize_path(raw)
            out.setdefault(current, [])
            pending_old = None
            continue
        if current is None:
            continue
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            out[current].append(line[1:])
    return out


def git_diff_added(args: list[str]) -> dict[str, list[str]]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"git unavailable: {exc}") from exc
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git diff failed: {result.stderr.strip()}")
    return parse_unified_diff_added(result.stdout)


def staged_added_lines() -> dict[str, list[str]]:
    return git_diff_added(["diff", "--cached", "-U0", "--no-color"])


def range_added_lines(rev_range: str) -> dict[str, list[str]]:
    return git_diff_added(["diff", "-U0", "--no-color", rev_range])


def normalize_number_token(text: str) -> str:
    return text.replace(",", "").replace("£", "").replace("$", "")


def compile_literal(token: str) -> re.Pattern[str]:
    return re.compile(re.escape(token))


def compile_bare_number(token: str) -> re.Pattern[str]:
    # Standalone number token: not embedded in identifiers (foo_120_000, status500)
    # or glued to other alphanumerics/underscores. Comma-grouped forms allowed.
    digits = re.escape(token)
    if len(token) > 3 and token.isdigit():
        parts: list[str] = []
        rest = token
        while len(rest) > 3:
            parts.insert(0, rest[-3:])
            rest = rest[:-3]
        parts.insert(0, rest)
        comma_form = ",".join(parts)
        body = rf"(?:{digits}|{re.escape(comma_form)})"
    else:
        body = digits
    # (?<![A-Za-z0-9_]) … (?![A-Za-z0-9_]) avoids 120_000 / HTTP-adjacent ids.
    return re.compile(rf"(?<![A-Za-z0-9_]){body}(?![A-Za-z0-9_])")


def match_tokens_in_lines(
    lines: list[str],
    tokens: list[str],
    *,
    bare_number: bool = False,
) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    patterns = [
        (token, compile_bare_number(token) if bare_number else compile_literal(token))
        for token in tokens
    ]
    for line in lines:
        hay = normalize_number_token(line) if bare_number else line
        for token, pattern in patterns:
            source = hay if bare_number else line
            if pattern.search(source):
                hits.append((token, line))
                break
    return hits


def match_regex_patterns_in_lines(
    lines: list[str],
    patterns: list[dict],
) -> list[tuple[str, str]]:
    """Match configured regex entries ({id, pattern, flags}) against added lines."""
    hits: list[tuple[str, str]] = []
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for entry in patterns:
        if not isinstance(entry, dict):
            continue
        raw = entry.get("pattern")
        if not isinstance(raw, str) or not raw:
            continue
        flags = 0
        flag_str = entry.get("flags") or ""
        if isinstance(flag_str, str) and "i" in flag_str.lower():
            flags |= re.IGNORECASE
        name = entry.get("id") or raw
        compiled.append((str(name), re.compile(raw, flags)))
    for line in lines:
        for name, pattern in compiled:
            if pattern.search(line):
                hits.append((name, line))
                break
    return hits


def check_funder_fixture_lines(path: str, lines: list[str], cfg: dict) -> list[Violation]:
    if not lines:
        return []
    if is_string_scan_excluded(path, cfg):
        return []
    if path_matches_prefix(path, cfg["path_scopes"]["engine_exempt"]):
        # Harness exempt from ordinary funder/fixture string guard.
        # Sealed tokens still checked below against sealed_only scope.
        violations: list[Violation] = []
    elif is_engine_path(path, cfg):
        tokens = (
            list(cfg["group1_funder_identity"])
            + list(cfg["group2_bridgelight_identity"])
            + list(cfg["group3_quoted_phrases_and_slugs"])
        )
        violations = []
        for token, line in match_tokens_in_lines(lines, tokens):
            violations.append(
                Violation(
                    guard="funder_fixture",
                    path=path,
                    detail=f"blocklisted token {token!r}",
                    line=line.strip()[:200],
                )
            )
        for name, line in match_regex_patterns_in_lines(
            lines, list(cfg.get("group3_anchored_patterns") or [])
        ):
            violations.append(
                Violation(
                    guard="funder_fixture",
                    path=path,
                    detail=f"anchored pattern {name!r}",
                    line=line.strip()[:200],
                )
            )
        if is_prompt_component(path, cfg):
            for token, line in match_tokens_in_lines(
                lines, list(cfg["group4_bare_numbers_prompt_only"]), bare_number=True
            ):
                violations.append(
                    Violation(
                        guard="funder_fixture",
                        path=path,
                        detail=f"bare fixture number {token!r} in prompt-component path",
                        line=line.strip()[:200],
                    )
                )
    else:
        violations = []

    # Group 5 sealed: blocked everywhere except sealed_only.
    sealed = list(cfg.get("group5_sealed_tokens") or [])
    if sealed and not is_sealed_only_path(path, cfg):
        for token, line in match_tokens_in_lines(lines, sealed):
            violations.append(
                Violation(
                    guard="sealed_fixture",
                    path=path,
                    detail=f"sealed token {token!r} outside tests/fixtures/",
                    line=line.strip()[:200],
                )
            )
    return violations


def check_harness_import_lines(path: str, lines: list[str], cfg: dict) -> list[Violation]:
    if not lines:
        return []
    # Only Python sources can introduce a real harness import.
    if not normalize_path(path).endswith(".py"):
        return []
    allowed = cfg["harness_import_allowed_importers"]
    if path_matches_prefix(path, allowed):
        return []
    for line in lines:
        # Strip inline comments for matching; still report the raw line.
        code = line.split("#", 1)[0]
        if HARNESS_IMPORT_RE.search(code) or HARNESS_DYNAMIC_IMPORT_RE.search(code):
            return [
                Violation(
                    guard="harness_import",
                    path=path,
                    detail=(
                        "engine must never import app.reports.eval "
                        "(harness may import engine; one-way only; no override)"
                    ),
                    line=line.strip()[:200],
                )
            ]
    return []


# Known planted fake secret — allowed only in the proof test file.
# Built from fragments so hook/engine code never reintroduces the contiguous form.
_PLANTED_SECRET_ALLOW = re.compile("sk-" + "abcdefghijklmnopqrstuvwxyz0123456789")
_PLANTED_SECRET_PATHS = {
    "tests/test_governance_guards.py",
}


def check_secrets_lines(path: str, lines: list[str], cfg: dict) -> list[Violation]:
    if not lines:
        return []
    # docs/ is NOT skipped for secrets (funder/fixture string-scan exclude is separate).
    # Only the known planted fake key in the proof test file is allowed.
    allow_planted = normalize_path(path) in _PLANTED_SECRET_PATHS
    patterns = [re.compile(p) for p in cfg.get("secret_patterns") or []]
    violations: list[Violation] = []
    for line in lines:
        if allow_planted and _PLANTED_SECRET_ALLOW.search(line):
            continue
        for pattern in patterns:
            if pattern.search(line):
                violations.append(
                    Violation(
                        guard="secret",
                        path=path,
                        detail=f"possible secret pattern: {pattern.pattern}",
                        line=line.strip()[:120],
                    )
                )
                break
    return violations


def resolve_override(commit_message: str | None = None) -> tuple[bool, str]:
    env_val = os.environ.get("GOVERNANCE_OVERRIDE", "").strip()
    if env_val:
        return True, env_val
    msg = commit_message or ""
    prefix = "GOVERNANCE_OVERRIDE:"
    for line in msg.splitlines():
        if line.strip().startswith(prefix):
            return True, line.strip()[len(prefix) :].strip()
    return False, ""


def log_override(*, path: str, reason: str, layer: str, actor: str = "") -> None:
    rel = normalize_path(path)
    try:
        log_rel = normalize_path(str(OVERRIDE_LOG_PATH.relative_to(REPO_ROOT)))
    except ValueError:
        log_rel = normalize_path(str(OVERRIDE_LOG_PATH))
    # Never log writes to the log file itself (avoids dirty-tree feedback loops).
    if rel == log_rel or rel.endswith("override_log.jsonl"):
        return
    OVERRIDE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor or os.environ.get("GITHUB_ACTOR") or os.environ.get("USER") or "unknown",
        "path": rel,
        "reason": reason,
        "layer": layer,
    }
    with OVERRIDE_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def check_protected_write(
    path: str,
    *,
    cfg: dict,
    layer: str,
    commit_message: str | None = None,
    log: bool = True,
) -> list[Violation]:
    if not is_protected_path(path, cfg):
        return []
    ok, reason = resolve_override(commit_message)
    if ok and reason:
        if log:
            log_override(path=path, reason=reason, layer=layer)
        return []
    return [
        Violation(
            guard="protected_file",
            path=path,
            detail=(
                "protected file write requires explicit override: "
                "set env GOVERNANCE_OVERRIDE=<reason> for pre-commit/PreToolUse; "
                "also put GOVERNANCE_OVERRIDE: <reason> in the commit message for CI"
            ),
        )
    ]


def evaluate_path_lines(
    path: str,
    lines: list[str],
    *,
    cfg: dict | None = None,
    layer: str = "library",
    commit_message: str | None = None,
    check_protected: bool = False,
    log_overrides: bool = True,
) -> GuardResult:
    cfg = cfg or load_blocklist()
    result = GuardResult()
    if check_protected:
        prot = check_protected_write(
            path, cfg=cfg, layer=layer, commit_message=commit_message, log=log_overrides
        )
        if not prot:
            ok, reason = resolve_override(commit_message)
            if ok and is_protected_path(path, cfg):
                result.override_used = True
                result.override_reason = reason
                result.overrides.append({"path": normalize_path(path), "reason": reason})
        result.violations.extend(prot)
    result.violations.extend(check_funder_fixture_lines(path, lines, cfg))
    result.violations.extend(check_harness_import_lines(path, lines, cfg))
    result.violations.extend(check_secrets_lines(path, lines, cfg))
    return result


def evaluate_added_map(
    added: dict[str, list[str]],
    *,
    layer: str,
    commit_message: str | None = None,
    check_protected: bool = True,
    log_overrides: bool = True,
) -> GuardResult:
    cfg = load_blocklist()
    merged = GuardResult()
    for path, lines in sorted(added.items()):
        # Protected: any change to a protected path (even deletion-only) needs override,
        # because the guard covers writes to protected files. Diff-aware string guards
        # only see added lines; protected guard keys off path presence in the change set.
        path_result = evaluate_path_lines(
            path,
            lines,
            cfg=cfg,
            layer=layer,
            commit_message=commit_message,
            check_protected=check_protected,
            log_overrides=log_overrides,
        )
        merged.violations.extend(path_result.violations)
        if path_result.override_used:
            merged.override_used = True
            merged.override_reason = path_result.override_reason
        merged.overrides.extend(path_result.overrides)
    return merged


def format_violations(violations: list[Violation], cfg: dict | None = None) -> str:
    cfg = cfg or load_blocklist()
    boundary = cfg.get("boundary_law_message", "THE BOUNDARY")
    lines = ["Governance guard denied the write:", f"- {boundary}"]
    for v in violations:
        extra = f" | line: {v.line}" if v.line else ""
        lines.append(f"- [{v.guard}] {v.path}: {v.detail}{extra}")
    return "\n".join(lines)


def read_hook_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def emit_deny(user_message: str, agent_message: str) -> None:
    emit_json(
        {
            "permission": "deny",
            "user_message": user_message,
            "agent_message": agent_message,
        }
    )


def emit_allow(*, user_message: str | None = None, agent_message: str | None = None) -> None:
    payload: dict = {"permission": "allow"}
    if user_message:
        payload["user_message"] = user_message
    if agent_message:
        payload["agent_message"] = agent_message
    emit_json(payload)


def tool_target_path(tool_input: dict) -> str:
    return normalize_path(
        tool_input.get("path")
        or tool_input.get("file_path")
        or tool_input.get("filePath")
        or ""
    )


def run_pretool_guard(
    *,
    which: str,
) -> int:
    """which: funder_fixture | protected_file | harness_import | secret_write | all"""
    payload = read_hook_input()
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}
    if tool_name not in EDIT_TOOLS:
        emit_allow()
        return 0

    rel = tool_target_path(tool_input if isinstance(tool_input, dict) else {})
    if not rel:
        emit_allow()
        return 0

    cfg = load_blocklist()
    full = REPO_ROOT / rel
    added = added_lines_for_tool(full, tool_name, tool_input if isinstance(tool_input, dict) else {})

    violations: list[Violation] = []
    override_flag: str | None = None

    if which in {"protected_file", "all"}:
        # Protected: deny if targeting protected path without override, regardless of diff.
        prot = check_protected_write(rel, cfg=cfg, layer="pretooluse", log=True)
        if not prot and is_protected_path(rel, cfg):
            ok, reason = resolve_override(None)
            if ok and reason:
                override_flag = (
                    f"Governance override accepted (PreToolUse): "
                    f"path={normalize_path(rel)} reason={reason!r} "
                    f"(logged to .governance/override_log.jsonl)"
                )
        violations.extend(prot)

    if added is None:
        # Cannot project (e.g. ApplyPatch) — fail closed for content guards.
        if which in {"funder_fixture", "all"} and is_engine_path(rel, cfg):
            violations.append(
                Violation(
                    guard="funder_fixture",
                    path=rel,
                    detail="cannot project edit diff; refusing engine-path write (fail closed)",
                )
            )
        if which in {"harness_import", "all"} and not path_matches_prefix(
            rel, cfg["harness_import_allowed_importers"]
        ):
            if normalize_path(rel).startswith("app/") and not path_matches_prefix(
                rel, cfg["path_scopes"]["engine_exempt"]
            ):
                violations.append(
                    Violation(
                        guard="harness_import",
                        path=rel,
                        detail="cannot project edit diff; refusing non-harness app write (fail closed)",
                    )
                )
        if which in {"secret_write", "all"}:
            violations.append(
                Violation(
                    guard="secret",
                    path=rel,
                    detail="cannot project edit diff; refusing write (fail closed for secrets)",
                )
            )
    else:
        if which in {"funder_fixture", "all"}:
            violations.extend(check_funder_fixture_lines(rel, added, cfg))
        if which in {"harness_import", "all"}:
            violations.extend(check_harness_import_lines(rel, added, cfg))
        if which in {"secret_write", "all"}:
            violations.extend(check_secrets_lines(rel, added, cfg))

    # Filter to the requested guard when not "all"
    if which != "all":
        guard_map = {
            "funder_fixture": {"funder_fixture", "sealed_fixture"},
            "protected_file": {"protected_file"},
            "harness_import": {"harness_import"},
            "secret_write": {"secret"},
        }
        allowed = guard_map.get(which, {which})
        violations = [v for v in violations if v.guard in allowed]

    if violations:
        message = format_violations(violations, cfg)
        emit_deny(message, message)
        return 2
    if override_flag:
        emit_allow(user_message=override_flag, agent_message=override_flag)
    else:
        emit_allow()
    return 0


def tree_scan(*, report_harness: bool = True) -> dict:
    """Report-only full-tree scan of engine paths + optional harness informational section."""
    cfg = load_blocklist()
    engine_hits: list[dict] = []
    harness_hits: list[dict] = []

    app_root = REPO_ROOT / "app"
    if not app_root.exists():
        return {"engine_violations": [], "harness_informational": []}

    for path in sorted(app_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml"}:
            continue
        rel = normalize_path(str(path.relative_to(REPO_ROOT)))
        text = read_text(path)
        lines = text.splitlines()
        if path_matches_prefix(rel, cfg["path_scopes"]["engine_exempt"]):
            if report_harness:
                # Informational only — scan for funder tokens but never as violations.
                tokens = (
                    list(cfg["group1_funder_identity"])
                    + list(cfg["group2_bridgelight_identity"])
                    + list(cfg["group3_quoted_phrases_and_slugs"])
                )
                for token, line in match_tokens_in_lines(lines, tokens):
                    harness_hits.append(
                        {"path": rel, "token": token, "line": line.strip()[:200]}
                    )
                for name, line in match_regex_patterns_in_lines(
                    lines, list(cfg.get("group3_anchored_patterns") or [])
                ):
                    harness_hits.append(
                        {"path": rel, "token": name, "line": line.strip()[:200]}
                    )
            continue
        if not is_engine_path(rel, cfg):
            continue
        for v in check_funder_fixture_lines(rel, lines, cfg):
            engine_hits.append(
                {
                    "path": v.path,
                    "guard": v.guard,
                    "detail": v.detail,
                    "line": v.line,
                }
            )
        for v in check_harness_import_lines(rel, lines, cfg):
            engine_hits.append(
                {
                    "path": v.path,
                    "guard": v.guard,
                    "detail": v.detail,
                    "line": v.line,
                }
            )
    return {
        "engine_violations": engine_hits,
        "harness_informational": harness_hits,
    }
