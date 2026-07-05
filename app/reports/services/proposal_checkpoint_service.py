"""Proposal extraction blocking checkpoint — ack proceed or retry re-enqueue."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.services.report_access import get_owned_donor_report

logger = logging.getLogger("reports.services.proposal_checkpoint")

PROPOSAL_MISSING_CONTENT_KEYS = [
    "objectives",
    "activities",
    "indicators",
    "partners",
    "consultation",
]


def _extract_stage_trace(job: ReportJob) -> dict[str, Any]:
    stages = (job.agent_trace_json or {}).get("stages") or {}
    extract = stages.get("extract") or {}
    return dict(extract) if isinstance(extract, dict) else {}


def get_proposal_checkpoint(job: ReportJob) -> dict[str, Any] | None:
    checkpoint = _extract_stage_trace(job).get("proposal_checkpoint")
    return dict(checkpoint) if isinstance(checkpoint, dict) else None


def re_enqueue_proposal_checkpoint_retry(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
) -> ReportJob | None:
    """Re-queue an awaiting proposal checkpoint job for extract retry."""
    job = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.EXTRACT.value,
        )
        .order_by(
            ReportJob.started_at.desc().nullslast(),
            ReportJob.id.desc(),
        )
        .first()
    )
    if job is None or get_proposal_checkpoint(job) is None:
        return None

    extract_trace = _extract_stage_trace(job)
    extract_trace.pop("proposal_checkpoint", None)
    trace = dict(job.agent_trace_json or {})
    stages = dict(trace.get("stages") or {})
    stages[ReportJobStage.EXTRACT.value] = extract_trace
    trace["stages"] = stages
    job.agent_trace_json = trace
    job.status = ReportJobStatus.QUEUED.value
    job.error = None
    job.finished_at = None
    db.add(job)
    logger.info(
        "proposal_checkpoint_retry_re_enqueue donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


def ack_proposal_checkpoint_proceed(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ReportJob:
    get_owned_donor_report(db, donor_report_id=donor_report_id, user_id=user_id)

    job = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.EXTRACT.value,
        )
        .order_by(
            ReportJob.started_at.desc().nullslast(),
            ReportJob.id.desc(),
        )
        .first()
    )
    if job is None:
        raise DomainError(
            error_code="CHECKPOINT_NOT_FOUND",
            message="No proposal extraction checkpoint is waiting for this report",
            status_code=404,
        )

    checkpoint = get_proposal_checkpoint(job)
    if checkpoint is None:
        raise DomainError(
            error_code="CHECKPOINT_NOT_FOUND",
            message="No proposal extraction checkpoint is waiting for this report",
            status_code=404,
        )
    if checkpoint.get("acknowledged"):
        raise DomainError(
            error_code="CHECKPOINT_ALREADY_ACKED",
            message="Proposal checkpoint was already acknowledged",
            status_code=409,
        )

    now = datetime.now(timezone.utc).isoformat()
    checkpoint = {
        **checkpoint,
        "acknowledged": True,
        "ack_action": "proceed_with_gap",
        "acknowledged_at": now,
    }
    extract_trace = _extract_stage_trace(job)
    extract_trace["proposal_checkpoint"] = checkpoint
    trace = dict(job.agent_trace_json or {})
    stages = dict(trace.get("stages") or {})
    stages[ReportJobStage.EXTRACT.value] = extract_trace
    trace["stages"] = stages
    job.agent_trace_json = trace
    job.stage = ReportJobStage.RECONCILE.value
    job.status = ReportJobStatus.QUEUED.value
    job.error = None
    job.finished_at = None
    db.add(job)
    logger.info(
        "proposal_checkpoint_proceed_ack donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job
