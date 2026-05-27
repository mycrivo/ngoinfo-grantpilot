from types import SimpleNamespace

import pytest

from app.reports.services.document_storage_service import DocumentStorageService


def test_document_storage_service_requires_config():
    settings = SimpleNamespace(
        ME_DOCUMENTS_S3_ENDPOINT="",
        ME_DOCUMENTS_S3_ACCESS_KEY="",
        ME_DOCUMENTS_S3_SECRET="",
        ME_DOCUMENTS_S3_BUCKET="",
    )
    with pytest.raises(RuntimeError, match="Document storage is not configured"):
        DocumentStorageService(settings=settings)


def test_build_storage_ref_scopes_by_user_and_report():
    import uuid

    settings = SimpleNamespace(
        ME_DOCUMENTS_S3_ENDPOINT="http://localhost:9000",
        ME_DOCUMENTS_S3_ACCESS_KEY="key",
        ME_DOCUMENTS_S3_SECRET="secret",
        ME_DOCUMENTS_S3_BUCKET="bucket",
    )
    service = DocumentStorageService(settings=settings)
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    ref = service.build_storage_ref(user_id, report_id, "report file.pdf")
    assert ref.startswith(f"users/{user_id}/reports/{report_id}/")
    assert ref.endswith("report_file.pdf")
