"""F-11 — unified wall-clock timeout semantics (worker + reaper alignment)."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.orm import Session

from app.reports.models.report_job import ReportJob
from app.reports.worker.job_failure import FAILURE_EVENT_TIMEOUT, mark_job_failed_by_id
from app.reports.worker.orphan_reaper import (
    _document_count,
    _visible_section_count,
    compute_stale_threshold_seconds,
)

JOB_WALL_CLOCK_CAP_SECONDS = float(os.getenv("ME_WORKER_JOB_TIMEOUT_SECONDS", "3600"))


def resolve_active_job_timeout_seconds(session: Session, job_id: UUID) -> float:
    """Stage-aware silence budget aligned with orphan reaper, capped by env."""
    job = session.get(ReportJob, job_id)
    if job is None:
        return JOB_WALL_CLOCK_CAP_SECONDS

    doc_count = _document_count(session, job)
    section_count = _visible_section_count(session, job)
    threshold = compute_stale_threshold_seconds(
        job,
        doc_count=doc_count,
        section_count=section_count,
    )
    return min(JOB_WALL_CLOCK_CAP_SECONDS, threshold)


def fail_job_wall_clock_exceeded(
    job_id: UUID,
    *,
    timeout_seconds: float,
    source: str,
) -> bool:
    """Shared terminal timeout path for worker thread backstop."""
    return mark_job_failed_by_id(
        job_id,
        error=(
            f"Job exceeded {timeout_seconds}s wall-clock limit "
            f"({source}; unified F-11 timeout)"
        ),
        event=FAILURE_EVENT_TIMEOUT,
    )
