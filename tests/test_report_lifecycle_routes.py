"""API tests for M&E report lifecycle entry routes."""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.core.security as security
from app.core.config import get_settings
from app.core.config import get_settings as config_get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.services.quota_service import PLAN_IMPACT
from app.reports.models.enums import (
    DonorReportStatus,
    ExtractionStatus,
    ReportJobStage,
    ReportJobStatus,
)
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.services.document_storage_service import DocumentStorageService
from app.reports.services.donor_report_lifecycle_service import (
    DEFAULT_FUNDER_NAME,
    DEFAULT_TEMPLATE_NAME,
    create_donor_report,
    enqueue_report_job,
    upload_document,
)
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_user_plan,
)

get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    security.get_settings = config_get_settings
    yield
    get_settings.cache_clear()
    security.get_settings = config_get_settings


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def _seed_template(session) -> FunderReportTemplate:
    now = datetime.now(timezone.utc)
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="Lifecycle Test Funder",
        template_name="Annual Report",
        region="uk",
        reporting_frequency="annual",
        report_sections_json=[],
        format_rules_json={},
        terminology_map_json={},
        docx_template_ref="validation/test.docx",
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(template)
    session.flush()
    return template


def _seed_sentinel_template(session) -> FunderReportTemplate:
    now = datetime.now(timezone.utc)
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name=DEFAULT_FUNDER_NAME,
        template_name=DEFAULT_TEMPLATE_NAME,
        region="global",
        reporting_frequency="annual",
        report_sections_json=[],
        format_rules_json={},
        terminology_map_json={},
        docx_template_ref="system/default.docx",
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(template)
    session.flush()
    return template


def _create_report_json(template_id: uuid.UUID) -> dict:
    return {
        "funder_report_template_id": str(template_id),
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
    }


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
    seed_user_plan(db, user_id, plan_name=PLAN_IMPACT)
    template = _seed_template(db)
    template_id = template.id
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
        template_id=template_id,
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
        json=_create_report_json(lifecycle_api.template_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == DonorReportStatus.DRAFT.value
    assert body["reporting_period_start"] == "2025-01-01"
    assert body["funder_name"] == "Lifecycle Test Funder"
    assert body["template_name"] == "Annual Report"


def test_create_rejects_missing_template_id(lifecycle_api):
    response = lifecycle_api.client.post(
        "/api/reports",
        headers=lifecycle_api.auth_header,
        json={
            "reporting_period_start": "2025-01-01",
            "reporting_period_end": "2025-12-31",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"


def test_create_rejects_sentinel_template_id(lifecycle_api):
    session = lifecycle_api.session_factory()
    sentinel = _seed_sentinel_template(session)
    sentinel_id = sentinel.id
    session.commit()
    session.close()

    response = lifecycle_api.client.post(
        "/api/reports",
        headers=lifecycle_api.auth_header,
        json=_create_report_json(sentinel_id),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "cannot be used" in body["message"].lower()


def test_upload_stores_via_mock_storage_and_creates_pending_document(lifecycle_api):
    session = lifecycle_api.session_factory()
    report = create_donor_report(
        session,
        user_id=lifecycle_api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=lifecycle_api.template_id,
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
        funder_report_template_id=lifecycle_api.template_id,
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
        funder_report_template_id=lifecycle_api.template_id,
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
        funder_report_template_id=lifecycle_api.template_id,
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
        funder_report_template_id=lifecycle_api.template_id,
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
    seed_user_plan(session, other_id, plan_name=PLAN_IMPACT)
    template = _seed_template(session)
    session.commit()
    report = create_donor_report(
        session,
        user_id=owner_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=template.id,
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
    assert forbidden.status_code == 404
    assert forbidden.json()["error_code"] == "DONOR_REPORT_NOT_FOUND"


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
    seed_user_plan(session, user_id, plan_name=PLAN_IMPACT)
    template = _seed_template(session)
    session.commit()
    report = create_donor_report(
        session,
        user_id=user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=template.id,
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
