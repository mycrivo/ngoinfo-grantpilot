"""Proposal extraction blocking checkpoint — halt, ack proceed, retry re-enqueue."""

from __future__ import annotations

import pytest

from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.services.donor_report_lifecycle_service import enqueue_report_job
from app.reports.services.proposal_checkpoint_service import ack_proposal_checkpoint_proceed
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from tests.orchestrator_mocks import (
    minimal_grant_terms_query_fn,
    minimal_proposal_query_fn,
    reconciler_query_fn,
    routing_classifier_query_fn,
)
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture


@pytest.fixture
def checkpoint_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    from app.reports.worker import job_failure as job_failure_module

    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def _text_loader(_document: UploadedDocument) -> str:
    base = (
        "Sample grant document text for validation testing. "
        "This fixture text must exceed the Docling minimum usable content threshold."
    )
    return (base + " ") * 3


def _never_yield_proposal_query_fn():
    from claude_agent_sdk import ResultMessage

    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await __import__("asyncio").sleep(3600)
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="never",
            structured_output={},
            usage={},
        )

    return _query


def _degraded_proposal_context(*, grant_doc_id: str) -> OrchestrationContext:
    return OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=_never_yield_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
        proposal_timeout_seconds=0.05,
    )


def test_proposal_checkpoint_ack_proceed_reaches_gate1(checkpoint_db):
    session = checkpoint_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=_degraded_proposal_context(grant_doc_id=grant_doc_id),
    )

    verify = checkpoint_db()
    job = verify.get(ReportJob, job_id)
    assert job.stage == ReportJobStage.EXTRACT.value
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value

    ack_proposal_checkpoint_proceed(
        verify,
        donor_report_id=report_id,
        user_id=user_id,
    )
    verify.commit()
    verify.refresh(job)
    assert job.stage == ReportJobStage.RECONCILE.value
    assert job.status == ReportJobStatus.QUEUED.value
    verify.close()

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=_degraded_proposal_context(grant_doc_id=grant_doc_id),
    )

    verify = checkpoint_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    verify.close()

    assert job.stage == ReportJobStage.GAP.value
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert report.knowledge_bank_json.get("facts")


def test_proposal_checkpoint_retry_re_enqueues_same_job(checkpoint_db):
    session = checkpoint_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=_degraded_proposal_context(grant_doc_id=grant_doc_id),
    )

    verify = checkpoint_db()
    job = enqueue_report_job(
        verify,
        donor_report_id=report_id,
        user_id=user_id,
    )
    retry_job_id = job.id
    retry_status = job.status
    retry_stage = job.stage
    extract_trace = (job.agent_trace_json or {}).get("stages", {}).get("extract", {})
    verify.commit()
    verify.close()

    assert retry_job_id == job_id
    assert retry_status == ReportJobStatus.QUEUED.value
    assert retry_stage == ReportJobStage.EXTRACT.value
    assert "proposal_checkpoint" not in extract_trace


def test_proposal_success_skips_checkpoint(checkpoint_db):
    session = checkpoint_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = checkpoint_db()
    job = verify.get(ReportJob, job_id)
    verify.close()

    extract_trace = job.agent_trace_json.get("stages", {}).get("extract", {})
    assert "proposal_checkpoint" not in extract_trace
    assert job.stage == ReportJobStage.GAP.value


def test_fault_flag_induces_checkpoint_with_job_trace_tags(checkpoint_db, monkeypatch):
    """D-056: env fault flag → real timeout degrade → checkpoint + job fault tags."""
    from app.reports.agents.proposal_extractor import FAULT_FLAG_ENV
    from app.reports.models.uploaded_document import UploadedDocument
    from sqlalchemy import select

    monkeypatch.setenv(FAULT_FLAG_ENV, "1")

    async def _would_succeed_if_given_time(*, prompt: str, options=None):
        """Completes under a normal 180s ceiling; flag clamp forces timeout."""
        _ = prompt
        _ = options
        await __import__("asyncio").sleep(1.0)
        from claude_agent_sdk import ResultMessage

        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="fault",
            structured_output={},
            usage={},
        )

    session = checkpoint_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=_would_succeed_if_given_time,
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
        proposal_timeout_seconds=180.0,
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = checkpoint_db()
    job = verify.get(ReportJob, job_id)
    docs = verify.scalars(
        select(UploadedDocument).where(UploadedDocument.donor_report_id == report_id)
    ).all()
    proposal_doc = next(d for d in docs if d.classification == "proposal")
    extract_trace = (job.agent_trace_json or {}).get("stages", {}).get("extract", {})
    agent_trace = (proposal_doc.extracted_json or {}).get("agent_trace") or {}
    verify.close()

    assert job.stage == ReportJobStage.EXTRACT.value
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert extract_trace.get("proposal_checkpoint") is not None
    assert extract_trace.get("proposal_fault_injected") is True
    assert extract_trace.get("proposal_fault_flag") == FAULT_FLAG_ENV
    assert agent_trace.get("fault_injected") is True
    assert agent_trace.get("fault_flag") == FAULT_FLAG_ENV
