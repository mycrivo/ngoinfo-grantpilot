#!/usr/bin/env python3
"""Honest gap-answer strategy for happy-path walks.

Answers are authored narrative grounded in the BridgeLight FCDO source set
(the legitimate Gate-2 human action). Unknown keys are skipped honestly rather
than invented. A separate adversarial module handles invention probes.
"""

from __future__ import annotations

from typing import Any

FCDO_SNIPPETS: dict[str, str] = {
    "overall_progress": (
        "Year 1 delivery remained broadly on track. OP1.1 achieved 684 girls "
        "re-enrolled against a Year 1 target of 650 (score A). OP1.2 attendance "
        "at 80%+ reached 472 against target 500 (score B). OP2.1 delivered 31 "
        "latrine stances against target 24 (score A)."
    ),
    "outcome_assessment": (
        "Outcome monitoring used term attendance registers and school safeguarding "
        "pathway checks. Supported girls' attendance and retention improved against "
        "Year 1 milestones, with variance notes recorded in the AR1 export."
    ),
    "new_evidence": (
        "Evidence includes school registers, re-entry club forms, WASH engineer "
        "certificates, mobile-money hardship grant lists, and district validation samples."
    ),
    "evaluation_progress": (
        "No standalone external evaluation was commissioned in Year 1; monitoring "
        "relied on termly indicator returns and partner spot checks."
    ),
    "evidence_base_strength": (
        "Indicator actuals are drawn from the BridgeLight AR1 export with source "
        "notes per output; attendance and financial lines include variance explanations."
    ),
    "data_quality_limitations": (
        "Review period in partner returns uses 01-Oct-24 to 30-Sep-25 while the award "
        "letter cites 15-Oct to 14-Oct; finance has not recut. Four schools submitted "
        "attendance registers late, affecting OP1.2."
    ),
    "new_risks": (
        "No new material risks beyond those in the grant risk register; menstrual "
        "health supply delays affected OP2.2 (17/20 schools)."
    ),
    "realised_assumptions": (
        "Assumption that community focal teachers would be available held in most schools; "
        "three schools lacked a female focal teacher for menstrual health training."
    ),
    "funds_not_used_as_intended_risk": (
        "No evidence of funds not used as intended; hardship grants deduplicated 16 "
        "caregiver records before payment."
    ),
    "climate_environment_risk": (
        "Lake-shore transport costs increased for OP1.1; no major climate shock "
        "stopped delivery in Year 1."
    ),
    "safeguarding_risk_where_relevant": (
        "Safeguarding referral pathways were tested in supported schools; no major "
        "incident trend reported in Year 1 monitoring returns."
    ),
    "recommendations_from_current_review": (
        "Recut finance to FCDO 15-Oct-14-Oct review window; complete menstrual health "
        "training in three remaining schools; submit late attendance registers."
    ),
    "updates_on_previous_recommendations": (
        "Previous review actions on register cleaning were partially complete; "
        "September deduplication removed double-count risk on OP1.1."
    ),
    "priorities_for_next_period": (
        "Close OP2.2 gap (17/20 schools); complete disposal bins at four latrine units; "
        "align reporting period labelling with award letter."
    ),
    "recommendations_action_plan": (
        "Owner: Programme Manager - recut AR1 period by Q1 next period; Owner: M&E - "
        "chase four schools for Term 3 registers; Owner: WASH - finish disposal bins."
    ),
    "partner_performance": (
        "District validation samples confirmed re-entry figures; late register "
        "submission from four schools affected attendance reporting."
    ),
    "supplier_consultant_performance": (
        "WASH engineer certificates received for 31 latrine stances; cement and "
        "transport over budget on OP2.1."
    ),
    "financial_delivery": (
        "Year 1 actual spend on outputs totalled GBP 694,860 against forecast "
        "GBP 653,000 across sampled lines in the AR1 export."
    ),
    "commercial_issues": (
        "Menstrual health supplies procured late, contributing to OP2.2 below milestone."
    ),
    "management_actions": (
        "FCDO review pack due per award letter; partner held district learning "
        "meetings with documented action points."
    ),
}


def answer_gap(gap: dict[str, Any], snippets: dict[str, str] | None = None) -> dict[str, Any]:
    snippets = snippets if snippets is not None else FCDO_SNIPPETS
    ref = (gap.get("required_item_ref") or "").lower()
    section = gap.get("section_key") or ""
    item_type = gap.get("required_item_type") or ""

    for key, text in snippets.items():
        if key in ref or key in section:
            return {"disposition": "answered", "answer_text": text}

    if "score" in ref or "output" in ref:
        return {
            "disposition": "answered",
            "answer_text": (
                "Output scoring is populated from the BridgeLight AR1 export with "
                "proposed scores A-C and variance explanations per indicator row."
            ),
        }
    if item_type == "table":
        return {"disposition": "skipped", "skip_reason": "cannot_provide"}
    return {"disposition": "skipped", "skip_reason": "not_applicable"}
