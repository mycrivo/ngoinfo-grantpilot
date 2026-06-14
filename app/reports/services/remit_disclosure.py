"""Remit-scoped, disclosure-complete gap statements (Package A, adjustment 1).

Two rules, reconciled so they can never collide into a silent omission OR a false
disclaimer:

- OWNER-ONLY EMISSION: a section discloses absence ONLY for items it OWNS
  (TemplateRequirement.section_key == section_key). This stops a narrative section
  (e.g. project_story, empty financial remit) from disclaiming the budget.
- PRESENT-ELSEWHERE SUPPRESSION: an item that is genuinely present in the report is
  never disclaimed. Presence uses the SAME notion the data-table renderer uses (KB
  facts under the table's data-source namespace), so a populated budget table is never
  contradicted by a "not available" line.

Together: every genuinely-absent required item is disclosed by exactly its owning
section — never orphaned (disclosure-completeness), never falsely disclaimed.
"""

from __future__ import annotations

from typing import Any

from app.reports.gap.requirement_satisfaction import evaluate_requirement_satisfaction
from app.reports.gap.template_requirements import (
    TemplateRequirement,
    enumerate_template_requirements,
)
from app.reports.knowledge.confirmed_kb import is_fact_citable
from app.reports.services.ngo_text_redaction import (
    humanize_identifier,
    redact_internal_identifiers,
)
from app.reports.services.report_inputs_builder import _namespace_root

# Table data_source -> KB namespace root the renderer fills the table from.
_TABLE_DATA_SOURCE_ROOTS: dict[str, str] = {
    "indicators": "indicators",
    "financials": "financials",
}


def _table_data_source_root(section: dict[str, Any], table_key: str) -> str | None:
    for table in section.get("required_tables") or []:
        if isinstance(table, dict) and table.get("table_key") == table_key:
            return _TABLE_DATA_SOURCE_ROOTS.get(str(table.get("data_source") or ""))
    return None


def _namespace_has_citable_fact(
    facts: dict[str, Any], root: str, gate1_confirmed_at: str | None
) -> bool:
    for key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if _namespace_root(str(key)) == root and is_fact_citable(
            fact, gate1_confirmed_at=gate1_confirmed_at
        ):
            return True
    return False


def _requirement_present(
    requirement: TemplateRequirement,
    section: dict[str, Any],
    *,
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
    gate1_confirmed_at: str | None,
    all_requirements: list[TemplateRequirement],
) -> bool:
    """True when the item is present/renderable in the report (suppress disclaimer)."""
    if requirement.required_item_type == "table":
        root = _table_data_source_root(section, requirement.required_item_ref)
        if root and _namespace_has_citable_fact(facts, root, gate1_confirmed_at):
            return True
    return evaluate_requirement_satisfaction(
        requirement,
        facts=facts,
        gap_answers=gap_answers,
        all_requirements=all_requirements,
        gate1_confirmed_at=gate1_confirmed_at,
        purpose="synthesis",
    ).satisfied


def owned_absent_requirements(
    section: dict[str, Any],
    knowledge_bank_json: dict[str, Any],
    *,
    report_context: dict[str, Any] | None = None,
) -> list[str]:
    """Human-readable names of this section's OWN required items that are genuinely
    absent from the report (present items suppressed). Identifier-free."""
    kb = knowledge_bank_json or {}
    facts = kb.get("facts") or {}
    gap_answers = kb.get("gap_answers") or {}
    gate1 = kb.get("gate1_confirmed_at")
    ctx = report_context or {"report_type": "annual"}
    requirements = enumerate_template_requirements([section], report_context=ctx)
    names: list[str] = []
    seen: set[str] = set()
    for requirement in requirements:
        if requirement.required_item_type == "section":
            continue
        if _requirement_present(
            requirement,
            section,
            facts=facts,
            gap_answers=gap_answers,
            gate1_confirmed_at=gate1,
            all_requirements=requirements,
        ):
            continue
        name = humanize_identifier(requirement.required_item_ref)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def build_owned_absent_disclosure(
    section: dict[str, Any],
    knowledge_bank_json: dict[str, Any],
    *,
    report_context: dict[str, Any] | None = None,
) -> str | None:
    """Deterministic, remit-scoped disclosure line for this section, or None.

    Guarantees a genuinely-absent OWNED item is disclosed in the output regardless of
    what the synthesis model wrote.
    """
    names = owned_absent_requirements(
        section, knowledge_bank_json, report_context=report_context
    )
    if not names:
        return None
    label = str(section.get("label") or section.get("section_key") or "this section").strip()
    if len(names) == 1:
        phrase = names[0]
    else:
        phrase = ", ".join(names[:-1]) + f", and {names[-1]}"
    statement = (
        f"The submitted records did not include {phrase} for \"{label}\". "
        f"This has been disclosed as a gap rather than estimated."
    )
    return redact_internal_identifiers(statement)
