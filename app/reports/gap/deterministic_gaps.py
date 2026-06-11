"""Deterministic E3 gap identification — no LLM required."""

from __future__ import annotations

from typing import Any

from app.reports.gap.logframe_completeness import is_logframe_row_ref
from app.reports.gap.requirement_metadata import is_ngo_data_gap_item
from app.reports.gap.satisfaction import unsatisfied_requirements
from app.reports.gap.template_requirements import TemplateRequirement, ngo_data_gap_denominator
from app.reports.schemas.gap_compliance_v1 import GapComplianceGapItem, GapComplianceOutput


def _human_label(ref: str) -> str:
    return ref.replace("_", " ").strip()


def _default_question(requirement: TemplateRequirement) -> str:
    label = _human_label(requirement.required_item_ref)
    if is_logframe_row_ref(requirement.required_item_ref):
        indicator_id = requirement.required_item_ref.split(":", 1)[-1].replace("_", ".").upper()
        return (
            f"What was the actual result for indicator {indicator_id} during this reporting period?"
        )
    if requirement.required_item_type == "table":
        return f"Please confirm or provide the data for the {label} table in {requirement.section_label}."
    if requirement.requirement_type == "data":
        return f"What is the {label} for {requirement.section_label}?"
    return f"Please provide information about {label} for {requirement.section_label}."


def _default_rationale(requirement: TemplateRequirement) -> str:
    if is_logframe_row_ref(requirement.required_item_ref):
        return (
            "We could not find a confirmed actual value for this logframe indicator "
            "in your uploaded documents."
        )
    return (
        f"We need this {requirement.required_item_type} to complete "
        f"{requirement.section_label} — it was not found in your confirmed knowledge bank."
    )


def _suggested_action_for(requirement: TemplateRequirement) -> str | None:
    if requirement.requirement_type != "data":
        return None
    return "provide"


def requirement_to_gap_item(
    requirement: TemplateRequirement,
    *,
    suggested_action: str | None = None,
) -> GapComplianceGapItem:
    action = suggested_action or _suggested_action_for(requirement)
    return GapComplianceGapItem(
        item_key=requirement.item_key,
        section_key=requirement.section_key,
        section_label=requirement.section_label,
        required_item_type=requirement.required_item_type,
        required_item_ref=requirement.required_item_ref,
        severity="required",
        question=_default_question(requirement),
        rationale=_default_rationale(requirement),
        owner=requirement.owner,
        requirement_type=requirement.requirement_type,
        suggested_action=action,
    )


def build_deterministic_gap_compliance_output(
    *,
    requirements: list[TemplateRequirement],
    knowledge_bank_json: dict[str, Any],
    logframe_gaps: list[GapComplianceGapItem],
    checklist_non_section_count: int | None = None,
    readiness_basis: str = "ngo_data",
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
        if requirement.requirement_type == "narrative":
            continue
        if not is_ngo_data_gap_item(requirement.requirement_type):
            continue
        gaps_by_key[requirement.item_key] = requirement_to_gap_item(requirement)
    for gap in logframe_gaps:
        gaps_by_key[gap.item_key] = gap
    merged = list(gaps_by_key.values())
    if not merged:
        return GapComplianceOutput(
            open_items_count=0,
            ready_for_gate2=True,
            gaps=[],
            readiness_basis=readiness_basis,
        )
    data_gaps = [g for g in merged if (g.requirement_type or "data") == "data"]
    return GapComplianceOutput(
        open_items_count=len(data_gaps),
        ready_for_gate2=False,
        gaps=merged,
        readiness_basis=readiness_basis,
    )
