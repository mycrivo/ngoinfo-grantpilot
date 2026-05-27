from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob

logger = logging.getLogger("reports.worker")


def run_pipeline(report_id: UUID, db: Session | None = None) -> None:
    """Swappable execution seam — Stage C no-op stub."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        job = (
            session.query(ReportJob)
            .filter(ReportJob.donor_report_id == report_id)
            .order_by(ReportJob.started_at.desc().nullslast())
            .first()
        )
        if job is None:
            logger.warning("run_pipeline: no report_job for report_id=%s", report_id)
            return

        logger.info(
            "run_pipeline stub start report_id=%s job_id=%s stage=%s",
            report_id,
            job.id,
            job.stage,
        )
        now = datetime.now(timezone.utc)
        job.status = ReportJobStatus.RUNNING.value
        job.started_at = job.started_at or now
        session.commit()

        job.status = ReportJobStatus.DONE.value
        job.finished_at = datetime.now(timezone.utc)
        session.commit()

        logger.info(
            "run_pipeline stub complete report_id=%s job_id=%s",
            report_id,
            job.id,
        )
    except Exception:
        session.rollback()
        if owns_session:
            try:
                job = (
                    session.query(ReportJob)
                    .filter(ReportJob.donor_report_id == report_id)
                    .order_by(ReportJob.started_at.desc().nullslast())
                    .first()
                )
                if job is not None:
                    job.status = ReportJobStatus.FAILED.value
                    job.error = "run_pipeline stub failed"
                    job.finished_at = datetime.now(timezone.utc)
                    session.commit()
            except Exception:
                session.rollback()
        raise
    finally:
        if owns_session:
            session.close()
