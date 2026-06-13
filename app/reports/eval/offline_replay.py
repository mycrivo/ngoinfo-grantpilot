"""Offline replay of content-keyed P3-1 gates against walk or fixture artefacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.reports.eval.gates import (
    extract_report_from_walk,
    gate_faithfulness,
    gate_forbidden,
    gate_honest_exit,
    load_walk_artifact,
    run_fcdo_gates,
    run_nlcf_regression_pin_gates,
)
from app.reports.eval.faithfulness_check import load_faithfulness_fixture
from app.reports.eval.fixtures import pad_fcdo_ngo_sections
from scripts.audit.full_walk import PASSING_VERDICTS


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_fcdo_template() -> list[dict[str, Any]]:
    template_path = _repo_root() / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    return list(payload.get("report_sections_json") or [])


def _expected_presence_from_content(content_json: dict[str, Any]) -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {}
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        section_key = str(section.get("section_key") or "")
        content = section.get("content") or {}
        tokens: list[str] = []
        for claim in content.get("claims") or []:
            if not isinstance(claim, dict):
                continue
            if claim.get("bind_status") not in ("bound", "omitted_numeric"):
                continue
            for token in claim.get("value_tokens") or []:
                raw = str(token).strip()
                if raw:
                    tokens.append(raw)
        if tokens:
            expected[section_key] = tokens
    return expected


def replay_walk(path: Path) -> tuple[dict[str, Any], int]:
    artifact = load_walk_artifact(path)
    verdict = str(artifact.get("verdict") or "")
    report = extract_report_from_walk(artifact)
    content_json = report.get("content_json") or {}
    gap_analysis = report.get("gap_analysis_json") or {}

    failures: list[str] = []
    honest = gate_honest_exit(verdict if verdict else None)
    if not honest.passed:
        failures.append(f"{honest.name}:{honest.summary}")

    if content_json.get("sections"):
        expected = _expected_presence_from_content(content_json)
        fh = gate_faithfulness(content_json, expected_presence=expected)
        if not fh.passed:
            failures.append(f"{fh.name}:{fh.summary}")

    if gap_analysis.get("gaps") is not None:
        forbidden = gate_forbidden(gap_analysis)
        if not forbidden.passed:
            failures.append(f"{forbidden.name}:{forbidden.summary}")

    summary = {
        "artifact": str(path),
        "verdict": verdict,
        "passed": not failures,
        "failures": failures,
        "passing_verdicts": sorted(PASSING_VERDICTS),
    }
    print(json.dumps(summary, indent=2))
    return summary, 0 if not failures else 1


def _default_nlcf_template() -> list[dict[str, Any]]:
    template_path = _repo_root() / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    return list(payload.get("report_sections_json") or [])


def replay_nlcf_regression_pin() -> tuple[dict[str, Any], int]:
    key_path = (
        _repo_root()
        / "tests"
        / "fixtures"
        / "gap"
        / "keys"
        / "nlcf_regression_pin_e7fa9bee.json"
    )
    key = json.loads(key_path.read_text(encoding="utf-8"))
    gaps = [
        {**item, "requirement_type": "data", "owner": "ngo"}
        for item in key.get("expected_missing") or []
    ]
    gap_analysis = {"gaps": gaps, "open_items_count": len(gaps)}
    template = _default_nlcf_template()
    visible = template  # annual context; conditional final section off in gate helper
    content = {
        "sections": [
            {
                "section_key": s["section_key"],
                "generation_status": "GENERATED",
                "content": {"citation_mode": "structured", "text": "", "claims": []},
            }
            for s in visible
            if s.get("section_key") != "final_update_only"
        ]
    }
    report = run_nlcf_regression_pin_gates(
        gap_analysis=gap_analysis,
        template_sections=template,
        content_json=content,
        report_context=key.get("report_context") or {"report_type": "annual"},
    )
    summary = report.to_summary_dict()
    summary["fixture"] = str(key_path)
    summary["pin_status"] = key.get("status")
    print(json.dumps(summary, indent=2))
    return summary, 0 if report.passed else 1


def replay_clean_fixture(path: Path) -> tuple[dict[str, Any], int]:
    fixture = load_faithfulness_fixture(path)
    template = _default_fcdo_template()
    content_json = pad_fcdo_ngo_sections(
        fixture.get("content_json") or {},
        template,
    )
    gap_analysis = {
        "gaps": [
            {
                "section_key": "performance_and_conclusions",
                "required_item_type": "indicator",
                "required_item_ref": "progress_against_expected_results",
                "requirement_type": "data",
                "owner": "ngo",
            },
            {
                "section_key": "performance_and_conclusions",
                "required_item_type": "indicator",
                "required_item_ref": "logframe_row:op2_3",
                "requirement_type": "data",
                "owner": "ngo",
            },
            {
                "section_key": "performance_and_conclusions",
                "required_item_type": "indicator",
                "required_item_ref": "logframe_row:op4_2",
                "requirement_type": "data",
                "owner": "ngo",
            },
        ],
        "open_items_count": 3,
    }
    report = run_fcdo_gates(
        content_json=content_json,
        gap_analysis=gap_analysis,
        template_sections=template,
        expected_presence=fixture.get("expected_presence"),
    )
    summary = report.to_summary_dict()
    summary["fixture"] = str(path)
    print(json.dumps(summary, indent=2))
    return summary, 0 if report.passed else 1


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = _repo_root()
    default_fixture = (
        root / "tests" / "fixtures" / "synthesis" / "clean_faithfulness_fixture.json"
    )

    if not args or args[0] == "--fixture":
        path = Path(args[1]) if len(args) > 1 else default_fixture
        _, code = replay_clean_fixture(path)
        return code

    if args[0] == "--nlcf-pin":
        _, code = replay_nlcf_regression_pin()
        return code

    path = Path(args[0])
    if not path.exists():
        print(f"REPLAY_FAIL missing artifact {path}", flush=True)
        return 1
    _, code = replay_walk(path)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
