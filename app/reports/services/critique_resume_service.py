"""Resume critique stage after synthesis park (P0-2)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.services.gate_preconditions import require_gate2_confirmed
from app.reports.services.report_access import get_owned_donor_report

logger = logging.getLogger("reports.services.critique_resume")


def re_enqueue_critique_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    """Re-queue the awaiting critique job so the worker runs F2."""
    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.CRITIQUE.value,
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
        "critique_re_enqueue donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


def _latest_critique_trace(db: Session, donor_report_id: uuid.UUID) -> dict:
    jobs = (
        db.query(ReportJob)
        .filter(ReportJob.donor_report_id == donor_report_id)
        .order_by(ReportJob.started_at.desc().nullslast(), ReportJob.id.desc())
        .all()
    )
    for job in jobs:
        critique = (job.agent_trace_json or {}).get("stages", {}).get("critique")
        if isinstance(critique, dict):
            return critique
    return {}


def resume_critique_for_report(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ReportJob:
    """Validate preconditions and re-queue critique after synthesis park."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    require_gate2_confirmed(report.knowledge_bank_json)

    content_json = report.content_json or {}
    if not content_json.get("sections"):
        raise DomainError(
            error_code="CRITIQUE_NO_CONTENT",
            message="Report sections must exist before running the critic",
            status_code=409,
        )

    critique_trace = _latest_critique_trace(db, donor_report_id)
    if critique_trace.get("action") == "critique_completed":
        raise DomainError(
            error_code="CRITIQUE_ALREADY_COMPLETED",
            message="Fact-safety critic has already completed for this report",
            status_code=409,
        )

    job = re_enqueue_critique_job(db, donor_report_id=donor_report_id)
    if job is None:
        raise DomainError(
            error_code="CRITIQUE_NOT_PARKED",
            message="No critique job is awaiting human resume for this report",
            status_code=409,
        )

    db.commit()
    db.refresh(job)
    return job
