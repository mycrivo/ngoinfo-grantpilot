"""P3-2 worker recovery — heartbeat, lease, requeue bound, charge-once."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.usage_ledger import UsageLedger
from app.reports.models.enums import DonorReportStatus, ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.services.report_export_service import export_and_persist
from app.reports.worker.job_failure import FAILURE_EVENT_ORPHAN_REAPED
from app.reports.worker.job_lease import REQUEUE_MAX, touch_heartbeat
from app.reports.worker.job_runner import claim_next_job
from app.reports.worker.orphan_reaper import (
    compute_last_progress_at,
    reap_stale_running_jobs,
)
from app.services.quota_service import report_create_idempotency_key
from tests.test_orphan_reaper import _seed_running_job
from tests.test_report_export_service import _seed_gate3_ready_report, export_db
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_queued_report_job,
)


@pytest.fixture
def recovery_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    import app.reports.worker.job_failure as job_failure_module
    import app.reports.worker.job_runner as job_runner_module
    import app.reports.worker.orphan_reaper as orphan_reaper_module
    import app.reports.worker.run_pipeline as run_pipeline_module

    monkeypatch.setattr(orphan_reaper_module, "_MARGIN_SECONDS", 10.0)
    monkeypatch.setattr(orphan_reaper_module, "_DOCLING_DOC_SECONDS", 5.0)
    monkeypatch.setattr(orphan_reaper_module, "_MAX_RUNNING_SECONDS", 120.0)
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def test_heartbeat_updates_last_progress(recovery_db):
    session = recovery_db()
    job = _seed_running_job(
        session,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        agent_trace_json={
            "stages": {
                "classify": {"completed_at": "2026-01-01T12:30:00+00:00"},
            }
        },
    )
    heartbeat = datetime(2026, 1, 1, 13, 15, tzinfo=timezone.utc)
    job.last_heartbeat_at = heartbeat
    session.add(job)
    session.commit()
    session.refresh(job)
    assert compute_last_progress_at(job) == heartbeat
    session.close()


def test_touch_heartbeat_extends_lease(recovery_db):
    session = recovery_db()
    job = _seed_running_job(session)
    touch_heartbeat(session, job)
    session.refresh(job)
    assert job.last_heartbeat_at is not None
    assert job.lease_owner is not None
    assert job.lease_expires_at is not None
    assert job.lease_expires_at > job.last_heartbeat_at
    session.close()


def test_claim_sets_lease(recovery_db):
    session = recovery_db()
    job = seed_queued_report_job(session)
    job_id = job.id
    session.close()

    session = recovery_db()
    claimed = claim_next_job(session)
    session.close()

    assert claimed is not None
    assert claimed.id == job_id
    verify = recovery_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.RUNNING.value
    assert row.lease_owner is not None
    assert row.last_heartbeat_at is not None
    assert row.lease_expires_at is not None


def test_first_stale_reap_requeues(recovery_db):
    session = recovery_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale)
    job_id = job.id
    session.close()

    session = recovery_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = recovery_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.QUEUED.value
    assert row.requeue_count == 1
    assert row.lease_owner is None
    assert (row.agent_trace_json.get("requeue_events") or [])


def test_second_stale_reap_terminal_fails(recovery_db):
    session = recovery_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(session, started_at=stale)
    job.requeue_count = REQUEUE_MAX
    session.add(job)
    session.commit()
    job_id = job.id
    session.close()

    session = recovery_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = recovery_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.FAILED.value
    assert "requeue bound exhausted" in (row.error or "")
    assert row.agent_trace_json.get("failure", {}).get("event") == FAILURE_EVENT_ORPHAN_REAPED


def test_degraded_job_never_requeued(recovery_db):
    session = recovery_db()
    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    job = _seed_running_job(
        session,
        started_at=stale,
        agent_trace_json={
            "stages": {
                "classify": {
                    "completed_at": stale.isoformat(),
                    "degraded_notes": ["doc-1"],
                }
            }
        },
    )
    report = job.donor_report
    report.status = DonorReportStatus.DEGRADED.value
    session.add(report)
    session.commit()
    job_id = job.id
    session.close()

    session = recovery_db()
    assert reap_stale_running_jobs(session) == 1
    session.close()

    verify = recovery_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.FAILED.value
    assert "degraded job not requeued" in (row.error or "")
    assert row.requeue_count == 0


def test_fresh_heartbeat_prevents_reap(recovery_db):
    session = recovery_db()
    old_progress = datetime.now(timezone.utc) - timedelta(hours=1)
    job = _seed_running_job(
        session,
        stage=ReportJobStage.EXTRACT.value,
        started_at=old_progress - timedelta(hours=1),
        agent_trace_json={
            "stages": {"classify": {"completed_at": old_progress.isoformat()}}
        },
    )
    job.last_heartbeat_at = datetime.now(timezone.utc)
    session.add(job)
    session.commit()
    job_id = job.id
    session.close()

    session = recovery_db()
    assert reap_stale_running_jobs(session) == 0
    session.close()

    verify = recovery_db()
    row = verify.get(ReportJob, job_id)
    verify.close()
    assert row.status == ReportJobStatus.RUNNING.value


def test_charge_once_across_requeue_path(export_db):
    """Export after one requeue still charges REPORT_CREATE at most once."""
    session = export_db()
    report_id, _user_id, storage = _seed_gate3_ready_report(session)
    job = seed_queued_report_job(session, donor_report_id=report_id)
    job.status = ReportJobStatus.RUNNING.value
    job.stage = ReportJobStage.EXPORT.value
    job.requeue_count = 1
    session.add(job)
    session.commit()
    session.close()

    export_and_persist(export_db(), report_id, storage=storage)

    session = export_db()
    rows = session.execute(
        select(UsageLedger).where(
            UsageLedger.idempotency_key == report_create_idempotency_key(report_id)
        )
    ).scalars().all()
    session.close()
    assert len(rows) == 1
