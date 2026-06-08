"""Persist grant-terms extraction results to uploaded_documents."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.reports.agents.grant_terms_extractor import (
    AGENT_NAME,
    GrantTermsExtractorError,
    GrantTermsExtractorResult,
    build_degraded_extraction_stop_result,
    compute_content_hash,
    extract_grant_terms_text,
)
from app.reports.models.enums import DocumentClassification, ExtractionStatus
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.schemas.grant_terms_extraction_v1 import GrantTermsExtractedEnvelope

logger = logging.getLogger("reports.services.grant_terms_extraction")

QueryFn = Callable[..., AsyncIterator[Any]]

_ALLOWED_CLASSIFICATIONS = frozenset(
    {
        DocumentClassification.GRANT_LETTER.value,
        DocumentClassification.MOU.value,
    }
)


class GrantTermsExtractionServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_grant_terms_document(document: UploadedDocument) -> None:
    if document.classification not in _ALLOWED_CLASSIFICATIONS:
        raise GrantTermsExtractionServiceError(
            "STOP_WRONG_CLASSIFICATION",
            f"Document classification must be grant_letter or mou, got "
            f"{document.classification!r}",
        )


def _envelope_to_json(envelope: GrantTermsExtractedEnvelope) -> dict:
    return envelope.model_dump(mode="json")


async def extract_and_persist_grant_terms(
    db: Session,
    document_id: uuid.UUID,
    text: str,
    *,
    query_fn: QueryFn | None = None,
    per_attempt_timeout_seconds: float | None = None,
) -> GrantTermsExtractorResult:
    """Run D3 extraction and persist to uploaded_documents.extracted_json."""
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise GrantTermsExtractionServiceError(
            "STOP_DOCUMENT_NOT_FOUND",
            f"Uploaded document {document_id} not found",
        )

    _require_grant_terms_document(document)

    prior_extracted_json = dict(document.extracted_json or {})
    content_hash = compute_content_hash(text)

    document.extraction_status = ExtractionStatus.PROCESSING.value
    db.add(document)
    db.flush()

    try:
        result = await extract_grant_terms_text(
            text,
            filename=document.original_filename,
            query_fn=query_fn,
            per_attempt_timeout_seconds=per_attempt_timeout_seconds,
        )
    except GrantTermsExtractorError as exc:
        document.extraction_status = ExtractionStatus.FAILED.value
        if prior_extracted_json.get("extractor_agent") == AGENT_NAME:
            document.extracted_json = {
                **prior_extracted_json,
                "error": exc.message,
                "agent_trace": {
                    **(prior_extracted_json.get("agent_trace") or {}),
                    "content_hash": content_hash,
                },
            }
        else:
            document.extracted_json = {
                "extractor_agent": AGENT_NAME,
                "extracted_at": None,
                "structured": {},
                "confidence": None,
                "error": exc.message,
                "agent_trace": {"content_hash": content_hash},
            }
        db.add(document)
        db.commit()
        raise

    envelope = result.envelope
    structured = envelope.structured
    if structured.extraction_outcome in ("degraded", "unreadable"):
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(envelope)
    elif structured.extraction_outcome == "failed":
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(
            envelope.model_copy(update={"error": "Extraction produced no usable fields"})
        )
    else:
        document.extraction_status = ExtractionStatus.COMPLETE.value
        document.extracted_json = _envelope_to_json(envelope)

    db.add(document)
    db.commit()
    db.refresh(document)
    return result


async def persist_degraded_grant_terms_extraction(
    db: Session,
    document_id: uuid.UUID,
    *,
    degraded_code: str,
    content_hash: str | None = None,
) -> GrantTermsExtractorResult:
    """Persist typed terminal degrade on uploaded_documents — never raises."""
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise GrantTermsExtractionServiceError(
            "STOP_DOCUMENT_NOT_FOUND",
            f"Uploaded document {document_id} not found",
        )
    _require_grant_terms_document(document)
    resolved_hash = content_hash or compute_content_hash(
        f"degraded:{document.original_filename}"
    )
    result = build_degraded_extraction_stop_result(
        content_hash=resolved_hash,
        stop_code=degraded_code,
    )
    document.extraction_status = ExtractionStatus.FAILED.value
    document.extracted_json = _envelope_to_json(result.envelope)
    db.add(document)
    db.commit()
    db.refresh(document)
    return result


def extract_and_persist_grant_terms_sync(
    db: Session,
    document_id: uuid.UUID,
    text: str,
    *,
    query_fn: QueryFn | None = None,
) -> GrantTermsExtractorResult:
    import asyncio

    return asyncio.run(
        extract_and_persist_grant_terms(
            db,
            document_id,
            text,
            query_fn=query_fn,
        )
    )
