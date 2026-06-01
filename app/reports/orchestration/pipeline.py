"""Orchestrated walk: classify -> extract -> reconcile -> Gate 1 halt -> gap (E3) -> Gate 2 halt."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.agents.classifier import classify_document_text
from app.reports.agents.gap_compliance_agent import run_gap_compliance
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DocumentClassification, ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
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
    persist_degraded_indicator_unparseable,
)
from app.reports.services.knowledge_bank_reconciliation_service import (
    KnowledgeBankReconciliationServiceError,
    reconcile_and_persist,
)
from app.reports.services.proposal_extraction_service import (
    ProposalExtractionServiceError,
    extract_and_persist_proposal,
)
from app.reports.schemas.gap_compliance_v1 import envelope_to_gap_analysis_json
from app.reports.services.gate_preconditions import (
    require_gate1_confirmed,
    require_gate2_confirmed,
    require_gate3_confirmed,
)
from app.reports.services.report_fact_safety_service import (
    ReportFactSafetyServiceError,
    critique_and_persist,
)
from app.reports.services.report_synthesis_service import (
    ReportSynthesisServiceError,
    synthesise_and_persist,
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
    query_fn_gap: Any | None = None
    query_fn_synthesis: Any | None = None
    query_fn_critic: Any | None = None
    text_loader: Callable[[UploadedDocument], str] | None = None
    spreadsheet_loader: Callable[[UploadedDocument], tuple[str, str | None]] | None = None
    reconciler_timeout_seconds: float | None = None
    grant_terms_timeout_seconds: float | None = None
    indicator_timeout_seconds: float | None = None
    proposal_timeout_seconds: float | None = None
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


def _halt_gate2(session: Session, job: ReportJob, report: DonorReport, *, gap_trace: dict[str, Any]) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    _append_stage_trace(job, ReportJobStage.GAP.value, gap_trace)
    job.stage = ReportJobStage.SYNTHESISE.value
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    session.add(report)
    session.add(job)
    session.commit()
    logger.info(
        "gate2_halt job_id=%s donor_report_id=%s stage=synthesise status=awaiting_human",
        job.id,
        job.donor_report_id,
    )


async def _run_gap_stage(
    session: Session,
    job: ReportJob,
    ctx: OrchestrationContext,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.GAP.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job)

    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(stage, "Donor report not found")

    try:
        require_gate1_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise StageFailure(stage, exc.message) from exc

    template = session.get(FunderReportTemplate, report.funder_report_template_id)
    if template is None:
        raise StageFailure(stage, "Funder template not found")

    template_payload = {
        "funder_name": template.funder_name,
        "template_name": template.template_name,
        "report_sections_json": template.report_sections_json,
        "format_rules_json": template.format_rules_json,
        "terminology_map_json": template.terminology_map_json,
    }

    outcome = await dispatch_stage(
        run_gap_compliance(
            knowledge_bank_json=report.knowledge_bank_json,
            template_payload=template_payload,
            query_fn=ctx.query_fn_gap,
        ),
        stage=stage,
    )
    result = outcome.result
    report.gap_analysis_json = envelope_to_gap_analysis_json(result.envelope)
    gap_trace = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "readiness_score": result.envelope.structured.readiness_score,
        "gap_count": len(result.envelope.structured.gaps),
        "degraded": outcome.degraded,
    }
    _halt_gate2(session, job, report, gap_trace=gap_trace)


def _park_critique_boundary(session: Session, job: ReportJob) -> None:
    """Resume boundary after synthesis — critic runs on worker re-claim at critique."""
    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(ReportJobStage.CRITIQUE.value, "Donor report not found")
    try:
        require_gate2_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise StageFailure(ReportJobStage.CRITIQUE.value, exc.message) from exc

    _append_stage_trace(
        job,
        ReportJobStage.CRITIQUE.value,
        {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "action": "parked_at_critique_boundary",
            "gate2_confirmed_at": report.knowledge_bank_json.get("gate2_confirmed_at"),
        },
    )
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    job.stage = ReportJobStage.CRITIQUE.value
    session.add(job)
    session.commit()
    logger.info(
        "critique_boundary_parked job_id=%s donor_report_id=%s awaiting_human",
        job.id,
        job.donor_report_id,
    )


def _halt_gate3(session: Session, job: ReportJob, *, critique_trace: dict[str, Any]) -> None:
    """Gate 3 halt — human review before export (Stage H not built)."""
    session.refresh(job)
    if _job_is_terminal(job):
        return
    _append_stage_trace(job, ReportJobStage.CRITIQUE.value, critique_trace)
    job.stage = ReportJobStage.EXPORT.value
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    session.add(job)
    session.commit()
    logger.info(
        "gate3_halt job_id=%s donor_report_id=%s stage=export status=awaiting_human",
        job.id,
        job.donor_report_id,
    )


async def _run_critique_stage(
    session: Session,
    job: ReportJob,
    ctx: OrchestrationContext,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.CRITIQUE.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job)

    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(stage, "Donor report not found")

    try:
        require_gate2_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise StageFailure(stage, exc.message) from exc

    try:
        result = await critique_and_persist(
            session,
            job.donor_report_id,
            query_fn_critic=ctx.query_fn_critic,
        )
    except ReportFactSafetyServiceError as exc:
        raise StageFailure(stage, exc.message) from exc

    critique_trace = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "action": "critique_completed",
        "section_count": result.section_count,
        "verified": result.verified,
        "flagged": result.flagged,
        "unverified": result.unverified,
        "skipped": result.skipped,
        "critic_blocks": result.critic_blocks,
        "gate2_confirmed_at": report.knowledge_bank_json.get("gate2_confirmed_at"),
    }
    _halt_gate3(session, job, critique_trace=critique_trace)


async def _run_export_stage(
    session: Session,
    job: ReportJob,
    ctx: OrchestrationContext,
) -> None:
    """Export stage stub — Stage H not built; advances past Gate 3 without re-running critic."""
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.EXPORT.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job)

    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(stage, "Donor report not found")

    try:
        require_gate3_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise StageFailure(stage, exc.message) from exc

    _append_stage_trace(
        job,
        stage,
        {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "action": "export_boundary_not_implemented",
            "gate3_confirmed_at": report.knowledge_bank_json.get("gate3_confirmed_at"),
        },
    )
    job.status = ReportJobStatus.DONE.value
    session.add(job)
    session.commit()
    logger.info(
        "export_boundary_stub job_id=%s donor_report_id=%s status=done",
        job.id,
        job.donor_report_id,
    )


async def _run_synthesise_stage(
    session: Session,
    job: ReportJob,
    ctx: OrchestrationContext,
) -> None:
    session.refresh(job)
    if _job_is_terminal(job):
        return
    stage = ReportJobStage.SYNTHESISE.value
    hook = ctx.stage_hooks.get(stage)
    if hook is not None:
        hook(session=session, job=job)

    report = session.get(DonorReport, job.donor_report_id)
    if report is None:
        raise StageFailure(stage, "Donor report not found")

    try:
        require_gate2_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise StageFailure(stage, exc.message) from exc

    try:
        outcome = await dispatch_stage(
            synthesise_and_persist(
                session,
                job.donor_report_id,
                query_fn_synthesis=ctx.query_fn_synthesis,
            ),
            stage=stage,
        )
    except ReportSynthesisServiceError as exc:
        raise StageFailure(stage, exc.message) from exc

    result = outcome.result
    synthesise_trace = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "action": "synthesise_completed",
        "section_count": result.section_count,
        "generated": result.generated,
        "failed": result.failed,
        "degraded": result.degraded,
        "gate2_confirmed_at": report.knowledge_bank_json.get("gate2_confirmed_at"),
    }
    _append_stage_trace(job, stage, synthesise_trace)
    session.add(job)
    session.commit()
    _park_critique_boundary(session, job)


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
                        per_attempt_timeout_seconds=ctx.proposal_timeout_seconds,
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
            try:
                spreadsheet_json, content_hash = load_spreadsheet_json(
                    document,
                    loader_override=ctx.spreadsheet_loader,
                )
            except ValueError:
                try:
                    outcome = await dispatch_stage(
                        persist_degraded_indicator_unparseable(
                            session,
                            document.id,
                        ),
                        stage=stage,
                    )
                except IndicatorDataExtractionServiceError as exc:
                    raise StageFailure(stage, exc.message) from exc
            else:
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
        await _run_gap_stage(session, job, context)
        return

    if stage == ReportJobStage.SYNTHESISE.value:
        await _run_synthesise_stage(session, job, context)
        return

    if stage == ReportJobStage.CRITIQUE.value:
        await _run_critique_stage(session, job, context)
        return

    if stage == ReportJobStage.EXPORT.value:
        await _run_export_stage(session, job, context)
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
