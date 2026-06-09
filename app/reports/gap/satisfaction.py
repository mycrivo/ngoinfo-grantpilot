"""Determine whether a template requirement is satisfied from a Gate-1-confirmed knowledge bank."""

from __future__ import annotations

import re
from typing import Any

from app.reports.gap.gap_answer import is_gap_answer_resolved
from app.reports.gap.logframe_completeness import (
    has_indicator_data_actual_for_id,
    is_logframe_row_ref,
    is_proposal_target_fact,
    logframe_indicator_id_from_ref,
)
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.knowledge.confirmed_kb import is_fact_citable


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _fact_is_citable(fact: dict[str, Any], *, gate1_confirmed_at: str | None) -> bool:
    return is_fact_citable(fact, gate1_confirmed_at=gate1_confirmed_at)


def _indicator_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> bool:
    if requirement.item_key in gap_answers:
        if is_gap_answer_resolved(gap_answers[requirement.item_key]):
            return True
    if is_logframe_row_ref(requirement.required_item_ref):
        indicator_id = logframe_indicator_id_from_ref(requirement.required_item_ref)
        if indicator_id is None:
            return False
        return has_indicator_data_actual_for_id(facts, indicator_id)
    indicator_token = _normalize_token(requirement.required_item_ref)
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _fact_is_citable(fact, gate1_confirmed_at=gate1_confirmed_at):
            continue
        if is_proposal_target_fact(str(fact_key), fact):
            continue
        key_token = _normalize_token(str(fact_key))
        label_token = _normalize_token(str(fact.get("semantic_label") or ""))
        if indicator_token in key_token or indicator_token in label_token:
            return True
    return False


def _table_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> bool:
    if requirement.item_key in gap_answers:
        if is_gap_answer_resolved(gap_answers[requirement.item_key]):
            return True
    table_token = _normalize_token(requirement.required_item_ref)
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _fact_is_citable(fact, gate1_confirmed_at=gate1_confirmed_at):
            continue
        key_token = _normalize_token(str(fact_key))
        label_token = _normalize_token(str(fact.get("semantic_label") or ""))
        if table_token in key_token or table_token in label_token:
            return True
    return False


def _section_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    child_requirements: list[TemplateRequirement],
    gate1_confirmed_at: str | None,
) -> bool:
    if requirement.item_key in gap_answers:
        if is_gap_answer_resolved(gap_answers[requirement.item_key]):
            return True
    children = [
        child
        for child in child_requirements
        if child.section_key == requirement.section_key
        and child.required_item_type != "section"
    ]
    if not children:
        section_token = _normalize_token(requirement.section_key)
        for fact_key, fact in facts.items():
            if not isinstance(fact, dict):
                continue
            if not _fact_is_citable(fact, gate1_confirmed_at=gate1_confirmed_at):
                continue
            if section_token in _normalize_token(str(fact_key)):
                return True
        return False
    return all(
        is_requirement_satisfied(
            child,
            facts=facts,
            gap_answers=gap_answers,
            gate1_confirmed_at=gate1_confirmed_at,
        )
        for child in children
    )


def is_requirement_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    all_requirements: list[TemplateRequirement] | None = None,
    gate1_confirmed_at: str | None = None,
) -> bool:
    """Satisfied via citable KB facts or resolved gap_answers."""
    if requirement.required_item_type == "indicator":
        return _indicator_satisfied(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            gate1_confirmed_at=gate1_confirmed_at,
        )
    if requirement.required_item_type == "table":
        return _table_satisfied(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            gate1_confirmed_at=gate1_confirmed_at,
        )
    return _section_satisfied(
        requirement,
        facts=facts,
        gap_answers=gap_answers,
        child_requirements=all_requirements or [],
        gate1_confirmed_at=gate1_confirmed_at,
    )


def unsatisfied_requirements(
    requirements: list[TemplateRequirement],
    knowledge_bank_json: dict[str, Any],
) -> list[TemplateRequirement]:
    facts = knowledge_bank_json.get("facts") or {}
    gap_answers = knowledge_bank_json.get("gap_answers") or {}
    gate1_at = knowledge_bank_json.get("gate1_confirmed_at")
    missing: list[TemplateRequirement] = []
    for requirement in requirements:
        if requirement.required_item_type == "section":
            continue
        if not is_requirement_satisfied(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            all_requirements=requirements,
            gate1_confirmed_at=gate1_at,
        ):
            missing.append(requirement)
    return missing
