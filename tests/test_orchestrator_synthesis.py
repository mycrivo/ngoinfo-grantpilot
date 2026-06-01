"""Orchestrator validation — F1 synthesise stage through critique boundary."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.models.report_job import ReportJob
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses
from app.reports.worker import run_pipeline as run_pipeline_module
from tests.orchestrator_mocks import fcdo_incomplete_gap_query_fn, fcdo_synthesis_query_fn
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
from tests.test_orchestrator_gate1 import (
    FCDO_TEMPLATE_PATH,
    _apply_fcdo_template_to_report,
)
from tests.worker_validation_seed import create_worker_validation_sessionmaker, seed_orchestrator_fixture


@pytest.fixture
def orchestrator_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    return session_factory


def _run_fixture_through_gate2_halt(orchestrator_db):
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
    kb.pop("gate1_confirmed_at", None)
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


def test_gate2_resume_runs_synthesis_and_parks_critique(orchestrator_db):
    job_id, report_id, user_id = _run_fixture_through_gate2_halt(orchestrator_db)

    pre = orchestrator_db()
    report_row = pre.get(DonorReport, report_id)
    pre.close()
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
    assert synth_trace.get("section_count") == 8

    critique_trace = parked.agent_trace_json.get("stages", {}).get("critique", {})
    assert critique_trace.get("action") == "parked_at_critique_boundary"

    sections = report.content_json.get("sections") or []
    assert len(sections) == 8


def test_critique_resume_does_not_re_synthesise(orchestrator_db):
    job_id, report_id, user_id = _run_fixture_through_gate2_halt(orchestrator_db)

    pre = orchestrator_db()
    report_row = pre.get(DonorReport, report_id)
    pre.close()
    gaps = report_row.gap_analysis_json.get("gaps") or []
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

    ctx = OrchestrationContext(query_fn_synthesis=fcdo_synthesis_query_fn())
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    after_first = orchestrator_db()
    job = after_first.get(ReportJob, job_id)
    report = after_first.get(DonorReport, report_id)
    after_first.close()
    synth_trace_first = dict(
        job.agent_trace_json.get("stages", {}).get("synthesise", {})
    )
    section_count_first = len(report.content_json.get("sections") or [])
    first_summary = report.content_json.get("generation_summary", {})

    job.status = ReportJobStatus.QUEUED.value
    after_first2 = orchestrator_db()
    after_first2.add(job)
    after_first2.commit()
    after_first2.close()

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    after_second = orchestrator_db()
    job2 = after_second.get(ReportJob, job_id)
    report2 = after_second.get(DonorReport, report_id)
    after_second.close()

    assert job2.stage == ReportJobStage.CRITIQUE.value
    synth_trace_second = job2.agent_trace_json.get("stages", {}).get("synthesise", {})
    assert synth_trace_second.get("completed_at") == synth_trace_first.get("completed_at")
    assert len(report2.content_json.get("sections") or []) == section_count_first
    assert report2.content_json.get("generation_summary") == first_summary
