"""A-02 — M&E plan gate and report-creation quota enforcement tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.core.security as security
from app.core.config import get_settings
from app.core.config import get_settings as config_get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.main import create_app
from app.models.usage_ledger import UsageActionType, UsageLedger
from app.models.user import User
from app.services.quota_service import (
    PLAN_FREE,
    PLAN_GROWTH,
    PLAN_IMPACT,
    get_entitlements,
    release_report_create_quota,
)
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DonorReportStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.services.document_storage_service import DocumentStorageService
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


_CREATE_JSON = {
    "reporting_period_start": "2025-01-01",
    "reporting_period_end": "2025-12-31",
}


def _seed_template(session) -> FunderReportTemplate:
    now = datetime.now(timezone.utc)
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="Enforcement Test Funder",
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


def _create_payload(template_id: uuid.UUID) -> dict:
    return {
        **_CREATE_JSON,
        "funder_report_template_id": str(template_id),
    }


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def _me_api(*, plan_name: str = PLAN_IMPACT):
    session_factory = create_worker_validation_sessionmaker()
    user_id = uuid.uuid4()
    db = session_factory()
    now = datetime.now(timezone.utc)
    db.add(
        User(
            id=user_id,
            email=f"me-enforce-{user_id.hex[:8]}@example.org",
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
    token, _ = create_access_token(str(user_id), "me@example.org", "free")
    client = TestClient(app)
    return SimpleNamespace(
        client=client,
        token=token,
        user_id=user_id,
        template_id=template_id,
        session_factory=session_factory,
        auth_header={"Authorization": f"Bearer {token}"},
    )


def _upgrade_required_body() -> dict:
    return {
        "error_code": "UPGRADE_REQUIRED",
        "message": "M&E reporting is available on the Impact plan.",
        "details": {
            "required_plan": PLAN_IMPACT,
            "feature": "me_reports",
        },
    }


def _seed_report_create_rows(session_factory, user_id: uuid.UUID, count: int) -> None:
    db = session_factory()
    plan = seed_user_plan(db, user_id, plan_name=PLAN_IMPACT)
    period_start = plan.billing_period_start or datetime.now(timezone.utc)
    for index in range(count):
        db.add(
            UsageLedger(
                id=uuid.uuid4(),
                user_id=user_id,
                event_type=UsageActionType.REPORT_CREATE.value,
                occurred_at=period_start + timedelta(hours=index + 1),
                idempotency_key=f"report:create:seed:{index}",
                metadata_json={},
            )
        )
    db.commit()
    db.close()


def test_free_user_create_returns_upgrade_required():
    api = _me_api(plan_name=PLAN_FREE)
    response = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert response.status_code == 403
    assert response.json() == _upgrade_required_body()


def test_growth_user_upload_returns_upgrade_required():
    api = _me_api(plan_name=PLAN_GROWTH)
    session = api.session_factory()
    now = datetime.now(timezone.utc)
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="__default__",
        template_name="__lifecycle_default__",
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
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=api.user_id,
        funder_report_template_id=template.id,
        reporting_period_start=datetime(2025, 1, 1).date(),
        reporting_period_end=datetime(2025, 12, 31).date(),
        status=DonorReportStatus.DRAFT.value,
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add_all([template, report])
    session.commit()
    report_id = report.id
    session.close()

    response = api.client.post(
        f"/api/reports/{report_id}/documents",
        headers=api.auth_header,
        files={"file": ("a.pdf", b"%PDF-sample", "application/pdf")},
    )
    assert response.status_code == 403
    assert response.json() == _upgrade_required_body()


def test_impact_user_passes_plan_gate_on_create_and_upload():
    api = _me_api(plan_name=PLAN_IMPACT)
    create_resp = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert create_resp.status_code == 200
    report_id = create_resp.json()["id"]

    mock_storage = MagicMock()
    real_build_storage_ref = DocumentStorageService.build_storage_ref
    with patch(
        "app.reports.services.donor_report_lifecycle_service.DocumentStorageService",
    ) as mock_svc_cls:
        mock_svc_cls.return_value = mock_storage
        mock_svc_cls.build_storage_ref = real_build_storage_ref
        upload_resp = api.client.post(
            f"/api/reports/{report_id}/documents",
            headers=api.auth_header,
            files={"file": ("proposal.pdf", b"%PDF-sample", "application/pdf")},
        )
    assert upload_resp.status_code == 200


def test_impact_create_decrements_reports_used():
    api = _me_api(plan_name=PLAN_IMPACT)
    response = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert response.status_code == 200

    db = api.session_factory()
    entitlements = get_entitlements(db, api.user_id)
    reports = entitlements["entitlements"]["reports"]
    assert reports["limit"] == 2
    assert reports["used"] == 1
    assert reports["remaining"] == 1
    db.close()


def test_impact_third_create_returns_quota_exceeded():
    api = _me_api(plan_name=PLAN_IMPACT)
    _seed_report_create_rows(api.session_factory, api.user_id, count=2)

    response = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert response.status_code == 429
    body = response.json()
    assert body["error_code"] == "QUOTA_EXCEEDED"
    assert body["message"] == "You have used all M&E reports for this billing period."
    details = body["details"]
    assert details["entitlement"] == "reports"
    assert details["limit"] == 2
    assert details["used"] == 2
    assert details["remaining"] == 0
    assert details["period"] == "BILLING_CYCLE"
    assert details["reset_at"] is not None
    assert "required_plan" not in details
    assert "upgrade" not in body["message"].lower()


def test_second_create_returns_429_when_one_slot_remains():
    api = _me_api(plan_name=PLAN_IMPACT)
    _seed_report_create_rows(api.session_factory, api.user_id, count=1)

    first = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    second = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json={
            "funder_report_template_id": str(api.template_id),
            "reporting_period_start": "2024-01-01",
            "reporting_period_end": "2024-12-31",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 429

    db = api.session_factory()
    ledger_count = db.execute(
        select(func.count())
        .select_from(UsageLedger)
        .where(
            UsageLedger.user_id == api.user_id,
            UsageLedger.event_type == UsageActionType.REPORT_CREATE.value,
        )
    ).scalar_one()
    report_count = db.execute(
        select(func.count())
        .select_from(DonorReport)
        .where(DonorReport.user_id == api.user_id)
    ).scalar_one()
    db.close()
    assert ledger_count == 2
    assert report_count == 1


def test_record_usage_quota_check_rolls_back_report():
    """When quota is exhausted at record_usage time, no report or ledger row persists."""
    api = _me_api(plan_name=PLAN_IMPACT)
    _seed_report_create_rows(api.session_factory, api.user_id, count=1)

    call_count = {"n": 0}

    def _fake_usage_count(*_args, **_kwargs):
        call_count["n"] += 1
        return 1 if call_count["n"] == 1 else 2

    with patch("app.services.quota_service._usage_count", side_effect=_fake_usage_count):
        response = api.client.post(
            "/api/reports",
            headers=api.auth_header,
            json=_create_payload(api.template_id),
        )

    assert response.status_code == 429
    assert response.json()["error_code"] == "QUOTA_EXCEEDED"

    db = api.session_factory()
    ledger_count = db.execute(
        select(func.count())
        .select_from(UsageLedger)
        .where(
            UsageLedger.user_id == api.user_id,
            UsageLedger.event_type == UsageActionType.REPORT_CREATE.value,
        )
    ).scalar_one()
    report_count = db.execute(
        select(func.count())
        .select_from(DonorReport)
        .where(DonorReport.user_id == api.user_id)
    ).scalar_one()
    db.close()
    assert ledger_count == 1
    assert report_count == 0


def test_create_failure_no_ledger_row():
    api = _me_api(plan_name=PLAN_IMPACT)
    client = TestClient(api.client.app, raise_server_exceptions=False)
    with patch(
        "app.reports.services.donor_report_lifecycle_service.record_usage",
        side_effect=RuntimeError("simulated persistence failure"),
    ):
        response = client.post(
            "/api/reports",
            headers=api.auth_header,
            json=_create_payload(api.template_id),
        )
    assert response.status_code == 500

    db = api.session_factory()
    ledger_count = db.execute(
        select(func.count())
        .select_from(UsageLedger)
        .where(
            UsageLedger.user_id == api.user_id,
            UsageLedger.event_type == UsageActionType.REPORT_CREATE.value,
        )
    ).scalar_one()
    report_count = db.execute(
        select(func.count())
        .select_from(DonorReport)
        .where(DonorReport.user_id == api.user_id)
    ).scalar_one()
    db.close()
    assert ledger_count == 0
    assert report_count == 0


def test_export_does_not_change_reports_used():
    api = _me_api(plan_name=PLAN_IMPACT)
    create_resp = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert create_resp.status_code == 200
    report_id = create_resp.json()["id"]

    db = api.session_factory()
    before = get_entitlements(db, api.user_id)["entitlements"]["reports"]["used"]
    db.close()

    export_resp = api.client.get(
        f"/api/reports/{report_id}/export",
        headers=api.auth_header,
    )
    assert export_resp.status_code in (200, 404)

    db = api.session_factory()
    after = get_entitlements(db, api.user_id)["entitlements"]["reports"]["used"]
    db.close()
    assert after == before == 1


def test_job_failure_refunds_report_create_quota():
    from app.reports.models.enums import ReportJobStage, ReportJobStatus
    from app.reports.models.report_job import ReportJob
    from app.reports.worker.job_failure import FAILURE_EVENT_EXCEPTION, mark_job_failed

    api = _me_api(plan_name=PLAN_IMPACT)
    create_resp = api.client.post(
        "/api/reports",
        headers=api.auth_header,
        json=_create_payload(api.template_id),
    )
    assert create_resp.status_code == 200
    report_id = uuid.UUID(create_resp.json()["id"])

    db = api.session_factory()
    before = get_entitlements(db, api.user_id)["entitlements"]["reports"]["used"]
    job = ReportJob(
        id=uuid.uuid4(),
        donor_report_id=report_id,
        stage=ReportJobStage.EXTRACT.value,
        status=ReportJobStatus.RUNNING.value,
        agent_trace_json={},
    )
    db.add(job)
    db.commit()

    assert mark_job_failed(
        db,
        job,
        error="extract: simulated failure",
        event=FAILURE_EVENT_EXCEPTION,
    )
    after = get_entitlements(db, api.user_id)["entitlements"]["reports"]["used"]
    refund_count = db.execute(
        select(func.count())
        .select_from(UsageLedger)
        .where(
            UsageLedger.user_id == api.user_id,
            UsageLedger.event_type == UsageActionType.REPORT_CREATE_REFUND.value,
        )
    ).scalar_one()
    db.close()

    assert before == 1
    assert after == 0
    assert refund_count == 1

    db = api.session_factory()
    refund_again = release_report_create_quota(
        db,
        api.user_id,
        report_id,
        commit=True,
    )
    after_repeat = get_entitlements(db, api.user_id)["entitlements"]["reports"]["used"]
    db.close()
    assert refund_again is False
    assert after_repeat == 0
