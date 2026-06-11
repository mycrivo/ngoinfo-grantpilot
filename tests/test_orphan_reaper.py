"""P3 orphan reaper — stale running job recovery (D3 Route A, D4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.services.donor_report_lifecycle_service import enqueue_report_job
from app.reports.worker.job_failure import FAILURE_EVENT_ORPHAN_REAPED
from app.reports.worker.orphan_reaper import (
    compute_last_progress_at,
    compute_stale_threshold_seconds,
    reap_stale_running_jobs,
    should_reap_job,
)
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_queued_report_job,
    seed_uploaded_document,
)


@pytest.fixture
def reaper_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    import app.reports.worker.orphan_reaper as orphan_reaper_module

    monkeypatch.setattr(orphan_reaper_module, "_MARGIN_SECONDS", 10.0)
    monkeypatch.setattr(orphan_reaper_module, "_DOCLING_DOC_SECONDS", 5.0)
    monkeypatch.setattr(orphan_reaper_module, "_MAX_RUNNING_SECONDS", 120.0)
    return session_factory


def _seed_running_job(
    session,
    *,
    stage: str = ReportJobStage.CLASSIFY.value,
    started_at: datetime | None = None,
    agent_trace_json: dict | None = None,
    donor_report_id=None,
) -> ReportJob:
    job = seed_queued_report_job(
        session,
        donor_report_id=donor_report_id,
        stage=stage,
    )
    now = datetime.now(timezone.utc)
    job.status = ReportJobStatus.RUNNING.value
    job.started_at = started_at or now
    job.agent_trace_json = agent_trace_json or {}
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_compute_last_progress_at_uses_max_of_started_and_stages():
    started = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    job = ReportJob(
        id=None,
        donor_report_id=None,
        stage=ReportJobStage.EXTRACT.value,
        status=ReportJobStatus.RUNNING.value,
        started_at=started,
        agent_trace_json={
            "stages": {
                "classify": {"completed_at": "2026-01-01T12:30:00+00:00"},
                "extract": {"completed_at": "2026-01-01T13:00:00+00:00"},
            }
        },
    )
    assert compute_last_progress_at(job) == datetime(
        2026, 1, 1, 13, 0, tzinfo=timezone.utc
    )


def test_compute_stale_threshold_extract_stage():
    job = ReportJob(
        id=None,
        donor_report_id=None,
        stage=ReportJobStage.EXTRACT.value,
        status=ReportJobStatus.RUNNING.value,
        agent_trace_json={},
    )
    threshold = compute_stale_threshold_seconds(
        job,
        doc_count=2,
        section_count=1,
        margin_seconds=10,
        docling_doc_seconds=5,
    )
    assert threshold == 2 * (5 + 180) + 10


def test_reaps_stale_running_job_with_old_started_at(reaper_db):
    session = reaper_db()
    stale_start = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale_start, agent_trace_json={})
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = reaper_db()
    requeued = verify.get(ReportJob, job_id)
    verify.close()

    assert requeued is not None
    assert requeued.status == ReportJobStatus.QUEUED.value
    assert requeued.requeue_count == 1
    assert requeued.finished_at is None


def test_does_not_reap_fresh_running_job(reaper_db):
    session = reaper_db()
    job = _seed_running_job(
        session,
        started_at=datetime.now(timezone.utc),
        agent_trace_json={},
    )
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 0
    session.close()

    verify = reaper_db()
    running = verify.get(ReportJob, job_id)
    verify.close()
    assert running.status == ReportJobStatus.RUNNING.value


def test_does_not_reap_extract_within_threshold(reaper_db):
    session = reaper_db()
    recent = datetime.now(timezone.utc) - timedelta(seconds=30)
    job = _seed_running_job(
        session,
        stage=ReportJobStage.EXTRACT.value,
        started_at=recent - timedelta(minutes=10),
        agent_trace_json={
            "stages": {
                "classify": {"completed_at": recent.isoformat()},
            }
        },
    )
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 0
    session.close()

    verify = reaper_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.RUNNING.value


def test_reaps_stale_extract_silence(reaper_db):
    session = reaper_db()
    old_progress = datetime.now(timezone.utc) - timedelta(hours=1)
    job = _seed_running_job(
        session,
        stage=ReportJobStage.EXTRACT.value,
        started_at=old_progress - timedelta(hours=1),
        agent_trace_json={
            "stages": {
                "classify": {"completed_at": old_progress.isoformat()},
            }
        },
    )
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = reaper_db()
    requeued = verify.get(ReportJob, job_id)
    verify.close()
    assert requeued.status == ReportJobStatus.QUEUED.value
    assert requeued.requeue_count == 1


def test_does_not_reap_awaiting_human(reaper_db):
    session = reaper_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=3)
    job = _seed_running_job(session, started_at=stale)
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    session.add(job)
    session.commit()
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 0
    session.close()

    verify = reaper_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.AWAITING_HUMAN.value


def test_reap_idempotent_second_pass(reaper_db):
    session = reaper_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale)
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 1
    assert reap_stale_running_jobs(session) == 0
    session.close()

    verify = reaper_db()
    requeued = verify.get(ReportJob, job_id)
    verify.close()
    assert requeued.status == ReportJobStatus.QUEUED.value
    assert requeued.requeue_count == 1


def test_reap_terminal_after_requeue_bound(reaper_db):
    session = reaper_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale)
    job.requeue_count = 1
    session.add(job)
    session.commit()
    job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = reaper_db()
    failed = verify.get(ReportJob, job_id)
    verify.close()
    assert failed.status == ReportJobStatus.FAILED.value
    assert failed.agent_trace_json.get("failure", {}).get("event") == (
        FAILURE_EVENT_ORPHAN_REAPED
    )


def test_enqueue_after_terminal_reap_succeeds(reaper_db):
    session = reaper_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale)
    job.requeue_count = 1
    session.add(job)
    session.commit()
    report = job.donor_report
    user_id = report.user_id
    report_id = report.id
    old_job_id = job.id
    session.close()

    session = reaper_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    session = reaper_db()
    enqueued = enqueue_report_job(
        session,
        donor_report_id=report_id,
        user_id=user_id,
    )
    session.close()

    assert enqueued.status == ReportJobStatus.QUEUED.value
    assert enqueued.donor_report_id == report_id
    assert enqueued.id != old_job_id

    verify = reaper_db()
    failed = verify.get(ReportJob, old_job_id)
    verify.close()
    assert failed.status == ReportJobStatus.FAILED.value


def test_max_running_backstop_empty_trace(reaper_db):
    session = reaper_db()
    started = datetime.now(timezone.utc) - timedelta(seconds=200)
    job = _seed_running_job(session, started_at=started, agent_trace_json={})
    now = datetime.now(timezone.utc)
    doc_count = 50
    section_count = 1
    assert should_reap_job(
        job,
        now=now,
        doc_count=doc_count,
        section_count=section_count,
        margin_seconds=10,
        docling_doc_seconds=5,
        max_running_seconds=120,
    )


def test_document_count_affects_threshold(reaper_db):
    session = reaper_db()
    job = seed_queued_report_job(session)
    report = job.donor_report
    user_id = report.user_id
    for idx in range(3):
        seed_uploaded_document(
            session,
            donor_report_id=report.id,
            user_id=user_id,
            filename=f"doc{idx}.pdf",
        )
    job.status = ReportJobStatus.RUNNING.value
    job.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
    session.add(job)
    session.commit()
    session.refresh(job)

    doc_count = 3
    threshold = compute_stale_threshold_seconds(
        job,
        doc_count=doc_count,
        section_count=1,
        margin_seconds=10,
        docling_doc_seconds=5,
    )
    assert threshold == 3 * (5 + 60) + 10
    session.close()
