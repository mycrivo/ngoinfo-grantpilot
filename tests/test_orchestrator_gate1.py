"""Orchestrator spine validation — classify through Gate 1 halt and resume."""

from __future__ import annotations

import uuid

import pytest

from app.reports.agents.classifier import ClassifierError
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import (
    StageFailure,
    dispatch_stage,
    is_degraded_result,
)
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from app.reports.worker.job_failure import FAILURE_EVENT_EXCEPTION, FAILURE_EVENT_TIMEOUT
from app.reports.worker.job_runner import poll_once
from tests.orchestrator_mocks import (
    minimal_grant_terms_query_fn,
    minimal_proposal_query_fn,
    reconciler_query_fn,
    routing_classifier_query_fn,
    slow_grant_terms_query_fn,
    slow_query_fn,
    slow_reconciler_query_fn,
)
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture


@pytest.fixture
def orchestrator_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    from app.reports.worker import job_failure as job_failure_module

    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def _text_loader(_document: UploadedDocument) -> str:
    return "Sample grant document text for validation testing."


def _build_happy_context(*, source_document_id: str) -> OrchestrationContext:
    return OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=source_document_id),
        text_loader=_text_loader,
    )


def test_outcome_a_dispatch_raises_stop_error():
    async def _failing():
        raise ClassifierError("STOP_EMPTY_INPUT", "empty")

    with pytest.raises(StageFailure) as exc:
        import asyncio

        asyncio.run(dispatch_stage(_failing(), stage="classify"))
    assert exc.value.stage == "classify"
    assert "empty" in exc.value.message


def test_outcome_a_dispatch_marks_degraded_envelope():
    from types import SimpleNamespace

    degraded = SimpleNamespace(
        envelope=SimpleNamespace(
            structured=SimpleNamespace(extraction_outcome="degraded")
        )
    )

    assert is_degraded_result(degraded) is True

    async def _return_degraded():
        return degraded

    outcome = __import__("asyncio").run(
        dispatch_stage(_return_degraded(), stage="extract")
    )
    assert outcome.degraded is True


def test_outcome_b_happy_path_halts_at_gate1(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=_build_happy_context(source_document_id=grant_doc_id),
    )

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    docs = (
        verify.query(UploadedDocument)
        .filter(UploadedDocument.donor_report_id == report_id)
        .all()
    )
    by_name = {doc.original_filename: doc for doc in docs}
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    assert job.agent_trace_json.get("stages", {}).get("classify") is not None
    assert job.agent_trace_json.get("stages", {}).get("extract") is not None
    assert job.agent_trace_json.get("stages", {}).get("reconcile") is not None

    assert report is not None
    assert report.knowledge_bank_json.get("facts")
    assert by_name["proposal.docx"].classification == "proposal"
    assert by_name["award_letter.pdf"].classification == "grant_letter"
    assert by_name["proposal.docx"].extracted_json.get("extractor_agent") == "proposal_extractor"
    assert by_name["award_letter.pdf"].extracted_json.get("extractor_agent") == "grant_terms_extractor"


def test_outcome_uniform_raised_failure_preserves_checkpoint(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    ctx = _build_happy_context(source_document_id=grant_doc_id)

    def _fail_extract(session, job, documents):
        raise RuntimeError("injected extract failure")

    ctx.stage_hooks = {ReportJobStage.EXTRACT.value: _fail_extract}

    with pytest.raises(RuntimeError):
        run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    docs = verify.query(UploadedDocument).filter_by(donor_report_id=report_id).all()
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.FAILED.value
    assert "extract" in (job.error or "")
    assert job.stage == ReportJobStage.EXTRACT.value
    assert all(doc.classification in ("proposal", "grant_letter") for doc in docs)


def test_outcome_uniform_degraded_extract_continues(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=slow_grant_terms_query_fn(delay_seconds=0.5),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
        grant_terms_timeout_seconds=0.05,
    )

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    extract_trace = job.agent_trace_json.get("stages", {}).get("extract", {})
    assert extract_trace.get("degraded_documents")


def test_outcome_uniform_degraded_reconcile_halts_not_failed(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=slow_reconciler_query_fn(delay_seconds=0.5),
        text_loader=_text_loader,
        reconciler_timeout_seconds=0.05,
    )

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    reconcile_trace = job.agent_trace_json.get("stages", {}).get("reconcile", {})
    assert reconcile_trace.get("degraded") is True


def test_outcome_h_timeout_backstop_with_real_stages(orchestrator_db, monkeypatch):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=slow_query_fn(delay_seconds=2.0),
        text_loader=_text_loader,
    )
    original = run_pipeline_module.run_pipeline

    def _run_with_ctx(job_id_arg, db=None, orchestration_ctx=None):
        return original(job_id_arg, db=db, orchestration_ctx=ctx)

    monkeypatch.setattr(run_pipeline_module, "run_pipeline", _run_with_ctx)
    monkeypatch.setattr(job_runner_module, "run_pipeline", _run_with_ctx)

    assert poll_once(job_timeout_seconds=0.2) == 1

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.FAILED.value
    assert "wall-clock limit" in (job.error or "")
    assert job.agent_trace_json.get("failure", {}).get("event") == FAILURE_EVENT_TIMEOUT


def test_outcome_f_g_resume_after_gate1_confirm(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(
        session,
        job_stage=ReportJobStage.GAP.value,
        job_status=ReportJobStatus.AWAITING_HUMAN.value,
    )
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    report = fixture["report"]
    doc_id = str(fixture["documents"][1].id)
    kb = {
        "schema_version": "1.0.0",
        "reconciler_agent": "knowledge_bank_reconciler",
        "facts": {
            "budget_total": {
                "value": "100000",
                "unit": "GBP",
                "semantic_label": "Award budget total",
                "coverage": "single_source",
                "source_document_id": doc_id,
                "source_label": "award_letter.pdf",
                "provenance": {"excerpt": "GBP 100000"},
            }
        },
        "conflicts": [],
        "unreadable_sources": [],
        "reconciliation_outcome": "complete",
    }
    report.knowledge_bank_json = kb
    session.add(report)
    session.commit()
    session.close()

    confirm_gate1(
        orchestrator_db(),
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=kb,
    )

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    verify.close()
    assert job is not None
    assert job.status == ReportJobStatus.QUEUED.value

    run_pipeline_module.run_pipeline(job_id)

    final = orchestrator_db()
    parked = final.get(ReportJob, job_id)
    final.close()

    assert parked is not None
    assert parked.status == ReportJobStatus.AWAITING_HUMAN.value
    assert parked.stage == ReportJobStage.GAP.value
    assert parked.agent_trace_json.get("stages", {}).get("gap", {}).get(
        "action"
    ) == "parked_at_gap_boundary"

    assert poll_once(job_timeout_seconds=2) == 0
