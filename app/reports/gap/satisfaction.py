"""Determine whether a template requirement is satisfied from a Gate-1-confirmed knowledge bank."""



from __future__ import annotations



from typing import Any



from app.reports.gap.requirement_satisfaction import evaluate_requirement_satisfaction

from app.reports.gap.template_requirements import TemplateRequirement





def is_requirement_satisfied(

    requirement: TemplateRequirement,

    *,

    facts: dict[str, Any],

    gap_answers: dict[str, Any],

    all_requirements: list[TemplateRequirement] | None = None,

    gate1_confirmed_at: str | None = None,

) -> bool:

    """Satisfied via typed matchers, citable KB facts, or resolved gap_answers."""

    return evaluate_requirement_satisfaction(

        requirement,

        facts=facts,

        gap_answers=gap_answers,

        all_requirements=all_requirements,

        gate1_confirmed_at=gate1_confirmed_at,

    ).satisfied





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





def requirement_suggested_actions(

    requirements: list[TemplateRequirement],

    knowledge_bank_json: dict[str, Any],

) -> dict[str, str | None]:

    """Map item_key → suggested_action for unsatisfied NGO data gaps."""

    facts = knowledge_bank_json.get("facts") or {}

    gap_answers = knowledge_bank_json.get("gap_answers") or {}

    gate1_at = knowledge_bank_json.get("gate1_confirmed_at")

    actions: dict[str, str | None] = {}

    for requirement in requirements:

        if requirement.required_item_type == "section":

            continue

        result = evaluate_requirement_satisfaction(

            requirement,

            facts=facts,

            gap_answers=gap_answers,

            all_requirements=requirements,

            gate1_confirmed_at=gate1_at,

        )

        if not result.satisfied:

            actions[requirement.item_key] = result.suggested_action or "provide"

    return actions

