from __future__ import annotations

import logging
import time

from app.db.session import SessionLocal
from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.worker.run_pipeline import run_pipeline

logger = logging.getLogger("reports.worker")
POLL_INTERVAL_SECONDS = 5


def poll_once() -> int:
    """Process one queued job if present. Returns count processed."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")

    session = SessionLocal()
    processed = 0
    try:
        job = (
            session.query(ReportJob)
            .filter(ReportJob.status == ReportJobStatus.QUEUED.value)
            .order_by(ReportJob.started_at.asc().nullsfirst())
            .first()
        )
        if job is None:
            return 0

        run_pipeline(job.donor_report_id, db=session)
        processed = 1
    finally:
        session.close()
    return processed


def run_forever() -> None:
    logger.info("M&E worker started (Stage C stub)")
    while True:
        try:
            count = poll_once()
            if count == 0:
                time.sleep(POLL_INTERVAL_SECONDS)
        except Exception:
            logger.exception("Worker poll cycle failed")
            time.sleep(POLL_INTERVAL_SECONDS)
