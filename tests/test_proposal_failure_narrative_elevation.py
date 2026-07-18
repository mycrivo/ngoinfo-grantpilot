"""Track 3 (D-053) — narrative Gate 2 elevation after proposal-failure proceed."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.reports.agents.gap_compliance_agent import run_gap_compliance
from app.reports.gap.gap_question_copy import build_gap_question
from app.reports.gap.proposal_failure_elevation import (
    apply_proposal_failure_elevation,
    elevate_on_proposal_failure_flag,
    is_proposal_failure_proceeded,
)
from app.reports.gap.template_requirements import enumerate_template_requirements
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.models.uploaded_document import UploadedDocument
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.schemas.gap_compliance_v1 import GapComplianceOutput
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses
from app.reports.services.proposal_checkpoint_service import ack_proposal_checkpoint_proceed
from app.reports.services.report_inputs_builder import section_has_synthesizable_inputs
from app.reports.services.section_prose import STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA
from app.reports.worker import job_runner as job_runner_module
from app.reports.worker import run_pipeline as run_pipeline_module
from tests.orchestrator_mocks import (
    minimal_grant_terms_query_fn,
    minimal_proposal_query_fn,
    reconciler_query_fn,
    routing_classifier_query_fn,
)
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture

REPO = Path(__file__).resolve().parents[1]
NLCF_TEMPLATE_PATH = (
    REPO / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
)
FCDO_TEMPLATE_PATH = (
    REPO / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
)

ELEVATED_KEYS = frozenset(
    {
        "community_involvement:indicator:community_participation_examples",
        "community_involvement:indicator:partner_or_local_collaboration_examples",
    }
)


@pytest.fixture
def elevation_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    monkeypatch.setattr(job_runner_module, "SessionLocal", session_factory)
    from app.reports.worker import job_failure as job_failure_module

    monkeypatch.setattr(job_failure_module, "SessionLocal", session_factory)
    return session_factory


def _nlcf_payload() -> dict:
    return json.loads(NLCF_TEMPLATE_PATH.read_text(encoding="utf-8"))


def _fcdo_payload() -> dict:
    return json.loads(FCDO_TEMPLATE_PATH.read_text(encoding="utf-8"))


def _confirmed_kb(facts: dict | None = None) -> dict:
    return {
        "schema_version": "knowledge_bank_reconciliation_v1",
        "facts": facts or {},
        "conflicts": [],
        "unreadable_sources": [],
        "gap_answers": {},
        "gate1_confirmed_at": "2026-07-18T12:00:00+00:00",
    }


def test_elevate_flag_reader_nlcf_and_absent():
    sections = _nlcf_payload()["report_sections_json"]
    assert elevate_on_proposal_failure_flag(
        sections,
        section_key="community_involvement",
        indicator_ref="community_participation_examples",
    )
    assert elevate_on_proposal_failure_flag(
        sections,
        section_key="community_involvement",
        indicator_ref="partner_or_local_collaboration_examples",
    )
    assert not elevate_on_proposal_failure_flag(
        sections,
        section_key="project_story",
        indicator_ref="anything",
    )
    fcdo_sections = _fcdo_payload()["report_sections_json"]
    assert not elevate_on_proposal_failure_flag(
        fcdo_sections,
        section_key="programme_management_delivery_commercial_financial",
        indicator_ref="partner_performance",
    )


def test_detector_proceed_ack_only():
    assert not is_proposal_failure_proceeded(None)
    assert not is_proposal_failure_proceeded({})
    assert not is_proposal_failure_proceeded(
        {
            "stages": {
                "extract": {
                    "proposal_checkpoint": {
                        "acknowledged": False,
                        "ack_action": None,
                    }
                }
            }
        }
    )
    assert is_proposal_failure_proceeded(
        {
            "stages": {
                "extract": {
                    "proposal_checkpoint": {
                        "acknowledged": True,
                        "ack_action": "proceed_with_gap",
                    }
                }
            }
        }
    )


def test_post_pass_nlcf_elevates_exactly_two():
    payload = _nlcf_payload()
    sections = payload["report_sections_json"]
    requirements = enumerate_template_requirements(sections, report_context={"report_type": "annual"})
    empty = GapComplianceOutput(
        open_items_count=0,
        ready_for_gate2=True,
        gaps=[],
        readiness_basis="ngo_data",
    )
    elevated = apply_proposal_failure_elevation(
        empty,
        requirements=requirements,
        knowledge_bank_json=_confirmed_kb(),
        report_sections_json=sections,
        elevate=True,
    )
    keys = {g.item_key for g in elevated.gaps}
    assert keys == ELEVATED_KEYS
    assert elevated.open_items_count == 2
    assert elevated.ready_for_gate2 is False
    by_key = {g.item_key: g for g in elevated.gaps}
    for key in ELEVATED_KEYS:
        req = next(r for r in requirements if r.item_key == key)
        assert by_key[key].question == build_gap_question(req)
        assert by_key[key].requirement_type == "narrative"
        assert by_key[key].suggested_action == "provide"
        assert "community_participation_examples" not in by_key[key].question
        assert "partner_or_local_collaboration_examples" not in by_key[key].question


def test_post_pass_fcdo_elevates_zero():
    payload = _fcdo_payload()
    sections = payload["report_sections_json"]
    requirements = enumerate_template_requirements(sections, report_context={"report_type": "annual"})
    empty = GapComplianceOutput(
        open_items_count=0,
        ready_for_gate2=True,
        gaps=[],
        readiness_basis="ngo_data",
    )
    elevated = apply_proposal_failure_elevation(
        empty,
        requirements=requirements,
        knowledge_bank_json=_confirmed_kb(),
        report_sections_json=sections,
        elevate=True,
    )
    assert elevated.gaps == []
    assert elevated.open_items_count == 0


def test_post_pass_no_trigger_is_noop():
    payload = _nlcf_payload()
    sections = payload["report_sections_json"]
    requirements = enumerate_template_requirements(sections, report_context={"report_type": "annual"})
    empty = GapComplianceOutput(
        open_items_count=0,
        ready_for_gate2=True,
        gaps=[],
        readiness_basis="ngo_data",
    )
    out = apply_proposal_failure_elevation(
        empty,
        requirements=requirements,
        knowledge_bank_json=_confirmed_kb(),
        report_sections_json=sections,
        elevate=False,
    )
    assert out.gaps == []
    assert out.open_items_count == 0


def test_satisfaction_guard_skips_when_partnerships_feed_community():
    payload = _nlcf_payload()
    sections = payload["report_sections_json"]
    requirements = enumerate_template_requirements(sections, report_context={"report_type": "annual"})
    kb = _confirmed_kb(
        facts={
            "partnerships.food_pantry": {
                "fact_key": "partnerships.food_pantry",
                "value": "the food pantry",
                "verification_status": "reconciled",
                "source_document_id": "doc-1",
                "source_label": "proposal",
                "provenance": {"excerpt": "the food pantry"},
            }
        }
    )
    empty = GapComplianceOutput(
        open_items_count=0,
        ready_for_gate2=True,
        gaps=[],
        readiness_basis="ngo_data",
    )
    elevated = apply_proposal_failure_elevation(
        empty,
        requirements=requirements,
        knowledge_bank_json=kb,
        report_sections_json=sections,
        elevate=True,
    )
    # Package A routes partnerships.* → community_involvement synthesis substrate.
    assert ELEVATED_KEYS.isdisjoint({g.item_key for g in elevated.gaps})


def test_healthy_nlcf_gate2_unchanged_without_proceed():
    payload = _nlcf_payload()
    kb = _confirmed_kb()
    baseline = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=False,
        )
    )
    with_flag_false = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=False,
        )
    )
    assert {g.item_key for g in baseline.envelope.structured.gaps} == {
        g.item_key for g in with_flag_false.envelope.structured.gaps
    }
    assert ELEVATED_KEYS.isdisjoint(
        {g.item_key for g in baseline.envelope.structured.gaps}
    )


def test_healthy_fcdo_gate2_unchanged_and_zero_elevated():
    payload = _fcdo_payload()
    kb = _build_incomplete_fcdo_kb()
    baseline = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=False,
        )
    )
    proceeded = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=True,
        )
    )
    base_keys = {g.item_key for g in baseline.envelope.structured.gaps}
    proceeded_keys = {g.item_key for g in proceeded.envelope.structured.gaps}
    assert base_keys == proceeded_keys
    assert ELEVATED_KEYS.isdisjoint(proceeded_keys)


def test_nlcf_proceed_emits_exactly_elevated_set():
    payload = _nlcf_payload()
    kb = _confirmed_kb()
    healthy = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=False,
        )
    )
    failed = asyncio.run(
        run_gap_compliance(
            knowledge_bank_json=kb,
            template_payload=payload,
            proposal_failure_proceeded=True,
        )
    )
    healthy_keys = {g.item_key for g in healthy.envelope.structured.gaps}
    failed_keys = {g.item_key for g in failed.envelope.structured.gaps}
    assert failed_keys - healthy_keys == ELEVATED_KEYS
    assert ELEVATED_KEYS.issubset(failed_keys)


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
        await asyncio.sleep(3600)
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


def _apply_nlcf_template(session, report_id) -> None:
    nlcf = _nlcf_payload()
    report = session.get(DonorReport, report_id)
    template = session.get(FunderReportTemplate, report.funder_report_template_id)
    template.funder_name = nlcf["funder_name"]
    template.template_name = nlcf["template_name"]
    template.report_sections_json = nlcf["report_sections_json"]
    template.format_rules_json = nlcf.get("format_rules_json", {})
    template.terminology_map_json = nlcf.get("terminology_map_json", {})
    session.add(template)
    session.commit()


def _run_to_gate2_after_proposal_fail(elevation_db):
    session = elevation_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    grant_doc_id = str(fixture["documents"][1].id)
    _apply_nlcf_template(session, report_id)
    session.close()

    ctx = _degraded_proposal_context(grant_doc_id=grant_doc_id)
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = elevation_db()
    job = verify.get(ReportJob, job_id)
    assert job.stage == ReportJobStage.EXTRACT.value
    ack_proposal_checkpoint_proceed(
        verify, donor_report_id=report_id, user_id=user_id
    )
    verify.commit()
    verify.close()

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = elevation_db()
    report = verify.get(DonorReport, report_id)
    kb = dict(report.knowledge_bank_json or {})
    kb.pop("gate1_confirmed_at", None)
    report.knowledge_bank_json = kb
    verify.add(report)
    verify.commit()
    verify.close()

    confirm_gate1(
        elevation_db(),
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=kb,
    )

    run_pipeline_module.run_pipeline(
        job_id,
        orchestration_ctx=OrchestrationContext(),
    )

    verify = elevation_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    gaps = list((report.gap_analysis_json or {}).get("gaps") or [])
    verify.close()
    assert job.stage == ReportJobStage.SYNTHESISE.value
    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    return job_id, report_id, user_id, gaps


def test_e2e_answered_elevated_gaps_feed_community_synthesis(elevation_db):
    job_id, report_id, user_id, gaps = _run_to_gate2_after_proposal_fail(elevation_db)
    gap_keys = {g["item_key"] for g in gaps}
    assert ELEVATED_KEYS.issubset(gap_keys)

    participation = (
        "Parents and carers joined monthly coffee mornings; "
        "26 residents were consulted on the delivery plan."
    )
    partners = (
        "We partnered with the food pantry and two tenants groups "
        "for outreach this year."
    )
    responses = {
        "community_involvement:indicator:community_participation_examples": Gate2GapResponseInput(
            disposition="answered",
            answer_text=participation,
        ),
        "community_involvement:indicator:partner_or_local_collaboration_examples": Gate2GapResponseInput(
            disposition="answered",
            answer_text=partners,
        ),
    }
    # Resolve any other data gaps by skip so Gate 2 unlocks.
    for gap in gaps:
        key = gap["item_key"]
        if key not in responses:
            responses[key] = Gate2GapResponseInput(
                disposition="skipped",
                skip_reason="cannot_provide",
            )

    submit_gate2_gap_responses(
        elevation_db(),
        donor_report_id=report_id,
        user_id=user_id,
        responses=responses,
    )

    verify = elevation_db()
    report = verify.get(DonorReport, report_id)
    template = verify.get(FunderReportTemplate, report.funder_report_template_id)
    kb = report.knowledge_bank_json or {}
    verify.close()

    for key in ELEVATED_KEYS:
        entry = kb["gap_answers"][key]
        assert entry["disposition"] == "answered"
        assert entry["provenance"]["source"] == "human_confirmed_gap_answer"
        assert entry["provenance"]["excerpt"]

    community = next(
        s
        for s in template.report_sections_json
        if s["section_key"] == "community_involvement"
    )
    assert section_has_synthesizable_inputs(
        kb,
        community,
        report_sections=template.report_sections_json,
    )
    assert participation in json.dumps(kb["gap_answers"])
    assert partners in json.dumps(kb["gap_answers"])
    _ = job_id  # chain reached Gate 2; synthesis substrate proven without OpenAI


def test_e2e_skipped_elevated_gaps_yield_insufficient_data(elevation_db):
    _job_id, report_id, user_id, gaps = _run_to_gate2_after_proposal_fail(elevation_db)
    responses = {
        gap["item_key"]: Gate2GapResponseInput(
            disposition="skipped",
            skip_reason="cannot_provide",
        )
        for gap in gaps
    }
    submit_gate2_gap_responses(
        elevation_db(),
        donor_report_id=report_id,
        user_id=user_id,
        responses=responses,
    )

    verify = elevation_db()
    report = verify.get(DonorReport, report_id)
    template = verify.get(FunderReportTemplate, report.funder_report_template_id)
    kb = report.knowledge_bank_json or {}
    community = next(
        s
        for s in template.report_sections_json
        if s["section_key"] == "community_involvement"
    )
    assert not section_has_synthesizable_inputs(
        kb,
        community,
        report_sections=template.report_sections_json,
    )
    from app.reports.services.section_prose import build_insufficient_data_section

    section = build_insufficient_data_section(section=community)
    bind = section.get("structured_bind_status") or (
        (section.get("content") or {}).get("structured_bind_status")
    )
    assert bind == STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA
    prose = (section.get("content") or {}).get("text") or ""
    assert "food pantry" not in prose.lower()
    assert "tenants" not in prose.lower()
    verify.close()


def test_healthy_proposal_skips_elevation_in_pipeline(elevation_db):
    session = elevation_db()
    fixture = seed_orchestrator_fixture(session)
    job_id = fixture["job"].id
    report_id = fixture["report"].id
    user_id = fixture["user"].id
    grant_doc_id = str(fixture["documents"][1].id)
    _apply_nlcf_template(session, report_id)
    session.close()

    ctx = OrchestrationContext(
        query_fn_classifier=routing_classifier_query_fn(),
        query_fn_proposal=minimal_proposal_query_fn(),
        query_fn_grant_terms=minimal_grant_terms_query_fn(),
        query_fn_reconciler=reconciler_query_fn(source_document_id=grant_doc_id),
        text_loader=_text_loader,
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    verify = elevation_db()
    job = verify.get(ReportJob, job_id)
    report = verify.get(DonorReport, report_id)
    assert "proposal_checkpoint" not in (
        (job.agent_trace_json or {}).get("stages") or {}
    ).get("extract", {})
    kb = dict(report.knowledge_bank_json or {})
    kb.pop("gate1_confirmed_at", None)
    report.knowledge_bank_json = kb
    verify.add(report)
    verify.commit()
    verify.close()

    confirm_gate1(
        elevation_db(),
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=kb,
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=OrchestrationContext())

    verify = elevation_db()
    report = verify.get(DonorReport, report_id)
    gap_keys = {g["item_key"] for g in (report.gap_analysis_json or {}).get("gaps") or []}
    verify.close()
    assert ELEVATED_KEYS.isdisjoint(gap_keys)
