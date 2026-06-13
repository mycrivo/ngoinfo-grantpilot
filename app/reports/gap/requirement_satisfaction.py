"""Typed requirement satisfaction — data/narrative/funder (Phase 2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.reports.gap.gap_answer import (
    GAP_ANSWER_DISPOSITION_ANSWERED,
    is_gap_answer_resolved,
)
from app.reports.gap.logframe_completeness import (
    has_indicator_data_actual_for_id,
    is_logframe_row_ref,
    is_proposal_target_fact,
    logframe_indicator_id_from_ref,
)
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.knowledge.confirmed_kb import is_fact_citable

DATA_BACKED_HINTS: dict[str, list[str]] = {
    "actual_results": ["ar1_actual", "indicators."],
    "output_indicators": ["indicators.", "ar1_milestone_target"],
    "outcome_indicators": ["indicators.", "proposal_target"],
    "logframe_milestones": ["ar1_milestone_target"],
    "progress_against_expected_results": ["ar1_actual", "ar1_milestone_target"],
    "forecast_vs_actual_costs": ["financials.lines", "financials."],
    "forecast_vs_actual_spend": ["financials.lines", "financials."],
    "financial_delivery": ["financials.lines", "financials."],
    "cost_drivers": ["financials.lines", "financials."],
    "beneficiary_numbers": ["indicators.", "beneficiar"],
    "outcome_indicators_where_available": ["indicators.", "outcome"],
    "review_summary_sheet": ["programme_title", "programme_code", "review_date"],
    "outcome_assessment": ["indicators.", "outcome"],
    "delivery_financial_performance": ["financials."],
}


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _fact_is_citable(fact: dict[str, Any], *, gate1_confirmed_at: str | None) -> bool:
    return is_fact_citable(fact, gate1_confirmed_at=gate1_confirmed_at)


def _iter_citable_facts(
    facts: dict[str, Any],
    *,
    gate1_confirmed_at: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _fact_is_citable(fact, gate1_confirmed_at=gate1_confirmed_at):
            continue
        if is_proposal_target_fact(str(fact_key), fact):
            continue
        out.append((str(fact_key), fact))
    return out


def _section_has_citable_facts(
    section_key: str,
    *,
    facts: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> bool:
    section_token = _normalize_token(section_key)
    for fact_key, _fact in _iter_citable_facts(facts, gate1_confirmed_at=gate1_confirmed_at):
        if section_token in _normalize_token(fact_key):
            return True
    return False


def _hints_match(ref: str, fact_keys: list[str]) -> bool:
    hints = DATA_BACKED_HINTS.get(ref)
    if not hints:
        return False
    for hint in hints:
        if any(hint in key for key in fact_keys):
            return True
    return False


def _data_indicator_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> tuple[bool, bool]:
    """Return (satisfied, confirm_existing_candidate)."""
    if is_logframe_row_ref(requirement.required_item_ref):
        indicator_id = logframe_indicator_id_from_ref(requirement.required_item_ref)
        if indicator_id is None:
            return False, False
        return has_indicator_data_actual_for_id(facts, indicator_id), False

    fact_keys = [key for key, _ in _iter_citable_facts(facts, gate1_confirmed_at=gate1_confirmed_at)]
    if _hints_match(requirement.required_item_ref, fact_keys):
        return True, True

    return False, False


def _table_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> tuple[bool, bool]:
    table_token = _normalize_token(requirement.required_item_ref)
    for fact_key, fact in _iter_citable_facts(facts, gate1_confirmed_at=gate1_confirmed_at):
        key_token = _normalize_token(fact_key)
        label_token = _normalize_token(str(fact.get("semantic_label") or ""))
        if table_token in key_token or table_token in label_token:
            return True, True
    return False, False


@dataclass(frozen=True)
class SatisfactionResult:
    satisfied: bool
    suggested_action: str | None = None


RequirementSatisfactionPurpose = Literal["gate", "synthesis"]


def _gap_answer_satisfies_requirement(
    entry: Any,
    *,
    purpose: RequirementSatisfactionPurpose,
) -> bool:
    if not isinstance(entry, dict):
        return False
    if purpose == "synthesis":
        if entry.get("disposition") != GAP_ANSWER_DISPOSITION_ANSWERED:
            return False
        return is_gap_answer_resolved(entry)
    return is_gap_answer_resolved(entry)


def evaluate_requirement_satisfaction(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    all_requirements: list[TemplateRequirement] | None = None,
    gate1_confirmed_at: str | None = None,
    purpose: RequirementSatisfactionPurpose = "gate",
) -> SatisfactionResult:
    if requirement.requirement_type == "funder_supplied" or requirement.owner == "funder":
        return SatisfactionResult(satisfied=True)

    if requirement.item_key in gap_answers and _gap_answer_satisfies_requirement(
        gap_answers[requirement.item_key],
        purpose=purpose,
    ):
        return SatisfactionResult(satisfied=True)

    if requirement.requirement_type == "narrative":
        if _section_has_citable_facts(
            requirement.section_key,
            facts=facts,
            gate1_confirmed_at=gate1_confirmed_at,
        ):
            return SatisfactionResult(satisfied=True)
        if requirement.required_item_type == "indicator" and purpose != "synthesis":
            return SatisfactionResult(satisfied=True)
        return SatisfactionResult(satisfied=False)

    if requirement.required_item_type == "indicator":
        satisfied, confirm = _data_indicator_satisfied(
            requirement,
            facts=facts,
            gate1_confirmed_at=gate1_confirmed_at,
        )
        if satisfied:
            action = "confirm_existing" if confirm else None
            return SatisfactionResult(satisfied=True, suggested_action=action)
        return SatisfactionResult(satisfied=False, suggested_action="provide")

    if requirement.required_item_type == "table":
        satisfied, confirm = _table_satisfied(
            requirement,
            facts=facts,
            gate1_confirmed_at=gate1_confirmed_at,
        )
        if satisfied:
            return SatisfactionResult(
                satisfied=True,
                suggested_action="confirm_existing" if confirm else None,
            )
        return SatisfactionResult(satisfied=False, suggested_action="provide")

    children = [
        child
        for child in (all_requirements or [])
        if child.section_key == requirement.section_key
        and child.required_item_type != "section"
    ]
    if not children:
        if _section_has_citable_facts(
            requirement.section_key,
            facts=facts,
            gate1_confirmed_at=gate1_confirmed_at,
        ):
            return SatisfactionResult(satisfied=True)
        return SatisfactionResult(satisfied=False)
    for child in children:
        child_result = evaluate_requirement_satisfaction(
            child,
            facts=facts,
            gap_answers=gap_answers,
            all_requirements=all_requirements,
            gate1_confirmed_at=gate1_confirmed_at,
            purpose=purpose,
        )
        if not child_result.satisfied:
            return SatisfactionResult(satisfied=False)
    return SatisfactionResult(satisfied=True)
