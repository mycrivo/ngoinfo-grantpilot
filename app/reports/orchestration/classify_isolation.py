"""Per-document classify isolation — degrade unreadable docs instead of killing the job (P0-1)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.reports.agents.classifier import classify_document_text
from app.reports.extraction.docling_adapter import DoclingIntakeError
from app.reports.extraction.docling_content_guard import (
    UNREADABLE_DOCUMENT_LOW_CONTENT,
    assess_docling_usable,
)
from app.reports.models.enums import DocumentClassification, ExtractionStatus
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import StageFailure, dispatch_stage
from app.reports.orchestration.document_intake import (
    classification_from_mime,
    load_document_extraction,
)
from app.reports.orchestration.extract_isolation import classify_intake_exception
from app.reports.orchestration.systemic_extraction_failure import (
    is_systemic_extraction_failure,
)

if TYPE_CHECKING:
    from app.reports.orchestration.pipeline import OrchestrationContext

logger = logging.getLogger("reports.orchestration.classify_isolation")


class ClassifyHardFailure(Exception):
    """Run-level classify failure — caller maps to StageFailure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _unreadable_intake_json(*, code: str, reason: str) -> dict:
    return {
        "intake_outcome": "unreadable",
        "unreadable_code": code,
        "reason": reason,
    }


def _persist_classify_degrade(
    session: Session,
    document: UploadedDocument,
    *,
    code: str,
    reason: str,
) -> None:
    document.classification = DocumentClassification.OTHER.value
    document.extraction_status = ExtractionStatus.FAILED.value
    document.extracted_json = _unreadable_intake_json(code=code, reason=reason)
    session.add(document)


async def process_classify_document(
    session: Session,
    document: UploadedDocument,
    *,
    ctx: OrchestrationContext,
    stage: str,
) -> str | None:
    """
    Classify one document with per-document isolation.

    Returns degraded document id when intake/classify degraded; None on success.
    Raises ClassifyHardFailure for systemic failures.
    """
    mime_label = classification_from_mime(document.mime_type)
    if mime_label is not None:
        document.classification = mime_label
        session.add(document)
        return None

    try:
        if ctx.text_loader is not None:
            text = ctx.text_loader(document)
            extracted = {"text": text, "conversion_status": "success", "conversion_errors": []}
        else:
            extracted = load_document_extraction(document)
    except DoclingIntakeError as exc:
        action = classify_intake_exception(exc)
        if action == "hard_fail":
            raise ClassifyHardFailure(str(exc)) from exc
        _persist_classify_degrade(
            session,
            document,
            code=UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason=str(exc),
        )
        return str(document.id)

    except Exception as exc:
        action = classify_intake_exception(exc)
        if action == "hard_fail":
            raise ClassifyHardFailure(str(exc)) from exc
        _persist_classify_degrade(
            session,
            document,
            code=UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason=str(exc),
        )
        return str(document.id)

    text = extracted.get("text", "")
    unreadable = assess_docling_usable(extracted)
    if unreadable is not None:
        _persist_classify_degrade(
            session,
            document,
            code=UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason=unreadable.reason,
        )
        return str(document.id)

    if not text.strip():
        _persist_classify_degrade(
            session,
            document,
            code=UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason="empty_text",
        )
        return str(document.id)

    try:
        outcome = await dispatch_stage(
            classify_document_text(
                text,
                filename=document.original_filename,
                mime_type=document.mime_type,
                query_fn=ctx.query_fn_classifier,
            ),
            stage=stage,
        )
    except StageFailure as exc:
        if is_systemic_extraction_failure(message=exc.message):
            raise ClassifyHardFailure(exc.message) from exc
        _persist_classify_degrade(
            session,
            document,
            code=UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason=exc.message,
        )
        return str(document.id)

    result = outcome.result
    if result.intake_outcome == "unreadable":
        _persist_classify_degrade(
            session,
            document,
            code=result.unreadable_code or UNREADABLE_DOCUMENT_LOW_CONTENT,
            reason="classifier_unreadable",
        )
        return str(document.id)

    document.classification = result.classification
    session.add(document)
    return None
