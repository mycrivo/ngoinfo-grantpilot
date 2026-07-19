"""Write-time conflict integrity: every conflict key must be materializable.

Pure normalizer used at the final KB persistence seam and for one-off repairs.
Never selects or invents a resolved value.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger("reports.knowledge.conflict_integrity")

PROVENANCE_ONLY_FOR = "provenance_only_for"


def _normalize_snapshot(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _values_match(left: Any, right: Any) -> bool:
    return _normalize_snapshot(left) == _normalize_snapshot(right)


def humanize_fact_key(fact_key: str) -> str:
    """Deterministic NGO-safe label from a dotted fact key (no internal jargon)."""
    parts = [p for p in str(fact_key or "").split(".") if p]
    if not parts:
        return "Project fact"
    words: list[str] = []
    for part in parts:
        token = part.replace("_", " ").strip()
        if not token:
            continue
        words.append(token[:1].upper() + token[1:] if len(token) > 1 else token.upper())
    return " — ".join(words) if words else "Project fact"


def _key_related_to_conflict(fact_key: str, conflict_key: str) -> bool:
    if not fact_key or not conflict_key or fact_key == conflict_key:
        return False
    return fact_key.startswith(conflict_key + "_") or fact_key.startswith(conflict_key + ".")


def _first_concrete_candidate(values: list[Any]) -> dict[str, Any] | None:
    for entry in values:
        if not isinstance(entry, dict):
            continue
        if _normalize_snapshot(entry.get("value")):
            return entry
    for entry in values:
        if isinstance(entry, dict):
            return entry
    return None


def _build_unresolved_canonical_stub(
    *,
    conflict_key: str,
    conflict: dict[str, Any],
) -> dict[str, Any]:
    values = [v for v in (conflict.get("values") or []) if isinstance(v, dict)]
    anchor = _first_concrete_candidate(values) or {}
    source_document_id = str(anchor.get("source_document_id") or "unresolved-conflict")
    source_label = str(anchor.get("source_label") or "Uploaded document")
    provenance = copy.deepcopy(anchor.get("provenance")) if isinstance(anchor.get("provenance"), dict) else {}
    if not provenance.get("excerpt"):
        provenance = {
            "excerpt": (
                "Unresolved conflict — candidate values are listed for owner review; "
                "no value has been selected."
            )
        }
    return {
        "value": None,
        "unit": None,
        "semantic_label": humanize_fact_key(conflict_key),
        "coverage": "single_source",
        "source_document_id": source_document_id,
        "source_label": source_label,
        "provenance": provenance,
        "interpretation_note": None,
        "verification_status": "unverified",
        "confirmed": False,
        "confirmed_at": None,
        "confirmed_by_user": False,
    }


def _mark_exact_match_siblings(
    facts: dict[str, Any],
    *,
    conflict_key: str,
    conflict: dict[str, Any],
) -> list[str]:
    """Mark siblings provenance-only only on exact value+source match + key relationship.

    Failure direction: when correspondence is not exact and unambiguous, do not mark
    (prefer visible duplication over silent impoverishment).
    """
    values = [v for v in (conflict.get("values") or []) if isinstance(v, dict)]
    marked: list[str] = []
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        if not _key_related_to_conflict(fact_key, conflict_key):
            continue
        matching = [
            cand
            for cand in values
            if _values_match(fact.get("value"), cand.get("value"))
            and str(fact.get("source_document_id") or "")
            == str(cand.get("source_document_id") or "")
        ]
        if len(matching) != 1:
            continue
        fact[PROVENANCE_ONLY_FOR] = conflict_key
        marked.append(fact_key)
    return marked


def ensure_conflicts_materializable(
    kb: dict[str, Any],
    *,
    donor_report_id: str | None = None,
    emit_log: bool = True,
) -> dict[str, Any]:
    """Ensure every conflict has a materializable facts entry; mark exact-match siblings.

    Mutates and returns ``kb``. Never sets resolved_value. Never invents a concrete value.
    """
    conflicts = kb.get("conflicts")
    if not isinstance(conflicts, list):
        return kb

    facts = kb.get("facts")
    if not isinstance(facts, dict):
        facts = {}
        kb["facts"] = facts

    repairs: list[dict[str, Any]] = []
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        raw_key = conflict.get("fact_key")
        # R4/F5 + DF-2: None, blank, or whitespace-only keys fail closed — never skip silently.
        if raw_key is None or not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(
                f"conflict integrity failed: blank fact_key {raw_key!r} is not materializable"
            )
        conflict_key = raw_key
        created_stub = False
        existing = facts.get(conflict_key)
        if not isinstance(existing, dict):
            facts[conflict_key] = _build_unresolved_canonical_stub(
                conflict_key=conflict_key,
                conflict=conflict,
            )
            created_stub = True

        marked = _mark_exact_match_siblings(
            facts,
            conflict_key=conflict_key,
            conflict=conflict,
        )
        if created_stub or marked:
            repairs.append(
                {
                    "conflict_key": conflict_key,
                    "created_canonical_stub": created_stub,
                    "provenance_only_fact_keys": marked,
                }
            )

    # Post-condition: every conflict key materializable
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        raw_key = conflict.get("fact_key")
        if raw_key is None or not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(
                f"conflict integrity failed: blank fact_key {raw_key!r} is not materializable"
            )
        if not isinstance(facts.get(raw_key), dict):
            raise ValueError(
                f"conflict integrity failed: fact_key {raw_key!r} has no materializable fact entry"
            )

    if repairs:
        events = kb.setdefault("agent_trace", {})
        if not isinstance(events, dict):
            events = {}
            kb["agent_trace"] = events
        integrity_events = events.setdefault("conflict_integrity_repairs", [])
        if not isinstance(integrity_events, list):
            integrity_events = []
            events["conflict_integrity_repairs"] = integrity_events
        for repair in repairs:
            integrity_events.append(
                {
                    "donor_report_id": donor_report_id,
                    **repair,
                }
            )
            if emit_log:
                logger.warning(
                    "conflict_integrity_orphan_repaired donor_report_id=%s conflict_key=%s "
                    "created_canonical_stub=%s provenance_only_fact_keys=%s",
                    donor_report_id,
                    repair["conflict_key"],
                    repair["created_canonical_stub"],
                    repair["provenance_only_fact_keys"],
                )

    return kb


def is_provenance_only_fact(fact: dict[str, Any]) -> bool:
    marker = fact.get(PROVENANCE_ONLY_FOR)
    return isinstance(marker, str) and bool(marker.strip())


def filter_exportable_facts(facts: dict[str, Any] | None) -> dict[str, Any]:
    """Facts eligible for DOCX table binding — excludes provenance-only siblings."""
    out: dict[str, Any] = {}
    for key, value in dict(facts or {}).items():
        if isinstance(value, dict) and not is_provenance_only_fact(value):
            out[key] = value
    return out
