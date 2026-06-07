"""Latest report_job resolution for list/detail surfaces."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.reports.models.enums import ReportJobStatus
from app.reports.models.report_job import ReportJob

_ACTIVE_JOB_STATUSES = frozenset(
    {
        ReportJobStatus.QUEUED.value,
        ReportJobStatus.RUNNING.value,
        ReportJobStatus.AWAITING_HUMAN.value,
    }
)


def _job_sort_key(job: ReportJob) -> tuple[int, datetime, uuid.UUID]:
    started = job.started_at
    if started is None:
        started = datetime.min.replace(tzinfo=timezone.utc)
    elif started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    active_rank = 1 if job.status in _ACTIVE_JOB_STATUSES else 0
    return (active_rank, started, job.id)


def resolve_latest_job(jobs: list[ReportJob]) -> ReportJob | None:
    """Prefer an active job; otherwise the most recently started job."""
    if not jobs:
        return None
    return max(jobs, key=_job_sort_key)


def get_latest_job_for_report(
    db: Session,
    donor_report_id: uuid.UUID,
) -> ReportJob | None:
    jobs = (
        db.query(ReportJob)
        .filter(ReportJob.donor_report_id == donor_report_id)
        .all()
    )
    return resolve_latest_job(jobs)


def get_latest_jobs_for_reports(
    db: Session,
    donor_report_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ReportJob]:
    if not donor_report_ids:
        return {}

    jobs = (
        db.query(ReportJob)
        .filter(ReportJob.donor_report_id.in_(donor_report_ids))
        .all()
    )
    grouped: dict[uuid.UUID, list[ReportJob]] = {}
    for job in jobs:
        grouped.setdefault(job.donor_report_id, []).append(job)

    return {
        report_id: resolved
        for report_id, report_jobs in grouped.items()
        if (resolved := resolve_latest_job(report_jobs)) is not None
    }
