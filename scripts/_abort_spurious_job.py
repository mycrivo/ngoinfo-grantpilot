#!/usr/bin/env python3
"""Abort accidental classify job created before reclaim deploy landed."""
from __future__ import annotations

import uuid

from app.db.session import SessionLocal
from app.reports.models.report_job import ReportJob
from app.reports.worker.job_failure import FAILURE_EVENT_EXCEPTION, mark_job_failed

SPURIOUS_JOB_ID = uuid.UUID("c16ccb58-eb16-4a87-ac16-f769944da74c")


def main() -> None:
    session = SessionLocal()
    try:
        job = session.get(ReportJob, SPURIOUS_JOB_ID)
        if job is None:
            print("job not found")
            return
        if job.status in {"done", "failed"}:
            print(f"job already terminal: {job.status}")
            return
        mark_job_failed(
            session,
            job,
            error="aborted: accidental enqueue before failed-job reclaim deploy",
            event=FAILURE_EVENT_EXCEPTION,
        )
        print(f"marked failed job_id={job.id} stage={job.stage}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
