"""P0-1 classify isolation unit tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.reports.extraction.docling_adapter import DoclingIntakeError
from app.reports.models.enums import DocumentClassification, ExtractionStatus
from app.reports.orchestration.classify_isolation import process_classify_document
from app.reports.orchestration.pipeline import OrchestrationContext


def _document() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        mime_type="application/pdf",
        original_filename="scan.pdf",
        classification=None,
        extraction_status=ExtractionStatus.PENDING.value,
        extracted_json={},
    )


def _ctx() -> OrchestrationContext:
    return OrchestrationContext()


@pytest.mark.asyncio
async def test_classify_degrades_on_docling_intake_error():
    session = MagicMock()
    document = _document()

    with patch(
        "app.reports.orchestration.classify_isolation.load_document_extraction",
        side_effect=DoclingIntakeError("libxcb.so.1 missing"),
    ):
        degraded_id = await process_classify_document(
            session,
            document,
            ctx=_ctx(),
            stage="classify",
        )

    assert degraded_id == str(document.id)
    assert document.classification == DocumentClassification.OTHER.value
    assert document.extraction_status == ExtractionStatus.FAILED.value
    assert document.extracted_json["intake_outcome"] == "unreadable"


@pytest.mark.asyncio
async def test_classify_continues_after_degrade():
    session = MagicMock()
    document = _document()

    with patch(
        "app.reports.orchestration.classify_isolation.load_document_extraction",
        return_value={"text": "x" * 250, "conversion_status": "success", "conversion_errors": []},
    ), patch(
        "app.reports.orchestration.classify_isolation.dispatch_stage",
        new_callable=AsyncMock,
    ) as dispatch:
        dispatch.return_value = SimpleNamespace(
            result=SimpleNamespace(
                intake_outcome="complete",
                classification=DocumentClassification.PROPOSAL.value,
            )
        )
        degraded_id = await process_classify_document(
            session,
            document,
            ctx=_ctx(),
            stage="classify",
        )

    assert degraded_id is None
    assert document.classification == DocumentClassification.PROPOSAL.value
