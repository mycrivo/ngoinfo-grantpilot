"""Deterministic E3 gap identification — no LLM required."""

from __future__ import annotations

from typing import Any

from app.reports.gap.logframe_completeness import is_logframe_row_ref
from app.reports.gap.satisfaction import unsatisfied_requirements
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.schemas.gap_compliance_v1 import GapComplianceGapItem, GapComplianceOutput


def _default_question(requirement: TemplateRequirement) -> str:
    return (
        f"Please provide the information required for {requirement.section_label}: "
        f"{requirement.required_item_ref}."
    )


def _default_rationale(requirement: TemplateRequirement) -> str:
    return (
        f"No matching fact or gap answer was found in the confirmed knowledge bank "
        f"for {requirement.required_item_type} {requirement.required_item_ref!r} "
        f"in section {requirement.section_key!r}."
    )


def requirement_to_gap_item(requirement: TemplateRequirement) -> GapComplianceGapItem:
    return GapComplianceGapItem(
        item_key=requirement.item_key,
        section_key=requirement.section_key,
        section_label=requirement.section_label,
        required_item_type=requirement.required_item_type,
        required_item_ref=requirement.required_item_ref,
        severity="required",
        question=_default_question(requirement),
        rationale=_default_rationale(requirement),
    )


def build_deterministic_gap_compliance_output(
    *,
    requirements: list[TemplateRequirement],
    knowledge_bank_json: dict[str, Any],
    logframe_gaps: list[GapComplianceGapItem],
    checklist_non_section_count: int,
) -> GapComplianceOutput:
    """Identify gaps from checklist satisfaction rules only."""
    missing = unsatisfied_requirements(requirements, knowledge_bank_json)
    logframe_keys = {gap.item_key for gap in logframe_gaps}
    gaps_by_key: dict[str, GapComplianceGapItem] = {}
    for requirement in missing:
        if requirement.item_key in logframe_keys:
            continue
        if is_logframe_row_ref(requirement.required_item_ref):
            continue
        gaps_by_key[requirement.item_key] = requirement_to_gap_item(requirement)
    for gap in logframe_gaps:
        gaps_by_key[gap.item_key] = gap
    merged = list(gaps_by_key.values())
    if not merged:
        return GapComplianceOutput(
            readiness_score=100,
            ready_for_gate2=True,
            gaps=[],
        )
    satisfied = max(0, checklist_non_section_count - len(merged))
    readiness = max(
        0,
        int(round(100 * satisfied / max(checklist_non_section_count, 1))),
    )
    return GapComplianceOutput(
        readiness_score=readiness,
        ready_for_gate2=False,
        gaps=merged,
    )
