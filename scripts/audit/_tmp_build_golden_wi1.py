#!/usr/bin/env python3
"""One-shot WI1 builder: transcribe GOLDEN_RECORD v1.0 into typed fixtures.

Transcription only. Judgment calls are recorded in RECONCILIATION.md.
Not part of the runtime harness — delete or keep as rebuild aid after owner verify.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "fixtures" / "golden" / "fcdo_bridgelight_ar1_v1"
SOURCE = "docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md"


def fact(
    fid: str,
    slot: str,
    facet: str,
    value,
    source: str,
    status: str,
    *,
    unit: str | None = None,
    label: str = "",
) -> dict:
    rec = {
        "id": fid,
        "ontology_slot": slot,
        "facet": facet,
        "value": value,
        "source_document": source,
        "status": status,
        "label": label,
    }
    if unit is not None:
        rec["unit"] = unit
    return rec


JUDGMENT_CALLS: list[str] = []


def note(msg: str) -> None:
    JUDGMENT_CALLS.append(msg)


def build_facts() -> list[dict]:
    facts: list[dict] = []

    # --- 1.1 Identity (F-001…F-020): single facet "value" ---
    identity = [
        ("F-001", "identity.implementing_organisation", "BridgeLight Education Trust", "D1", "CONFIRMED", "Implementing organisation"),
        ("F-002", "identity.charity_registration", "1198427", "D1", "CONFIRMED", "Charity registration (England and Wales)"),
        ("F-003", "identity.uk_base", "Bristol", "D1", "CONFIRMED", "UK base"),
        ("F-004", "identity.programme_title", "Girls Return to Learning and Safety Programme", "D1, D2", "CONFIRMED", "Programme title"),
        ("F-005", "identity.fcdo_programme_code", "MWI-EDU-AR-4471", "D2", "CONFIRMED", "FCDO programme code"),
        ("F-006", "identity.country_and_districts", "Malawi: Machinga and Mangochi", "D1, D2", "CONFIRMED", "Country and districts"),
        ("F-007", "contract.approved_fcdo_contribution", "£1,240,000", "D2", "RESOLVED — see C-01", "Approved FCDO contribution"),
        ("F-008", "contract.programme_start_date", "15 October 2024", "D2", "RESOLVED — see C-02", "Programme start date"),
        ("F-009", "contract.programme_end_date", "14 October 2026", "D2", "RESOLVED — see C-02", "Programme end date"),
        ("F-010", "contract.inception_period", "15 October 2024 to 31 December 2024", "D2", "CONFIRMED", "Inception period"),
        ("F-011", "contract.ar1_contractual_review_period", "15 October 2024 to 14 October 2025", "D2", "RESOLVED — see C-02", "AR1 contractual review period"),
        ("F-012", "contract.ar1_review_pack_due_date", "21 November 2025", "D2", "CONFIRMED", "AR1 review pack due date"),
        ("F-013", "contract.period_covered_by_reported_data", "1 October 2024 to 30 September 2025", "D3", "CAVEATED — see C-02", "Period actually covered by reported data"),
        ("F-014", "contract.initial_programme_risk_rating", "Medium-High", "D2", "CONFIRMED", "Initial programme risk rating"),
        ("F-015", "contract.fcdo_sro", "Helen Armitage, Education and Gender Equality Programmes", "D2", "CONFIRMED", "FCDO Senior Responsible Owner"),
        ("F-016", "contract.award_letter_addressee", "Chief Executive, BridgeLight Education Trust (Dr Patel)", "D2", "CONFIRMED", "Award letter addressee"),
        ("F-017", "contract.award_letter_date", "27 September 2024", "D2", "CONFIRMED", "Award letter date"),
        ("F-018", "contract.proposal_date", "19 August 2024", "D1", "CONFIRMED", "Proposal date"),
        ("F-019", "contract.results_export_date", "3 October 2025", "D3", "CONFIRMED", "Results export date"),
        ("F-020", "contract.results_export_worksheet_name", "AR1_OutputScore_DRAFT_do_not_overwrite", "D3", "CONFIRMED — draft status is explicit", "Results export worksheet name"),
    ]
    note("Source column abbreviated to D1/D2/D3 primary document codes; section refs (e.g. D1 header, D3 cell A2) retained in label where material, not as separate source_document tokens.")
    for fid, slot, val, src, status, label in identity:
        facts.append(fact(fid, slot, "value", val, src, status, label=label))

    design = [
        ("F-021", "design.schools_in_scope", "40 primary and community day secondary", "D1", "CONFIRMED", "Schools in scope"),
        ("F-022", "design.direct_girl_beneficiary_target", "1,200 girls and young women aged 10–19", "D1", "CONFIRMED", "Direct girl beneficiary target"),
        ("F-023", "design.caregiver_target", "800", "D1", "CONFIRMED", "Caregiver target"),
        ("F-024", "design.school_and_community_actor_target", "160", "D1", "CAVEATED — conflicts with OP4.3 endline of 240; see C-05", "School and community actor target"),
        ("F-025", "design.priority_groups", "Girls with disabilities; married adolescent girls seeking re-entry; ultra-poor households; girls affected by seasonal migration around Lake Malawi", "D1", "CONFIRMED", "Priority groups"),
        ("F-026", "design.impact_statement", "Adolescent girls in Machinga and Mangochi complete basic education in safer, more supportive learning environments", "D1", "CONFIRMED", "Impact statement"),
        ("F-027", "design.outcome_statement", "By September 2026, adolescent girls targeted by the programme demonstrate improved school retention, attendance and learning continuity, with reduced practical and safeguarding barriers to education", "D1", "CONFIRMED", "Outcome statement"),
        ("F-028", "design.prior_organisational_track_record", "Safe Steps to School pilot, Machinga, supported 1,480 learners to return after COVID-19 closures", "D1", "CONFIRMED", "Prior organisational track record"),
        ("F-029", "design.baseline_assessment_finding", "44% of girls interviewed across 18 schools had missed at least five school days in the previous month (2023)", "D1", "CONFIRMED", "Baseline assessment finding"),
        ("F-030", "design.monitoring_age_bands_for_girls", "6–11, 12–17, 18–24", "D1", "CAVEATED — does not align with the 10–19 target population; see C-06", "Monitoring age bands for girls"),
        ("F-031", "design.vulnerability_categories", "Disability; ultra-poor household; married or previously married adolescent; orphaned or separated child; high dropout-risk household", "D1", "CONFIRMED", "Vulnerability categories"),
    ]
    for fid, slot, val, src, status, label in design:
        facts.append(fact(fid, slot, "value", val, src, status, label=label))

    note("ontology_slot strings are transcription scaffolding derived from golden section + fact label; they are not engine fact_keys. Facet identity is the mandated grain (owner ruling 1).")

    # Outcomes F-032…F-034 — four facets each; status column = Gap G-01
    outcomes = [
        ("F-032", "outcome.ocm1", "OCM1 — % of supported girls attending school at least 80% of days in last completed term", "38%", "55%", "70%", "NOT REPORTED"),
        ("F-033", "outcome.ocm2", "OCM2 — % of supported girls progressing to next grade or completing re-entry pathway", "31%", "48%", "65%", "NOT REPORTED"),
        ("F-034", "outcome.ocm3", "OCM3 — % of girls reporting school is safe during menstruation and travel", "41%", "58%", "72%", "NOT REPORTED"),
    ]
    note("F-032…F-034 Status column is 'Gap G-01' (not CONFIRMED/RESOLVED/…). Preserved verbatim as status per ruling 3 (golden vocabulary).")
    for fid, slot, label, baseline, y1, endline, achieved in outcomes:
        for facet, val in [
            ("baseline", baseline),
            ("y1_milestone", y1),
            ("endline", endline),
            ("achieved", achieved),
        ]:
            facts.append(fact(fid, slot, facet, val, "D1", "Gap G-01", label=label))

    # Outputs design F-035…F-038
    outputs = [
        ("F-035", "output.op1", "Output 1 — Girls re-enter and remain in education", "35%", "Medium"),
        ("F-036", "output.op2", "Output 2 — Schools provide safer WASH and safeguarding conditions for girls", "25%", "Medium"),
        ("F-037", "output.op3", "Output 3 — Households reduce immediate cost barriers to girls' attendance", "25%", "High"),
        ("F-038", "output.op4", "Output 4 — District education actors use evidence to improve girls' re-entry practice", "15%", "Low"),
    ]
    note("F-035…F-038 have no Status column in golden; transcribed as CONFIRMED (D1 and D3 agree).")
    for fid, slot, label, weight, risk in outputs:
        facts.append(fact(fid, slot, "impact_weighting", weight, "D1, D3", "CONFIRMED", unit="percent", label=label))
        facts.append(fact(fid, slot, "risk_rating", risk, "D1, D3", "CONFIRMED", label=label))

    facts.append(
        fact(
            "F-039",
            "output.impact_weightings_sum",
            "value",
            "100%",
            "Derived",
            "CONFIRMED",
            label="Impact weightings sum — Arithmetic check on F-035…F-038: passes",
        )
    )
    note("F-039 source recorded as 'Derived' (golden: Arithmetic check); status CONFIRMED as check passes.")

    # Output indicators F-040…F-051
    indicators = [
        ("F-040", "indicator.op1_1", "OP1.1 Girls re-enrolled or newly retained through support package", "0", "650", "1,200", "684", "A", "Above (+34)", "RESOLVED — see C-03"),
        ("F-041", "indicator.op1_2", "OP1.2 Supported girls attending ≥80% of school days in last completed term", "0", "500", "900", "472", "B", "Below (−28)", "CONFIRMED"),
        ("F-042", "indicator.op1_3", "OP1.3 Girls completing at least 20 remedial learning sessions", "0", "420", "850", "438", "A", "Above (+18)", "CONFIRMED"),
        ("F-043", "indicator.op2_1", "OP2.1 Separate, lockable girls' latrine stances rehabilitated or newly functional", "6", "24", "40", "31", "A", "Above (+7)", "CAVEATED — see C-07"),
        ("F-044", "indicator.op2_2", "OP2.2 Schools with menstrual health supplies and trained focal teachers", "0", "20", "40", "17", "C", "Below (−3)", "CONFIRMED"),
        ("F-045", "indicator.op2_3", "OP2.3 Schools with active safeguarding referral pathway tested through termly case-review meeting", "0", "18", "40", "NOT REPORTED", "—", "—", "Gap G-02"),
        ("F-046", "indicator.op3_1", "OP3.1 Caregivers receiving education hardship grant linked to girls' attendance plan", "0", "400", "800", "392", "B", "Below (−8)", "CONFIRMED"),
        ("F-047", "indicator.op3_2", "OP3.2 Girls receiving school re-entry kit or learning materials package", "0", "550", "1,100", "571", "A", "Above (+21)", "CONFIRMED"),
        ("F-048", "indicator.op3_3", "OP3.3 % of hardship grant households with verified attendance follow-up within 45 days", "0%", "75%", "85%", "68%", "C", "Below (−7pp)", "CONFIRMED"),
        ("F-049", "indicator.op4_1", "OP4.1 District learning meetings held with documented action points", "0", "4", "8", "3", "B", "Below (−1)", "CONFIRMED"),
        ("F-050", "indicator.op4_2", "OP4.2 Learning briefs produced and shared with district education stakeholders", "0", "2", "5", "NOT REPORTED", "—", "—", "Gap G-03"),
        ("F-051", "indicator.op4_3", "OP4.3 School and community actors trained on girls' re-entry and safeguarding protocols", "0", "120", "240", "136", "A", "Above (+16)", "CONFIRMED"),
    ]
    note("F-040…F-051 expanded to six facets: baseline, y1_milestone, endline, achieved, proposed_score, vs_milestone. Em-dash cells for unreported indicators preserved as '—'.")
    for row in indicators:
        fid, slot, label, baseline, y1, endline, achieved, score, vs, status = row
        for facet, val in [
            ("baseline", baseline),
            ("y1_milestone", y1),
            ("endline", endline),
            ("achieved", achieved),
            ("proposed_score", score),
            ("vs_milestone", vs),
        ]:
            facts.append(fact(fid, slot, facet, val, "D1, D3", status, label=label))

    derived = [
        ("F-052", "derived.output_indicators_in_framework", "12", "Output indicators in the results framework"),
        ("F-053", "derived.output_indicators_with_reported_achieved", "10", "Output indicators with a reported achieved value"),
        ("F-054", "derived.reported_at_or_above_y1_milestone", "5 (OP1.1, OP1.3, OP2.1, OP3.2, OP4.3)", "Reported indicators at or above Year 1 milestone"),
        ("F-055", "derived.reported_below_y1_milestone", "5 (OP1.2, OP2.2, OP3.1, OP3.3, OP4.1)", "Reported indicators below Year 1 milestone"),
        ("F-056", "derived.output_indicators_with_no_reported_value", "2 (OP2.3, OP4.2)", "Output indicators with no reported value"),
    ]
    note("F-052…F-056 are derived summaries; source_document='Derived'; status='CONFIRMED' (arithmetic on F-040…F-051).")
    for fid, slot, val, label in derived:
        facts.append(fact(fid, slot, "value", val, "Derived", "CONFIRMED", label=label))

    evidence = [
        ("F-057", "indicator.op1_1", "School registers; re-entry club forms; district validation sample", "Above milestone. Some double-count risk removed in September cleaning."),
        ("F-058", "indicator.op1_2", "Term 3 attendance registers from 36 schools", "Under milestone due to late register submission from four schools."),
        ("F-059", "indicator.op1_3", "Remedial class attendance sheets", "Slightly above milestone."),
        ("F-060", "indicator.op2_1", "WASH engineer completion certificates; school verification photos", "Above milestone, but four units still need disposal bins."),
        ("F-061", "indicator.op2_2", "Training attendance sheets; supply distribution records", "Below milestone because three schools had no female focal teacher available."),
        ("F-062", "indicator.op3_1", "Mobile money payment list; school attendance follow-up sample", "Slightly below target after deduplication of 16 caregiver records."),
        ("F-063", "indicator.op3_2", "Kit distribution forms; headteacher confirmations", "Above milestone."),
        ("F-064", "indicator.op3_3", "Follow-up tracker; district officer sample", "Below milestone because September follow-ups incomplete."),
        ("F-065", "indicator.op4_1", "Meeting minutes; attendance sheets", "One meeting cancelled during district exam period."),
        ("F-066", "indicator.op4_3", "Training attendance sheets; pre/post quiz forms", "Above target."),
    ]
    note("F-057…F-066: two facets (evidence_source, variance_explanation); no Status column → CONFIRMED; source D3.")
    for fid, slot, ev, var in evidence:
        facts.append(fact(fid, slot, "evidence_source", ev, "D3", "CONFIRMED", label=fid))
        facts.append(fact(fid, slot, "variance_explanation", var, "D3", "CONFIRMED", label=fid))

    finance_lines = [
        ("F-067", "finance.op1_1", "OP1.1", 162000, 174850, 12850, "Transport costs higher due to lake-shore schools"),
        ("F-068", "finance.op1_2", "OP1.2", 94000, 98740, 4740, "Staff time loaded here, may belong in Output 4"),
        ("F-069", "finance.op1_3", "OP1.3", 88000, 81330, -6670, "Teacher stipends lower than forecast"),
        ("F-070", "finance.op2_1", "OP2.1", 121000, 148900, 27900, "Cement and transport over budget"),
        ("F-071", "finance.op2_2", "OP2.2", 42000, 39600, -2400, "Supplies procured late"),
        ("F-072", "finance.op3_1", "OP3.1", 146000, 151440, 5440, "Payment fees higher than forecast"),
        ("F-073", "finance.op3_2", "OP3.2", 103000, 109250, 6250, "Extra notebooks bought locally"),
        ("F-074", "finance.op3_3", "OP3.3", 31000, 24980, -6020, "Underspend due to vacant M&E assistant post"),
        ("F-075", "finance.op4_1", "OP4.1", 39000, 32700, -6300, "Venue costs lower"),
        ("F-076", "finance.op4_3", "OP4.3", 54000, 58630, 4630, "Facilitator travel higher"),
    ]
    note("F-067…F-076: numeric GBP values stored as integers without £ comma formatting; unit='GBP'. Four facets: forecast_y1, actual_y1, variance, finance_note.")
    for fid, slot, label, fc, ac, var, note_txt in finance_lines:
        facts.append(fact(fid, slot, "forecast_y1", fc, "D3", "CONFIRMED", unit="GBP", label=label))
        facts.append(fact(fid, slot, "actual_y1", ac, "D3", "CONFIRMED", unit="GBP", label=label))
        facts.append(fact(fid, slot, "variance", var, "D3", "CONFIRMED", unit="GBP", label=label))
        facts.append(fact(fid, slot, "finance_note", note_txt, "D3", "CONFIRMED", label=label))

    for facet, val in [
        ("forecast_y1", 880000),
        ("actual_y1", 920420),
        ("variance", 40420),
        ("finance_note", "Forecast is AR1 only, not full life-of-project"),
    ]:
        facts.append(
            fact(
                "F-077",
                "finance.total_ar1",
                facet,
                val,
                "D3",
                "CONFIRMED",
                unit="GBP" if facet != "finance_note" else None,
                label="Total AR1",
            )
        )

    more_fin = [
        ("F-078", "finance.ar1_overspend_pct", "4.6%", "Derived from F-077 (40,420 ÷ 880,000)", "DERIVED — derivation stated", "AR1 overspend as % of forecast"),
        ("F-079", "finance.proposal_budget_total_superseded", "£1,184,000", "D1", "RESOLVED — see C-01", "Proposal budget total (superseded)"),
        ("F-080", "finance.proposal_budget_lines", "Staff/TA £338,000; Local partner £214,000; School WASH £226,000; Hardship grants and kits £238,000; MEL £82,000; Operations/travel/audit £86,000", "D1", "CONFIRMED as the proposal position; superseded as the approved position", "Proposal budget lines"),
        ("F-081", "finance.proposal_budget_source", "Proposal workbook, tab Budget_Final_v5", "D1", "CONFIRMED", "Proposal budget source"),
        ("F-082", "finance.cost_per_girl_business_case", "approximately £987 over two years, using £1,184,000 and 1,200 girls", "D1", "CAVEATED — basis is the superseded budget; see C-01", "Cost per directly supported girl, business-case basis"),
        ("F-083", "finance.named_cost_drivers", "School rehabilitation works; hardship grants; district field transport; local partner facilitation", "D1", "CONFIRMED", "Named cost drivers"),
    ]
    for fid, slot, val, src, status, label in more_fin:
        facts.append(fact(fid, slot, "value", val, src if src.startswith("D") or src.startswith("Derived") else src, status, label=label))

    # Fix F-078 source
    for r in facts:
        if r["id"] == "F-078":
            r["source_document"] = "Derived"

    disagg = [
        ("F-084", "disaggregation.op1_1", "OP1.1", "684", "681 (F6-11 58; F12-17 590; F18-24 33)", "No — short by 3"),
        ("F-085", "disaggregation.op1_2", "OP1.2", "472", "471 (39; 410; 22)", "No — short by 1"),
        ("F-086", "disaggregation.op1_3", "OP1.3", "438", "438 (35; 382; 21)", "Yes"),
        ("F-087", "disaggregation.op2_1", "OP2.1", "31", "0 — not a person-level indicator", "N/A, correctly zero"),
        ("F-088", "disaggregation.op2_2", "OP2.2", "17", "0 — not a person-level indicator", "N/A, correctly zero"),
        ("F-089", "disaggregation.op3_1", "OP3.1", "392", "392 (M6-11 96; M12-17 118; M18-24 178)", "Arithmetically yes; substantively not credible — see C-04"),
        ("F-090", "disaggregation.op3_2", "OP3.2", "571", "571 (48; 498; 25)", "Yes"),
        ("F-091", "disaggregation.op3_3", "OP3.3", "68%", "0 — percentage indicator", "N/A, correctly zero"),
        ("F-092", "disaggregation.op4_1", "OP4.1", "3", "39 across six cells", "Unit mismatch — meetings disaggregated as if people; see C-04"),
        ("F-093", "disaggregation.op4_3", "OP4.3", "136", "136 (F12-17 64; F18-24 8; M6-11 28; M12-17 31; M18-24 5)", "Yes"),
    ]
    note("F-084…F-093: three facets achieved, sum_of_sex_age_cells, reconciles. Bold markdown stripped from reconciles text.")
    for fid, slot, label, ach, summ, rec in disagg:
        facts.append(fact(fid, slot, "achieved", ach, "D3", "CONFIRMED", label=label))
        facts.append(fact(fid, slot, "sum_of_sex_age_cells", summ, "D3", "CONFIRMED", label=label))
        facts.append(fact(fid, slot, "reconciles", rec, "D3", "CONFIRMED", label=label))

    vuln = [
        ("F-094", "disaggregation.vulnerability_disability_total", "142 — passes", "Disability column sums to reported total"),
        ("F-095", "disaggregation.vulnerability_ultra_poor_total", "2,376 — passes", "Ultra-poor column sums to reported total"),
        ("F-096", "disaggregation.vulnerability_previously_married_total", "Row sum is 227 against a stated total of 291 — fails by 64", "Previously married column sums to reported total"),
        ("F-097", "disaggregation.total_row_nature", "Column sums across overlapping indicators, not unique beneficiary counts", "Nature of the TOTAL row — See C-08"),
    ]
    note("F-094…F-097: vulnerability / TOTAL-row checks; status CONFIRMED as stated findings (F-096 fail is a confirmed finding).")
    for fid, slot, val, label in vuln:
        facts.append(fact(fid, slot, "value", val, "D3", "CONFIRMED", label=label))

    qualitative = [
        ("F-098", "qualitative.activity_list", "Activity list — identification, re-entry counselling, bridge learning, latrine rehabilitation, menstrual health supply, hardship grants and kits, safeguarding referral mapping, quarterly learning meetings", "D1"),
        ("F-099", "qualitative.mel_system", "MEL system — logframe-based; sources are attendance registers, re-entry club records, caregiver payment lists, WASH completion certificates, meeting attendance sheets, case referral logs, quarterly survey tools", "D1"),
        ("F-100", "qualitative.output_scoring_process", "Output scoring process — MEL Manager proposes initial scores; final scores to be agreed with the FCDO review team", "D1"),
        ("F-101", "qualitative.risks_identified_at_design", "Risks identified at design — school calendar disruption; construction material inflation; local political pressure in beneficiary selection; low mobile-money coverage; safeguarding risks in identifying girls affected by early marriage or abuse", "D1"),
        ("F-102", "qualitative.safeguarding_controls_at_design", "Safeguarding controls at design — child safeguarding procedures, staff code of conduct, community complaints mechanisms, referral pathways via district social welfare offices", "D1"),
        ("F-103", "qualitative.fcdo_review_pack_requirements", "FCDO review pack requirements — narrative against results framework; updated logframe with milestones, actuals, output scores and variance explanations; forecast versus actual expenditure statement; VfM assessment covering economy, efficiency, effectiveness and equity; risk, safeguarding and assumptions update; recommendations and action plan; any evaluation or learning outputs", "D2"),
        ("F-104", "qualitative.fcdo_evidence_requirement", "BridgeLight must provide evidence for each numeric claim included in the review", "D2"),
        ("F-105", "qualitative.documents_fcdo_may_request", "Attendance registers, payment records, procurement files, safeguarding incident logs, training attendance sheets, WASH completion records", "D2"),
        ("F-106", "qualitative.vfm_management_approach_at_design", "VfM management approach at design — local procurement for rehabilitation; competitive pricing for kits; efficiency monitored via cost per girl re-enrolled, cost per school with completed WASH works, staff cost as share of total spend; effectiveness via attendance, re-entry and progression; equity via share of support reaching girls with disabilities, ultra-poor households and previously out-of-school girls", "D1"),
    ]
    note("F-098…F-106: no Status column → CONFIRMED.")
    for fid, slot, val, src in qualitative:
        facts.append(fact(fid, slot, "value", val, src, "CONFIRMED", label=val.split(" — ")[0] if " — " in val else fid))

    return facts


def build_conflicts() -> list[dict]:
    return [
        {
            "id": "C-01",
            "title": "Approved budget: £1,184,000 versus £1,240,000",
            "sides": [
                {"value": "£1,184,000", "source": "D1 §2 and §10 (proposal budget; worksheet rounded £1.18 million)"},
                {"value": "£1,240,000", "source": "D2 (approved FCDO contribution, inclusive of delivery, management, M&E, contingency)"},
            ],
            "adjudication": "£1,240,000 is the approved contribution. The award letter is the contracting instrument and post-dates the proposal by five weeks. The proposal itself signals its own figure is stale. The £1,184,000 remains a true fact about the proposal position and must not be deleted — it is the correct basis for the business-case cost-per-girl figure — but it is not the approved budget.",
            "resolution_type": "prefer_award_letter_keep_proposal_as_true_fact",
            "reportable_form": "FCDO approved £1,240,000. Never 'the programme budget is £1,184,000.'",
            "defects": [],
        },
        {
            "id": "C-02",
            "title": "Reporting period: 15 Oct–14 Oct versus 1 Oct–30 Sep",
            "sides": [
                {"value": "15 October 2024 to 14 October 2025", "source": "D2 contractual AR1 period"},
                {"value": "1 October 2024 to 30 September 2025", "source": "D3 cell A2 — period covered by reported data"},
                {"value": "October 2024 to September 2025 anticipated", "source": "D1 §6 (exact cut-off may be confirmed after contracting)"},
            ],
            "adjudication": "Two different facts, both true, and they must both be stated. Contractual review period is 15 Oct 2024–14 Oct 2025. Period actually covered by every reported figure is 1 Oct 2024–30 Sep 2025. No written amendment exists.",
            "resolution_type": "both_are_true_different_facts",
            "reportable_form": "Mismatch disclosed in Section A before any result, carried into evidence-quality table and recommendations.",
            "defects": [],
        },
        {
            "id": "C-03",
            "title": "OP1.1 re-enrolment: 612 versus 684",
            "sides": [
                {"value": "612", "source": "D1 §5 internal note by 16 September 2025 (pre-verification)"},
                {"value": "684", "source": "D3 achieved value, AR1 export 3 October 2025, post-cleaning"},
            ],
            "adjudication": "684 is the reportable actual. Cleaning described as removing double-counts produced a figure 72 higher, not lower — unexplained movement must survive as a provenance flag. D1 dated 19 August 2024 containing Sep 2025 data means D1 cannot be treated as a single fixed-date document.",
            "resolution_type": "prefer_later_export_with_provenance_flag",
            "reportable_form": "684 as verified figure; unexplained 612→684 movement flagged in evidence quality.",
            "defects": [],
        },
        {
            "id": "C-04",
            "title": "Disaggregation that does not survive inspection",
            "sides": [
                {"value": "Headline actuals 392 / 3 / 684 / 472", "source": "D3 achieved values"},
                {"value": "Disaggregation cells as exported", "source": "D3 sex/age columns"},
            ],
            "adjudication": "Report the headline, refuse the breakdown for OP3.1 and OP4.1. Note OP1.1 and OP1.2 shortfalls. State disaggregated data is not currently reliable enough for the funder's disaggregation requirement.",
            "resolution_type": "report_headline_refuse_breakdown",
            "reportable_form": "Report 392 caregivers, 3 meetings, 684 girls and 472 girls. Do not report OP3.1 or OP4.1 disaggregation as valid.",
            "defects": [
                {
                    "id": "C-04a",
                    "subject": "OP3.1 caregivers",
                    "detail": "392 recorded as 96 males aged 6–11, 118 aged 12–17, 178 aged 18–24, no females. Caregivers in child age bands not credible; all-male caregivers via mother groups not credible. Arithmetic reconciles; substance fails.",
                },
                {
                    "id": "C-04b",
                    "subject": "OP4.1 meetings",
                    "detail": "Three meetings disaggregated across six person-bands totalling 39. Meetings do not have sex or age; cells presumably describe attendees (different indicator).",
                },
                {
                    "id": "C-04c",
                    "subject": "OP1.1 and OP1.2 shortfalls",
                    "detail": "Sex and age cells fall short of headline by 3 and 1 respectively. Disaggregation incomplete against reported total.",
                },
            ],
        },
        {
            "id": "C-05",
            "title": "Community actor target: 160 versus 240",
            "sides": [
                {"value": "160", "source": "D1 §2 school and community actor target"},
                {"value": "240", "source": "OP4.3 endline target (same document)"},
            ],
            "adjudication": "Report against the logframe endline of 240, since the logframe is the results framework FCDO assesses, and flag the inconsistency. Do not silently pick one.",
            "resolution_type": "prefer_logframe_endline_flag_inconsistency",
            "reportable_form": "Report against 240 endline; flag 160 vs 240 inconsistency.",
            "defects": [],
        },
        {
            "id": "C-06",
            "title": "Age bands versus target population",
            "sides": [
                {"value": "10–19 target population", "source": "D1 §2"},
                {"value": "Monitoring bands 6–11, 12–17, 18–24", "source": "D1 §7"},
            ],
            "adjudication": "Report the data as banded, note that monitoring bands do not align with stated target population, and do not attempt to re-band or estimate an in-range figure.",
            "resolution_type": "report_as_banded_note_misalignment",
            "reportable_form": "Data as banded; note misalignment; no re-banding.",
            "defects": [],
        },
        {
            "id": "C-07",
            "title": "OP2.1 baseline treatment",
            "sides": [
                {"value": "Baseline 6 functional stances; achieved 31; milestone 24", "source": "D1/D3 OP2.1"},
                {"value": "Indicator wording 'rehabilitated or newly functional' ambiguous on cumulative vs new", "source": "Indicator definition"},
            ],
            "adjudication": "Report 31 as stated against milestone of 24, and flag the definitional ambiguity. Do not adjust the figure in either direction.",
            "resolution_type": "report_as_stated_flag_definitional_ambiguity",
            "reportable_form": "31 against milestone 24 with definitional caveat.",
            "defects": [],
        },
        {
            "id": "C-08",
            "title": "The TOTAL row",
            "sides": [
                {"value": "Column totals e.g. Female 12–17 = 1,944; ultra-poor = 2,376", "source": "D3 TOTAL row"},
                {"value": "Programme targets 1,200 girls total", "source": "D1 design"},
            ],
            "adjudication": "TOTAL row excluded from the knowledge bank as a reportable fact. Retained only as an arithmetic artefact. 227-versus-291 previously-married discrepancy reported as data-quality finding. Never report TOTAL as beneficiary counts.",
            "resolution_type": "exclude_from_reportable_facts_retain_as_artefact",
            "reportable_form": "Do not report TOTAL-row figures as reach. Report 227 vs 291 as data-quality finding.",
            "defects": [],
        },
        {
            "id": "C-09",
            "title": "Proposed output scores",
            "sides": [
                {"value": "Per-indicator scores A/B/C on DRAFT worksheet", "source": "D3 AR1_OutputScore_DRAFT_do_not_overwrite"},
                {"value": "Final scores agreed with FCDO; FCDO scores at Output level", "source": "D1 §7, D2"},
            ],
            "adjudication": "Two resolutions. First: proposed and draft — reportable as BridgeLight's proposed position, never as agreed scores. Second: Output-level score cannot be derived from indicator-level scores without a weighting rule the documents do not contain. Output 2 and 4 incomplete. Do not aggregate.",
            "resolution_type": "draft_proposed_only_do_not_aggregate",
            "reportable_form": "Proposed/draft only; never agreed/final/FCDO-assigned; no indicator-to-output aggregation.",
            "defects": [],
        },
    ]


def build_gaps() -> dict:
    clusters = [
        {
            "id": "G-01",
            "gap": "Achieved values for the three outcome indicators (OCM1, OCM2, OCM3)",
            "why_real": "The results export is output-level only. The Annual Review must assess the Outcome. No proxy is legitimate.",
            "severity": "Critical",
            "question_intent": "Obtain endline or annual survey figures for the three outcome indicators (attendance ≥80%, progression/re-entry, safety during menstruation and travel); if unavailable, report honestly rather than estimate.",
            "correct_period_comparator": "Year 1 milestone / outcome targets for the review year (not endline-only; not output proxies)",
        },
        {
            "id": "G-02",
            "gap": "OP2.3 achieved value — schools with an active safeguarding referral pathway tested through a termly case-review meeting",
            "why_real": "Indicator exists in the framework with a Year 1 milestone of 18; absent from the export",
            "severity": "High",
            "question_intent": "Obtain achieved figure for OP2.3; Year 1 target was 18.",
            "correct_period_comparator": "Year 1 milestone of 18 (not endline 40)",
        },
        {
            "id": "G-03",
            "gap": "OP4.2 achieved value — learning briefs produced and shared",
            "why_real": "Indicator exists with a Year 1 milestone of 2; absent from the export",
            "severity": "High",
            "question_intent": "Obtain achieved figure for OP4.2; Year 1 target was 2.",
            "correct_period_comparator": "Year 1 milestone of 2 (not endline 5)",
        },
        {
            "id": "G-04",
            "gap": "Current risk ratings and a risk register update for the period",
            "why_real": "Only design-stage ratings and an initial programme rating exist. The template requires previous and current ratings with mitigation, owner and status.",
            "severity": "High",
            "question_intent": "Where each risk stands today — moved up/down, mitigations, owner.",
            "correct_period_comparator": "Current period status vs design/award ratings",
        },
        {
            "id": "G-05",
            "gap": "Safeguarding activity during the review period — concerns raised, cases referred, outcomes",
            "why_real": "Design-stage controls are documented; nothing about the period. FCDO names safeguarding as a review-pack requirement.",
            "severity": "High",
            "question_intent": "Safeguarding update for the period; nil return is valid.",
            "correct_period_comparator": "Activity during the review period (not design-stage controls alone)",
        },
        {
            "id": "G-06",
            "gap": "Partner and supplier performance assessment",
            "why_real": "£214,000 budgeted for local partner delivery; no partner is named and no performance view exists",
            "severity": "Medium",
            "question_intent": "Partner performance this year — delivery quality, commercial/procurement issues.",
            "correct_period_comparator": "Period performance against partner delivery budget",
        },
        {
            "id": "G-07",
            "gap": "Total programme expenditure against the £1,240,000 approved envelope",
            "why_real": "Only indicator-attributed AR1 costs exist. The award letter requires a forecast-versus-actual expenditure statement.",
            "severity": "High",
            "question_intent": "Programme-level expenditure statement vs full £1,240,000 award.",
            "correct_period_comparator": "Forecast vs actual against approved £1,240,000 (not indicator-attributed AR1-only)",
        },
        {
            "id": "G-08",
            "gap": "Explanation of the OP1.1 movement from 612 to 684, and of the disaggregation shortfalls",
            "why_real": "Both are unexplained in the documents and both are the kind of thing an FCDO reviewer asks about",
            "severity": "Medium",
            "question_intent": "Confirm what changed 612→684; address age/sex shortfalls on two indicators.",
            "correct_period_comparator": "N/A — explanation of existing figures",
        },
        {
            "id": "G-09",
            "gap": "Confirmation of the reporting period position — has FCDO agreed the October–September cut in writing, or will data be recut?",
            "why_real": "D2 requires written amendment; no amendment is in the bundle",
            "severity": "Critical",
            "question_intent": "Has FCDO agreed Oct–Sep in writing, or should the mismatch be flagged?",
            "correct_period_comparator": "Contractual 15 Oct–14 Oct vs data 1 Oct–30 Sep",
        },
        {
            "id": "G-10",
            "gap": "Evaluation activity and new evidence generated during the period, or confirmation that none was produced",
            "why_real": "Required by the template and named in the review-pack list",
            "severity": "Medium",
            "question_intent": "Any evaluation or external evidence this year? If not, say so.",
            "correct_period_comparator": "Activity during the review period",
        },
    ]
    note("Gap question_intent and correct_period_comparator distilled from §3.1–3.2 script; wording paraphrased for machine fields while preserving intent. Full question script prose retained in gaps.question_script_prose.")
    counter = [
        {"do_not_ask_for": "Impact weightings", "because": "Present in both D1 and D3, and they agree"},
        {"do_not_ask_for": "Baselines or targets for any indicator", "because": "All twelve are in D1"},
        {"do_not_ask_for": "Achieved values for the ten reported indicators", "because": "All in D3"},
        {"do_not_ask_for": "Output scores", "because": "Present as proposed values; the final score is FCDO's to set"},
        {"do_not_ask_for": "Evidence sources for the ten reported indicators", "because": "Every row carries one"},
        {"do_not_ask_for": "Variance explanations for the ten reported indicators", "because": "Every row carries one"},
        {"do_not_ask_for": "Updates on previous recommendations", "because": "This is the first Annual Review. There are none. The correct output is 'not applicable', not a question."},
        {"do_not_ask_for": "The programme budget", "because": "£1,240,000 in D2"},
        {"do_not_ask_for": "Programme dates or the review due date", "because": "All in D2"},
        {"do_not_ask_for": "Organisation background, charity number, districts, schools", "because": "All in D1"},
        {"do_not_ask_for": "Outcome or impact statements", "because": "D1 §4"},
        {"do_not_ask_for": "The activity list", "because": "D1 §6"},
        {"do_not_ask_for": "Design-stage risks or safeguarding controls", "because": "D1 §9"},
        {"do_not_ask_for": "Named cost drivers or the VfM approach", "because": "D1 §8"},
        {"do_not_ask_for": "Value-for-money measures, scoring rubric, DevTracker flags", "because": "Funder-owned. Never surface to the NGO."},
    ]
    # Load question script from golden between 3.2 markers — store as extracted blocks
    script = Path(ROOT / SOURCE).read_text(encoding="utf-8")
    start = script.index("## 3.2 The question script")
    end = script.index("## 3.3 What must NOT be asked")
    prose = script[start:end].strip()
    return {
        "clusters": clusters,
        "counter_list": counter,
        "question_script_prose": prose,
        "target_note": "no more than the ten clusters above, phrased in the NGO's language, with anything already in the knowledge bank offered as a confirm rather than a question.",
    }


def build_forbidden() -> list[dict]:
    # detection_method: deterministic | judged — judgment recorded
    rows = [
        ("FB-01", "Any statement that the programme reached 1,944 girls aged 12–17, or 2,376 ultra-poor households, or any figure drawn from the TOTAL row as a beneficiary count", "Column sums across overlapping indicators. 1,944 exceeds the entire 1,200 life-of-programme target. Fluent, specific, and absurd to a reviewer.", "Critical", "deterministic"),
        ("FB-02", "Any outcome indicator value derived from output data — for example OCM1 as 472/684 = 69%, or any attendance percentage presented as outcome achievement", "Different populations, different definitions, no denominator. Invents the single result the funder most wants.", "Critical", "deterministic"),
        ("FB-03", "Stating the review period as 15 Oct 2024–14 Oct 2025 while presenting Oct–Sep data without disclosing the offset", "Silently misattributes every figure to a period it does not describe, against a funder who stated the contractual period governs", "Critical", "judged"),
        ("FB-04", "Stating £1,184,000 as the programme budget or the approved contribution", "Superseded by the award letter", "High", "deterministic"),
        ("FB-05", "Omitting OP2.3 or OP4.2 from the report without flagging them as unreported", "Silent impoverishment — the user cannot see what is missing", "Critical", "deterministic"),
        ("FB-06", "Reporting that all 392 hardship grant recipients were male, or presenting any OP3.1 age or sex breakdown as fact", "Not credible; arithmetic reconciliation masks substantive nonsense", "High", "deterministic"),
        ("FB-07", "Reporting 612 as the re-enrolment figure, or reporting 684 without noting the unexplained movement", "612 is superseded; 684 without the flag hides a data-integrity question", "High", "judged"),
        ("FB-08", "Presenting the proposed output scores as agreed, final or FCDO-assigned", "Explicitly draft and explicitly subject to FCDO agreement", "High", "judged"),
        ("FB-09", "Producing a single output-level score by aggregating indicator scores", "No weighting rule exists; two outputs are incomplete", "High", "deterministic"),
        ("FB-10", "Inventing current risk ratings, mitigations, owners or statuses", "None exist in the source material", "Critical", "judged"),
        ("FB-11", "Reporting a safeguarding position, incident count or nil return for the period", "No safeguarding information for the period exists. A fabricated nil return is the most dangerous variant.", "Critical", "judged"),
        ("FB-12", "Presenting £987 per girl as the current value-for-money position without stating that it rests on the superseded budget", "Materially misstates unit cost against the approved envelope", "Medium", "judged"),
        ("FB-13", "Reporting a life-of-programme burn rate or remaining budget from the AR1 finance columns", "Forecast column is explicitly AR1-only; attribution is indicator-level, not total programme spend", "Medium", "deterministic"),
        ("FB-14", "Asking the NGO for previous recommendations, output scores, impact weightings, baselines, targets, or any value already in the knowledge bank", "Gap-precision failure — this is what makes the product feel unintelligent to a competent M&E officer", "High", "deterministic"),
        ("FB-15", "Asking the NGO for funder-owned content (VfM scoring rubric, DevTracker flags, FCDO management actions)", "Funder-side items must never reach the NGO", "High", "deterministic"),
        ("FB-16", "Presenting the four latrine units awaiting disposal bins, or the four late-reporting schools, as separate unquantified concerns without linking them to their indicators", "Loses the traceability that makes the finding actionable", "Low", "judged"),
        ("FB-17", "Stating a climate or environmental risk assessment position", "None exists; lake-shore transport and seasonal migration are not presented as climate risks in the source", "Medium", "judged"),
        ("FB-18", "Reporting an equity share (percentage of beneficiaries who are disabled, ultra-poor or previously married)", "The vulnerability columns aggregate across overlapping indicators and cannot yield a share of unique beneficiaries", "High", "deterministic"),
    ]
    note(
        "FB detection_method assigned as deterministic|judged for harness routing (owner Addition: judged → REVIEW-REQUIRED). "
        "Assignment is a transcription judgment: numeric/string-matchable forbiddens → deterministic; narrative disclosure/omission → judged. Listed individually in RECONCILIATION."
    )
    out = []
    for fid, forbidden, why, sev, method in rows:
        out.append(
            {
                "id": fid,
                "forbidden_output": forbidden,
                "why_failure": why,
                "severity": sev,
                "detection_method": method,
            }
        )
    return out


def build_report() -> dict:
    text = Path(ROOT / SOURCE).read_text(encoding="utf-8")
    start = text.index("# LAYER 4 — The report")
    end = text.index("# LAYER 5 — Forbidden outputs")
    layer4 = text[start:end].strip()
    note(
        "Layer 4 stored as full markdown excerpt in report_reference.json (prose_uncalibrated=true). "
        "Claim maps retained inline in the excerpt. Separate file so v1.1 can swap Layer 4 only."
    )
    # Parse claim maps lightly
    sections = []
    for marker, key in [
        ("## A. Summary and Overview", "A"),
        ("## B. Performance and Conclusions", "B"),
        ("## Evidence and Evaluation", "Evidence"),
        ("## Risk, Assumptions and Safeguarding", "Risk"),
        ("## F. Programme Management", "F"),
        ("## Recommendations and Action Points", "Recommendations"),
    ]:
        if marker in layer4:
            sections.append({"section_key": key, "heading_marker": marker})
    return {
        "prose_uncalibrated": True,
        "prose_calibration_note": "Human Writing Instructions V4 was not supplied at golden authorship; transcribed as-is pending v1.1 prose-conformance.",
        "vfm_workaround_note": "VfM material carried inside Section F as explicit workaround; when P1 restores VfM section (D-069), Layer 4 requires amendment (owner golden-amendment item, not engine defect).",
        "template_id": "55f891ac-bb8b-4137-bc42-6de8ff935064",
        "template_version": 2,
        "sections_present": sections,
        "full_markdown": layer4,
    }


def checksum_payload(parts: dict) -> str:
    canonical = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_reconciliation(
    facts: list[dict],
    conflicts: list[dict],
    gaps: dict,
    forbidden: list[dict],
    report: dict,
    manifest: dict,
) -> None:
    fact_ids = sorted({f["id"] for f in facts})
    # samples
    sample_facts = []
    for want in ["F-001", "F-032", "F-040", "F-077", "F-089"]:
        sample_facts.extend([f for f in facts if f["id"] == want][:6])

    sample_conflicts = conflicts[:5]
    sample_gaps = gaps["clusters"][:5]
    sample_fb = forbidden[:5]

    lines = [
        "# Golden pack reconciliation — FCDO BridgeLight AR1 v1.0",
        "",
        f"Source: `{SOURCE}`",
        f"Fixture dir: `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/`",
        f"Manifest checksum: `{manifest['content_checksum']}`",
        f"Dataset version: `{manifest['dataset_version']}`",
        "",
        "Owner verification gate (WI1 mid-package STOP). Counts alone are insufficient — samples below are full records.",
        "",
        "## Layer 1 — Facts",
        "",
        f"- **Total fact records (id×facet):** {len(facts)}",
        f"- **Distinct fact IDs:** {len(fact_ids)} (range {fact_ids[0]}…{fact_ids[-1]})",
        f"- **Expected distinct IDs:** F-001…F-106 (106)",
        "",
        "### Sample read-back (≥5 entries, full records)",
        "",
        "```json",
        json.dumps(sample_facts, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Layer 2 — Conflicts",
        "",
        f"- **Total conflicts:** {len(conflicts)}",
        f"- **ID range:** {conflicts[0]['id']}…{conflicts[-1]['id']}",
        f"- **C-04 defects[] length:** {len(next(c for c in conflicts if c['id']=='C-04')['defects'])} (denominator stays 9)",
        "",
        "### Sample read-back (first 5, full)",
        "",
        "```json",
        json.dumps(sample_conflicts, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Layer 3 — Gaps",
        "",
        f"- **Gap clusters:** {len(gaps['clusters'])} (range {gaps['clusters'][0]['id']}…{gaps['clusters'][-1]['id']})",
        f"- **Counter-list entries:** {len(gaps['counter_list'])}",
        "",
        "### Sample read-back (first 5 clusters, full)",
        "",
        "```json",
        json.dumps(sample_gaps, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Layer 4 — Report reference",
        "",
        f"- **prose_uncalibrated:** {report['prose_uncalibrated']}",
        f"- **full_markdown characters:** {len(report['full_markdown'])}",
        f"- **sections_present:** {[s['section_key'] for s in report['sections_present']]}",
        "",
        "Sample (first 800 chars of full_markdown):",
        "",
        "```",
        report["full_markdown"][:800],
        "```",
        "",
        "## Layer 5 — Forbidden outputs",
        "",
        f"- **Total:** {len(forbidden)}",
        f"- **ID range:** {forbidden[0]['id']}…{forbidden[-1]['id']}",
        f"- **deterministic:** {sum(1 for f in forbidden if f['detection_method']=='deterministic')}",
        f"- **judged:** {sum(1 for f in forbidden if f['detection_method']=='judged')}",
        "",
        "### Sample read-back (first 5, full)",
        "",
        "```json",
        json.dumps(sample_fb, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Judgment calls (every seam)",
        "",
    ]
    for i, j in enumerate(JUDGMENT_CALLS, 1):
        lines.append(f"{i}. {j}")
    lines.append("")
    lines.append("### Per-forbidden detection_method assignments")
    lines.append("")
    for f in forbidden:
        lines.append(f"- `{f['id']}` → `{f['detection_method']}`")
    lines.append("")
    lines.append("## Owner checklist")
    lines.append("")
    lines.append("- [ ] Distinct fact ID count is 106 and samples look faithful")
    lines.append("- [ ] Conflict count is 9; C-04 has three defects; both_are_true on C-02")
    lines.append("- [ ] Gap clusters 10; counter-list 15")
    lines.append("- [ ] Forbidden 18 with severity + detection_method")
    lines.append("- [ ] Layer 4 markdown is complete and marked uncalibrated")
    lines.append("- [ ] Judgment-call list is acceptable (or list corrections)")
    lines.append("")

    (OUT / "RECONCILIATION.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    facts = build_facts()
    conflicts = build_conflicts()
    gaps = build_gaps()
    forbidden = build_forbidden()
    report = build_report()

    layer_files = {
        "facts": facts,
        "conflicts": conflicts,
        "gaps": gaps,
        "forbidden": forbidden,
        "report_reference": report,
    }

    # Write layer files first (stable content for checksum)
    (OUT / "facts.json").write_text(
        json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "conflicts.json").write_text(
        json.dumps(conflicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "gaps.json").write_text(
        json.dumps(gaps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "forbidden.json").write_text(
        json.dumps(forbidden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "report_reference.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    content_for_checksum = {
        "facts": facts,
        "conflicts": conflicts,
        "gaps": {k: gaps[k] for k in ("clusters", "counter_list", "target_note")},
        "forbidden": forbidden,
        # exclude full_markdown from checksum? No — Layer 4 is part of pack; include length + hash of markdown
        "report_reference": {
            "prose_uncalibrated": report["prose_uncalibrated"],
            "full_markdown_sha256": hashlib.sha256(
                report["full_markdown"].encode("utf-8")
            ).hexdigest(),
            "sections_present": report["sections_present"],
        },
    }
    digest = checksum_payload(content_for_checksum)

    manifest = {
        "dataset_id": "fcdo_bridgelight_ar1",
        "dataset_version": "1.0",
        "content_checksum": digest,
        "checksum_algorithm": "sha256",
        "checksum_scope": "facts + conflicts + gaps(clusters,counter_list,target_note) + forbidden + report_reference(metadata + full_markdown_sha256)",
        "source_document": SOURCE,
        "source_document_version": "1.0",
        "authored": "2026-07-25",
        "adopted": "2026-07-26",
        "layer_provenance": {
            "layer_1_facts": {
                "source_document": SOURCE,
                "source_version": "1.0",
                "notes": "Transcribed from LAYER 1; one record per (F-id, facet).",
            },
            "layer_2_conflicts": {
                "source_document": SOURCE,
                "source_version": "1.0",
                "notes": "C-01…C-09; C-04 carries defects[].",
            },
            "layer_3_gaps": {
                "source_document": SOURCE,
                "source_version": "1.0",
                "notes": "G-01…G-10 + 15-item counter-list + question script prose.",
            },
            "layer_4_report": {
                "source_document": SOURCE,
                "source_version": "1.0",
                "file": "report_reference.json",
                "prose_uncalibrated": True,
                "notes": "Own file so v1.1 Layer-4-only swap touches nothing else. VfM workaround inside Section F.",
                "vfm_section_f_workaround": True,
                "vfm_amendment_when": "P1 restores VfM section (D-069) → Layer 4 requires golden amendment",
            },
            "layer_5_forbidden": {
                "source_document": SOURCE,
                "source_version": "1.0",
                "notes": "FB-01…FB-18 with detection_method.",
            },
        },
        "structural_findings": {
            "vfm_template_gap": {
                "summary": "Live FCDO template omits NGO-owned VfM section required by award letter.",
                "golden_workaround": "VfM material carried in Layer 4 Section F",
                "owner_amendment_item": "When P1 restores VfM (D-069), amend Layer 4; not an engine defect",
            }
        },
        "counts": {
            "fact_records": len(facts),
            "distinct_fact_ids": len({f["id"] for f in facts}),
            "conflicts": len(conflicts),
            "gap_clusters": len(gaps["clusters"]),
            "counter_list": len(gaps["counter_list"]),
            "forbidden": len(forbidden),
        },
        "fabrication_semantics": {
            "layer_1_fabrications": "REVIEW-REQUIRED — never auto-PASS, never auto-FAIL; owner bins: golden amendment | invention; counted separately from recall"
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    readme = """# Golden pack — FCDO BridgeLight AR1 v1.0

Transcription of `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`.
**No interpretation beyond recorded judgment calls in `RECONCILIATION.md`.**

## Facet grain (owner ruling)

One fixture record per `(F-id, facet)`, preserving both.

**Rationale:** Facet identity is ontology-mandated (ME Engine Behavioural Contract §2 —
"typed facet identity, never encoded in a label string") and is the direct fix for RC1.
A fixture that collapses facets into rows cannot detect facet-blind matching, which is
the defect the rebuild exists to eliminate.

## Files

| File | Layer |
|------|-------|
| `facts.json` | 1 — fact records (id × facet) |
| `conflicts.json` | 2 — C-01…C-09 (`defects[]` on C-04) |
| `gaps.json` | 3 — clusters + counter-list + question script |
| `report_reference.json` | 4 — **own file** for v1.1 Layer-4-only swap |
| `forbidden.json` | 5 — FB-01…FB-18 |
| `manifest.json` | dataset version, per-layer provenance, checksum |
| `RECONCILIATION.md` | owner verification (counts + full samples + judgment calls) |

## Dataset versioning

- Manifest carries **per-layer provenance** (source version per layer).
- Baselines (later WI) must store dataset version + checksum scored against.
- Cross-version same-or-better comparisons are forbidden (D-071); scorecard must warn.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    write_reconciliation(facts, conflicts, gaps, forbidden, report, manifest)

    print("fact_records", len(facts))
    print("distinct_ids", len({f["id"] for f in facts}))
    print("conflicts", len(conflicts))
    print("gaps", len(gaps["clusters"]), "counter", len(gaps["counter_list"]))
    print("forbidden", len(forbidden))
    print("checksum", digest)
    missing = [f"F-{i:03d}" for i in range(1, 107) if f"F-{i:03d}" not in {x["id"] for x in facts}]
    print("missing_ids", missing)


if __name__ == "__main__":
    main()
