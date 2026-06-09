"""Gate 1 — persist human-confirmed knowledge bank and unlock stamp."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.knowledge.confirmed_kb import (
    count_unverified_excluded,
    effective_verification_status,
)
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    validate_gate1_confirm_payload,
)
from app.reports.services.report_access import get_owned_donor_report

logger = logging.getLogger("reports.services.gate1_confirmation")


@dataclass(frozen=True)
class Gate1PromotionOutcome:
    promoted_fact_keys: list[str]
    rejected_promotions: list[dict[str, Any]]


def re_enqueue_gate1_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    """Re-queue the awaiting Gate 1 job after human confirmation (deterministic pick)."""
    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.GAP.value,
        )
        .order_by(
            ReportJob.started_at.desc().nullslast(),
            ReportJob.id.desc(),
        )
        .all()
    )
    if not candidates:
        return None
    job = candidates[0]
    job.status = ReportJobStatus.QUEUED.value
    db.add(job)
    logger.info(
        "gate1_re_enqueue donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


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


def _snapshot_matches(fact_value: Any, snapshot: Any) -> bool:
    return _normalize_snapshot(fact_value) == _normalize_snapshot(snapshot)


def apply_gate1_fact_promotions(
    facts: dict[str, Any],
    promote_fact_keys: list[dict[str, Any]],
    *,
    confirmed_at_iso: str,
) -> Gate1PromotionOutcome:
    """Promote unverified facts after per-fact snapshot validation."""
    promoted: list[str] = []
    rejected: list[dict[str, Any]] = []
    for entry in promote_fact_keys:
        fact_key = entry.get("fact_key")
        snapshot = entry.get("confirmed_value_snapshot")
        if not fact_key or not str(fact_key).strip():
            rejected.append({"fact_key": fact_key, "reason": "missing fact_key"})
            continue
        fact = facts.get(str(fact_key))
        if not isinstance(fact, dict):
            rejected.append({"fact_key": fact_key, "reason": "unknown fact_key"})
            continue
        if effective_verification_status(fact) != "unverified":
            rejected.append(
                {"fact_key": fact_key, "reason": "fact is not unverified — no promotion needed"}
            )
            continue
        if not _snapshot_matches(fact.get("value"), snapshot):
            rejected.append({"fact_key": fact_key, "reason": "value snapshot mismatch"})
            continue
        fact["confirmed_by_user"] = True
        fact["confirmed"] = True
        fact["confirmed_at"] = confirmed_at_iso
        promoted.append(str(fact_key))
    return Gate1PromotionOutcome(
        promoted_fact_keys=promoted,
        rejected_promotions=rejected,
    )


def promote_gate1_facts(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    promote_fact_keys: list[dict[str, Any]],
    cluster_id: str | None = None,
) -> tuple[dict[str, Any], Gate1PromotionOutcome]:
    """Batch-promote unverified facts from one reviewed cluster (no gate stamp)."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    kb = dict(report.knowledge_bank_json or {})
    facts = dict(kb.get("facts") or {})
    confirmed_at_iso = datetime.now(timezone.utc).isoformat()
    outcome = apply_gate1_fact_promotions(
        facts,
        promote_fact_keys,
        confirmed_at_iso=confirmed_at_iso,
    )
    kb["facts"] = facts
    report.knowledge_bank_json = kb
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(
        "gate1_promote donor_report_id=%s user_id=%s promoted=%d rejected=%d cluster_id=%s",
        donor_report_id,
        user_id,
        len(outcome.promoted_fact_keys),
        len(outcome.rejected_promotions),
        cluster_id,
    )
    return report.knowledge_bank_json, outcome


def confirm_gate1(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    knowledge_bank_json: dict[str, Any],
    promote_fact_keys: list[dict[str, Any]] | None = None,
    cluster_id: str | None = None,
) -> tuple[dict[str, Any], Gate1PromotionOutcome]:
    """Set gate1_confirmed_at; optionally promote one cluster batch — no bulk rubber-stamp."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    payload = dict(knowledge_bank_json)
    payload.pop("gate1_confirmed_at", None)

    validation_errors = validate_gate1_confirm_payload(payload)
    if validation_errors:
        raise DomainError(
            error_code="GATE1_VALIDATION_FAILED",
            message="Knowledge bank failed Gate 1 validation",
            status_code=422,
            details={"errors": validation_errors},
        )

    confirmed_at = datetime.now(timezone.utc)
    confirmed_at_iso = confirmed_at.isoformat()
    facts = payload.get("facts") or {}
    if not isinstance(facts, dict):
        facts = {}
        payload["facts"] = facts

    promotion = apply_gate1_fact_promotions(
        facts,
        promote_fact_keys or [],
        confirmed_at_iso=confirmed_at_iso,
    )

    payload["gate1_confirmed_at"] = confirmed_at_iso
    report.knowledge_bank_json = payload
    db.add(report)
    re_enqueue_gate1_job(db, donor_report_id=donor_report_id)
    db.commit()
    db.refresh(report)

    logger.info(
        "gate1_confirmed donor_report_id=%s user_id=%s promoted=%d excluded_unverified=%d cluster_id=%s",
        donor_report_id,
        user_id,
        len(promotion.promoted_fact_keys),
        count_unverified_excluded(report.knowledge_bank_json or {}),
        cluster_id,
    )
    return report.knowledge_bank_json, promotion
