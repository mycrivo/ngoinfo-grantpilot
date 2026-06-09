"""Tests for F1 per-section report_inputs trimming."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.services.report_inputs_builder import (
    build_knowledge_bank_inputs_for_section,
    subset_facts_for_section,
)

FCDO_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "artefacts"
    / "me_module"
    / "TEMPLATE_INSTANCE_FCDO.json"
)
CITED_FIXTURE_PATH = (
    Path(__file__).resolve().parents[0]
    / "fixtures"
    / "synthesis"
    / "bridgelight_6643d922_cited_keys.json"
)

WORKING_SECTIONS = (
    "summary_and_overview",
    "performance_and_conclusions",
    "evidence_and_evaluation",
    "risk_and_safeguarding",
    "programme_management_delivery_commercial_financial",
    "recommendations_and_actions",
)


@pytest.fixture
def fcdo_sections() -> dict[str, dict]:
    template = json.loads(FCDO_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return {s["section_key"]: s for s in template["report_sections_json"]}


@pytest.fixture
def bridgelight_facts_and_cited() -> tuple[dict, dict[str, list[str]]]:
    data = json.loads(CITED_FIXTURE_PATH.read_text(encoding="utf-8"))
    facts = dict(data["facts"])
    for fact in facts.values():
        if isinstance(fact, dict):
            fact.setdefault("verification_status", "reconciled")
            fact.setdefault("source_document_id", "fixture-doc")
            fact.setdefault("source_label", "fixture")
            fact.setdefault("semantic_label", "fixture")
            fact.setdefault("provenance", {"excerpt": "fixture"})
    facts["noise.unrelated_safeguarding_only"] = {
        "value": "should not appear in VfM trim",
        "unit": None,
        "semantic_label": "noise",
        "verification_status": "reconciled",
        "source_document_id": "fixture-doc",
        "source_label": "fixture",
        "provenance": {"excerpt": "noise"},
    }
    return facts, data["cited_by_section"]


def _kb_with_gate1(facts: dict, gap_answers: dict | None = None) -> dict:
    return {
        "facts": facts,
        "gap_answers": gap_answers or {},
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
    }


def test_value_for_money_excludes_unrelated_facts_includes_financials(
    fcdo_sections, bridgelight_facts_and_cited
):
    facts, _ = bridgelight_facts_and_cited
    section = fcdo_sections["value_for_money"]
    trimmed = subset_facts_for_section(facts, section)
    assert "noise.unrelated_safeguarding_only" not in trimmed
    assert any(k.startswith("financials.") for k in trimmed)
    assert any(k.startswith("grant.") for k in trimmed)
    kb = build_knowledge_bank_inputs_for_section(
        _kb_with_gate1(
            facts,
            {
                "value_for_money:indicator:economy": {
                    "disposition": "answered",
                    "answer_text": "Economy note",
                    "provenance": {
                        "source": "human_confirmed_gap_answer",
                        "excerpt": "Economy note",
                    },
                },
                "risk_and_safeguarding:indicator:new_risks": {
                    "disposition": "answered",
                    "answer_text": "Risk note",
                    "provenance": {
                        "source": "human_confirmed_gap_answer",
                        "excerpt": "Risk note",
                    },
                },
            },
        ),
        section,
    )
    assert "value_for_money:indicator:economy" in kb["gap_answers"]
    assert "risk_and_safeguarding:indicator:new_risks" in kb["gap_answers"]


def test_detailed_output_scoring_includes_indicators_and_output_scores_gap(
    fcdo_sections, bridgelight_facts_and_cited
):
    facts, _ = bridgelight_facts_and_cited
    section = fcdo_sections["detailed_output_scoring"]
    trimmed = subset_facts_for_section(facts, section)
    assert any(k.startswith("indicators.") for k in trimmed)
    assert "indicators.op1_1_girls_reenrolled_retained.y1_actual" in trimmed
    kb = build_knowledge_bank_inputs_for_section(
        _kb_with_gate1(
            facts,
            {
                "detailed_output_scoring:indicator:output_scores": {
                    "disposition": "answered",
                    "answer_text": "Scores A–C from AR1 export",
                    "provenance": {
                        "source": "human_confirmed_gap_answer",
                        "excerpt": "Scores A–C from AR1 export",
                    },
                },
            },
        ),
        section,
    )
    assert "detailed_output_scoring:indicator:output_scores" in kb["gap_answers"]
    assert kb["facts"]


def test_all_fcdo_sections_get_non_empty_fact_payload(
    fcdo_sections, bridgelight_facts_and_cited
):
    facts, _ = bridgelight_facts_and_cited
    for section_key, section in fcdo_sections.items():
        trimmed = subset_facts_for_section(facts, section)
        assert trimmed, f"{section_key} got empty fact payload"


def test_working_sections_retain_all_cited_fact_keys(
    fcdo_sections, bridgelight_facts_and_cited
):
    facts, cited_by_section = bridgelight_facts_and_cited
    missing: list[tuple[str, str]] = []
    for section_key in WORKING_SECTIONS:
        trimmed = subset_facts_for_section(facts, fcdo_sections[section_key])
        for ref in cited_by_section.get(section_key, []):
            if ref in facts and ref not in trimmed:
                missing.append((section_key, ref))
    assert missing == []


def test_trim_reduces_payload_for_table_sections(
    fcdo_sections, bridgelight_facts_and_cited
):
    facts, _ = bridgelight_facts_and_cited
    full = len(facts)
    vfm = len(subset_facts_for_section(facts, fcdo_sections["value_for_money"]))
    assert 0 < vfm < full
