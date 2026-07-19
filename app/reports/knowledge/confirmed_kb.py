"""Single source of truth for KB citability (P1-3 degrade fence).

Citability depends only on explicit ``verification_status`` plus per-fact
``confirmed_by_user`` promotion — never key prefixes or interpretation_note text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.reports.gap.gap_answer import is_gap_answer_resolved

FactVerificationStatus = Literal["reconciled", "unverified"]


@dataclass(frozen=True)
class ConfirmedKBView:
    facts: dict[str, Any]
    gap_answers: dict[str, Any]
    conflicts_resolved: list[dict[str, Any]]
    gate1_confirmed_at: str | None
    gate2_confirmed_at: str | None


def effective_verification_status(fact: dict[str, Any]) -> FactVerificationStatus:
    """Explicit marker only; missing field is fail-closed unverified."""
    status = fact.get("verification_status")
    if status == "reconciled":
        return "reconciled"
    return "unverified"


def is_fact_citable(fact: dict[str, Any], *, gate1_confirmed_at: str | None) -> bool:
    if not gate1_confirmed_at:
        return False
    # D-060: conflict-sibling provenance must never flow as an independent claim.
    provenance_only_for = fact.get("provenance_only_for")
    if isinstance(provenance_only_for, str) and provenance_only_for.strip():
        return False
    status = effective_verification_status(fact)
    if status == "reconciled":
        return True
    if status == "unverified" and fact.get("confirmed_by_user") is True:
        return True
    return False


def is_gap_answer_citable(entry: dict[str, Any]) -> bool:
    return is_gap_answer_resolved(entry)


def filter_citable_facts(knowledge_bank_json: dict[str, Any]) -> dict[str, Any]:
    gate1_at = knowledge_bank_json.get("gate1_confirmed_at")
    facts = knowledge_bank_json.get("facts") or {}
    return {
        key: value
        for key, value in facts.items()
        if isinstance(value, dict) and is_fact_citable(value, gate1_confirmed_at=gate1_at)
    }


def filter_citable_gap_answers(knowledge_bank_json: dict[str, Any]) -> dict[str, Any]:
    gap_answers = knowledge_bank_json.get("gap_answers") or {}
    return {
        key: value
        for key, value in gap_answers.items()
        if isinstance(value, dict) and is_gap_answer_citable(value)
    }


def count_unverified_excluded(knowledge_bank_json: dict[str, Any]) -> int:
    """Unverified facts not yet promoted — excluded from synthesis/critic."""
    gate1_at = knowledge_bank_json.get("gate1_confirmed_at")
    if not gate1_at:
        return 0
    excluded = 0
    for fact in (knowledge_bank_json.get("facts") or {}).values():
        if not isinstance(fact, dict):
            continue
        if effective_verification_status(fact) == "unverified" and not fact.get(
            "confirmed_by_user"
        ):
            excluded += 1
    return excluded


def build_confirmed_kb_view(knowledge_bank_json: dict[str, Any]) -> ConfirmedKBView:
    kb = knowledge_bank_json or {}
    conflicts = kb.get("conflicts") or []
    resolved = [
        item
        for item in conflicts
        if isinstance(item, dict) and item.get("resolved_value") is not None
    ]
    return ConfirmedKBView(
        facts=filter_citable_facts(kb),
        gap_answers=filter_citable_gap_answers(kb),
        conflicts_resolved=resolved,
        gate1_confirmed_at=kb.get("gate1_confirmed_at"),
        gate2_confirmed_at=kb.get("gate2_confirmed_at"),
    )


def is_evidence_ref_citable(ref: str, knowledge_bank_json: dict[str, Any]) -> bool:
    gate1_at = knowledge_bank_json.get("gate1_confirmed_at")
    if ref.startswith("fact:"):
        key = ref.removeprefix("fact:")
        fact = (knowledge_bank_json.get("facts") or {}).get(key)
        return isinstance(fact, dict) and is_fact_citable(fact, gate1_confirmed_at=gate1_at)
    if ref.startswith("gap:"):
        key = ref.removeprefix("gap:")
        entry = (knowledge_bank_json.get("gap_answers") or {}).get(key)
        return isinstance(entry, dict) and is_gap_answer_citable(entry)
    return False


def non_citable_evidence_refs(
    evidence_used: list[str],
    knowledge_bank_json: dict[str, Any],
) -> list[str]:
    """Refs in evidence_used that fail citability — for critic fence flags."""
    blocked: list[str] = []
    for ref in evidence_used:
        if not isinstance(ref, str):
            continue
        if ref.startswith(("fact:", "gap:")) and not is_evidence_ref_citable(
            ref, knowledge_bank_json
        ):
            blocked.append(ref)
    return blocked
