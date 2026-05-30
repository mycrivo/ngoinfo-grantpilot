import threading
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.orchestration.pipeline import run_orchestrated_walk_sync
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from app.reports.worker.job_failure import (
    FAILURE_EVENT_EXCEPTION,
    FAILURE_EVENT_TIMEOUT,
)
from app.reports.worker.job_runner import claim_next_job, poll_once
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_queued_report_job,
)


@pytest.fixture
def worker_db(monkeypatch):
    """Bind worker modules to an isolated in-memory DB."""
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    from app.reports.worker import job_failure as job_failure_module

    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def _gate1_halt(job, session, *, ctx=None):
    session.refresh(job)
    if job.status == ReportJobStatus.FAILED.value:
        return
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    job.stage = ReportJobStage.GAP.value
    session.add(job)
    session.commit()


def test_run_pipeline_delegates_to_orchestrator():
    job = MagicMock()
    job.id = uuid.uuid4()
    job.donor_report_id = uuid.uuid4()
    job.stage = "classify"
    job.status = ReportJobStatus.RUNNING.value
    job.started_at = None
    job.finished_at = None
    job.error = None

    session = MagicMock()
    session.get.return_value = job

    with patch.object(run_pipeline_module, "run_orchestrated_walk_sync") as walk:
        run_pipeline_module.run_pipeline(job.id, db=session)
        walk.assert_called_once()


def test_main_does_not_import_worker():
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")
    assert "app.reports.worker" not in source


def test_web_procfile_separate_from_worker():
    procfile = Path(__file__).resolve().parents[1] / "Procfile"
    content = procfile.read_text(encoding="utf-8")
    assert "web:" in content
    assert "worker: python -m app.reports.worker" in content


def test_outcome_2_correct_row_threading(worker_db):
    """Exactly one job for a report is processed per claim; sibling stays queued."""
    session = worker_db()
    first = seed_queued_report_job(session)
    second = seed_queued_report_job(session, donor_report_id=first.donor_report_id)
    job_ids = {first.id, second.id}
    session.close()

    with patch.object(run_pipeline_module, "run_orchestrated_walk_sync", _gate1_halt):
        assert poll_once(job_timeout_seconds=5) == 1

    verify = worker_db()
    rows = [verify.get(ReportJob, job_id) for job_id in job_ids]
    verify.close()

    statuses = {row.status for row in rows if row is not None}
    assert statuses == {ReportJobStatus.AWAITING_HUMAN.value, ReportJobStatus.QUEUED.value}


def test_outcome_3_failure_marks_failed_with_trace_and_loop_survives(worker_db):
    session = worker_db()
    job = seed_queued_report_job(session)
    job_id = job.id
    session.close()

    def _boom(job_row, db_session, *, ctx=None):
        raise RuntimeError("injected pipeline failure")

    with patch.object(run_pipeline_module, "run_orchestrated_walk_sync", side_effect=_boom):
        assert poll_once(job_timeout_seconds=5) == 1
        assert poll_once(job_timeout_seconds=5) == 0

    verify = worker_db()
    failed_job = verify.get(ReportJob, job_id)
    verify.close()

    assert failed_job is not None
    assert failed_job.status == ReportJobStatus.FAILED.value
    assert "injected pipeline failure" in (failed_job.error or "")
    assert failed_job.agent_trace_json.get("failure", {}).get("event") == (
        FAILURE_EVENT_EXCEPTION
    )
    assert failed_job.finished_at is not None


def test_outcome_4_timeout_backstop_marks_failed_and_loop_survives(worker_db):
    session = worker_db()
    job = seed_queued_report_job(session)
    job_id = job.id
    session.close()

    def _hang(job_row, db_session, *, ctx=None):
        import time

        time.sleep(2.0)

    with patch.object(run_pipeline_module, "run_orchestrated_walk_sync", side_effect=_hang):
        assert poll_once(job_timeout_seconds=0.2) == 1
        assert poll_once(job_timeout_seconds=0.2) == 0

    verify = worker_db()
    failed_job = verify.get(ReportJob, job_id)
    verify.close()

    assert failed_job is not None
    assert failed_job.status == ReportJobStatus.FAILED.value
    assert "wall-clock limit" in (failed_job.error or "")
    assert failed_job.agent_trace_json.get("failure", {}).get("event") == (
        FAILURE_EVENT_TIMEOUT
    )
    assert failed_job.finished_at is not None


def test_outcome_1_concurrent_claim_only_one_wins(worker_db):
    session = worker_db()
    job = seed_queued_report_job(session)
    expected_job_id = job.id
    session.close()

    results: list[uuid.UUID | None] = []
    lock = threading.Lock()

    def _try_claim() -> None:
        local = worker_db()
        try:
            claimed = claim_next_job(local)
            with lock:
                results.append(claimed.id if claimed is not None else None)
        finally:
            local.close()

    threads = [threading.Thread(target=_try_claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    claimed_ids = [job_id for job_id in results if job_id is not None]
    assert len(claimed_ids) == 1
    assert claimed_ids[0] == expected_job_id
    assert results.count(None) == 1

    verify = worker_db()
    row = verify.get(ReportJob, expected_job_id)
    verify.close()
    assert row is not None
    assert row.status == ReportJobStatus.RUNNING.value


def test_outcome_5_seeded_job_halts_at_gate1(worker_db):
    session = worker_db()
    job = seed_queued_report_job(session)
    job_id = job.id
    session.close()

    with patch.object(run_pipeline_module, "run_orchestrated_walk_sync", _gate1_halt):
        assert poll_once(job_timeout_seconds=5) == 1

    verify = worker_db()
    done_job = verify.get(ReportJob, job_id)
    verify.close()

    assert done_job is not None
    assert done_job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert done_job.stage == ReportJobStage.GAP.value
    assert done_job.started_at is not None
    assert done_job.error is None


def test_outcome_5_poll_cycle_error_does_not_exit_worker(worker_db, monkeypatch):
    calls = {"count": 0}

    def _flaky_poll(*, job_timeout_seconds=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient poll failure")
        monkeypatch.setattr(job_runner_module, "poll_once", lambda **_: 0)
        return 0

    monkeypatch.setattr(job_runner_module, "poll_once", _flaky_poll)
    monkeypatch.setattr(
        job_runner_module,
        "time",
        MagicMock(sleep=MagicMock(side_effect=SystemExit(0))),
    )

    with pytest.raises(SystemExit):
        job_runner_module.run_forever()

    assert calls["count"] == 1
