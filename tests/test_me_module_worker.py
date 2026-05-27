import uuid
from pathlib import Path
from unittest.mock import MagicMock

from app.reports.models.enums import ReportJobStatus
from app.reports.worker import run_pipeline as run_pipeline_module


class _FakeJob:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.donor_report_id = uuid.uuid4()
        self.stage = "classify"
        self.status = ReportJobStatus.QUEUED.value
        self.started_at = None
        self.finished_at = None
        self.error = None


def test_run_pipeline_stub_updates_job_status():
    job = _FakeJob()
    session = MagicMock()
    query = MagicMock()
    session.query.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = job

    run_pipeline_module.run_pipeline(job.donor_report_id, db=session)

    assert job.status == ReportJobStatus.DONE.value
    assert job.started_at is not None
    assert job.finished_at is not None
    assert session.commit.called


def test_main_does_not_import_worker():
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")
    assert "app.reports.worker" not in source


def test_web_procfile_separate_from_worker():
    procfile = Path(__file__).resolve().parents[1] / "Procfile"
    content = procfile.read_text(encoding="utf-8")
    assert "web:" in content
    assert "worker: python -m app.reports.worker" in content
