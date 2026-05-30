"""Orchestrated walk: classify -> extract -> reconcile -> Gate 1 halt (+ gap resume boundary)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.reports.agents.classifier import classify_document_text
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DocumentClassification, ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import DispatchOutcome, StageFailure, dispatch_stage
from app.reports.orchestration.document_intake import (
    classification_from_mime,
    load_document_text,
    load_spreadsheet_json,
)
from app.reports.services.grant_terms_extraction_service import (
    GrantTermsExtractionServiceError,
    extract_and_persist_grant_terms,
)
from app.reports.services.indicator_data_extraction_service import (
    IndicatorDataExtractionServiceError,
    extract_and_persist_indicator_data,
)
from app.reports.services.knowledge_bank_reconciliation_service import (
    KnowledgeBankReconciliationServiceError,
    reconcile_and_persist,
)
from app.reports.services.proposal_extraction_service import (
    ProposalExtractionServiceError,
    extract_and_persist_proposal,
)

logger = logging.getLogger("reports.orchestration.pipeline")

_EXTRACT_SKIP_CLASSIFICATIONS = frozenset(
    {
        DocumentClassification.PHOTO.value,
        DocumentClassification.DECK.value,
        DocumentClassification.OTHER.value,
    }
)


@dataclass
class OrchestrationContext:
    """Optional hooks for tests — no live API or storage required."""

    query_fn_classifier: Any | None = None
    query_fn_proposal: Any | None = None
    query_fn_grant_terms: Any | None = None
    query_fn_indicator_data: Any | None = None
    query_fn_reconciler: Any | None = None
    text_loader: Callable[[UploadedDocument], str] | None = None
    spreadsheet_loader: Callable[[UploadedDocument], tuple[str, str | None]] | None = None
    reconciler_timeout_seconds: float | None = None
    grant_terms_timeout_seconds: float | None = None
    indicator_timeout_seconds: float | None = None
    stage_hooks: dict[str, Callable[..., None]] = field(default_factory=dict)


def _append_stage_trace(job: ReportJob, stage: str, entry: dict[str, Any]) -> None:
    trace = dict(job.agent_trace_json or {})
    stages = dict(trace.get("stages") or {})
    stages[stage] = entry
    trace["stages"] = stages
    job.agent_trace_json = trace


def _job_is_terminal(job: ReportJob) -> bool:
    return job.status in (
        ReportJobStatus.FAILED.value,
        ReportJobStatus.AWAITING_HUMAN.value,
    )


def _commit_checkpoint(
    session: Session,
    job: ReportJob,
    *,
    next_stage: str,
    stage_completed: str,
    trace_entry: dict[str, Any] | None = None,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    if trace_entry is not None:
        _append_stage_trace(job, stage_completed, trace_entry)
    job.stage = next_stage
    session.add(job)
    session.commit()


def _halt_gate1(session: Session, job: ReportJob, *, reconcile_trace: dict[str, Any]) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    _append_stage_trace(job, ReportJobStage.RECONCILE.value, reconcile_trace)
    job.stage = ReportJobStage.GAP.value
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    session.add(job)
    session.commit()
    logger.info(
        "gate1_halt job_id=%s donor_report_id=%s stage=gap status=awaiting_human",
        job.id,
        job.donor_report_id,
    )


def _park_gap_boundary(session: Session, job: ReportJob) -> None:
    """Resume boundary — Gate 1 confirmed; gap/E3 out of scope for this prompt."""
    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(ReportJobStage.GAP.value, "Donor report not found")
    if not (report.knowledge_bank_json or {}).get("gate1_confirmed_at"):
        raise StageFailure(
            ReportJobStage.GAP.value,
            "Gate 1 confirmation required before gap stage resume",
        )

    _append_stage_trace(
        job,
        ReportJobStage.GAP.value,
        {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "action": "parked_at_gap_boundary",
            "gate1_confirmed_at": report.knowledge_bank_json.get("gate1_confirmed_at"),
        },
    )
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    job.stage = ReportJobStage.GAP.value
    session.add(job)
    session.commit()
    logger.info(
        "gap_boundary_parked job_id=%s donor_report_id=%s awaiting_human",
        job.id,
        job.donor_report_id,
    )


async def _run_classify_stage(
    session: Session,
    job: ReportJob,
    documents: list[UploadedDocument],
    ctx: OrchestrationContext,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.CLASSIFY.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job, documents=documents)

    degraded_notes: list[str] = []
    for document in documents:
        session.refresh(job)
        if _job_is_terminal(job):
            return
        mime_label = classification_from_mime(document.mime_type)
        if mime_label is not None:
            document.classification = mime_label
            session.add(document)
            continue

        text = load_document_text(document, loader_override=ctx.text_loader)
        outcome = await dispatch_stage(
            classify_document_text(
                text,
                filename=document.original_filename,
                mime_type=document.mime_type,
                query_fn=ctx.query_fn_classifier,
            ),
            stage=stage,
        )
        result = outcome.result
        if result.intake_outcome == "unreadable":
            document.classification = DocumentClassification.OTHER.value
        else:
            document.classification = result.classification
        session.add(document)

    _commit_checkpoint(
        session,
        job,
        next_stage=ReportJobStage.EXTRACT.value,
        stage_completed=stage,
        trace_entry={
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(documents),
            "degraded_notes": degraded_notes,
        },
    )


async def _run_extract_stage(
    session: Session,
    job: ReportJob,
    documents: list[UploadedDocument],
    ctx: OrchestrationContext,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.EXTRACT.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job, documents=documents)

    degraded_documents: list[str] = []
    for document in documents:
        classification = document.classification
        if not classification or classification in _EXTRACT_SKIP_CLASSIFICATIONS:
            continue

        if classification == DocumentClassification.PROPOSAL.value:
            text = load_document_text(document, loader_override=ctx.text_loader)
            try:
                outcome = await dispatch_stage(
                    extract_and_persist_proposal(
                        session,
                        document.id,
                        text,
                        query_fn=ctx.query_fn_proposal,
                    ),
                    stage=stage,
                )
            except ProposalExtractionServiceError as exc:
                raise StageFailure(stage, exc.message) from exc
            if outcome.degraded:
                degraded_documents.append(str(document.id))

        elif classification in (
            DocumentClassification.GRANT_LETTER.value,
            DocumentClassification.MOU.value,
        ):
            text = load_document_text(document, loader_override=ctx.text_loader)
            try:
                outcome = await dispatch_stage(
                    extract_and_persist_grant_terms(
                        session,
                        document.id,
                        text,
                        query_fn=ctx.query_fn_grant_terms,
                        per_attempt_timeout_seconds=ctx.grant_terms_timeout_seconds,
                    ),
                    stage=stage,
                )
            except GrantTermsExtractionServiceError as exc:
                raise StageFailure(stage, exc.message) from exc
            if outcome.degraded:
                degraded_documents.append(str(document.id))

        elif classification == DocumentClassification.INDICATOR_DATA.value:
            spreadsheet_json, content_hash = load_spreadsheet_json(
                document,
                loader_override=ctx.spreadsheet_loader,
            )
            try:
                outcome = await dispatch_stage(
                    extract_and_persist_indicator_data(
                        session,
                        document.id,
                        spreadsheet_json,
                        content_hash=content_hash,
                        query_fn=ctx.query_fn_indicator_data,
                        per_attempt_timeout_seconds=ctx.indicator_timeout_seconds,
                    ),
                    stage=stage,
                )
            except IndicatorDataExtractionServiceError as exc:
                raise StageFailure(stage, exc.message) from exc
            if outcome.degraded:
                degraded_documents.append(str(document.id))

    _commit_checkpoint(
        session,
        job,
        next_stage=ReportJobStage.RECONCILE.value,
        stage_completed=stage,
        trace_entry={
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "degraded_documents": degraded_documents,
        },
    )


async def _run_reconcile_stage(
    session: Session,
    job: ReportJob,
    ctx: OrchestrationContext,
) -> DispatchOutcome:
    session.refresh(job)
    if _job_is_terminal(job):
        return DispatchOutcome(result=None, degraded=False)
    stage = ReportJobStage.RECONCILE.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job)

    try:
        outcome = await dispatch_stage(
            reconcile_and_persist(
                session,
                job.donor_report_id,
                query_fn=ctx.query_fn_reconciler,
                per_attempt_timeout_seconds=ctx.reconciler_timeout_seconds,
            ),
            stage=stage,
        )
    except KnowledgeBankReconciliationServiceError as exc:
        raise StageFailure(stage, exc.message) from exc

    reconcile_trace = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "degraded": outcome.degraded,
    }
    _halt_gate1(session, job, reconcile_trace=reconcile_trace)
    return outcome


async def run_orchestrated_walk(
    job: ReportJob,
    session: Session,
    *,
    ctx: OrchestrationContext | None = None,
) -> None:
    """Execute pipeline stages from the job's stage cursor."""
    context = ctx or OrchestrationContext()
    session.refresh(job)

    if job.status == ReportJobStatus.FAILED.value:
        return

    documents = (
        session.query(UploadedDocument)
        .filter(UploadedDocument.donor_report_id == job.donor_report_id)
        .order_by(UploadedDocument.created_at.asc())
        .all()
    )

    stage = job.stage

    if stage == ReportJobStage.GAP.value:
        _park_gap_boundary(session, job)
        return

    if stage == ReportJobStage.CLASSIFY.value:
        await _run_classify_stage(session, job, documents, context)
        session.refresh(job)
        stage = job.stage

    if stage == ReportJobStage.EXTRACT.value:
        await _run_extract_stage(session, job, documents, context)
        session.refresh(job)
        stage = job.stage

    if stage == ReportJobStage.RECONCILE.value:
        await _run_reconcile_stage(session, job, context)


def run_orchestrated_walk_sync(
    job: ReportJob,
    session: Session,
    *,
    ctx: OrchestrationContext | None = None,
) -> None:
    asyncio.run(run_orchestrated_walk(job, session, ctx=ctx))
