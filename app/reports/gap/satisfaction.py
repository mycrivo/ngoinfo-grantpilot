"""Determine whether a template requirement is satisfied from a Gate-1-confirmed knowledge bank."""

from __future__ import annotations

import re
from typing import Any

from app.reports.gap.gap_answer import is_gap_answer_resolved
from app.reports.gap.template_requirements import TemplateRequirement


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _fact_from_uploaded_documents(fact: dict[str, Any]) -> bool:
    source_id = fact.get("source_document_id")
    return bool(source_id and str(source_id).strip())


def _indicator_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
) -> bool:
    if requirement.item_key in gap_answers:
        if is_gap_answer_resolved(gap_answers[requirement.item_key]):
            return True
    indicator_token = _normalize_token(requirement.required_item_ref)
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _fact_from_uploaded_documents(fact):
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
) -> bool:
    if requirement.item_key in gap_answers:
        if is_gap_answer_resolved(gap_answers[requirement.item_key]):
            return True
    table_token = _normalize_token(requirement.required_item_ref)
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _fact_from_uploaded_documents(fact):
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
            if not _fact_from_uploaded_documents(fact):
                continue
            if section_token in _normalize_token(str(fact_key)):
                return True
        return False
    return all(
        is_requirement_satisfied(child, facts=facts, gap_answers=gap_answers)
        for child in children
    )


def is_requirement_satisfied(
    requirement: TemplateRequirement,
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    all_requirements: list[TemplateRequirement] | None = None,
) -> bool:
    """Satisfied only via allowed sources: uploaded_documents facts or gap_answers."""
    if requirement.required_item_type == "indicator":
        return _indicator_satisfied(requirement, facts=facts, gap_answers=gap_answers)
    if requirement.required_item_type == "table":
        return _table_satisfied(requirement, facts=facts, gap_answers=gap_answers)
    return _section_satisfied(
        requirement,
        facts=facts,
        gap_answers=gap_answers,
        child_requirements=all_requirements or [],
    )


def unsatisfied_requirements(
    requirements: list[TemplateRequirement],
    knowledge_bank_json: dict[str, Any],
) -> list[TemplateRequirement]:
    facts = knowledge_bank_json.get("facts") or {}
    gap_answers = knowledge_bank_json.get("gap_answers") or {}
    missing: list[TemplateRequirement] = []
    for requirement in requirements:
        if requirement.required_item_type == "section":
            continue
        if not is_requirement_satisfied(
            requirement,
            facts=facts,
            gap_answers=gap_answers,
            all_requirements=requirements,
        ):
            missing.append(requirement)
    return missing
