"""Elevate template-flagged narrative requirements to Gate 2 after proposal-failure proceed.

Funder-specific which-refs live in template JSON (`elevate_on_proposal_failure`).
Trigger is checkpoint-acked `proceed_with_gap` only (D-053).
"""

from __future__ import annotations

from typing import Any

from app.reports.gap.deterministic_gaps import requirement_to_gap_item
from app.reports.gap.gap_answer import is_gap_answer_resolved
from app.reports.gap.requirement_metadata import _indicator_meta
from app.reports.gap.requirement_satisfaction import evaluate_requirement_satisfaction
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.schemas.gap_compliance_v1 import GapComplianceOutput
from app.reports.services.report_inputs_builder import section_has_synthesizable_inputs


def is_proposal_failure_proceeded(agent_trace_json: dict[str, Any] | None) -> bool:
    """True when extract checkpoint was acked with proceed_with_gap."""
    stages = (agent_trace_json or {}).get("stages") or {}
    extract = stages.get("extract") or {}
    checkpoint = extract.get("proposal_checkpoint")
    if not isinstance(checkpoint, dict):
        return False
    return bool(checkpoint.get("acknowledged")) and checkpoint.get("ack_action") == (
        "proceed_with_gap"
    )


def elevate_on_proposal_failure_flag(
    sections: list[dict[str, Any]],
    *,
    section_key: str,
    indicator_ref: str,
) -> bool:
    """Read optional per-indicator elevate_on_proposal_failure from template sections."""
    for section in sections:
        if not isinstance(section, dict):
            continue
        if section.get("section_key") != section_key:
            continue
        meta = _indicator_meta(section, indicator_ref)
        return bool(meta.get("elevate_on_proposal_failure"))
    return False


def apply_proposal_failure_elevation(
    output: GapComplianceOutput,
    *,
    requirements: list[TemplateRequirement],
    knowledge_bank_json: dict[str, Any],
    report_sections_json: list[dict[str, Any]],
    elevate: bool,
) -> GapComplianceOutput:
    """Merge elevated narrative gaps when trigger is true; healthy path is a no-op."""
    if not elevate:
        return output

    facts = knowledge_bank_json.get("facts") or {}
    gap_answers = knowledge_bank_json.get("gap_answers") or {}
    gate1 = knowledge_bank_json.get("gate1_confirmed_at")
    if not isinstance(facts, dict):
        facts = {}
    if not isinstance(gap_answers, dict):
        gap_answers = {}

    sections_by_key = {
        str(s.get("section_key")): s
        for s in report_sections_json
        if isinstance(s, dict) and s.get("section_key")
    }
    by_key = {gap.item_key: gap for gap in output.gaps}
    for requirement in requirements:
        if requirement.required_item_type != "indicator":
            continue
        if not elevate_on_proposal_failure_flag(
            report_sections_json,
            section_key=requirement.section_key,
            indicator_ref=requirement.required_item_ref,
        ):
            continue
        if requirement.item_key in by_key:
            continue
        existing_answer = gap_answers.get(requirement.item_key)
        if isinstance(existing_answer, dict) and is_gap_answer_resolved(existing_answer):
            # Already resolved at Gate 2 — do not re-ask.
            continue
        result = evaluate_requirement_satisfaction(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            all_requirements=requirements,
            gate1_confirmed_at=gate1 if isinstance(gate1, str) else None,
            purpose="synthesis",
        )
        if result.satisfied:
            continue
        section = sections_by_key.get(requirement.section_key)
        if section is not None and section_has_synthesizable_inputs(
            knowledge_bank_json,
            section,
            report_sections=report_sections_json,
        ):
            # Proposal-side facts (e.g. partnerships.*/engagement.*) already feed synthesis.
            continue
        by_key[requirement.item_key] = requirement_to_gap_item(
            requirement,
            suggested_action="provide",
        )

    merged = list(by_key.values())
    if not merged:
        return GapComplianceOutput(
            open_items_count=0,
            ready_for_gate2=True,
            gaps=[],
            readiness_basis=output.readiness_basis,
        )
    return GapComplianceOutput(
        open_items_count=len(merged),
        ready_for_gate2=False,
        gaps=merged,
        readiness_basis=output.readiness_basis,
    )
