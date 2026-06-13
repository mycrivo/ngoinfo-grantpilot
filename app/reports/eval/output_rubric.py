"""Output rubric checks — forbidden refs, funder-owned gaps, narrative-as-data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# P3-8 moat — complete FCDO forbidden gap refs (see ME_MODULE_DECISION_LOG P3-8):
#   review_summary_sheet — adjudicated funder (summary RSS table)
#   outcome_assessment — adjudicated narrative (table_requirements)
#   outcome_indicators — regression pin (P3-B1 R4 walk-3347590c namespace)
FCDO_FORBIDDEN_GAP_REFS = frozenset({"outcome_indicators"})

FCDO_LITERAL_FORBIDDEN_GAP_REFS = frozenset(
    {
        "review_summary_sheet",
        "outcome_assessment",
        "outcome_indicators",
    }
)


@dataclass(frozen=True)
class OutputRubricReport:
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "rubric.violation_count": len(self.violations),
            "rubric.passed": self.passed,
        }


def evaluate_gap_rubric(gap_analysis: dict[str, Any]) -> OutputRubricReport:
    violations: list[str] = []
    gaps = gap_analysis.get("gaps") or []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        ref = str(gap.get("required_item_ref") or "")
        if ref in FCDO_LITERAL_FORBIDDEN_GAP_REFS:
            violations.append(f"literal_forbidden_gap_ref:{ref}")
        if ref in FCDO_FORBIDDEN_GAP_REFS:
            violations.append(f"forbidden_gap_ref:{ref}")
        owner = str(gap.get("owner") or "")
        req_type = str(gap.get("requirement_type") or "data")
        if owner == "funder" or req_type == "funder_supplied":
            violations.append(f"funder_owned_gap:{ref}")
        if req_type == "narrative":
            violations.append(f"narrative_data_gap:{ref}")
    return OutputRubricReport(violations=violations)


def count_generated_ngo_sections(
    content_json: dict[str, Any],
    *,
    visible_section_keys: set[str],
) -> int:
    count = 0
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        key = str(section.get("section_key") or "")
        if key not in visible_section_keys:
            continue
        if section.get("generation_status") == "GENERATED":
            count += 1
    return count
