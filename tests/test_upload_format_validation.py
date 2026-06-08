"""Tests for P1 upload format gating — lane-based door validation (D1)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import app.core.security as security
from app.core.config import get_settings
from app.core.config import get_settings as config_get_settings
from app.core.errors import DomainError
from app.models.user import User
from app.services.quota_service import PLAN_IMPACT
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.services.document_storage_service import DocumentStorageService
from app.reports.services.donor_report_lifecycle_service import (
    create_donor_report,
    upload_document,
)
from app.reports.services.upload_format_validation import validate_upload_format
from tests.test_report_lifecycle_routes import _seed_template, lifecycle_api
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


@pytest.mark.parametrize(
    ("filename", "mime_type"),
    [
        ("proposal.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("award.pdf", "application/pdf"),
        ("notes.txt", "text/plain"),
        ("monitoring.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("actuals.csv", "text/csv"),
        ("site_photo.jpg", "image/jpeg"),
        ("site_photo.png", "image/png"),
        ("site_photo.gif", "image/gif"),
        ("site_photo.webp", "image/webp"),
        ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("slides.ppt", "application/vnd.ms-powerpoint"),
    ],
)
def test_validate_upload_format_accepts_d1_lanes(filename, mime_type):
    validate_upload_format(filename=filename, mime_type=mime_type)


@pytest.mark.parametrize(
    ("filename", "mime_type", "expected_lane", "expected_fragment"),
    [
        (
            "legacy.xls",
            "application/vnd.ms-excel",
            "spreadsheet",
            "Excel (.xlsx) or CSV (.csv)",
        ),
        (
            "legacy.ods",
            "application/vnd.oasis.opendocument.spreadsheet",
            "spreadsheet",
            "Excel (.xlsx) or CSV (.csv)",
        ),
        (
            "legacy.doc",
            "application/msword",
            "text",
            "Word (.docx), PDF (.pdf), or plain text (.txt)",
        ),
        (
            "archive.zip",
            "application/zip",
            "unsupported",
            "Compressed archives are not supported",
        ),
        (
            "random.bin",
            "application/octet-stream",
            "unsupported",
            "This file type is not supported",
        ),
    ],
)
def test_validate_upload_format_rejects_with_lane_specific_message(
    filename, mime_type, expected_lane, expected_fragment
):
    with pytest.raises(DomainError) as exc_info:
        validate_upload_format(filename=filename, mime_type=mime_type)

    error = exc_info.value
    assert error.error_code == "UNSUPPORTED_DOCUMENT_FORMAT"
    assert error.status_code == 422
    assert expected_fragment in error.message
    assert error.details is not None
    assert error.details["lane"] == expected_lane


def test_upload_reject_does_not_touch_storage_or_db(lifecycle_api):
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

    mock_storage = MagicMock()
    with patch(
        "app.reports.services.donor_report_lifecycle_service.DocumentStorageService",
    ) as mock_svc_cls:
        mock_svc_cls.return_value = mock_storage
        response = lifecycle_api.client.post(
            f"/api/reports/{report_id}/documents",
            headers=lifecycle_api.auth_header,
            files={"file": ("legacy.xls", b"excel-bytes", "application/vnd.ms-excel")},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "UNSUPPORTED_DOCUMENT_FORMAT"
    assert body["details"]["lane"] == "spreadsheet"
    assert "Excel (.xlsx) or CSV (.csv)" in body["message"]
    mock_storage.upload_bytes.assert_not_called()

    verify = lifecycle_api.session_factory()
    count = verify.query(UploadedDocument).filter_by(donor_report_id=report_id).count()
    verify.close()
    assert count == 0


def test_upload_docx_still_accepted_text_lane(lifecycle_api):
    """P1 accepts .docx in the text lane; NLCF classify→extract is out of P1 scope."""
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

    mock_storage = MagicMock()
    with patch(
        "app.reports.services.donor_report_lifecycle_service.DocumentStorageService",
    ) as mock_svc_cls:
        mock_svc_cls.return_value = mock_storage
        mock_svc_cls.build_storage_ref = DocumentStorageService.build_storage_ref
        response = lifecycle_api.client.post(
            f"/api/reports/{report_id}/documents",
            headers=lifecycle_api.auth_header,
            files={
                "file": (
                    "03_NLCF_Monitoring_Table.docx",
                    b"docx-bytes",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    mock_storage.upload_bytes.assert_called_once()

    verify = lifecycle_api.session_factory()
    doc = verify.query(UploadedDocument).filter_by(donor_report_id=report_id).one()
    verify.close()
    assert doc.original_filename == "03_NLCF_Monitoring_Table.docx"


def test_service_upload_reject_before_storage():
    session_factory = create_worker_validation_sessionmaker()
    session = session_factory()
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    session.add(
        User(
            id=user_id,
            email="fmt@example.org",
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

    with pytest.raises(DomainError) as exc_info:
        upload_document(
            session,
            donor_report_id=report.id,
            user_id=user_id,
            filename="data.zip",
            mime_type="application/zip",
            data=b"zip-bytes",
            storage=mock_storage,
        )

    assert exc_info.value.error_code == "UNSUPPORTED_DOCUMENT_FORMAT"
    mock_storage.upload_bytes.assert_not_called()
    assert session.query(UploadedDocument).filter_by(donor_report_id=report.id).count() == 0
    session.close()
