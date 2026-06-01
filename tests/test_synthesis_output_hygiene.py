"""Unit tests for F1 synthesis output hygiene."""

from __future__ import annotations

from app.reports.services.synthesis_output_hygiene import (
    normalize_identifier,
    sanitize_evidence_used,
    sanitize_generated_content,
    sanitize_prose,
)

KB_FACTS = {
    "indicators.op2_1.ar1_target": {"value": "24"},
    "indicators.op2_2.ar1_actual": {"value": "17"},
    "indicators.op3_1.ar1_actual": {"value": "392"},
    "fcdo.summary.overall_progress": {"value": "On track"},
}

KB_GAPS = {
    "summary_and_overview:indicator:overall_progress": {"answer_text": "Broadly on track"},
}


def test_normalize_identifier_maps_indic_digits_to_ascii():
    corrupt = "indicators.op2_\u09e7.ar\u0967_target"
    assert normalize_identifier(corrupt) == "indicators.op2_1.ar1_target"


def test_sanitize_evidence_used_corrects_indic_digit_fact_key():
    kept, dropped = sanitize_evidence_used(
        ["fact:indicators.op2_\u09e7.ar\u0967_target"],
        kb_fact_keys=KB_FACTS,
    )
    assert kept == ["fact:indicators.op2_1.ar1_target"]
    assert dropped == []


def test_sanitize_evidence_used_drops_nonexistent_key_and_records():
    kept, dropped = sanitize_evidence_used(
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


def test_sanitize_evidence_used_keeps_canonical_and_gap_keys():
    kept, dropped = sanitize_evidence_used(
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


def test_sanitize_prose_strips_control_characters():
    raw = "Year\u0010 milestone on latrine delivery. Term \u0013 registers late."
    assert sanitize_prose(raw) == "Year milestone on latrine delivery. Term  registers late."


def test_sanitize_prose_does_not_alter_clean_text_or_numbers():
    raw = (
        "Re-enrolment reached 684 girls against the Year 1 target of 650. "
        "Spend was GBP121,000 against budget GBP 121,000."
    )
    assert sanitize_prose(raw) == raw


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


def test_sanitize_generated_content_full_hygiene_pass():
    result = sanitize_generated_content(
        text="Year\u0010 milestone: 392 caregivers.",
        evidence_used=[
            "fact:indicators.op3_\u0967.ar\u09e7_actual",
            "fact:indicators.op4_0?ar?_target",
        ],
        kb_fact_keys=KB_FACTS,
    )
    assert result.text == "Year milestone: 392 caregivers."
    assert result.evidence_used == ["fact:indicators.op3_1.ar1_actual"]
    assert result.dropped_citations == ["fact:indicators.op4_0?ar?_target"]
