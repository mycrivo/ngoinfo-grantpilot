from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.worker.job_failure import (
    FAILURE_EVENT_EXCEPTION,
    FAILURE_EVENT_TIMEOUT,
    mark_job_failed_by_id,
)
from app.reports.worker.orphan_reaper import reap_stale_running_jobs
from app.reports.worker.run_pipeline import run_pipeline

logger = logging.getLogger("reports.worker")

POLL_INTERVAL_SECONDS = 5
JOB_TIMEOUT_SECONDS = float(os.getenv("ME_WORKER_JOB_TIMEOUT_SECONDS", "3600"))


def claim_next_job(session: Session) -> ReportJob | None:
    """Atomically claim one queued job row (PostgreSQL: SKIP LOCKED)."""
    pick = (
        select(ReportJob.id)
        .where(ReportJob.status == ReportJobStatus.QUEUED.value)
        .order_by(ReportJob.started_at.asc().nullsfirst())
        .limit(1)
    )
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        pick = pick.with_for_update(skip_locked=True)
    else:
        pick = pick.with_for_update()

    job_id = session.scalars(pick).first()
    if job_id is None:
        session.rollback()
        return None

    now = datetime.now(timezone.utc)
    claimed_id = session.scalar(
        update(ReportJob)
        .where(
            ReportJob.id == job_id,
            ReportJob.status == ReportJobStatus.QUEUED.value,
        )
        .values(
            status=ReportJobStatus.RUNNING.value,
            started_at=func.coalesce(ReportJob.started_at, now),
        )
        .returning(ReportJob.id)
    )
    if claimed_id is None:
        session.rollback()
        return None

    session.commit()
    return session.get(ReportJob, claimed_id)


def _execute_job_with_timeout(job_id: UUID, timeout_seconds: float) -> None:
    """Run pipeline in a worker thread with a wall-clock backstop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_pipeline, job_id)
        try:
            future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            mark_job_failed_by_id(
                job_id,
                error=f"Job exceeded {timeout_seconds}s wall-clock limit",
                event=FAILURE_EVENT_TIMEOUT,
            )
            raise TimeoutError(str(exc)) from exc


def poll_once(*, job_timeout_seconds: float | None = None) -> int:
    """Claim and process one queued job if present. Returns count processed."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")

    timeout = (
        job_timeout_seconds if job_timeout_seconds is not None else JOB_TIMEOUT_SECONDS
    )

    session = SessionLocal()
    job_id: UUID | None = None
    try:
        job = claim_next_job(session)
        if job is None:
            return 0
        job_id = job.id
    finally:
        session.close()

    try:
        _execute_job_with_timeout(job_id, timeout)
    except Exception as exc:
        logger.exception("Job processing failed job_id=%s", job_id)
        if not isinstance(exc, TimeoutError):
            mark_job_failed_by_id(
                job_id,
                error=str(exc),
                event=FAILURE_EVENT_EXCEPTION,
            )

    return 1


def _reap_stale_jobs_once() -> int:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")

    session = SessionLocal()
    try:
        return reap_stale_running_jobs(session)
    finally:
        session.close()


def run_forever() -> None:
    logger.info("M&E worker started")
    reaped = _reap_stale_jobs_once()
    if reaped:
        logger.warning("Startup orphan reaper failed %d stale running job(s)", reaped)
    while True:
        try:
            count = poll_once()
            if count == 0:
                reaped = _reap_stale_jobs_once()
                if reaped:
                    logger.warning(
                        "Idle-cycle orphan reaper failed %d stale running job(s)",
                        reaped,
                    )
                time.sleep(POLL_INTERVAL_SECONDS)
        except Exception:
            logger.exception("Worker poll cycle failed")
            time.sleep(POLL_INTERVAL_SECONDS)
