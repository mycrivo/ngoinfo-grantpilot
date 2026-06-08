"""Per-document extract isolation — degrade vs hard-fail routing (P2)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session

from app.reports.agents.grant_terms_extractor import GrantTermsExtractorError
from app.reports.agents.indicator_data_extractor import (
    DEGRADED_EXTRACTION_UNPARSEABLE,
    IndicatorDataExtractorError,
)
from app.reports.agents.proposal_extractor import ProposalExtractorError
from app.reports.extraction.docling_adapter import DoclingIntakeError
from app.reports.models.enums import DocumentClassification
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import DispatchOutcome, is_degraded_result
from app.reports.orchestration.document_intake import load_document_text, load_spreadsheet_json
from app.reports.orchestration.extract_stage_state import ExtractStageRunState
from app.reports.orchestration.systemic_extraction_failure import is_systemic_extraction_failure
from app.reports.services.grant_terms_extraction_service import (
    GrantTermsExtractionServiceError,
    extract_and_persist_grant_terms,
    persist_degraded_grant_terms_extraction,
)
from app.reports.services.indicator_data_extraction_service import (
    IndicatorDataExtractionServiceError,
    extract_and_persist_indicator_data,
    persist_degraded_indicator_data_extraction,
    persist_degraded_indicator_unparseable,
)
from app.reports.services.proposal_extraction_service import (
    ProposalExtractionServiceError,
    extract_and_persist_proposal,
    persist_degraded_proposal_extraction,
)

if TYPE_CHECKING:
    from app.reports.orchestration.pipeline import OrchestrationContext

logger = logging.getLogger("reports.orchestration.extract_isolation")

_EXTRACT_SKIP_CLASSIFICATIONS = frozenset(
    {
        DocumentClassification.PHOTO.value,
        DocumentClassification.DECK.value,
        DocumentClassification.OTHER.value,
    }
)


class ExtractHardFailure(Exception):
    """Run-level failure — caller maps to StageFailure."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def classify_intake_exception(exc: Exception) -> str:
    """Return 'hard_fail' or 'degrade' for load/intake errors."""
    if isinstance(exc, DoclingIntakeError):
        return "degrade"
    if is_systemic_extraction_failure(message=str(exc)):
        return "hard_fail"
    if isinstance(exc, RuntimeError):
        return "hard_fail"
    if isinstance(exc, (ClientError, BotoCoreError)):
        if isinstance(exc, ClientError):
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return "degrade"
        return "hard_fail"
    if isinstance(exc, ValueError):
        return "degrade"
    return "degrade"


async def _persist_text_lane_degrade(
    session: Session,
    document: UploadedDocument,
    *,
    degraded_code: str,
) -> None:
    classification = document.classification
    if classification == DocumentClassification.PROPOSAL.value:
        await persist_degraded_proposal_extraction(
            session,
            document.id,
            degraded_code=degraded_code,
        )
    elif classification in (
        DocumentClassification.GRANT_LETTER.value,
        DocumentClassification.MOU.value,
    ):
        await persist_degraded_grant_terms_extraction(
            session,
            document.id,
            degraded_code=degraded_code,
        )
    else:
        await persist_degraded_indicator_data_extraction(
            session,
            document.id,
            degraded_code=degraded_code,
        )


async def _handle_extractor_stop(
    session: Session,
    document: UploadedDocument,
    *,
    code: str,
    message: str,
    state: ExtractStageRunState,
) -> None:
    action = state.resolve_agent_stop_action(code=code, message=message)
    if action == "hard_fail":
        raise ExtractHardFailure(message)
    await _persist_text_lane_degrade(session, document, degraded_code=code)
    if code == "STOP_AGENT_ERROR":
        state.record_ambiguous_agent_stop_degraded()


async def _run_proposal_extract(
    session: Session,
    document: UploadedDocument,
    ctx: OrchestrationContext,
    state: ExtractStageRunState,
    *,
    stage: str,
) -> DispatchOutcome:
    try:
        text = load_document_text(document, loader_override=ctx.text_loader)
    except Exception as exc:
        if classify_intake_exception(exc) == "hard_fail":
            raise ExtractHardFailure(str(exc)) from exc
        await persist_degraded_proposal_extraction(
            session,
            document.id,
            degraded_code=DEGRADED_EXTRACTION_UNPARSEABLE,
        )
        return DispatchOutcome(result=None, degraded=True)

    try:
        result = await extract_and_persist_proposal(
            session,
            document.id,
            text,
            query_fn=ctx.query_fn_proposal,
            per_attempt_timeout_seconds=ctx.proposal_timeout_seconds,
        )
    except ProposalExtractionServiceError as exc:
        raise ExtractHardFailure(exc.message) from exc
    except ProposalExtractorError as exc:
        await _handle_extractor_stop(
            session,
            document,
            code=exc.code,
            message=exc.message,
            state=state,
        )
        return DispatchOutcome(result=None, degraded=True)

    degraded = is_degraded_result(result)
    if not degraded:
        state.record_extract_success()
    return DispatchOutcome(result=result, degraded=degraded)


async def _run_grant_terms_extract(
    session: Session,
    document: UploadedDocument,
    ctx: OrchestrationContext,
    state: ExtractStageRunState,
    *,
    stage: str,
) -> DispatchOutcome:
    try:
        text = load_document_text(document, loader_override=ctx.text_loader)
    except Exception as exc:
        if classify_intake_exception(exc) == "hard_fail":
            raise ExtractHardFailure(str(exc)) from exc
        await persist_degraded_grant_terms_extraction(
            session,
            document.id,
            degraded_code=DEGRADED_EXTRACTION_UNPARSEABLE,
        )
        return DispatchOutcome(result=None, degraded=True)

    try:
        result = await extract_and_persist_grant_terms(
            session,
            document.id,
            text,
            query_fn=ctx.query_fn_grant_terms,
            per_attempt_timeout_seconds=ctx.grant_terms_timeout_seconds,
        )
    except GrantTermsExtractionServiceError as exc:
        raise ExtractHardFailure(exc.message) from exc
    except GrantTermsExtractorError as exc:
        await _handle_extractor_stop(
            session,
            document,
            code=exc.code,
            message=exc.message,
            state=state,
        )
        return DispatchOutcome(result=None, degraded=True)

    degraded = is_degraded_result(result)
    if not degraded:
        state.record_extract_success()
    return DispatchOutcome(result=result, degraded=degraded)


async def _run_indicator_extract(
    session: Session,
    document: UploadedDocument,
    ctx: OrchestrationContext,
    state: ExtractStageRunState,
    *,
    stage: str,
) -> DispatchOutcome:
    try:
        spreadsheet_json, content_hash = load_spreadsheet_json(
            document,
            loader_override=ctx.spreadsheet_loader,
        )
    except Exception as exc:
        if classify_intake_exception(exc) == "hard_fail":
            raise ExtractHardFailure(str(exc)) from exc
        await persist_degraded_indicator_unparseable(session, document.id)
        return DispatchOutcome(result=None, degraded=True)

    try:
        result = await extract_and_persist_indicator_data(
            session,
            document.id,
            spreadsheet_json,
            content_hash=content_hash,
            query_fn=ctx.query_fn_indicator_data,
            per_attempt_timeout_seconds=ctx.indicator_timeout_seconds,
        )
    except IndicatorDataExtractionServiceError as exc:
        raise ExtractHardFailure(exc.message) from exc
    except IndicatorDataExtractorError as exc:
        await _handle_extractor_stop(
            session,
            document,
            code=exc.code,
            message=exc.message,
            state=state,
        )
        return DispatchOutcome(result=None, degraded=True)

    degraded = is_degraded_result(result)
    if not degraded:
        state.record_extract_success()
    return DispatchOutcome(result=result, degraded=degraded)


async def process_extract_document(
    session: Session,
    document: UploadedDocument,
    ctx: OrchestrationContext,
    state: ExtractStageRunState,
    *,
    stage: str,
) -> bool:
    """Extract one document; return True when degraded. Raises ExtractHardFailure."""
    classification = document.classification
    if not classification or classification in _EXTRACT_SKIP_CLASSIFICATIONS:
        return False

    if classification == DocumentClassification.PROPOSAL.value:
        outcome = await _run_proposal_extract(session, document, ctx, state, stage=stage)
    elif classification in (
        DocumentClassification.GRANT_LETTER.value,
        DocumentClassification.MOU.value,
    ):
        outcome = await _run_grant_terms_extract(session, document, ctx, state, stage=stage)
    elif classification == DocumentClassification.INDICATOR_DATA.value:
        outcome = await _run_indicator_extract(session, document, ctx, state, stage=stage)
    else:
        return False

    return outcome.degraded
