"""API tests for M&E read endpoints and path alignment."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.core.security as security
from app.core.config import get_settings
from app.core.config import get_settings as config_get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app
from app.models.user import User
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DonorReportStatus, ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from app.reports.services.donor_report_lifecycle_service import (
    DEFAULT_FUNDER_NAME,
    DEFAULT_TEMPLATE_NAME,
    create_donor_report,
)
from app.services.quota_service import PLAN_FREE, PLAN_GROWTH, PLAN_IMPACT
from tests.worker_validation_seed import (
    create_worker_validation_sessionmaker,
    seed_user_plan,
)

get_settings.cache_clear()

_CREATE_JSON = {
    "reporting_period_start": "2025-01-01",
    "reporting_period_end": "2025-12-31",
}


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


def _read_api(*, plan_name: str = PLAN_IMPACT):
    session_factory = create_worker_validation_sessionmaker()
    user_id = uuid.uuid4()
    db = session_factory()
    now = datetime.now(timezone.utc)
    db.add(
        User(
            id=user_id,
            email=f"read-{user_id.hex[:8]}@example.org",
            auth_provider="email",
            created_at=now,
            updated_at=now,
        )
    )
    seed_user_plan(db, user_id, plan_name=plan_name)
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
    token, _ = create_access_token(str(user_id), "read@example.org", "free")
    client = TestClient(app)
    return SimpleNamespace(
        client=client,
        user_id=user_id,
        template_id=template_id,
        session_factory=session_factory,
        auth_header={"Authorization": f"Bearer {token}"},
    )


def _seed_template(session) -> FunderReportTemplate:
    now = datetime.now(timezone.utc)
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="Test Funder",
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


def test_list_reports_empty_for_new_impact_user():
    api = _read_api(plan_name=PLAN_IMPACT)
    response = api.client.get("/api/reports", headers=api.auth_header)
    assert response.status_code == 200
    assert response.json()["reports"] == []


def test_list_reports_returns_only_owner_reports_respects_limit():
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    template = _seed_template(session)
    for index in range(3):
        report = DonorReport(
            id=uuid.uuid4(),
            user_id=api.user_id,
            funder_report_template_id=template.id,
            reporting_period_start=date(2025, 1, 1),
            reporting_period_end=date(2025, 12, 31),
            status=DonorReportStatus.DRAFT.value,
            knowledge_bank_json={},
            gap_analysis_json={},
            indicator_actuals_json={},
            content_json={},
            version=1,
            created_at=datetime(2025, 1, index + 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, index + 1, tzinfo=timezone.utc),
        )
        session.add(report)

    other_id = uuid.uuid4()
    session.add(
        User(
            id=other_id,
            email="other-read@example.org",
            auth_provider="email",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        DonorReport(
            id=uuid.uuid4(),
            user_id=other_id,
            funder_report_template_id=template.id,
            reporting_period_start=date(2024, 1, 1),
            reporting_period_end=date(2024, 12, 31),
            status=DonorReportStatus.DRAFT.value,
            knowledge_bank_json={},
            gap_analysis_json={},
            indicator_actuals_json={},
            content_json={},
            version=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.close()

    response = api.client.get("/api/reports?limit=2", headers=api.auth_header)
    assert response.status_code == 200
    body = response.json()
    assert len(body["reports"]) == 2
    item = body["reports"][0]
    assert set(item.keys()) == {
        "id",
        "funder_name",
        "template_name",
        "status",
        "reporting_period_start",
        "reporting_period_end",
        "current_gate",
        "latest_job_status",
        "latest_job_stage",
        "document_count",
        "created_at",
        "updated_at",
    }
    assert "knowledge_bank_json" not in item
    assert body["reports"][0]["created_at"] >= body["reports"][1]["created_at"]


def test_list_reports_includes_document_count():
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    template = _seed_template(session)
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=api.user_id,
        funder_report_template_id=template.id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        status=DonorReportStatus.DRAFT.value,
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(report)
    session.flush()
    from app.reports.models.uploaded_document import UploadedDocument

    session.add(
        UploadedDocument(
            id=uuid.uuid4(),
            donor_report_id=report.id,
            user_id=api.user_id,
            original_filename="proposal.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size_bytes=100,
            storage_ref="test/proposal.docx",
            extracted_json={},
            extraction_status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    report_id = report.id
    session.close()

    response = api.client.get("/api/reports", headers=api.auth_header)
    assert response.status_code == 200
    item = next(row for row in response.json()["reports"] if row["id"] == str(report_id))
    assert item["document_count"] == 1


def test_list_reports_includes_latest_failed_job_status():
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    report = create_donor_report(
        session,
        user_id=api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=api.template_id,
    )
    session.add(
        ReportJob(
            id=uuid.uuid4(),
            donor_report_id=report.id,
            stage=ReportJobStage.EXTRACT.value,
            status=ReportJobStatus.FAILED.value,
            agent_trace_json={},
            error="extract: unsupported format",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.close()

    response = api.client.get("/api/reports", headers=api.auth_header)
    assert response.status_code == 200
    item = response.json()["reports"][0]
    assert item["latest_job_status"] == ReportJobStatus.FAILED.value
    assert item["latest_job_stage"] == ReportJobStage.EXTRACT.value


def test_get_report_detail_owner_and_foreign_404():
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    report = create_donor_report(
        session,
        user_id=api.user_id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        funder_report_template_id=api.template_id,
    )
    report_id = report.id
    session.commit()
    session.close()

    ok = api.client.get(f"/api/reports/{report_id}", headers=api.auth_header)
    assert ok.status_code == 200
    detail = ok.json()
    assert detail["id"] == str(report_id)
    assert detail["funder_name"] == "Test Funder"
    assert detail["template_name"] == "Annual Report"
    assert "content_json" in detail
    assert "current_gate" in detail

    other_api = _read_api(plan_name=PLAN_IMPACT)
    forbidden = other_api.client.get(
        f"/api/reports/{report_id}", headers=other_api.auth_header
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error_code"] == "DONOR_REPORT_NOT_FOUND"

    missing = api.client.get(f"/api/reports/{uuid.uuid4()}", headers=api.auth_header)
    assert missing.status_code == 404


def test_list_report_templates():
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    real_template = _seed_template(session)
    sentinel = _seed_sentinel_template(session)
    real_template_id = real_template.id
    sentinel_id = sentinel.id
    session.commit()
    session.close()

    response = api.client.get("/api/report-templates", headers=api.auth_header)
    assert response.status_code == 200
    templates = response.json()["report_templates"]
    template_ids = {item["id"] for item in templates}
    assert str(real_template_id) in template_ids
    assert str(sentinel_id) not in template_ids
    assert len(templates) >= 1
    assert all(
        not (
            item["funder_name"] == DEFAULT_FUNDER_NAME
            and item["template_name"] == DEFAULT_TEMPLATE_NAME
        )
        for item in templates
    )
    assert set(templates[0].keys()) == {
        "id",
        "funder_name",
        "template_name",
        "region",
        "reporting_frequency",
        "version",
    }


def test_sentinel_linked_report_detail_still_readable():
    """Historical reports FK'd to the system template remain readable on GET detail."""
    api = _read_api(plan_name=PLAN_IMPACT)
    session = api.session_factory()
    sentinel = _seed_sentinel_template(session)
    now = datetime.now(timezone.utc)
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=api.user_id,
        funder_report_template_id=sentinel.id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        status=DonorReportStatus.DRAFT.value,
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    session.commit()
    report_id = report.id
    session.close()

    response = api.client.get(f"/api/reports/{report_id}", headers=api.auth_header)
    assert response.status_code == 200
    detail = response.json()
    assert detail["funder_name"] == DEFAULT_FUNDER_NAME
    assert detail["template_name"] == DEFAULT_TEMPLATE_NAME


def test_read_endpoints_inherit_upgrade_required_gate():
    api = _read_api(plan_name=PLAN_FREE)
    for path in ("/api/reports", f"/api/reports/{uuid.uuid4()}", "/api/report-templates"):
        response = api.client.get(path, headers=api.auth_header)
        assert response.status_code == 403
        assert response.json()["error_code"] == "UPGRADE_REQUIRED"

    growth = _read_api(plan_name=PLAN_GROWTH)
    response = growth.client.get("/api/reports", headers=growth.auth_header)
    assert response.status_code == 403


def test_old_donor_reports_gate_paths_return_404():
    api = _read_api(plan_name=PLAN_IMPACT)
    report_id = uuid.uuid4()
    old_paths = [
        f"/api/reports/donor-reports/{report_id}/knowledge-bank/gate1/confirm",
        f"/api/reports/donor-reports/{report_id}/knowledge-bank/gate2/gap-responses",
        f"/api/reports/donor-reports/{report_id}/knowledge-bank/gate3/confirm",
    ]
    for path in old_paths:
        response = api.client.post(path, json={}, headers=api.auth_header)
        assert response.status_code == 404


def test_gate1_confirm_canonical_path_still_registered():
    api = _read_api(plan_name=PLAN_IMPACT)
    report_id = uuid.uuid4()
    kb = {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "facts": {},
        "conflicts": [],
        "reconciliation_outcome": "complete",
        "reconciler_agent": RECONCILER_AGENT_NAME,
    }
    response = api.client.post(
        f"/api/reports/{report_id}/knowledge-bank/gate1/confirm",
        headers=api.auth_header,
        json={"knowledge_bank_json": kb},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "DONOR_REPORT_NOT_FOUND"
