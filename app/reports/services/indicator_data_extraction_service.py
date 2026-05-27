"""Persist indicator-data extraction results to uploaded_documents."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.reports.agents.indicator_data_extractor import (
    AGENT_NAME,
    IndicatorDataExtractorError,
    IndicatorDataExtractorResult,
    compute_content_hash,
    extract_indicator_data_text,
)
from app.reports.models.enums import DocumentClassification, ExtractionStatus
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.schemas.indicator_data_extraction_v1 import IndicatorDataExtractedEnvelope

logger = logging.getLogger("reports.services.indicator_data_extraction")

QueryFn = Callable[..., AsyncIterator[Any]]

_ALLOWED_CLASSIFICATIONS = frozenset({DocumentClassification.INDICATOR_DATA.value})


class IndicatorDataExtractionServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_indicator_data_document(document: UploadedDocument) -> None:
    if document.classification not in _ALLOWED_CLASSIFICATIONS:
        raise IndicatorDataExtractionServiceError(
            "STOP_WRONG_CLASSIFICATION",
            f"Document classification must be indicator_data, got "
            f"{document.classification!r}",
        )


def _envelope_to_json(envelope: IndicatorDataExtractedEnvelope) -> dict:
    return envelope.model_dump(mode="json")


async def extract_and_persist_indicator_data(
    db: Session,
    document_id: uuid.UUID,
    spreadsheet_json: str,
    *,
    content_hash: str | None = None,
    query_fn: QueryFn | None = None,
    per_attempt_timeout_seconds: float | None = None,
) -> IndicatorDataExtractorResult:
    """Run D4 extraction and persist to uploaded_documents.extracted_json."""
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise IndicatorDataExtractionServiceError(
            "STOP_DOCUMENT_NOT_FOUND",
            f"Uploaded document {document_id} not found",
        )

    _require_indicator_data_document(document)

    prior_extracted_json = dict(document.extracted_json or {})
    resolved_hash = content_hash or compute_content_hash(spreadsheet_json)

    document.extraction_status = ExtractionStatus.PROCESSING.value
    db.add(document)
    db.flush()

    try:
        result = await extract_indicator_data_text(
            spreadsheet_json,
            filename=document.original_filename,
            query_fn=query_fn,
            per_attempt_timeout_seconds=per_attempt_timeout_seconds,
        )
    except IndicatorDataExtractorError as exc:
        document.extraction_status = ExtractionStatus.FAILED.value
        if prior_extracted_json.get("extractor_agent") == AGENT_NAME:
            document.extracted_json = {
                **prior_extracted_json,
                "error": exc.message,
                "agent_trace": {
                    **(prior_extracted_json.get("agent_trace") or {}),
                    "content_hash": resolved_hash,
                },
            }
        else:
            document.extracted_json = {
                "extractor_agent": AGENT_NAME,
                "extracted_at": None,
                "structured": {},
                "confidence": None,
                "error": exc.message,
                "agent_trace": {"content_hash": resolved_hash},
            }
        db.add(document)
        db.commit()
        raise

    envelope = result.envelope
    structured = envelope.structured
    if structured.extraction_outcome == "degraded":
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(envelope)
    elif structured.extraction_outcome == "failed":
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(
            envelope.model_copy(update={"error": "Extraction produced no usable rows"})
        )
    else:
        document.extraction_status = ExtractionStatus.COMPLETE.value
        document.extracted_json = _envelope_to_json(envelope)

    db.add(document)
    db.commit()
    db.refresh(document)
    return result
