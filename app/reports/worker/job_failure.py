"""Terminal failure handling for report_jobs — worker seam only."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob

logger = logging.getLogger("reports.worker")

FAILURE_EVENT_EXCEPTION = "pipeline_exception"
FAILURE_EVENT_TIMEOUT = "pipeline_timeout"

_TERMINAL_STATUSES = frozenset(
    {
        ReportJobStatus.DONE.value,
        ReportJobStatus.FAILED.value,
    }
)


def append_failure_trace(job: ReportJob, *, event: str, message: str) -> None:
    trace = dict(job.agent_trace_json or {})
    trace["failure"] = {
        "event": event,
        "message": message,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    job.agent_trace_json = trace


def mark_job_failed(
    session: Session,
    job: ReportJob,
    *,
    error: str,
    event: str,
) -> bool:
    """Mark a job failed with error + trace. Returns True if status was updated."""
    if job.status in _TERMINAL_STATUSES:
        return False

    now = datetime.now(timezone.utc)
    job.status = ReportJobStatus.FAILED.value
    job.error = error
    job.finished_at = now
    append_failure_trace(job, event=event, message=error)
    session.add(job)
    session.commit()
    logger.warning(
        "report_job failed job_id=%s event=%s error=%s",
        job.id,
        event,
        error,
    )
    return True


def mark_job_failed_by_id(
    job_id: UUID,
    *,
    error: str,
    event: str,
) -> bool:
    """Fresh-session failure mark for timeout / outer-shell recovery."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")

    session = SessionLocal()
    try:
        job = session.get(ReportJob, job_id)
        if job is None:
            logger.warning("mark_job_failed_by_id: job not found job_id=%s", job_id)
            return False
        return mark_job_failed(session, job, error=error, event=event)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
