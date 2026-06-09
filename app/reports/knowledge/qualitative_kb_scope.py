"""Section-scoped + shared citable KB view for P1-2 qualitative critic.

Verification boundary: section-relevant facts + genuinely global prefixes + all
citable gap answers (not section-bound). NOT the full citable KB — prevents a
true-but-wrong-section claim from validating as supported elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.reports.knowledge.confirmed_kb import (
    build_confirmed_kb_view,
    filter_citable_facts,
    filter_citable_gap_answers,
)
from app.reports.services.report_inputs_builder import (
    _resolved_conflicts,
    subset_facts_for_section,
)


@dataclass(frozen=True)
class QualitativeKBView:
    facts: dict[str, Any]
    gap_answers: dict[str, Any]
    conflicts_resolved: list[dict[str, Any]]
    section_key: str


def build_qualitative_kb_view(
    knowledge_bank_json: dict[str, Any],
    *,
    section: dict[str, Any],
) -> QualitativeKBView:
    """Scoped facts (shared prefixes + section trim) + all citable gap answers."""
    kb = knowledge_bank_json or {}
    citable_facts = filter_citable_facts(kb)
    section_key = str(section.get("section_key") or "")
    return QualitativeKBView(
        facts=subset_facts_for_section(citable_facts, section),
        gap_answers=filter_citable_gap_answers(kb),
        conflicts_resolved=_resolved_conflicts(kb.get("conflicts") or []),
        section_key=section_key,
    )


def serialize_qualitative_kb_for_critic(view: QualitativeKBView) -> dict[str, Any]:
    """Compact KB payload for LLM qualitative verification."""
    facts_out: dict[str, Any] = {}
    for key, fact in (view.facts or {}).items():
        if not isinstance(fact, dict):
            continue
        prov = fact.get("provenance") or {}
        excerpt = prov.get("excerpt") if isinstance(prov, dict) else None
        facts_out[key] = {
            "value": fact.get("value"),
            "semantic_label": fact.get("semantic_label"),
            "excerpt": excerpt,
        }
    gaps_out: dict[str, Any] = {}
    for key, entry in (view.gap_answers or {}).items():
        if not isinstance(entry, dict):
            continue
        gaps_out[key] = {
            "answer_text": entry.get("answer_text"),
            "disposition": entry.get("disposition"),
        }
    return {
        "section_key": view.section_key,
        "facts": facts_out,
        "gap_answers": gaps_out,
        "conflicts_resolved": view.conflicts_resolved,
    }
