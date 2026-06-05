"""API tests for M&E report lifecycle entry routes."""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.reports.models.enums import (
    DonorReportStatus,
    ExtractionStatus,
    ReportJobStage,
    ReportJobStatus,
)
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.services.document_storage_service import DocumentStorageService
from app.reports.services.donor_report_lifecycle_service import (
    create_donor_report,
    enqueue_report_job,
    upload_document,
)
from tests.worker_validation_seed import create_worker_validation_sessionmaker

get_settings.cache_clear()


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


@pytest.fixture
def lifecycle_api():
    session_factory = create_worker_validation_sessionmaker()
    user_id = uuid.uuid4()
    db = session_factory()
    now = datetime.now(timezone.utc)
    db.add(
        User(
            id=user_id,
            email=f"lifecycle-{user_id.hex[:8]}@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    db.close()

    app = create_app(_settings(me_enabled=True))

    def _override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    token, _ = create_access_token(str(user_id), "lifecycle@example.org", "free")
    client = TestClient(app)
    return SimpleNamespace(
        client=client,
        token=token,
        user_id=user_id,
        session_factory=session_factory,
        auth_header={"Authorization": f"Bearer {token}"},
    )


def test_outcome_d_routes_absent_when_module_disabled():
    app = create_app(_settings(me_enabled=False))
    client = TestClient(app)
    token, _ = create_access_token(str(uuid.uuid4()), "u@example.org", "free")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/reports", json={}, headers=headers).status_code == 404
    report_id = uuid.uuid4()
    assert (
        client.post(
            f"/api/reports/{report_id}/documents",
            files={"file": ("a.pdf", b"x", "application/pdf")},
            headers=headers,
        ).status_code
        == 404
    )


def test_create_persists_draft_report(lifecycle_api):
    response = lifecycle_api.client.post(
        "/api/reports",
        headers=lifecycle_api.auth_header,
        json={
            "reporting_period_start": "2025-01-01",
            "reporting_period_end": "2025-12-31",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == DonorReportStatus.DRAFT.value
    assert body["reporting_period_start"] == "2025-01-01"
    assert body["funder_name"]
    assert body["template_name"]


def test_upload_stores_via_mock_storage_and_creates_pending_document(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report_id = report.id
    session.close()

    real_build_storage_ref = DocumentStorageService.build_storage_ref
    mock_storage = MagicMock()
    with patch(
        "app.reports.services.donor_report_lifecycle_service.DocumentStorageService",
    ) as mock_svc_cls:
        mock_svc_cls.return_value = mock_storage
        mock_svc_cls.build_storage_ref = real_build_storage_ref
        response = lifecycle_api.client.post(
            f"/api/reports/{report_id}/documents",
            headers=lifecycle_api.auth_header,
            files={"file": ("proposal.pdf", b"%PDF-sample", "application/pdf")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["donor_report_id"] == str(report_id)
    assert body["original_filename"] == "proposal.pdf"
    assert body["classification"] is None
    assert body["extraction_status"] == ExtractionStatus.PENDING.value
    mock_storage.upload_bytes.assert_called_once()

    verify = lifecycle_api.session_factory()
    doc = verify.query(UploadedDocument).filter_by(donor_report_id=report_id).one()
    verify.close()
    assert doc.extraction_status == ExtractionStatus.PENDING.value
    assert doc.classification is None


def test_enqueue_creates_one_queued_job_and_rejects_duplicate_active(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report_id = report.id
    session.close()

    first = lifecycle_api.client.post(
        f"/api/reports/{report_id}/job",
        headers=lifecycle_api.auth_header,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["status"] == ReportJobStatus.QUEUED.value
    assert first_body["stage"] == ReportJobStage.CLASSIFY.value

    second = lifecycle_api.client.post(
        f"/api/reports/{report_id}/job",
        headers=lifecycle_api.auth_header,
    )
    assert second.status_code == 409
    assert second.json()["error_code"] == "ACTIVE_JOB_EXISTS"

    verify = lifecycle_api.session_factory()
    jobs = verify.query(ReportJob).filter_by(donor_report_id=report_id).all()
    verify.close()
    assert len(jobs) == 1
    assert jobs[0].status == ReportJobStatus.QUEUED.value


def test_enqueue_reclaims_failed_gap_job_at_failed_stage(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report.knowledge_bank_json = {
        "facts": {},
        "conflicts": [],
        "gate1_confirmed_at": "2026-06-05T12:29:58+00:00",
    }
    session.add(report)
    failed_job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=report.id,
        stage=ReportJobStage.GAP.value,
        status=ReportJobStatus.FAILED.value,
        agent_trace_json={"failed_stage": "gap", "failure": {"message": "parse"}},
        error="gap: Gap agent response is not valid JSON",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    session.add(failed_job)
    session.commit()
    report_id = report.id
    failed_job_id = failed_job.id
    session.close()

    resp = lifecycle_api.client.post(
        f"/api/reports/{report_id}/job",
        headers=lifecycle_api.auth_header,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == str(failed_job_id)
    assert body["stage"] == ReportJobStage.GAP.value
    assert body["status"] == ReportJobStatus.QUEUED.value

    verify = lifecycle_api.session_factory()
    jobs = verify.query(ReportJob).filter_by(donor_report_id=report_id).all()
    job = verify.query(ReportJob).filter_by(id=failed_job_id).one()
    verify.close()
    assert len(jobs) == 1
    assert job.error is None
    assert job.finished_at is None
    assert "failed_stage" not in (job.agent_trace_json or {})


def test_enqueue_does_not_hijack_awaiting_human_job(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report.knowledge_bank_json = {
        "facts": {},
        "gate1_confirmed_at": "2026-06-05T12:29:58+00:00",
    }
    session.add(report)
    awaiting_job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=report.id,
        stage=ReportJobStage.GAP.value,
        status=ReportJobStatus.AWAITING_HUMAN.value,
        agent_trace_json={},
    )
    session.add(awaiting_job)
    session.commit()
    report_id = report.id
    session.close()

    resp = lifecycle_api.client.post(
        f"/api/reports/{report_id}/job",
        headers=lifecycle_api.auth_header,
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "ACTIVE_JOB_EXISTS"


def test_status_and_knowledge_bank_reads(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report.knowledge_bank_json = {
        "facts": {"budget_total": {"value": 100}},
        "conflicts": [],
        "reconciler_agent": "knowledge_bank_reconciler",
        "reconciliation_outcome": "complete",
    }
    session.add(report)
    job = enqueue_report_job(
        session, donor_report_id=report.id, user_id=lifecycle_api.user_id
    )
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    job.stage = ReportJobStage.GAP.value
    session.add(job)
    session.commit()
    report_id = report.id
    job_id = job.id
    session.close()

    status_resp = lifecycle_api.client.get(
        f"/api/reports/{report_id}/job",
        headers=lifecycle_api.auth_header,
    )
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["job_id"] == str(job_id)
    assert status_body["status"] == ReportJobStatus.AWAITING_HUMAN.value
    assert status_body["stage"] == ReportJobStage.GAP.value

    kb_resp = lifecycle_api.client.get(
        f"/api/reports/{report_id}/knowledge-bank",
        headers=lifecycle_api.auth_header,
    )
    assert kb_resp.status_code == 200
    kb_body = kb_resp.json()
    assert kb_body["donor_report_id"] == str(report_id)
    assert kb_body["facts"]["budget_total"]["value"] == 100
    assert kb_body["ready_for_gate1"] is True


def test_unauthorized_and_non_owner_rejected(lifecycle_api):
    session = lifecycle_api.session_factory()
    owner_id = lifecycle_api.user_id
    other_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.add(
        User(
            id=other_id,
            email=f"other-{other_id.hex[:8]}@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
    )
    report = create_donor_report(
        session,
        user_id=owner_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    report_id = report.id
    session.close()

    other_token, _ = create_access_token(str(other_id), "other@example.org", "free")
    other_header = {"Authorization": f"Bearer {other_token}"}

    no_auth = lifecycle_api.client.get(f"/api/reports/{report_id}/job")
    assert no_auth.status_code == 401

    forbidden = lifecycle_api.client.get(
        f"/api/reports/{report_id}/job", headers=other_header
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error_code"] == "FORBIDDEN"


def test_service_upload_unit_with_mock_storage():
    session_factory = create_worker_validation_sessionmaker()
    session = session_factory()
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.add(
        User(
            id=user_id,
            email="svc@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
    )
    report = create_donor_report(
        session,
        user_id=user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
    )
    mock_storage = MagicMock()
    doc = upload_document(
        session,
        donor_report_id=report.id,
        user_id=user_id,
        filename="sheet.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        data=b"excel-bytes",
        storage=mock_storage,
    )
    assert doc.extraction_status == ExtractionStatus.PENDING.value
    mock_storage.upload_bytes.assert_called_once()
    session.close()
