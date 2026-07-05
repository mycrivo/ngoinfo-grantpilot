"""P2 extract isolation — per-document degrade vs systemic hard-fail."""

from __future__ import annotations

import uuid

import pytest
from botocore.exceptions import ClientError

from app.reports.agents.indicator_data_extractor import DEGRADED_EXTRACTION_UNPARSEABLE
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.dispatch import StageFailure
from app.reports.orchestration.extract_isolation import (
    classify_intake_exception,
    process_extract_document,
)
from app.reports.orchestration.extract_stage_state import ExtractStageRunState
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.orchestration.systemic_extraction_failure import is_systemic_extraction_failure
from app.reports.reconciliation.input_builder import build_reconciliation_bundle, document_dict_to_input
from app.reports.services.donor_report_lifecycle_service import get_knowledge_bank
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from tests.orchestrator_mocks import (
    agent_stop_error_query_fn,
    infra_agent_stop_query_fn,
    minimal_grant_terms_query_fn,
    minimal_indicator_data_query_fn,
    minimal_proposal_query_fn,
    mixed_indicator_extract_classifier_query_fn,
    mixed_indicator_spreadsheet_loader,
    reconciler_query_fn,
)
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture


@pytest.fixture
def isolation_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    from app.reports.worker import job_failure as job_failure_module

    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def test_systemic_classifier_unifies_table_b_and_table_c():
    assert is_systemic_extraction_failure(
        code="STOP_AGENT_ERROR",
        message="Proposal extractor returned an error (stop_reason=401)",
    )
    assert is_systemic_extraction_failure(
        code="STOP_WRONG_CLASSIFICATION",
        message="wrong lane",
    )
    assert not is_systemic_extraction_failure(
        code="STOP_AGENT_ERROR",
        message="Proposal extractor returned an error (stop_reason=end_turn)",
    )


def test_table_c_second_consecutive_ambiguous_hard_fails():
    state = ExtractStageRunState()
    assert state.resolve_agent_stop_action(
        code="STOP_AGENT_ERROR",
        message="Proposal extractor returned an error (stop_reason=error)",
    ) == "degrade"
    state.record_ambiguous_agent_stop_degraded()
    assert state.resolve_agent_stop_action(
        code="STOP_AGENT_ERROR",
        message="Proposal extractor returned an error (stop_reason=error)",
    ) == "hard_fail"


def test_table_c_prior_success_resets_consecutive_rule():
    state = ExtractStageRunState()
    state.record_extract_success()
    assert state.resolve_agent_stop_action(
        code="STOP_AGENT_ERROR",
        message="Proposal extractor returned an error (stop_reason=error)",
    ) == "degrade"


def test_input_builder_maps_degraded_to_unreadable_sources():
    doc_id = str(uuid.uuid4())
    bundle = document_dict_to_input(
        {
            "id": doc_id,
            "original_filename": "logframe_data.docx",
            "classification": "indicator_data",
            "extracted_json": {
                "error": DEGRADED_EXTRACTION_UNPARSEABLE,
                "structured": {"extraction_outcome": "degraded"},
            },
        }
    )
    assert len(bundle.unreadable_sources) == 1
    assert bundle.unreadable_sources[0].document_id == doc_id
    assert bundle.unreadable_sources[0].code == DEGRADED_EXTRACTION_UNPARSEABLE
    assert bundle.fact_candidates == []


def test_degraded_document_never_becomes_reconciler_fact_candidate():
    good_id = str(uuid.uuid4())
    bad_id = str(uuid.uuid4())
    bundle = build_reconciliation_bundle(
        [
            {
                "id": good_id,
                "original_filename": "award_letter.pdf",
                "classification": "grant_letter",
                "extracted_json": {
                    "structured": {
                        "extraction_outcome": "complete",
                        "funder": {
                            "absent": False,
                            "raw": "FCDO",
                            "normalized": "FCDO",
                            "provenance": {"excerpt": "FCDO approved funding"},
                        },
                        "grant_reference": {"absent": True},
                        "award_budget": {
                            "amount": {"absent": True},
                            "currency": {"absent": True},
                            "tranches": [],
                        },
                        "grant_period": {
                            "start": {"absent": True},
                            "end": {"absent": True},
                        },
                        "reporting_period": {
                            "start": {"absent": True},
                            "end": {"absent": True},
                        },
                        "reporting_obligations": [],
                        "reporting_deadlines": [],
                    }
                },
            },
            {
                "id": bad_id,
                "original_filename": "logframe_data.docx",
                "classification": "indicator_data",
                "extracted_json": {
                    "error": DEGRADED_EXTRACTION_UNPARSEABLE,
                    "structured": {"extraction_outcome": "degraded"},
                },
            },
        ]
    )
    assert len(bundle.unreadable_sources) == 1
    assert bundle.unreadable_sources[0].document_id == bad_id
    assert all(candidate.document_id != bad_id for candidate in bundle.fact_candidates)


def test_classify_intake_nosuchkey_degrades():
    error = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
        "GetObject",
    )
    assert classify_intake_exception(error) == "degrade"


def test_classify_intake_access_denied_hard_fails():
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "denied"}},
        "GetObject",
    )
    assert classify_intake_exception(error) == "hard_fail"


@pytest.mark.asyncio
async def test_process_extract_proposal_empty_input_degrades(isolation_db):
    session = isolation_db()
    fixture = seed_orchestrator_fixture(session)
    document = fixture["documents"][0]
    document.classification = "proposal"
    session.commit()
    ctx = OrchestrationContext(
        text_loader=lambda _doc: "",
        query_fn_proposal=minimal_proposal_query_fn(),
    )
    state = ExtractStageRunState()
    degraded = await process_extract_document(
        session,
        document,
        ctx,
        state,
        stage=ReportJobStage.EXTRACT.value,
    )
    session.refresh(document)
    assert degraded is True
    assert document.extracted_json.get("structured", {}).get("extraction_outcome") == "degraded"


def test_input_builder_dedupes_unreadable_sources_by_document_id():
    doc_id = str(uuid.uuid4())
    degraded_json = {
        "structured": {"extraction_outcome": "degraded"},
        "error": "DEGRADED_EXTRACTION_TIMEOUT",
    }
    documents = [
        {
            "id": doc_id,
            "original_filename": "proposal.docx",
            "classification": "proposal",
            "extracted_json": degraded_json,
        },
        {
            "id": doc_id,
            "original_filename": "proposal.docx",
            "classification": "proposal",
            "extracted_json": degraded_json,
        },
    ]
    bundle = build_reconciliation_bundle(documents)
    assert len(bundle.unreadable_sources) == 1
    assert bundle.unreadable_sources[0].document_id == doc_id


def test_mixed_unparseable_indicator_reaches_gate1_with_unreadable_sources(isolation_db):
    session = isolation_db()
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
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    grant_doc_id = str(fixture["documents"][1].id)
    logframe_doc_id = str(fixture["documents"][2].id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=mixed_indicator_extract_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_indicator_data=minimal_indicator_data_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=lambda _doc: "Sample grant document text for validation testing.",
        spreadsheet_loader=mixed_indicator_spreadsheet_loader(),
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = isolation_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    kb_payload = get_knowledge_bank(
        verify,
        donor_report_id=report_id,
        user_id=user_id,
    )
    verify.close()

    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    unreadable = kb_payload["unreadable_sources"]
    assert any(item["source_document_id"] == str(logframe_doc_id) for item in unreadable)
    assert all(
        fact.get("source_document_id") != str(logframe_doc_id)
        for fact in (report.knowledge_bank_json.get("facts") or {}).values()
    )


def test_two_consecutive_agent_stops_without_success_hard_fail(isolation_db):
    session = isolation_db()
    fixture = seed_orchestrator_fixture(
        session,
        documents=[
            (
                "proposal_a.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "proposal_b.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ],
        job_stage=ReportJobStage.EXTRACT.value,
        job_status=ReportJobStatus.RUNNING.value,
    )
    job_id = fixture["job"].id
    for doc in fixture["documents"]:
        doc.classification = "proposal"
    session.commit()
    session.close()

    ctx = OrchestrationContext(
        query_fn_proposal=agent_stop_error_query_fn(),
        text_loader=lambda _doc: "Proposal body text long enough to pass intake.",
    )

    with pytest.raises(StageFailure):
        run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = isolation_db()
    job = verify.get(ReportJob, job_id)
    verify.close()
    assert job.status == ReportJobStatus.FAILED.value


def test_agent_stop_after_prior_success_degrades(isolation_db):
    session = isolation_db()
    fixture = seed_orchestrator_fixture(
        session,
        documents=[
            (
                "proposal_good.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("award_letter.pdf", "application/pdf"),
            (
                "proposal_bad.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ],
        job_stage=ReportJobStage.EXTRACT.value,
        job_status=ReportJobStatus.RUNNING.value,
    )
    job_id = fixture["job"].id
    grant_doc_id = str(fixture["documents"][1].id)
    docs = fixture["documents"]
    docs[0].classification = "proposal"
    docs[1].classification = "grant_letter"
    docs[2].classification = "proposal"
    session.commit()
    session.close()

    async def _mixed_query(*, prompt: str, options=None):
        if "proposal_bad.docx" in prompt:
            async for item in agent_stop_error_query_fn()(
                prompt=prompt,
                options=options,
            ):
                yield item
            return
        async for item in minimal_proposal_query_fn()(prompt=prompt, options=options):
            yield item

    ctx = OrchestrationContext(
        query_fn_proposal=_mixed_query,
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=lambda doc: (
            "Second proposal body text long enough to pass intake."
            if doc.original_filename == "proposal_bad.docx"
            else "First proposal body text long enough to pass intake."
            if doc.original_filename == "proposal_good.docx"
            else "Sample grant document text for validation testing."
        ),
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = isolation_db()
    job = verify.get(ReportJob, job_id)
    verify.close()
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    extract_trace = job.agent_trace_json.get("stages", {}).get("extract", {})
    assert len(extract_trace.get("degraded_documents", [])) == 1


def test_infra_agent_stop_hard_fails_immediately(isolation_db):
    session = isolation_db()
    fixture = seed_orchestrator_fixture(
        session,
        job_stage=ReportJobStage.EXTRACT.value,
        job_status=ReportJobStatus.RUNNING.value,
    )
    job_id = fixture["job"].id
    doc = fixture["documents"][0]
    doc.classification = "proposal"
    session.commit()
    session.close()

    ctx = OrchestrationContext(
        query_fn_proposal=infra_agent_stop_query_fn(),
        text_loader=lambda _doc: "Proposal body text long enough to pass intake.",
    )

    with pytest.raises(StageFailure):
        run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = isolation_db()
    job = verify.get(ReportJob, job_id)
    verify.close()
    assert job.status == ReportJobStatus.FAILED.value


def test_load_document_text_failure_degrades_sibling(isolation_db):
    session = isolation_db()
    fixture = seed_orchestrator_fixture(
        session,
        job_stage=ReportJobStage.EXTRACT.value,
        job_status=ReportJobStatus.RUNNING.value,
    )
    job_id = fixture["job"].id
    proposal_doc_id = fixture["documents"][0].id
    grant_doc_id = str(fixture["documents"][1].id)
    docs = fixture["documents"]
    docs[0].classification = "proposal"
    docs[1].classification = "grant_letter"
    session.commit()
    session.close()

    def _text_loader(doc: UploadedDocument) -> str:
        if doc.id == proposal_doc_id:
            raise ValueError("Simulated Docling conversion failure")
        return "Sample grant document text for validation testing."

    ctx = OrchestrationContext(
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = isolation_db()
    job = verify.get(ReportJob, job_id)
    proposal = verify.get(UploadedDocument, proposal_doc_id)
    verify.close()

    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert str(proposal_doc_id) in (
        job.agent_trace_json.get("stages", {}).get("extract", {}).get("degraded_documents", [])
    )
    assert (
        proposal.extracted_json.get("structured", {}).get("extraction_outcome") == "degraded"
    )
