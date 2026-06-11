"""Orchestrator spine validation — classify through Gate 1 halt and resume."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.reports.agents.classifier import ClassifierError
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import (
    StageFailure,
    dispatch_stage,
    is_degraded_result,
)
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from app.reports.worker.job_failure import FAILURE_EVENT_EXCEPTION, FAILURE_EVENT_TIMEOUT
from app.reports.worker.job_runner import poll_once
from tests.orchestrator_mocks import (
    fcdo_incomplete_gap_query_fn,
    fcdo_synthesis_query_fn,
    gap_stop_error_query_fn,
    minimal_grant_terms_query_fn,
    minimal_indicator_data_query_fn,
    minimal_proposal_query_fn,
    mixed_indicator_extract_classifier_query_fn,
    mixed_indicator_spreadsheet_loader,
    parse_failing_reconciler_query_fn,
    reconciler_query_fn,
    routing_classifier_query_fn,
    slow_grant_terms_query_fn,
    slow_proposal_query_fn,
    slow_query_fn,
    slow_reconciler_query_fn,
)
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture

FCDO_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "artefacts"
    / "me_module"
    / "TEMPLATE_INSTANCE_FCDO.json"
)
FCDO_INCOMPLETE_KEY_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "gap"
    / "keys"
    / "fcdo_incomplete_answer_key.json"
)


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


def test_outcome_uniform_degraded_proposal_extract_continues_to_gate1(orchestrator_db):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    grant_doc_id = str(fixture["documents"][1].id)
    proposal_doc_id = fixture["documents"][0].id
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=slow_proposal_query_fn(delay_seconds=0.5),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
        proposal_timeout_seconds=0.05,
    )

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    proposal_doc = verify.get(UploadedDocument, proposal_doc_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    assert job.error is None
    extract_trace = job.agent_trace_json.get("stages", {}).get("extract", {})
    assert str(proposal_doc_id) in extract_trace.get("degraded_documents", [])
    assert proposal_doc is not None
    assert proposal_doc.extracted_json.get("structured", {}).get("extraction_outcome") == "degraded"
    assert proposal_doc.extracted_json.get("error") == "DEGRADED_EXTRACTION_TIMEOUT"


def test_outcome_uniform_degraded_indicator_unparseable_mixed_stage_reaches_gate1(
    orchestrator_db,
):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(
        session,
        documents=[
            (
                "proposal.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("award_letter.pdf", "application/pdf"),
            (
                "logframe_data.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "indicator_data.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        ],
    )
    job_id = fixture["job"].id
    grant_doc_id = str(fixture["documents"][1].id)
    logframe_doc_id = fixture["documents"][2].id
    spreadsheet_doc_id = fixture["documents"][3].id
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=mixed_indicator_extract_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_indicator_data=minimal_indicator_data_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
        spreadsheet_loader=mixed_indicator_spreadsheet_loader(),
    )

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    logframe_doc = verify.get(UploadedDocument, logframe_doc_id)
    spreadsheet_doc = verify.get(UploadedDocument, spreadsheet_doc_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    assert job.error is None
    extract_trace = job.agent_trace_json.get("stages", {}).get("extract", {})
    assert str(logframe_doc_id) in extract_trace.get("degraded_documents", [])
    assert logframe_doc is not None
    assert (
        logframe_doc.extracted_json.get("structured", {}).get("extraction_outcome")
        == "degraded"
    )
    assert logframe_doc.extracted_json.get("error") == "DEGRADED_EXTRACTION_UNPARSEABLE"
    assert spreadsheet_doc is not None
    assert (
        spreadsheet_doc.extracted_json.get("structured", {}).get("extraction_outcome")
        == "complete"
    )


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


def test_outcome_degraded_reconcile_parse_failure_pass_through_reaches_gate1(
    orchestrator_db,
):
    session = orchestrator_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    grant_doc_id = str(fixture["documents"][1].id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=parse_failing_reconciler_query_fn(),
        text_loader=_text_loader,
    )

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = orchestrator_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    verify.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.GAP.value
    assert job.error is None
    reconcile_trace = job.agent_trace_json.get("stages", {}).get("reconcile", {})
    assert reconcile_trace.get("degraded") is True

    kb = report.knowledge_bank_json if report else {}
    assert kb.get("reconciliation_outcome") == "degraded"
    facts = kb.get("facts") or {}
    assert len(facts) > 0
    assert all(f.get("confirmed") is False for f in facts.values())
    assert all(
        f.get("interpretation_note", "").startswith("Degraded reconciliation pass-through")
        for f in facts.values()
    )
    trace = kb.get("agent_trace") or {}
    assert trace.get("output_tokens") == 15000
    assert trace.get("parse_failure_response_head")


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


def _apply_fcdo_template_to_report(session, report_id: uuid.UUID) -> None:
    fcdo = json.loads(FCDO_TEMPLATE_PATH.read_text(encoding="utf-8"))
    report = session.get(DonorReport, report_id)
    assert report is not None
    template = session.get(FunderReportTemplate, report.funder_report_template_id)
    assert template is not None
    template.funder_name = fcdo["funder_name"]
    template.template_name = fcdo["template_name"]
    template.report_sections_json = fcdo["report_sections_json"]
    template.format_rules_json = fcdo.get("format_rules_json", {})
    template.terminology_map_json = fcdo.get("terminology_map_json", {})
    session.add(template)
    session.commit()


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
    _apply_fcdo_template_to_report(session, report_id)
    kb = _build_incomplete_fcdo_kb()
    kb.pop("gate1_confirmed_at")
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

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=OrchestrationContext(
            query_fn_gap=fcdo_incomplete_gap_query_fn(),
        ),
    )

    final = orchestrator_db()
    parked = final.get(ReportJob, job_id)
    report_row = final.get(DonorReport, report_id)
    final.close()

    assert parked is not None
    assert parked.status == ReportJobStatus.AWAITING_HUMAN.value
    assert parked.stage == ReportJobStage.SYNTHESISE.value
    gap_trace = parked.agent_trace_json.get("stages", {}).get("gap", {})
    assert gap_trace.get("completed_at")
    assert gap_trace.get("gap_count", 0) > 0
    assert gap_trace.get("action") != "parked_at_gap_boundary"

    assert report_row is not None
    assert report_row.gap_analysis_json.get("gap_agent") == "gap_compliance_agent"
    gaps = report_row.gap_analysis_json.get("gaps") or []
    assert len(gaps) > 0
    answer_key = json.loads(FCDO_INCOMPLETE_KEY_PATH.read_text(encoding="utf-8"))
    assert len(gaps) == len(answer_key.get("expected_missing") or [])

    assert poll_once(job_timeout_seconds=2) == 0


def test_outcome_f_g_gap_stage_failure_does_not_halt_at_gate2(orchestrator_db):
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
    _apply_fcdo_template_to_report(session, report_id)
    kb = _build_incomplete_fcdo_kb()
    kb.pop("gate1_confirmed_at")
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

    with pytest.raises(StageFailure) as exc:
        run_pipeline_module.run_pipeline(
            job_id,
            orchestration_ctx=OrchestrationContext(
                query_fn_gap=gap_stop_error_query_fn(),
            ),
        )
    assert exc.value.stage == ReportJobStage.GAP.value

    final = orchestrator_db()
    failed = final.get(ReportJob, job_id)
    report_row = final.get(DonorReport, report_id)
    final.close()

    assert failed is not None
    assert failed.status == ReportJobStatus.FAILED.value
    assert failed.stage == ReportJobStage.GAP.value
    assert failed.agent_trace_json.get("failed_stage") == ReportJobStage.GAP.value
    assert report_row is not None
    assert report_row.gap_analysis_json == {}


def _run_fixture_through_gate2_halt(orchestrator_db):
    """Gate 1 confirm → E3 → halt at (awaiting_human, synthesise). Returns fixture ids."""
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
    _apply_fcdo_template_to_report(session, report_id)
    kb = _build_incomplete_fcdo_kb()
    kb.pop("gate1_confirmed_at")
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

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=OrchestrationContext(
            query_fn_gap=fcdo_incomplete_gap_query_fn(),
        ),
    )
    return job_id, report_id, user_id


def test_outcome_g_h_resume_after_gate2_full_confirm(orchestrator_db):
    job_id, report_id, user_id = _run_fixture_through_gate2_halt(orchestrator_db)

    pre = orchestrator_db()
    report_row = pre.get(DonorReport, report_id)
    pre.close()
    assert report_row is not None
    gaps = report_row.gap_analysis_json.get("gaps") or []
    assert gaps

    responses = {
        gap["item_key"]: Gate2GapResponseInput(
            disposition="answered",
            answer_text=f"Human answer for {gap['required_item_ref']}.",
        )
        for gap in gaps
    }
    submit_gate2_gap_responses(
        orchestrator_db(),
        donor_report_id=report_id,
        user_id=user_id,
        responses=responses,
    )

    queued = orchestrator_db()
    job = queued.get(ReportJob, job_id)
    queued.close()
    assert job is not None
    assert job.status == ReportJobStatus.QUEUED.value
    assert job.stage == ReportJobStage.SYNTHESISE.value

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=OrchestrationContext(
            query_fn_synthesis=fcdo_synthesis_query_fn(),
        ),
    )

    final = orchestrator_db()
    parked = final.get(ReportJob, job_id)
    report = final.get(DonorReport, report_id)
    final.close()

    assert parked is not None
    assert parked.status == ReportJobStatus.AWAITING_HUMAN.value
    assert parked.stage == ReportJobStage.CRITIQUE.value
    synth_trace = parked.agent_trace_json.get("stages", {}).get("synthesise", {})
    assert synth_trace.get("action") == "synthesise_completed"
    assert synth_trace.get("gate2_confirmed_at")
    assert synth_trace.get("section_count") == 6

    critique_trace = parked.agent_trace_json.get("stages", {}).get("critique", {})
    assert critique_trace.get("action") == "parked_at_critique_boundary"

    sections = report.content_json.get("sections") or []
    assert len(sections) == 6

    assert poll_once(job_timeout_seconds=2) == 0


def test_outcome_g_h_partial_gate2_does_not_re_enqueue(orchestrator_db):
    job_id, report_id, user_id = _run_fixture_through_gate2_halt(orchestrator_db)

    pre = orchestrator_db()
    report_row = pre.get(DonorReport, report_id)
    pre.close()
    assert report_row is not None
    gaps = report_row.gap_analysis_json.get("gaps") or []
    assert len(gaps) >= 2

    first_key = gaps[0]["item_key"]
    submit_gate2_gap_responses(
        orchestrator_db(),
        donor_report_id=report_id,
        user_id=user_id,
        responses={
            first_key: Gate2GapResponseInput(
                disposition="answered",
                answer_text="Partial answer only.",
            )
        },
    )

    after = orchestrator_db()
    job = after.get(ReportJob, job_id)
    report = after.get(DonorReport, report_id)
    after.close()

    assert job is not None
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.SYNTHESISE.value
    assert report is not None
    assert report.knowledge_bank_json.get("gate2_confirmed_at") is None

    assert poll_once(job_timeout_seconds=2) == 0
