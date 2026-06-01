"""Unit tests for F1 claim-granular citation emission."""

from __future__ import annotations

from app.reports.services.synthesis_citation_emission import emit_claim_granular_evidence

BRIDGELIGHT_FINANCIALS = {
    "indicators.op2_1_latrine_stances_functional.y1_actual": {"value": "31"},
    "indicators.op2_1_latrine_stances_functional.y1_target": {"value": "24"},
    "financials.lines.op2_1.y1_actual": {"value": "148900"},
    "financials.lines.op2_1.y1_budget": {"value": "121000"},
    "financials.y1_actual.total": {"value": "920420"},
    "financials.y1_budget.total": {"value": "880000"},
    "indicators.op1_2_girls_attending_80pct.y1_actual": {"value": "472"},
    "indicators.op1_2_girls_attending_80pct.y1_target": {"value": "500"},
    "indicators.op3_3_hardship_households_followup.y1_actual": {"value": "0.68"},
    "reporting.obligation.annual_review": {"value": "Annual Review"},
    "reporting.annual_review_period_1.start": {"value": "2024-10-15"},
    "reporting.annual_review_period_1.end": {"value": "2025-10-14"},
    "reporting.annual_review_pack_deadline": {"value": "2025-11-21"},
}

BRIDGELIGHT_GAPS = {
    "risk_and_safeguarding:indicator:realised_assumptions": {
        "answer_text": (
            "Assumption that community focal teachers would be available held in most schools; "
            "three schools lacked a female focal teacher for menstrual health training."
        ),
    },
    "risk_and_safeguarding:indicator:funds_not_used_as_intended_risk": {
        "answer_text": (
            "No evidence of funds not used as intended; hardship grants deduplicated "
            "16 caregiver records before payment."
        ),
    },
    "evidence_and_evaluation:indicator:data_quality_limitations": {
        "answer_text": (
            "Review period in partner returns uses 01-Oct-24 to 30-Sep-25 while the award "
            "letter cites 15-Oct to 14-Oct. Four schools submitted attendance registers late."
        ),
    },
}


def test_money_claim_binds_financial_line_not_indicator():
    text = "OP2.1 at GBP 148,900 against a budget of GBP 121,000."
    evidence = [
        "fact:indicators.op2_1_latrine_stances_functional.y1_actual",
        "fact:indicators.op2_1_latrine_stances_functional.y1_target",
    ]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:financials.lines.op2_1.y1_actual" in result
    assert "fact:financials.lines.op2_1.y1_budget" in result
    assert not any("indicators.op2_1" in ref for ref in result)


def test_y1_budget_total_bound_for_total_spend_claim():
    text = "Total Year 1 actual spend was GBP 920,420 against a Year 1 budget of GBP 880,000."
    evidence = ["fact:financials.y1_actual.total"]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:financials.y1_actual.total" in result
    assert "fact:financials.y1_budget.total" in result


def test_gap_derived_claim_binds_gap_key_in_section():
    text = (
        "Assumption that community focal teachers would be available held in most schools; "
        "this did not hold fully in three schools, which lacked a female focal teacher "
        "for menstrual health training."
    )
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=[],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
        kb_gap_answer_keys=BRIDGELIGHT_GAPS,
        section_key="risk_and_safeguarding",
    )
    assert "gap:risk_and_safeguarding:indicator:realised_assumptions" in result


def test_gap_deduplicated_records_binds_funds_gap():
    text = "This process removed 16 duplicate records before payment."
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=[],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
        kb_gap_answer_keys=BRIDGELIGHT_GAPS,
        section_key="risk_and_safeguarding",
    )
    assert "gap:risk_and_safeguarding:indicator:funds_not_used_as_intended_risk" in result


def test_specific_reporting_dates_not_generic_obligation_only():
    text = (
        "The first Annual Review period as 15 October 2024 to 14 October 2025 and "
        "required submission of the review pack by 21 November 2025."
    )
    evidence = ["fact:reporting.obligation.annual_review"]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:reporting.annual_review_period_1.start" in result
    assert "fact:reporting.annual_review_period_1.end" in result
    assert "fact:reporting.annual_review_pack_deadline" in result
    assert "fact:reporting.obligation.annual_review" not in result


def test_indicator_actual_bound_when_count_in_prose():
    text = "Attendance at or above 80% reached 472 against a target of 500."
    evidence = ["fact:indicators.op1_2_girls_attending_80pct.y1_target"]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:indicators.op1_2_girls_attending_80pct.y1_actual" in result
    assert "fact:indicators.op1_2_girls_attending_80pct.y1_target" in result


def test_hardship_proportion_binds_y1_actual():
    text = "Follow-up for hardship-supported households reached a recorded proportion of 0.68 in Year 1."
    evidence = ["fact: indicators.op3_3_hardship_households_followup.y1_actual"]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:indicators.op3_3_hardship_households_followup.y1_actual" in result
    assert not any("fact: " in ref for ref in result)


def test_wrong_index_reporting_key_emits_canonical_period_1():
    text = "The award letter set the first Annual Review period ending 14 October 2025."
    evidence = ["fact:reporting.annual_review_period_0.end"]
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:reporting.annual_review_period_1.end" in result
    assert not any("period_0" in ref for ref in result)


def test_does_not_fabricate_citation_for_absent_kb_value():
    """Bucket-B safety: report-creation window not in KB must not receive a cite."""
    text = "The reporting period of 2025-04-01 to 2026-03-31 was used for this review."
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=["fact:reporting.obligation.annual_review"],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:reporting.annual_review_period_1.start" not in result
    assert not any("2025-04-01" in ref for ref in result)
    assert "fact:reporting.obligation.annual_review" in result


def test_does_not_fabricate_derived_aggregate():
    text = "Actual spend totalled GBP 694,860 against forecast GBP 653,000."
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=[],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert result == []


def test_does_not_fabricate_derived_overrun():
    text = "An overrun of GBP 40,420 on the logframe export basis."
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=["fact:financials.y1_actual.total"],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert "fact:financials.y1_budget.total" not in result
    assert len(result) == 1


def test_idempotent_emission_no_duplicate_keys():
    text = "OP2.1 at GBP 148,900 against GBP 121,000."
    evidence = ["fact:financials.lines.op2_1.y1_actual"]
    first = emit_claim_granular_evidence(
        text=text,
        evidence_used=evidence,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    second = emit_claim_granular_evidence(
        text=text,
        evidence_used=first,
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
    )
    assert first == second
    assert len(first) == len(set(first))


def test_four_schools_gap_binds_in_evidence_section():
    text = "Four schools submitted attendance registers late, affecting OP1.2."
    result = emit_claim_granular_evidence(
        text=text,
        evidence_used=[],
        kb_fact_keys=BRIDGELIGHT_FINANCIALS,
        kb_gap_answer_keys=BRIDGELIGHT_GAPS,
        section_key="evidence_and_evaluation",
    )
    assert "gap:evidence_and_evaluation:indicator:data_quality_limitations" in result
