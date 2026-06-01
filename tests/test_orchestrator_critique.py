"""Orchestrator validation — F2 critique stage and Gate 3 halt."""

from __future__ import annotations

import uuid

import pytest

from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.orchestration.pipeline import OrchestrationContext
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses
from app.reports.services.gate3_confirmation_service import confirm_gate3
from app.reports.worker import run_pipeline as run_pipeline_module
from tests.orchestrator_mocks import (
    fcdo_critic_query_fn,
    fcdo_incomplete_gap_query_fn,
    fcdo_synthesis_query_fn,
)
from tests.test_gap_compliance_agent import _build_incomplete_fcdo_kb
from tests.test_orchestrator_gate1 import _apply_fcdo_template_to_report
from tests.test_orchestrator_synthesis import _run_fixture_through_gate2_halt
from tests.worker_validation_seed import create_worker_validation_sessionmaker


@pytest.fixture
def orchestrator_db(monkeypatch):
    session_factory = create_worker_validation_sessionmaker()
    monkeypatch.setattr(run_pipeline_module, "SessionLocal", session_factory)
    return session_factory


def _accept_all_sections_for_gate3(db_factory, report_id: uuid.UUID) -> None:
    session = db_factory()
    report = session.get(DonorReport, report_id)
    content = dict(report.content_json or {})
    sections = []
    for section in content.get("sections") or []:
        updated = dict(section)
        updated["generation_status"] = "ACCEPTED"
        flags = []
        for flag in updated.get("critic_flags") or []:
            f = dict(flag)
            f["accepted"] = True
            flags.append(f)
        updated["critic_flags"] = flags
        sections.append(updated)
    content["sections"] = sections
    report.content_json = content
    session.add(report)
    session.commit()
    session.close()


def test_critique_resume_runs_critic_and_parks_gate3(orchestrator_db):
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

    ctx = OrchestrationContext(
        query_fn_synthesis=fcdo_synthesis_query_fn(),
        query_fn_critic=fcdo_critic_query_fn(),
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    after_synth = orchestrator_db()
    parked = after_synth.get(ReportJob, job_id)
    after_synth.close()
    assert parked.status == ReportJobStatus.AWAITING_HUMAN.value
    assert parked.stage == ReportJobStage.CRITIQUE.value

    parked.status = ReportJobStatus.QUEUED.value
    requeue = orchestrator_db()
    requeue.add(parked)
    requeue.commit()
    requeue.close()

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    final = orchestrator_db()
    job = final.get(ReportJob, job_id)
    report = final.get(DonorReport, report_id)
    final.close()

    assert job.status == ReportJobStatus.AWAITING_HUMAN.value
    assert job.stage == ReportJobStage.EXPORT.value

    critique_trace = job.agent_trace_json.get("stages", {}).get("critique", {})
    assert critique_trace.get("action") == "critique_completed"
    assert critique_trace.get("critic_blocks") == 0

    sections = report.content_json.get("sections") or []
    assert sections
    assert all(s.get("critic_flags") == [] for s in sections)


def test_gate3_resume_does_not_re_run_critic(orchestrator_db):
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

    ctx = OrchestrationContext(
        query_fn_synthesis=fcdo_synthesis_query_fn(),
        query_fn_critic=fcdo_critic_query_fn(),
    )
    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    after_synth = orchestrator_db()
    job = after_synth.get(ReportJob, job_id)
    job.status = ReportJobStatus.QUEUED.value
    after_synth.add(job)
    after_synth.commit()
    after_synth.close()

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    _accept_all_sections_for_gate3(orchestrator_db, report_id)
    confirm_gate3(
        orchestrator_db(),
        donor_report_id=report_id,
        user_id=user_id,
    )

    after_gate3 = orchestrator_db()
    job = after_gate3.get(ReportJob, job_id)
    report = after_gate3.get(DonorReport, report_id)
    after_gate3.close()
    critique_trace_first = dict(
        job.agent_trace_json.get("stages", {}).get("critique", {})
    )
    flags_first = [
        list(s.get("critic_flags") or []) for s in report.content_json.get("sections") or []
    ]

    run_pipeline_module.run_pipeline(job_id, orchestration_ctx=ctx)

    after_export = orchestrator_db()
    job2 = after_export.get(ReportJob, job_id)
    report2 = after_export.get(DonorReport, report_id)
    after_export.close()

    critique_trace_second = job2.agent_trace_json.get("stages", {}).get("critique", {})
    assert critique_trace_second.get("completed_at") == critique_trace_first.get("completed_at")
    flags_second = [
        list(s.get("critic_flags") or []) for s in report2.content_json.get("sections") or []
    ]
    assert flags_second == flags_first
    assert job2.stage == ReportJobStage.EXPORT.value
    export_trace = job2.agent_trace_json.get("stages", {}).get("export", {})
    assert export_trace.get("action") == "export_boundary_not_implemented"


def test_re_enqueue_gate3_job_key_is_export_stage(orchestrator_db):
    from app.reports.services.gate3_confirmation_service import re_enqueue_gate3_job

    job_id, report_id, _user_id = _run_fixture_through_gate2_halt(orchestrator_db)
    session = orchestrator_db()
    job = session.get(ReportJob, job_id)
    job.stage = ReportJobStage.EXPORT.value
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    session.add(job)
    session.commit()
    session.close()

    session = orchestrator_db()
    re_enqueue_gate3_job(session, donor_report_id=report_id)
    session.commit()
    job = session.get(ReportJob, job_id)
    session.close()
    assert job.stage == ReportJobStage.EXPORT.value
    assert job.status == ReportJobStatus.QUEUED.value
