"""Gate 1 — persist human-confirmed knowledge bank and unlock stamp."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    validate_gate1_confirm_payload,
)
from app.reports.services.report_access import get_owned_donor_report

logger = logging.getLogger("reports.services.gate1_confirmation")


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


def confirm_gate1(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    knowledge_bank_json: dict[str, Any],
) -> dict[str, Any]:
    """Overwrite knowledge_bank_json with human final state and set gate1_confirmed_at."""
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
    for fact in payload.get("facts", {}).values():
        if isinstance(fact, dict):
            fact["confirmed"] = True
            fact["confirmed_by_user"] = True
            fact["confirmed_at"] = confirmed_at_iso
    payload["gate1_confirmed_at"] = confirmed_at_iso
    report.knowledge_bank_json = payload
    db.add(report)
    re_enqueue_gate1_job(db, donor_report_id=donor_report_id)
    db.commit()
    db.refresh(report)

    logger.info(
        "gate1_confirmed donor_report_id=%s user_id=%s",
        donor_report_id,
        user_id,
    )
    return report.knowledge_bank_json
