"""P3-6 reliability — R2 delete ordering, synthesis advisory lock."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.reports.services.document_storage_service import DocumentStorageError
from app.reports.services.donor_report_lifecycle_service import delete_document
from app.reports.services.report_synthesis_service import (
    _acquire_synthesis_lock,
    synthesise_and_persist,
)
from tests.orchestrator_mocks import fcdo_synthesis_query_fn
from tests.worker_validation_seed import create_worker_validation_sessionmaker

FCDO_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "artefacts"
    / "me_module"
    / "TEMPLATE_INSTANCE_FCDO.json"
)


@pytest.fixture
def lifecycle_db():
    return create_worker_validation_sessionmaker()


def _seed_deletable_document(session):
    from app.models.user import User
    from app.reports.models.donor_report import DonorReport
    from app.reports.models.funder_report_template import FunderReportTemplate
    from app.reports.models.uploaded_document import UploadedDocument
    from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
        KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        RECONCILER_AGENT_NAME,
    )

    now = datetime.now(timezone.utc)
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"p36-{user_id.hex[:8]}@example.org",
        auth_provider="email",
        created_at=now,
        updated_at=now,
    )
    template = FunderReportTemplate(
        id=uuid.uuid4(),
        funder_name="FCDO",
        template_name="Annual Review",
        region="uk",
        reporting_frequency="annual",
        report_sections_json=[],
        format_rules_json={},
        terminology_map_json={},
        docx_template_ref="test.docx",
        is_active=True,
        version=1,
        created_at=now,
        updated_at=now,
    )
    report = DonorReport(
        id=uuid.uuid4(),
        user_id=user_id,
        funder_report_template_id=template.id,
        reporting_period_start=date(2025, 1, 1),
        reporting_period_end=date(2025, 12, 31),
        status="DRAFT",
        knowledge_bank_json={
            "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
            "facts": {},
            "conflicts": [],
            "gap_answers": {},
            "gate1_confirmed_at": now.isoformat(),
            "reconciler_agent": RECONCILER_AGENT_NAME,
        },
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
        version=1,
        created_at=now,
        updated_at=now,
    )
    doc_id = uuid.uuid4()
    document = UploadedDocument(
        id=doc_id,
        donor_report_id=report.id,
        user_id=user_id,
        original_filename="proposal.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        storage_ref=f"users/{user_id}/reports/{report.id}/{doc_id}/proposal.pdf",
        classification=None,
        extraction_status="PENDING",
        extracted_json={},
        created_at=now,
    )
    session.add_all([user, template, report, document])
    session.commit()
    return report.id, doc_id, user_id, document.storage_ref


def test_delete_document_db_before_storage_and_fail_loud(lifecycle_db):
    from app.reports.models.uploaded_document import UploadedDocument

    session = lifecycle_db()
    report_id, doc_id, user_id, storage_ref = _seed_deletable_document(session)
    session.close()

    mock_storage = MagicMock()

    def _delete(key: str) -> None:
        verify = lifecycle_db()
        row = verify.query(UploadedDocument).filter_by(id=doc_id).first()
        verify.close()
        assert row is None, "DB row must be deleted before storage delete"
        assert key == storage_ref

    mock_storage.delete_object.side_effect = _delete

    session = lifecycle_db()
    delete_document(
        session,
        donor_report_id=report_id,
        document_id=doc_id,
        user_id=user_id,
        storage=mock_storage,
    )
    session.close()
    mock_storage.delete_object.assert_called_once_with(storage_ref)


def test_delete_document_raises_when_storage_cleanup_fails(lifecycle_db):
    from app.core.errors import DomainError

    session = lifecycle_db()
    report_id, doc_id, user_id, _storage_ref = _seed_deletable_document(session)
    session.close()

    mock_storage = MagicMock()
    mock_storage.delete_object.side_effect = DocumentStorageError(
        "STORAGE_DELETE_FAILED",
        "simulated R2 failure",
    )

    session = lifecycle_db()
    with pytest.raises(DomainError) as exc_info:
        delete_document(
            session,
            donor_report_id=report_id,
            document_id=doc_id,
            user_id=user_id,
            storage=mock_storage,
        )
    session.close()
    assert exc_info.value.error_code == "DOCUMENT_STORAGE_DELETE_FAILED"


def test_synthesis_lock_noop_on_sqlite(lifecycle_db):
    session = lifecycle_db()
    _acquire_synthesis_lock(session, uuid.uuid4())
    session.close()


def test_synthesis_output_unchanged_when_lock_enabled(synthesis_db):
    """Advisory lock hook must not alter synthesis content (F-5)."""
    from app.reports.models.donor_report import DonorReport
    from tests.test_report_synthesis_service import _seed_report_ready_for_synthesis

    session = synthesis_db()
    report_id = _seed_report_ready_for_synthesis(session)
    session.close()

    query_fn = fcdo_synthesis_query_fn()

    session = synthesis_db()
    baseline = asyncio.run(
        synthesise_and_persist(session, report_id, query_fn_synthesis=query_fn)
    )
    report = session.get(DonorReport, report_id)
    baseline_content = json.dumps(report.content_json, sort_keys=True)
    session.close()

    session = synthesis_db()
    report = session.get(DonorReport, report_id)
    report.content_json = {}
    report.status = "DRAFT"
    session.add(report)
    session.commit()
    session.close()

    session = synthesis_db()
    with patch(
        "app.reports.services.report_synthesis_service._acquire_synthesis_lock",
    ) as lock_mock:
        locked = asyncio.run(
            synthesise_and_persist(session, report_id, query_fn_synthesis=query_fn)
        )
        report = session.get(DonorReport, report_id)
        locked_content = json.dumps(report.content_json, sort_keys=True)
        lock_mock.assert_called_once()
    session.close()

    assert baseline.generated == locked.generated == 6
    assert baseline_content == locked_content


@pytest.fixture
def synthesis_db():
    return create_worker_validation_sessionmaker()
