"""P3-1 named FCDO eval gates — content-keyed assertions only."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.reports.eval.citation_pr import evaluate_citation_pr
from app.reports.eval.faithfulness_check import check_content_json_faithfulness
from app.reports.eval.output_rubric import (
    count_generated_ngo_sections,
    evaluate_gap_rubric,
)
from app.reports.gap.section_visibility import visible_sections_for_context
from scripts.audit.full_walk import PASSING_VERDICTS, exit_code_for_verdict

FCDO_COMPLETE_GAP_REFS = frozenset({"logframe_row:op2_3", "logframe_row:op4_2"})
FCDO_NGO_SECTION_COUNT = 6


@dataclass
class GateResult:
    name: str
    passed: bool
    summary: dict[str, Any] = field(default_factory=dict)
    detail: str | None = None


@dataclass
class EvalGateReport:
    results: list[GateResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "gates": {
                r.name: {"passed": r.passed, **r.summary}
                for r in self.results
            },
        }


def gate_degrade_leak(content_json: dict[str, Any]) -> GateResult:
    report = check_content_json_faithfulness(content_json)
    count = len(report.degraded_leaks)
    return GateResult(
        name="G-degrade-leak",
        passed=count == 0,
        summary={"degraded_pass_through": count},
    )


def gate_faithfulness(
    content_json: dict[str, Any],
    *,
    expected_presence: dict[str, list[str]] | None = None,
) -> GateResult:
    report = check_content_json_faithfulness(
        content_json,
        expected_presence=expected_presence,
    )
    count = len(report.unmatched_numbers)
    return GateResult(
        name="G-faithfulness",
        passed=count == 0,
        summary=report.to_summary_dict(),
    )


def gate_fcdo_gap_exact(gap_analysis: dict[str, Any]) -> GateResult:
    gaps = gap_analysis.get("gaps") or []
    refs = {
        str(g.get("required_item_ref") or "")
        for g in gaps
        if isinstance(g, dict)
    }
    passed = refs == set(FCDO_COMPLETE_GAP_REFS)
    return GateResult(
        name="G-fcdo-gap-exact",
        passed=passed,
        summary={"gap_refs": sorted(refs), "expected": sorted(FCDO_COMPLETE_GAP_REFS)},
    )


def gate_forbidden(gap_analysis: dict[str, Any]) -> GateResult:
    rubric = evaluate_gap_rubric(gap_analysis)
    forbidden_hits = [
        v for v in rubric.violations if v.startswith("forbidden_gap_ref:")
    ]
    funder_hits = [
        v for v in rubric.violations if v.startswith("funder_owned_gap:")
    ]
    narrative_hits = [
        v for v in rubric.violations if v.startswith("narrative_data_gap:")
    ]
    passed = not forbidden_hits and not funder_hits and not narrative_hits
    return GateResult(
        name="G-forbidden",
        passed=passed,
        summary={
            "forbidden_rss_oa": len(forbidden_hits),
            "funder_owned": len(funder_hits),
            "narrative_data": len(narrative_hits),
            "violations": rubric.violations,
        },
    )


def gate_section_count(
    content_json: dict[str, Any],
    *,
    template_sections: list[dict[str, Any]],
    report_context: dict[str, Any],
    expected_count: int = FCDO_NGO_SECTION_COUNT,
) -> GateResult:
    visible = visible_sections_for_context(
        template_sections,
        report_context=report_context,
        include_funder_owned=False,
    )
    visible_keys = {str(s.get("section_key") or "") for s in visible}
    generated = count_generated_ngo_sections(
        content_json,
        visible_section_keys=visible_keys,
    )
    return GateResult(
        name="G-section-count",
        passed=generated == expected_count,
        summary={
            "generated_ngo_sections": generated,
            "expected": expected_count,
            "visible_keys": sorted(visible_keys),
        },
    )


def gate_honest_exit(verdict: str | None) -> GateResult:
    """Verify walk verdict maps to the correct process exit code."""
    if not verdict:
        return GateResult(
            name="G-honest-exit",
            passed=False,
            summary={"verdict": None, "exit_code": 1},
            detail="missing_verdict",
        )
    code = exit_code_for_verdict(verdict)
    if verdict in PASSING_VERDICTS:
        passed = code == 0
    else:
        passed = code != 0
    return GateResult(
        name="G-honest-exit",
        passed=passed,
        summary={"verdict": verdict, "exit_code": code},
    )


def run_fcdo_gates(
    *,
    content_json: dict[str, Any],
    gap_analysis: dict[str, Any],
    template_sections: list[dict[str, Any]],
    report_context: dict[str, Any] | None = None,
    expected_presence: dict[str, list[str]] | None = None,
    walk_verdict: str | None = None,
) -> EvalGateReport:
    ctx = report_context or {"report_type": "annual"}
    report = EvalGateReport(
        results=[
            gate_degrade_leak(content_json),
            gate_faithfulness(content_json, expected_presence=expected_presence),
            gate_fcdo_gap_exact(gap_analysis),
            gate_forbidden(gap_analysis),
            gate_section_count(
                content_json,
                template_sections=template_sections,
                report_context=ctx,
            ),
        ]
    )
    if walk_verdict is not None:
        report.results.append(gate_honest_exit(walk_verdict))
    return report


def expected_gap_identities_from_refs(
    refs: set[str],
    *,
    section_key: str = "performance_and_conclusions",
    required_item_type: str = "indicator",
) -> set[tuple[str, str, str]]:
    return {
        (section_key, required_item_type, ref)
        for ref in refs
    }


def load_walk_artifact(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_report_from_walk(artifact: dict[str, Any]) -> dict[str, Any]:
    snaps = artifact.get("snapshots") or {}
    for key in ("after_export", "after_critique", "after_critique_detail", "after_gap"):
        snap = snaps.get(key) or {}
        if key == "after_critique_detail":
            body = snap.get("body")
            if isinstance(body, dict) and body.get("content_json"):
                return body
            continue
        report = snap.get("report") or {}
        if report.get("content_json") or report.get("gap_analysis_json"):
            return report
    extra = artifact.get("extra") or {}
    detail = extra.get("report_detail")
    if isinstance(detail, dict):
        return detail
    return {}
