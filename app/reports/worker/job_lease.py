"""Worker lease + heartbeat for report_jobs (P3-2)."""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DonorReportStatus, ReportJobStatus
from app.reports.models.report_job import ReportJob

logger = logging.getLogger("reports.worker.job_lease")

LEASE_SECONDS = float(os.getenv("ME_WORKER_LEASE_SECONDS", "120"))
REQUEUE_MAX = int(os.getenv("ME_WORKER_REQUEUE_MAX", "1"))


def worker_id() -> str:
    explicit = os.getenv("ME_WORKER_ID", "").strip()
    if explicit:
        return explicit
    return f"{socket.gethostname()}:{os.getpid()}"


def lease_claim_values(*, owner: str | None = None) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=LEASE_SECONDS)
    owner_id = owner or worker_id()
    return {
        "lease_owner": owner_id,
        "lease_expires_at": expires,
        "last_heartbeat_at": now,
    }


def touch_heartbeat(session: Session, job: ReportJob) -> None:
    """Refresh liveness markers for an in-flight job row."""
    if job.status != ReportJobStatus.RUNNING.value:
        return
    now = datetime.now(timezone.utc)
    job.last_heartbeat_at = now
    job.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
    if not job.lease_owner:
        job.lease_owner = worker_id()
    session.add(job)
    session.commit()


def touch_heartbeat_by_id(session: Session, job_id: UUID) -> None:
    job = session.get(ReportJob, job_id)
    if job is None:
        return
    touch_heartbeat(session, job)


def _append_requeue_trace(job: ReportJob, *, message: str) -> None:
    trace = dict(job.agent_trace_json or {})
    events = list(trace.get("requeue_events") or [])
    events.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "requeue_count": job.requeue_count,
        }
    )
    trace["requeue_events"] = events
    job.agent_trace_json = trace


def job_has_degraded_outcomes(session: Session, job: ReportJob) -> bool:
    """Degraded jobs must not auto-requeue (P3-2 policy)."""
    report = session.get(DonorReport, job.donor_report_id)
    if report is not None and report.status == DonorReportStatus.DEGRADED.value:
        return True

    stages = (job.agent_trace_json or {}).get("stages") or {}
    if not isinstance(stages, dict):
        return False
    for entry in stages.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("degraded"):
            return True
        if entry.get("degraded_documents") or entry.get("degraded_notes"):
            return True
    return False


def requeue_stale_job(
    session: Session,
    job: ReportJob,
    *,
    reason: str,
) -> bool:
    """Requeue a stale running job once; returns True if requeued."""
    if job.status != ReportJobStatus.RUNNING.value:
        return False
    if job_has_degraded_outcomes(session, job):
        return False
    if job.requeue_count >= REQUEUE_MAX:
        return False

    job.requeue_count = (job.requeue_count or 0) + 1
    job.status = ReportJobStatus.QUEUED.value
    job.lease_owner = None
    job.lease_expires_at = None
    _append_requeue_trace(job, message=reason)
    session.add(job)
    session.commit()
    logger.warning(
        "orphan_reaper requeued job_id=%s donor_report_id=%s stage=%s requeue_count=%s",
        job.id,
        job.donor_report_id,
        job.stage,
        job.requeue_count,
    )
    return True
