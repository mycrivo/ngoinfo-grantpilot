from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.orchestration.dispatch import StageFailure
from app.reports.orchestration.pipeline import OrchestrationContext, run_orchestrated_walk_sync
from app.reports.worker.job_failure import (
    FAILURE_EVENT_EXCEPTION,
    mark_job_failed,
)

logger = logging.getLogger("reports.worker")


def run_pipeline(
    job_id: UUID,
    db: Session | None = None,
    *,
    orchestration_ctx: OrchestrationContext | None = None,
) -> None:
    """Execute the orchestrated pipeline for one claimed job row."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        job = session.get(ReportJob, job_id)
        if job is None:
            logger.warning("run_pipeline: no report_job for job_id=%s", job_id)
            return

        logger.info(
            "run_pipeline start job_id=%s donor_report_id=%s stage=%s status=%s",
            job.id,
            job.donor_report_id,
            job.stage,
            job.status,
        )

        if job.status == ReportJobStatus.QUEUED.value:
            now = datetime.now(timezone.utc)
            job.status = ReportJobStatus.RUNNING.value
            job.started_at = job.started_at or now
            session.add(job)
            session.commit()

        session.refresh(job)
        if job.status == ReportJobStatus.FAILED.value:
            return

        try:
            run_orchestrated_walk_sync(job, session, ctx=orchestration_ctx)
        except StageFailure as exc:
            session.rollback()
            job = session.get(ReportJob, job_id)
            if job is not None:
                trace = dict(job.agent_trace_json or {})
                trace["failed_stage"] = exc.stage
                job.agent_trace_json = trace
                mark_job_failed(
                    session,
                    job,
                    error=f"{exc.stage}: {exc.message}",
                    event=FAILURE_EVENT_EXCEPTION,
                )
            raise
        except Exception as exc:
            session.rollback()
            job = session.get(ReportJob, job_id)
            if job is not None:
                mark_job_failed(
                    session,
                    job,
                    error=str(exc),
                    event=FAILURE_EVENT_EXCEPTION,
                )
            raise

        logger.info(
            "run_pipeline complete job_id=%s stage=%s status=%s",
            job_id,
            job.stage if job else None,
            job.status if job else None,
        )
    finally:
        if owns_session:
            session.close()
