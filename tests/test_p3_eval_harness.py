"""P3-1 content-keyed eval harness — seven named FCDO gates on main."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.eval.citation_pr import evaluate_citation_pr
from app.reports.eval.faithfulness_check import load_faithfulness_fixture
from app.reports.eval.gap_pr import evaluate_gap_pr
from app.reports.eval.gates import (
    FCDO_COMPLETE_GAP_REFS,
    FCDO_NGO_SECTION_COUNT,
    gate_degrade_leak,
    gate_fcdo_gap_exact,
    gate_faithfulness,
    gate_forbidden,
    gate_honest_exit,
    gate_section_count,
    run_fcdo_gates,
)
from app.reports.eval.fixtures import pad_fcdo_ngo_sections
from app.reports.eval.offline_replay import replay_clean_fixture
from app.reports.eval.output_rubric import (
    FCDO_FORBIDDEN_GAP_REFS,
    FCDO_LITERAL_FORBIDDEN_GAP_REFS,
)
from app.reports.gap.section_visibility import visible_sections_for_context
from scripts.audit.full_walk import PASSING_VERDICTS, exit_code_for_verdict

ROOT = Path(__file__).resolve().parents[1]
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
NLCF_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
CLEAN_FIXTURE = ROOT / "tests" / "fixtures" / "synthesis" / "clean_faithfulness_fixture.json"
FCDO_COMPLETE_KEY = ROOT / "tests" / "fixtures" / "gap" / "keys" / "fcdo_complete_answer_key.json"


@pytest.fixture
def fcdo_template_sections() -> list[dict]:
    payload = json.loads(FCDO_TEMPLATE.read_text(encoding="utf-8"))
    return list(payload["report_sections_json"])


@pytest.fixture
def nlcf_template_sections() -> list[dict]:
    payload = json.loads(NLCF_TEMPLATE.read_text(encoding="utf-8"))
    return list(payload["report_sections_json"])


@pytest.fixture
def clean_fixture() -> dict:
    return load_faithfulness_fixture(CLEAN_FIXTURE)


@pytest.fixture
def fcdo_complete_gap_analysis() -> dict:
    key = json.loads(FCDO_COMPLETE_KEY.read_text(encoding="utf-8"))
    gaps = []
    for item in key["expected_missing"]:
        gaps.append(
            {
                **item,
                "requirement_type": "data",
                "owner": "ngo",
            }
        )
    return {"gaps": gaps, "open_items_count": len(gaps)}


def test_g_degrade_leak_zero_on_clean(clean_fixture):
    result = gate_degrade_leak(clean_fixture["content_json"])
    assert result.passed
    assert result.summary["degraded_pass_through"] == 0


def test_g_faithfulness_zero_unmatched_on_clean(clean_fixture):
    result = gate_faithfulness(
        clean_fixture["content_json"],
        expected_presence=clean_fixture.get("expected_presence"),
    )
    assert result.passed
    assert result.summary["faithfulness.unmatched_numbers"] == 0


def test_g_fcdo_gap_exact_two_ref(fcdo_complete_gap_analysis):
    result = gate_fcdo_gap_exact(fcdo_complete_gap_analysis)
    assert result.passed
    assert set(result.summary["gap_refs"]) == set(FCDO_COMPLETE_GAP_REFS)


def test_g_forbidden_no_rss_oa_funder_narrative(fcdo_complete_gap_analysis):
    result = gate_forbidden(fcdo_complete_gap_analysis)
    assert result.passed
    assert result.summary["literal_forbidden_count"] == 0
    assert result.summary["forbidden_rss_oa"] == 0
    assert result.summary["funder_owned"] == 0
    assert result.summary["narrative_data"] == 0
    gap_refs = {
        g["required_item_ref"]
        for g in fcdo_complete_gap_analysis["gaps"]
    }
    assert FCDO_LITERAL_FORBIDDEN_GAP_REFS.isdisjoint(gap_refs)


@pytest.mark.parametrize(
    "forbidden_ref,section_key,required_item_type",
    [
        ("review_summary_sheet", "summary_and_overview", "table"),
        ("outcome_assessment", "performance_and_conclusions", "table"),
        ("outcome_indicators", "performance_and_conclusions", "indicator"),
        (
            "progress_against_expected_results",
            "performance_and_conclusions",
            "indicator",
        ),
    ],
)
def test_g_forbidden_negative_control_literal_ref_injected(
    fcdo_complete_gap_analysis,
    forbidden_ref,
    section_key,
    required_item_type,
):
    gap_analysis = json.loads(json.dumps(fcdo_complete_gap_analysis))
    gap_analysis["gaps"].append(
        {
            "section_key": section_key,
            "required_item_type": required_item_type,
            "required_item_ref": forbidden_ref,
            "requirement_type": "data",
            "owner": "ngo",
        }
    )
    result = gate_forbidden(gap_analysis)
    assert not result.passed
    assert forbidden_ref in result.summary["literal_forbidden_refs"]


def test_g_section_count_fcdo_six(fcdo_template_sections, clean_fixture):
    padded = pad_fcdo_ngo_sections(
        clean_fixture["content_json"],
        fcdo_template_sections,
        report_context={"report_type": "annual"},
    )
    result = gate_section_count(
        padded,
        template_sections=fcdo_template_sections,
        report_context={"report_type": "annual"},
    )
    assert result.passed
    assert result.summary["generated_ngo_sections"] == FCDO_NGO_SECTION_COUNT


def test_g_section_count_nlcf_unchanged(nlcf_template_sections):
    visible = visible_sections_for_context(
        nlcf_template_sections,
        report_context={"report_type": "annual"},
        include_funder_owned=False,
    )
    expected = len(visible)
    content = {
        "sections": [
            {
                "section_key": s["section_key"],
                "generation_status": "GENERATED",
                "content": {"citation_mode": "structured", "text": "", "claims": []},
            }
            for s in visible
        ]
    }
    result = gate_section_count(
        content,
        template_sections=nlcf_template_sections,
        report_context={"report_type": "annual"},
        expected_count=expected,
    )
    assert result.passed


def test_g_honest_exit_passing_verdicts():
    for verdict in PASSING_VERDICTS:
        assert gate_honest_exit(verdict).passed
        assert exit_code_for_verdict(verdict) == 0


def test_g_honest_exit_failing_verdicts():
    for verdict in ("failed_before_gate1", "export_incomplete", "timeout_before_gate1"):
        assert gate_honest_exit(verdict).passed
        assert exit_code_for_verdict(verdict) == 1


def test_g_charge_once_export_idempotent(export_db):
    from tests.test_report_export_service import _seed_gate3_ready_report
    from app.reports.services.report_export_service import export_and_persist
    from app.models.usage_ledger import UsageLedger
    from app.services.quota_service import report_create_idempotency_key
    from sqlalchemy import select

    session = export_db()
    report_id, _user_id, storage = _seed_gate3_ready_report(session)
    session.close()
    export_and_persist(export_db(), report_id, storage=storage)
    export_and_persist(export_db(), report_id, storage=storage)
    session = export_db()
    rows = session.execute(
        select(UsageLedger).where(
            UsageLedger.idempotency_key == report_create_idempotency_key(report_id)
        )
    ).scalars().all()
    session.close()
    assert len(rows) == 1


@pytest.fixture
def export_db():
    from tests.worker_validation_seed import create_worker_validation_sessionmaker

    return create_worker_validation_sessionmaker()


def test_run_fcdo_gates_all_pass(clean_fixture, fcdo_template_sections, fcdo_complete_gap_analysis):
    content_json = pad_fcdo_ngo_sections(
        clean_fixture["content_json"],
        fcdo_template_sections,
    )
    report = run_fcdo_gates(
        content_json=content_json,
        gap_analysis=fcdo_complete_gap_analysis,
        template_sections=fcdo_template_sections,
        expected_presence=clean_fixture.get("expected_presence"),
    )
    assert report.passed


def test_offline_replay_clean_fixture_passes():
    summary, code = replay_clean_fixture(CLEAN_FIXTURE)
    assert code == 0
    assert summary["passed"]


def test_citation_pr_perfect_on_clean(clean_fixture):
    content = clean_fixture["content_json"]
    report = evaluate_citation_pr(content)
    assert report.passed


def test_gap_pr_exact_on_complete(fcdo_complete_gap_analysis):
    expected = {
        ("performance_and_conclusions", "indicator", ref)
        for ref in FCDO_COMPLETE_GAP_REFS
    }
    report = evaluate_gap_pr(fcdo_complete_gap_analysis, expected_identities=expected)
    assert report.passed
