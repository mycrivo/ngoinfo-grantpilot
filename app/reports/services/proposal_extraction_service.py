"""Persist proposal extraction results to uploaded_documents."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.reports.agents.proposal_extractor import (
    AGENT_NAME,
    ProposalExtractorError,
    ProposalExtractorResult,
    compute_content_hash,
    extract_proposal_text,
)
from app.reports.models.enums import DocumentClassification, ExtractionStatus
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.schemas.proposal_extraction_v1 import ProposalExtractedEnvelope

logger = logging.getLogger("reports.services.proposal_extraction")

QueryFn = Callable[..., AsyncIterator[Any]]


class ProposalExtractionServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _require_proposal_document(document: UploadedDocument) -> None:
    if document.classification != DocumentClassification.PROPOSAL.value:
        raise ProposalExtractionServiceError(
            "STOP_WRONG_CLASSIFICATION",
            f"Document classification must be proposal, got {document.classification!r}",
        )


def _envelope_to_json(envelope: ProposalExtractedEnvelope) -> dict:
    return envelope.model_dump(mode="json")


async def extract_and_persist_proposal(
    db: Session,
    document_id: uuid.UUID,
    text: str,
    *,
    query_fn: QueryFn | None = None,
) -> ProposalExtractorResult:
    """Run D2 extraction and persist to uploaded_documents.extracted_json."""
    document = db.get(UploadedDocument, document_id)
    if document is None:
        raise ProposalExtractionServiceError(
            "STOP_DOCUMENT_NOT_FOUND",
            f"Uploaded document {document_id} not found",
        )

    _require_proposal_document(document)

    prior_extracted_json = dict(document.extracted_json or {})
    content_hash = compute_content_hash(text)

    document.extraction_status = ExtractionStatus.PROCESSING.value
    db.add(document)
    db.flush()

    try:
        result = await extract_proposal_text(
            text,
            filename=document.original_filename,
            query_fn=query_fn,
        )
    except ProposalExtractorError as exc:
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
    if structured.extraction_outcome == "unreadable":
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(envelope)
    elif structured.extraction_outcome == "failed":
        document.extraction_status = ExtractionStatus.FAILED.value
        document.extracted_json = _envelope_to_json(
            envelope.model_copy(update={"error": "Extraction produced no usable items"})
        )
    else:
        document.extraction_status = ExtractionStatus.COMPLETE.value
        document.extracted_json = _envelope_to_json(envelope)

    db.add(document)
    db.commit()
    db.refresh(document)
    return result


def extract_and_persist_proposal_sync(
    db: Session,
    document_id: uuid.UUID,
    text: str,
    *,
    query_fn: QueryFn | None = None,
) -> ProposalExtractorResult:
    import asyncio

    return asyncio.run(
        extract_and_persist_proposal(
            db,
            document_id,
            text,
            query_fn=query_fn,
        )
    )
