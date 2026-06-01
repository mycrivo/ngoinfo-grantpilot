"""Unit tests for F1 synthesis output hygiene."""

from __future__ import annotations

from app.reports.services.synthesis_output_hygiene import (
    enrich_evidence_from_kb,
    fact_key_signature,
    normalize_identifier,
    sanitize_evidence_used,
    sanitize_generated_content,
    sanitize_prose,
)

KB_FACTS = {
    "indicators.op2_1.ar1_target": {"value": "24", "semantic_label": "OP2.1 latrine target"},
    "indicators.op2_2.ar1_actual": {"value": "17", "semantic_label": "OP2.2 schools actual"},
    "indicators.op3_1.ar1_actual": {"value": "392", "semantic_label": "OP3.1 caregivers actual"},
    "indicators.op1_1.ar1_actual": {"value": "684", "semantic_label": "OP1.1 girls re-enrolled actual"},
    "indicators.op1_1.ar1_target": {"value": "650", "semantic_label": "OP1.1 girls milestone target"},
    "indicators.op4_1.ar1_actual": {"value": "3", "semantic_label": "OP4.1 district meetings actual"},
    "indicators.op4_3.ar1_actual": {"value": "136", "semantic_label": "OP4.3 actors trained actual"},
    "indicators.op4_3.ar1_target": {"value": "120", "semantic_label": "OP4.3 actors trained target"},
    "fcdo.summary.overall_progress": {"value": "On track"},
}

KB_GAPS = {
    "summary_and_overview:indicator:overall_progress": {"answer_text": "Broadly on track"},
}


def test_normalize_identifier_maps_indic_digits_to_ascii():
    corrupt = "indicators.op2_\u09e7.ar\u0967_target"
    assert normalize_identifier(corrupt) == "indicators.op2_1.ar1_target"


def test_sanitize_evidence_used_corrects_indic_digit_fact_key():
    kept, dropped, remapped = sanitize_evidence_used(
        ["fact:indicators.op2_\u09e7.ar\u0967_target"],
        kb_fact_keys=KB_FACTS,
    )
    assert kept == ["fact:indicators.op2_1.ar1_target"]
    assert dropped == []
    assert remapped == [
        {
            "from": "fact:indicators.op2_\u09e7.ar\u0967_target",
            "to": "fact:indicators.op2_1.ar1_target",
        }
    ]


def test_near_miss_repair_maps_case_and_shape_to_canonical():
    kept, dropped, remapped = sanitize_evidence_used(
        ["fact:indicators.OP4_1_district_meetings.AR1_actual"],
        kb_fact_keys=KB_FACTS,
    )
    assert kept == ["fact:indicators.op4_1.ar1_actual"]
    assert dropped == []
    assert remapped == [
        {
            "from": "fact:indicators.OP4_1_district_meetings.AR1_actual",
            "to": "fact:indicators.op4_1.ar1_actual",
        }
    ]


def test_signature_ambiguity_drops_instead_of_guessing():
    ambiguous_kb = {
        **KB_FACTS,
        "indicators.op4_1_district_learning_meetings.ar1_actual": {"value": "3"},
    }
    assert fact_key_signature("indicators.op4_1.ar1_actual") == fact_key_signature(
        "indicators.op4_1_district_learning_meetings.ar1_actual"
    )
    kept, dropped, remapped = sanitize_evidence_used(
        ["fact:indicators.OP4_1_district_meetings.AR1_actual"],
        kb_fact_keys=ambiguous_kb,
    )
    assert kept == []
    assert dropped == ["fact:indicators.OP4_1_district_meetings.AR1_actual"]
    assert remapped == []


def test_sanitize_evidence_used_drops_nonexistent_key_and_records():
    kept, dropped, remapped = sanitize_evidence_used(
        [
            "fact:indicators.op4_0?ar?_target",
            "fact:indicators.op4_1.ar11_actual",
        ],
        kb_fact_keys=KB_FACTS,
    )
    assert kept == []
    assert dropped == [
        "fact:indicators.op4_0?ar?_target",
        "fact:indicators.op4_1.ar11_actual",
    ]
    assert remapped == []


def test_sanitize_evidence_used_keeps_canonical_and_gap_keys():
    kept, dropped, remapped = sanitize_evidence_used(
        [
            "fact:fcdo.summary.overall_progress",
            "gap:summary_and_overview:indicator:overall_progress",
        ],
        kb_fact_keys=KB_FACTS,
        kb_gap_answer_keys=KB_GAPS,
    )
    assert kept == [
        "fact:fcdo.summary.overall_progress",
        "gap:summary_and_overview:indicator:overall_progress",
    ]
    assert dropped == []
    assert remapped == []


def test_sanitize_prose_strips_control_characters():
    raw = "Year\u0010 milestone on latrine delivery. Term \u0013 registers late."
    assert sanitize_prose(raw) == "Year milestone on latrine delivery. Term  registers late."


def test_sanitize_prose_does_not_alter_clean_text_or_numbers():
    raw = (
        "Re-enrolment reached 684 girls against the Year 1 target of 650. "
        "Spend was GBP121,000 against budget GBP 121,000."
    )
    assert sanitize_prose(raw) == raw


def test_backfill_unique_value_with_indicator_token():
    text = "OP1.1 reached 684 girls re-enrolled against a milestone of 650."
    merged, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=KB_FACTS,
    )
    assert "fact:indicators.op1_1.ar1_actual" in auto
    assert "fact:indicators.op1_1.ar1_target" in auto
    assert set(merged) == set(auto)


def test_backfill_collision_value_136_attaches_nothing():
    collision_kb = {
        "indicators.op4_3.ar1_actual": {
            "value": "136",
            "semantic_label": "OP4.3 actors trained",
        },
        "indicators.other_metric.ar1_actual": {
            "value": "136",
            "semantic_label": "Other metric",
        },
    }
    text = "OP4.3 trained 136 school actors."
    _, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=collision_kb,
    )
    assert auto == []


def test_backfill_hallucinated_value_not_in_kb():
    text = "OP9.9 reached 999 beneficiaries."
    _, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=KB_FACTS,
    )
    assert auto == []


def test_backfill_without_identifier_token_attaches_nothing():
    text = "The programme reached 392 beneficiaries overall."
    _, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=KB_FACTS,
    )
    assert auto == []


def test_backfill_aggregate_total_with_second_home_attaches_nothing():
    aggregate_kb = {
        "financials.total_programme_budget.actual_spend": {
            "value": "920420",
            "semantic_label": "Total programme actual spend",
        },
        "financials.output_lines.actual_spend": {
            "value": "920420",
            "semantic_label": "Output lines actual spend",
        },
    }
    text = "Total output-line actual spend was GBP 920,420."
    _, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=aggregate_kb,
    )
    assert auto == []


def test_backfill_date_without_identifier_attaches_nothing():
    date_kb = {
        "reporting_period.partner.start": {
            "value": "2024-10-01",
            "semantic_label": "Partner reporting start",
        },
    }
    text = "Partner returns used the period starting 2024-10-01."
    _, auto = enrich_evidence_from_kb(
        text=text,
        evidence_used=[],
        kb_fact_keys=date_kb,
    )
    assert auto == []


def test_sanitize_generated_content_idempotent_on_clean_input():
    text = "Delivery reached 684 against target 650."
    evidence = ["fact:fcdo.summary.overall_progress"]
    first = sanitize_generated_content(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=KB_FACTS,
        kb_gap_answer_keys=KB_GAPS,
    )
    second = sanitize_generated_content(
        text=first.text,
        evidence_used=first.evidence_used,
        kb_fact_keys=KB_FACTS,
        kb_gap_answer_keys=KB_GAPS,
    )
    assert second.text == first.text
    assert second.evidence_used == first.evidence_used
    assert second.dropped_citations == []
    assert second.auto_citations == first.auto_citations
    assert second.remapped_citations == first.remapped_citations


def test_sanitize_generated_content_full_hygiene_pass():
    result = sanitize_generated_content(
        text="Year\u0010 milestone: 392 caregivers for OP3.1.",
        evidence_used=[
            "fact:indicators.op3_\u0967.ar\u09e7_actual",
            "fact:indicators.op4_0?ar?_target",
        ],
        kb_fact_keys=KB_FACTS,
    )
    assert result.text == "Year milestone: 392 caregivers for OP3.1."
    assert "fact:indicators.op3_1.ar1_actual" in result.evidence_used
    assert "fact:indicators.op3_1.ar1_actual" in result.auto_citations
    assert result.dropped_citations == ["fact:indicators.op4_0?ar?_target"]


def test_sanitize_generated_content_no_non_ascii_in_evidence_used():
    result = sanitize_generated_content(
        text="OP1.1 reached 684 against 650.",
        evidence_used=["fact:indicators.op1_\u0967.ar\u09e7_actual"],
        kb_fact_keys=KB_FACTS,
    )
    for ref in result.evidence_used:
        key = ref.removeprefix("fact:").removeprefix("gap:")
        assert key == normalize_identifier(key)
