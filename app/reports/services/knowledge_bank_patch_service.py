"""Gate 1 — PATCH knowledge bank (conflict resolution + fact edits before confirm)."""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.knowledge.confirmed_kb import effective_verification_status
from app.reports.schemas.knowledge_bank_patch import PatchKnowledgeBankRequest
from app.reports.services.donor_report_lifecycle_service import get_knowledge_bank
from app.reports.services.report_access import get_owned_donor_report

logger = logging.getLogger("reports.services.knowledge_bank_patch")

OWNER_ATTESTED_SOURCE_ID = "owner-attested"
USER_PROVIDED_SOURCE_ID = "user-provided"


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


def _match_conflict_value(
    values: list[dict[str, Any]], resolved_value: Any
) -> dict[str, Any] | None:
    for entry in values:
        if isinstance(entry, dict) and _values_match(entry.get("value"), resolved_value):
            return entry
    return None


def _require_patchable_kb(kb: dict[str, Any]) -> None:
    if kb.get("gate1_confirmed_at"):
        raise DomainError(
            error_code="GATE_NOT_SATISFIED",
            message="Knowledge bank cannot be edited after Gate 1 confirmation",
            status_code=409,
        )
    if not kb.get("reconciler_agent"):
        raise DomainError(
            error_code="GATE_NOT_SATISFIED",
            message="Knowledge bank must be reconciled before Gate 1 edits",
            status_code=409,
        )


def _find_conflict(conflicts: list[Any], fact_key: str) -> dict[str, Any] | None:
    for item in conflicts:
        if isinstance(item, dict) and item.get("fact_key") == fact_key:
            return item
    return None


def _require_concrete_resolved_value(resolved_value: Any, *, fact_key: str) -> None:
    """D-059: null/blank resolved_value is never acceptable on PATCH."""
    if resolved_value is None or (
        isinstance(resolved_value, str) and not resolved_value.strip()
    ):
        raise DomainError(
            error_code="KB_CONFLICT_RESOLUTION_VALUE_REQUIRED",
            message="Conflict resolution requires a concrete resolved_value",
            status_code=422,
            details={"fact_key": fact_key},
        )


def materialize_conflict_resolution(
    kb: dict[str, Any],
    *,
    fact_key: str,
    resolved_value: Any,
    resolved_at_iso: str,
) -> None:
    """Atomically set conflict resolution and materialize onto facts[fact_key]."""
    _require_concrete_resolved_value(resolved_value, fact_key=fact_key)

    conflicts = kb.get("conflicts")
    if not isinstance(conflicts, list):
        conflicts = []
        kb["conflicts"] = conflicts

    conflict = _find_conflict(conflicts, fact_key)
    if conflict is None:
        raise DomainError(
            error_code="KB_PATCH_VALIDATION_FAILED",
            message=f"Unknown conflict fact_key {fact_key!r}",
            status_code=422,
            details={"fact_key": fact_key},
        )

    facts = kb.get("facts")
    if not isinstance(facts, dict):
        raise DomainError(
            error_code="KB_PATCH_VALIDATION_FAILED",
            message=f"Conflict fact_key {fact_key!r} has no matching fact entry",
            status_code=422,
            details={"fact_key": fact_key},
        )

    fact = facts.get(fact_key)
    if not isinstance(fact, dict):
        raise DomainError(
            error_code="KB_PATCH_VALIDATION_FAILED",
            message=f"Conflict fact_key {fact_key!r} has no matching fact entry",
            status_code=422,
            details={"fact_key": fact_key},
        )

    conflict["resolved_value"] = resolved_value
    conflict["resolved_at"] = resolved_at_iso

    values = conflict.get("values") or []
    winner = _match_conflict_value(
        [v for v in values if isinstance(v, dict)],
        resolved_value,
    )
    if winner:
        fact["value"] = winner.get("value", resolved_value)
        if "unit" in winner:
            fact["unit"] = winner.get("unit")
        fact["source_document_id"] = winner.get("source_document_id")
        fact["source_label"] = winner.get("source_label")
        fact["provenance"] = copy.deepcopy(winner.get("provenance") or {"excerpt": str(resolved_value)})
    else:
        fact["value"] = resolved_value
        fact["source_document_id"] = OWNER_ATTESTED_SOURCE_ID
        fact["source_label"] = "Owner attestation (Gate 1)"
        fact["provenance"] = {
            "excerpt": f"Owner-entered value at Gate 1: {resolved_value}",
        }
        fact["confirmed_by_user"] = True

    # Unresolved stub becomes human-confirmed after an owner choice (citability fence).
    fact["confirmed"] = True
    fact["confirmed_at"] = resolved_at_iso
    fact["confirmed_by_user"] = True
    fact.pop("provenance_only_for", None)


def _build_user_provided_fact(*, value: Any, fact_key: str) -> dict[str, Any]:
    label = fact_key.removeprefix("user_fact_") or "User-provided fact"
    return {
        "value": value,
        "unit": None,
        "semantic_label": label,
        "coverage": "single_source",
        "source_document_id": USER_PROVIDED_SOURCE_ID,
        "source_label": "User-provided",
        "provenance": {"excerpt": "User-provided fact"},
        "interpretation_note": None,
        "verification_status": "unverified",
        "confirmed": True,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "confirmed_by_user": True,
    }


def apply_fact_patches(
    kb: dict[str, Any],
    facts_patch: dict[str, dict[str, Any]],
    *,
    patched_at_iso: str,
) -> None:
    facts = kb.get("facts")
    if not isinstance(facts, dict):
        facts = {}
        kb["facts"] = facts

    for fact_key, patch in facts_patch.items():
        if not fact_key or not str(fact_key).strip():
            raise DomainError(
                error_code="KB_PATCH_VALIDATION_FAILED",
                message="Fact patch requires a non-empty fact_key",
                status_code=422,
            )

        existing = facts.get(fact_key)
        if isinstance(existing, dict):
            existing["value"] = patch.get("value")
            if patch.get("confirmed"):
                existing["confirmed"] = True
                existing["confirmed_at"] = patched_at_iso
                if effective_verification_status(existing) == "unverified":
                    existing["confirmed_by_user"] = True
        else:
            value = patch.get("value")
            new_fact = _build_user_provided_fact(value=value, fact_key=fact_key)
            if patch.get("confirmed"):
                new_fact["confirmed_at"] = patched_at_iso
            facts[fact_key] = new_fact


def apply_conflict_resolutions(
    kb: dict[str, Any],
    resolutions: list[dict[str, Any]],
    *,
    resolved_at_iso: str,
) -> None:
    for entry in resolutions:
        fact_key = entry.get("fact_key")
        if not fact_key or not str(fact_key).strip():
            raise DomainError(
                error_code="KB_PATCH_VALIDATION_FAILED",
                message="Conflict resolution requires a non-empty fact_key",
                status_code=422,
            )
        materialize_conflict_resolution(
            kb,
            fact_key=str(fact_key),
            resolved_value=entry.get("resolved_value"),
            resolved_at_iso=resolved_at_iso,
        )


def patch_knowledge_bank(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    body: PatchKnowledgeBankRequest,
) -> dict[str, Any]:
    if body.confirm_gate1:
        raise DomainError(
            error_code="USE_GATE1_CONFIRM_ENDPOINT",
            message="Gate 1 confirmation must use POST /knowledge-bank/gate1/confirm",
            status_code=422,
        )

    has_facts = bool(body.facts)
    has_conflicts = bool(body.conflict_resolutions)
    if not has_facts and not has_conflicts:
        raise DomainError(
            error_code="KB_PATCH_VALIDATION_FAILED",
            message="PATCH requires facts and/or conflict_resolutions",
            status_code=422,
        )

    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    kb = copy.deepcopy(report.knowledge_bank_json or {})
    _require_patchable_kb(kb)

    patched_at_iso = datetime.now(timezone.utc).isoformat()

    # Conflicts first: fact patches in the same request must not overwrite resolution.
    if body.conflict_resolutions:
        apply_conflict_resolutions(
            kb,
            [entry.model_dump() for entry in body.conflict_resolutions],
            resolved_at_iso=patched_at_iso,
        )

    if body.facts:
        apply_fact_patches(
            kb,
            {key: patch.model_dump() for key, patch in body.facts.items()},
            patched_at_iso=patched_at_iso,
        )

    report.knowledge_bank_json = kb
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        "knowledge_bank_patch donor_report_id=%s user_id=%s facts=%d conflicts=%d",
        donor_report_id,
        user_id,
        len(body.facts or {}),
        len(body.conflict_resolutions or []),
    )

    return get_knowledge_bank(
        db,
        donor_report_id=donor_report_id,
        user_id=user_id,
    )
