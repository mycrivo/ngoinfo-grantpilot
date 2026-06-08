"""Orphan reaper — fail stale running report_jobs (P3 / D3 Route A, D4)."""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.worker.job_failure import FAILURE_EVENT_ORPHAN_REAPED, mark_job_failed

logger = logging.getLogger("reports.worker.orphan_reaper")

_CLASSIFIER_SECONDS = 60
_EXTRACT_AGENT_SECONDS = 180
_RECONCILE_OR_GAP_SECONDS = 360
_SYNTHESIS_WAVE_SECONDS = 181
_CRITIC_SECTION_SECONDS = 120
_EXPORT_SECONDS = 300

_MARGIN_SECONDS = float(os.getenv("ME_ORPHAN_REAPER_MARGIN_SECONDS", "900"))
_DOCLING_DOC_SECONDS = float(os.getenv("ME_ORPHAN_REAPER_DOCLING_DOC_SECONDS", "300"))
_MAX_RUNNING_SECONDS = float(os.getenv("ME_ORPHAN_REAPER_MAX_SECONDS", "7200"))


def _parse_iso_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def compute_last_progress_at(job: ReportJob) -> datetime | None:
    """Latest durable progress from started_at and stage completed_at markers."""
    candidates: list[datetime] = []
    if job.started_at is not None:
        candidates.append(_as_utc(job.started_at))

    stages = (job.agent_trace_json or {}).get("stages") or {}
    if isinstance(stages, dict):
        for entry in stages.values():
            if not isinstance(entry, dict):
                continue
            completed_at = entry.get("completed_at")
            if not completed_at or not isinstance(completed_at, str):
                continue
            try:
                candidates.append(_parse_iso_timestamp(completed_at))
            except ValueError:
                logger.warning(
                    "orphan_reaper invalid completed_at job_id=%s value=%r",
                    job.id,
                    completed_at,
                )

    if not candidates:
        return None
    return max(candidates)


def _visible_section_count(session: Session, job: ReportJob) -> int:
    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        return 0
    template = session.get(FunderReportTemplate, report.funder_report_template_id)
    if template is None:
        return 0
    sections = template.report_sections_json or []
    if not isinstance(sections, list):
        return 0
    return sum(
        1
        for item in sections
        if isinstance(item, dict) and item.get("section_key")
    )


def _document_count(session: Session, job: ReportJob) -> int:
    return (
        session.query(func.count(UploadedDocument.id))
        .filter(UploadedDocument.donor_report_id == job.donor_report_id)
        .scalar()
        or 0
    )


def compute_stale_threshold_seconds(
    job: ReportJob,
    *,
    doc_count: int,
    section_count: int,
    margin_seconds: float | None = None,
    docling_doc_seconds: float | None = None,
) -> float:
    """Stage-aware silence budget since last_progress_at (seconds)."""
    margin = _MARGIN_SECONDS if margin_seconds is None else margin_seconds
    docling = _DOCLING_DOC_SECONDS if docling_doc_seconds is None else docling_doc_seconds
    docs = max(doc_count, 1)
    sections = max(section_count, 1)

    stage = job.stage or ReportJobStage.CLASSIFY.value
    if stage == ReportJobStage.CLASSIFY.value:
        per_doc = docling + _CLASSIFIER_SECONDS
        return docs * per_doc + margin
    if stage == ReportJobStage.EXTRACT.value:
        per_doc = docling + _EXTRACT_AGENT_SECONDS
        return docs * per_doc + margin
    if stage in (ReportJobStage.RECONCILE.value, ReportJobStage.GAP.value):
        return _RECONCILE_OR_GAP_SECONDS + margin
    if stage == ReportJobStage.SYNTHESISE.value:
        waves = math.ceil(sections / 2)
        return waves * _SYNTHESIS_WAVE_SECONDS + margin
    if stage == ReportJobStage.CRITIQUE.value:
        return sections * _CRITIC_SECTION_SECONDS + margin
    if stage == ReportJobStage.EXPORT.value:
        return _EXPORT_SECONDS + margin
    return docs * (docling + _EXTRACT_AGENT_SECONDS) + margin


def _has_completed_stages(job: ReportJob) -> bool:
    stages = (job.agent_trace_json or {}).get("stages") or {}
    if not isinstance(stages, dict):
        return False
    return any(
        isinstance(entry, dict) and entry.get("completed_at")
        for entry in stages.values()
    )


def should_reap_job(
    job: ReportJob,
    *,
    now: datetime,
    doc_count: int,
    section_count: int,
    margin_seconds: float | None = None,
    docling_doc_seconds: float | None = None,
    max_running_seconds: float | None = None,
) -> bool:
    if job.status != ReportJobStatus.RUNNING.value:
        return False
    if job.finished_at is not None:
        return False

    last_progress = compute_last_progress_at(job)
    if last_progress is None:
        return False

    silence = (now - last_progress).total_seconds()
    threshold = compute_stale_threshold_seconds(
        job,
        doc_count=doc_count,
        section_count=section_count,
        margin_seconds=margin_seconds,
        docling_doc_seconds=docling_doc_seconds,
    )
    if silence > threshold:
        return True

    max_running = _MAX_RUNNING_SECONDS if max_running_seconds is None else max_running_seconds
    if job.started_at is None or _has_completed_stages(job):
        return False
    started = _as_utc(job.started_at)
    return (now - started).total_seconds() > max_running


def reap_stale_running_jobs(session: Session) -> int:
    """Fail stale running jobs via mark_job_failed. Returns count reaped."""
    now = datetime.now(timezone.utc)
    running_ids = list(
        session.scalars(
            select(ReportJob.id).where(
                ReportJob.status == ReportJobStatus.RUNNING.value,
                ReportJob.finished_at.is_(None),
            )
        ).all()
    )

    reaped = 0
    for job_id in running_ids:
        pick = (
            select(ReportJob.id)
            .where(
                ReportJob.id == job_id,
                ReportJob.status == ReportJobStatus.RUNNING.value,
            )
            .with_for_update()
        )
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            pick = pick.with_for_update(skip_locked=True)

        locked_id = session.scalars(pick).first()
        if locked_id is None:
            session.rollback()
            continue

        job = session.get(ReportJob, locked_id)
        if job is None:
            session.rollback()
            continue

        doc_count = _document_count(session, job)
        section_count = _visible_section_count(session, job)
        if not should_reap_job(
            job,
            now=now,
            doc_count=doc_count,
            section_count=section_count,
        ):
            session.rollback()
            continue

        last_progress = compute_last_progress_at(job)
        progress_iso = last_progress.isoformat() if last_progress else "unknown"
        error = (
            f"aborted: no worker progress since {progress_iso} "
            f"(stage={job.stage}; orphan reaper)"
        )
        if mark_job_failed(session, job, error=error, event=FAILURE_EVENT_ORPHAN_REAPED):
            reaped += 1
            logger.warning(
                "orphan_reaper reaped job_id=%s donor_report_id=%s stage=%s",
                job.id,
                job.donor_report_id,
                job.stage,
            )
        else:
            session.rollback()

    return reaped
