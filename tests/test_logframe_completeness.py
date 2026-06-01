"""Unit tests for deterministic logframe missing-actual detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.agents.gap_compliance_agent import run_gap_compliance
from app.reports.gap.logframe_completeness import (
    derive_missing_logframe_actuals,
    is_logframe_enabled,
    logframe_row_ref,
    missing_to_gap_items,
    normalize_indicator_id,
)
from app.reports.gap.satisfaction import is_requirement_satisfied
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.schemas.gap_compliance_v1 import envelope_to_gap_analysis_json

ROOT = Path(__file__).resolve().parents[1]
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
NLCF_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
BRIDGELIGHT_KB = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "reconciler"
    / "recorded"
    / "fcdo_bridgelight_recorded_knowledge_bank.json"
)

DOC_PROPOSAL = "a1111111-1111-4111-8111-111111111101"
DOC_XLSX = "a1111111-1111-4111-8111-111111111103"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _proposal_target(indicator_key: str, label: str, value: str) -> dict:
    return {
        "value": value,
        "semantic_label": label,
        "source_document_id": DOC_PROPOSAL,
        "source_label": "fcdo_bridgelight_proposal.md",
        "provenance": {"excerpt": label},
    }


def _xlsx_actual(indicator_key: str, label: str, value: str) -> dict:
    return {
        "value": value,
        "semantic_label": label,
        "source_document_id": DOC_XLSX,
        "source_label": "fcdo_bridgelight_indicator_data.xlsx",
        "provenance": {"excerpt": value, "cell_ref": "Indicators!E2"},
    }


def test_normalize_indicator_id_from_key_and_label():
    assert normalize_indicator_id("indicators.op2_3_schools.target") == "op2_3"
    assert normalize_indicator_id("OP4.2 learning briefs") == "op4_2"


def test_missing_logframe_actual_op2_3_op4_2():
    template = _load_json(FCDO_TEMPLATE)
    kb = {
        "facts": {
            "indicators.op1_1_girls.actual": _xlsx_actual(
                "op1_1", "OP1.1 actual", "684"
            ),
            "indicators.op1_1_girls.target": _proposal_target(
                "op1_1", "OP1.1 target", "650"
            ),
            "indicators.op2_3_schools.target": _proposal_target(
                "op2_3",
                "OP2.3 schools with safeguarding referral pathway",
                "40",
            ),
            "indicators.op4_2_learning_briefs.target": _proposal_target(
                "op4_2",
                "OP4.2 learning briefs produced",
                "5",
            ),
            "indicators.op4_3_actors.target": _xlsx_actual(
                "op4_3", "OP4.3 actors trained actual", "136"
            ),
        }
    }
    missing = derive_missing_logframe_actuals(
        kb,
        format_rules_json=template["format_rules_json"],
        report_sections_json=template["report_sections_json"],
    )
    ids = {entry.indicator_id for entry in missing}
    assert ids == {"op2_3", "op4_2"}
    assert all(entry.required_item_ref == logframe_row_ref(entry.indicator_id) for entry in missing)


def test_complete_kb_no_false_missing_when_proposal_rows_have_actuals():
    template = _load_json(FCDO_TEMPLATE)
    kb = {
        "facts": {
            "indicators.op1_1_girls.target": _proposal_target("op1_1", "OP1.1 target", "650"),
            "indicators.op1_1_girls.actual": _xlsx_actual("op1_1", "OP1.1 actual", "684"),
        }
    }
    missing = derive_missing_logframe_actuals(
        kb,
        format_rules_json=template["format_rules_json"],
        report_sections_json=template["report_sections_json"],
    )
    assert missing == []


def test_nlcf_logframe_logic_noop():
    template = _load_json(NLCF_TEMPLATE)
    kb = {"facts": {"indicators.op2_3_schools.target": _proposal_target("op2_3", "x", "40")}}
    missing = derive_missing_logframe_actuals(
        kb,
        format_rules_json=template.get("format_rules_json"),
        report_sections_json=template["report_sections_json"],
    )
    assert missing == []
    assert not is_logframe_enabled(template.get("format_rules_json"))


def test_proposal_target_does_not_satisfy_output_scores():
    req = TemplateRequirement(
        item_key="detailed_output_scoring:indicator:output_scores",
        section_key="detailed_output_scoring",
        section_label="C. Detailed Output Scoring",
        required_item_type="indicator",
        required_item_ref="output_scores",
    )
    facts = {
        "indicators.op2_3_schools.target": _proposal_target("op2_3", "OP2.3 target", "40"),
    }
    assert not is_requirement_satisfied(req, facts=facts, gap_answers={})


def test_logframe_row_requirement_unsatisfied_without_actual():
    req = TemplateRequirement(
        item_key="detailed_output_scoring:indicator:logframe_row:op2_3",
        section_key="detailed_output_scoring",
        section_label="C. Detailed Output Scoring",
        required_item_type="indicator",
        required_item_ref=logframe_row_ref("op2_3"),
    )
    facts = {
        "indicators.op2_3_schools.target": _proposal_target("op2_3", "OP2.3 target", "40"),
    }
    assert not is_requirement_satisfied(req, facts=facts, gap_answers={})


def test_bridgelight_recorded_kb_flags_op2_3_and_op4_2():
    template = _load_json(FCDO_TEMPLATE)
    kb = _load_json(BRIDGELIGHT_KB)
    missing = derive_missing_logframe_actuals(
        kb,
        format_rules_json=template["format_rules_json"],
        report_sections_json=template["report_sections_json"],
    )
    ids = {entry.indicator_id for entry in missing}
    assert "op2_3" in ids
    assert "op4_2" in ids


@pytest.mark.asyncio
async def test_e3_merge_deterministic_gaps_when_llm_omits_logframe_rows():
    template = _load_json(FCDO_TEMPLATE)
    kb = {
        "facts": {
            "indicators.op2_3_schools.target": _proposal_target("op2_3", "OP2.3 target", "40"),
            "indicators.op4_2_learning_briefs.target": _proposal_target(
                "op4_2", "OP4.2 learning briefs", "5"
            ),
        },
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
    }

    async def _query(**kwargs):
        class _Msg:
            structured_output = {"readiness_score": 100, "gaps": []}
            is_error = False
            stop_reason = "end_turn"
            duration_ms = 1
            usage = None

        yield _Msg()

    result = await run_gap_compliance(
        knowledge_bank_json=kb,
        template_payload=template,
        report_context={"report_type": "annual"},
        query_fn=_query,
    )
    persisted = envelope_to_gap_analysis_json(result.envelope)
    gap_refs = {g["required_item_ref"] for g in persisted["gaps"]}
    assert logframe_row_ref("op2_3") in gap_refs
    assert logframe_row_ref("op4_2") in gap_refs
    assert persisted["ready_for_gate2"] is False


def test_missing_to_gap_items_names_indicator_in_rationale():
    template = _load_json(FCDO_TEMPLATE)
    missing = derive_missing_logframe_actuals(
        {
            "facts": {
                "indicators.op2_3_schools.target": _proposal_target(
                    "op2_3", "OP2.3 safeguarding pathway", "40"
                ),
            }
        },
        format_rules_json=template["format_rules_json"],
        report_sections_json=template["report_sections_json"],
    )
    gaps = missing_to_gap_items(missing)
    assert len(gaps) == 1
    assert "OP2_3" in gaps[0].rationale.upper() or "op2_3" in gaps[0].rationale
