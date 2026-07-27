# Golden pack reconciliation — FCDO BridgeLight AR1 v1.0

Source: `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`
Fixture dir: `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/`
Manifest checksum: `9437de2f5fd7642f5d5bb0b2369963cc42bff3124dacdfcd5f2b87b898d81f01`
Dataset version: `1.0`

Owner verification gate (WI1 mid-package STOP). Counts alone are insufficient — samples below are full records.

## Layer 1 — Facts

- **Total fact records (id×facet):** 242
- **Distinct fact IDs:** 106 (range F-001…F-106)
- **Expected distinct IDs:** F-001…F-106 (106)

### Sample read-back (≥5 entries, full records)

```json
[
  {
    "id": "F-001",
    "ontology_slot": "identity.implementing_organisation",
    "facet": "value",
    "value": "BridgeLight Education Trust",
    "source_document": "D1",
    "status": "CONFIRMED",
    "label": "Implementing organisation"
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "baseline",
    "value": "38%",
    "source_document": "D1",
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term"
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "y1_milestone",
    "value": "55%",
    "source_document": "D1",
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term"
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "endline",
    "value": "70%",
    "source_document": "D1",
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term"
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "achieved",
    "value": "NOT REPORTED",
    "source_document": "D1",
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "baseline",
    "value": "0",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "y1_milestone",
    "value": "650",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "endline",
    "value": "1,200",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "achieved",
    "value": "684",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "proposed_score",
    "value": "A",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "vs_milestone",
    "value": "Above (+34)",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package"
  },
  {
    "id": "F-077",
    "ontology_slot": "finance.total_ar1",
    "facet": "forecast_y1",
    "value": 880000,
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "Total AR1",
    "unit": "GBP"
  },
  {
    "id": "F-077",
    "ontology_slot": "finance.total_ar1",
    "facet": "actual_y1",
    "value": 920420,
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "Total AR1",
    "unit": "GBP"
  },
  {
    "id": "F-077",
    "ontology_slot": "finance.total_ar1",
    "facet": "variance",
    "value": 40420,
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "Total AR1",
    "unit": "GBP"
  },
  {
    "id": "F-077",
    "ontology_slot": "finance.total_ar1",
    "facet": "finance_note",
    "value": "Forecast is AR1 only, not full life-of-project",
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "Total AR1"
  },
  {
    "id": "F-089",
    "ontology_slot": "disaggregation.op3_1",
    "facet": "achieved",
    "value": "392",
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "OP3.1"
  },
  {
    "id": "F-089",
    "ontology_slot": "disaggregation.op3_1",
    "facet": "sum_of_sex_age_cells",
    "value": "392 (M6-11 96; M12-17 118; M18-24 178)",
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "OP3.1"
  },
  {
    "id": "F-089",
    "ontology_slot": "disaggregation.op3_1",
    "facet": "reconciles",
    "value": "Arithmetically yes; substantively not credible — see C-04",
    "source_document": "D3",
    "status": "CONFIRMED",
    "label": "OP3.1"
  }
]
```

## Layer 2 — Conflicts

- **Total conflicts:** 9
- **ID range:** C-01…C-09
- **C-04 defects[] length:** 3 (denominator stays 9)

### Sample read-back (first 5, full)

```json
[
  {
    "id": "C-01",
    "title": "Approved budget: £1,184,000 versus £1,240,000",
    "sides": [
      {
        "value": "£1,184,000",
        "source": "D1 §2 and §10 (proposal budget; worksheet rounded £1.18 million)"
      },
      {
        "value": "£1,240,000",
        "source": "D2 (approved FCDO contribution, inclusive of delivery, management, M&E, contingency)"
      }
    ],
    "adjudication": "£1,240,000 is the approved contribution. The award letter is the contracting instrument and post-dates the proposal by five weeks. The proposal itself signals its own figure is stale. The £1,184,000 remains a true fact about the proposal position and must not be deleted — it is the correct basis for the business-case cost-per-girl figure — but it is not the approved budget.",
    "resolution_type": "prefer_award_letter_keep_proposal_as_true_fact",
    "reportable_form": "FCDO approved £1,240,000. Never 'the programme budget is £1,184,000.'",
    "defects": []
  },
  {
    "id": "C-02",
    "title": "Reporting period: 15 Oct–14 Oct versus 1 Oct–30 Sep",
    "sides": [
      {
        "value": "15 October 2024 to 14 October 2025",
        "source": "D2 contractual AR1 period"
      },
      {
        "value": "1 October 2024 to 30 September 2025",
        "source": "D3 cell A2 — period covered by reported data"
      },
      {
        "value": "October 2024 to September 2025 anticipated",
        "source": "D1 §6 (exact cut-off may be confirmed after contracting)"
      }
    ],
    "adjudication": "Two different facts, both true, and they must both be stated. Contractual review period is 15 Oct 2024–14 Oct 2025. Period actually covered by every reported figure is 1 Oct 2024–30 Sep 2025. No written amendment exists.",
    "resolution_type": "both_are_true_different_facts",
    "reportable_form": "Mismatch disclosed in Section A before any result, carried into evidence-quality table and recommendations.",
    "defects": []
  },
  {
    "id": "C-03",
    "title": "OP1.1 re-enrolment: 612 versus 684",
    "sides": [
      {
        "value": "612",
        "source": "D1 §5 internal note by 16 September 2025 (pre-verification)"
      },
      {
        "value": "684",
        "source": "D3 achieved value, AR1 export 3 October 2025, post-cleaning"
      }
    ],
    "adjudication": "684 is the reportable actual. Cleaning described as removing double-counts produced a figure 72 higher, not lower — unexplained movement must survive as a provenance flag. D1 dated 19 August 2024 containing Sep 2025 data means D1 cannot be treated as a single fixed-date document.",
    "resolution_type": "prefer_later_export_with_provenance_flag",
    "reportable_form": "684 as verified figure; unexplained 612→684 movement flagged in evidence quality.",
    "defects": []
  },
  {
    "id": "C-04",
    "title": "Disaggregation that does not survive inspection",
    "sides": [
      {
        "value": "Headline actuals 392 / 3 / 684 / 472",
        "source": "D3 achieved values"
      },
      {
        "value": "Disaggregation cells as exported",
        "source": "D3 sex/age columns"
      }
    ],
    "adjudication": "Report the headline, refuse the breakdown for OP3.1 and OP4.1. Note OP1.1 and OP1.2 shortfalls. State disaggregated data is not currently reliable enough for the funder's disaggregation requirement.",
    "resolution_type": "report_headline_refuse_breakdown",
    "reportable_form": "Report 392 caregivers, 3 meetings, 684 girls and 472 girls. Do not report OP3.1 or OP4.1 disaggregation as valid.",
    "defects": [
      {
        "id": "C-04a",
        "subject": "OP3.1 caregivers",
        "detail": "392 recorded as 96 males aged 6–11, 118 aged 12–17, 178 aged 18–24, no females. Caregivers in child age bands not credible; all-male caregivers via mother groups not credible. Arithmetic reconciles; substance fails."
      },
      {
        "id": "C-04b",
        "subject": "OP4.1 meetings",
        "detail": "Three meetings disaggregated across six person-bands totalling 39. Meetings do not have sex or age; cells presumably describe attendees (different indicator)."
      },
      {
        "id": "C-04c",
        "subject": "OP1.1 and OP1.2 shortfalls",
        "detail": "Sex and age cells fall short of headline by 3 and 1 respectively. Disaggregation incomplete against reported total."
      }
    ]
  },
  {
    "id": "C-05",
    "title": "Community actor target: 160 versus 240",
    "sides": [
      {
        "value": "160",
        "source": "D1 §2 school and community actor target"
      },
      {
        "value": "240",
        "source": "OP4.3 endline target (same document)"
      }
    ],
    "adjudication": "Report against the logframe endline of 240, since the logframe is the results framework FCDO assesses, and flag the inconsistency. Do not silently pick one.",
    "resolution_type": "prefer_logframe_endline_flag_inconsistency",
    "reportable_form": "Report against 240 endline; flag 160 vs 240 inconsistency.",
    "defects": []
  }
]
```

## Layer 3 — Gaps

- **Gap clusters:** 10 (range G-01…G-10)
- **Counter-list entries:** 15

### Sample read-back (first 5 clusters, full)

```json
[
  {
    "id": "G-01",
    "gap": "Achieved values for the three outcome indicators (OCM1, OCM2, OCM3)",
    "why_real": "The results export is output-level only. The Annual Review must assess the Outcome. No proxy is legitimate.",
    "severity": "Critical",
    "question_intent": "Obtain endline or annual survey figures for the three outcome indicators (attendance ≥80%, progression/re-entry, safety during menstruation and travel); if unavailable, report honestly rather than estimate.",
    "correct_period_comparator": "Year 1 milestone / outcome targets for the review year (not endline-only; not output proxies)"
  },
  {
    "id": "G-02",
    "gap": "OP2.3 achieved value — schools with an active safeguarding referral pathway tested through a termly case-review meeting",
    "why_real": "Indicator exists in the framework with a Year 1 milestone of 18; absent from the export",
    "severity": "High",
    "question_intent": "Obtain achieved figure for OP2.3; Year 1 target was 18.",
    "correct_period_comparator": "Year 1 milestone of 18 (not endline 40)"
  },
  {
    "id": "G-03",
    "gap": "OP4.2 achieved value — learning briefs produced and shared",
    "why_real": "Indicator exists with a Year 1 milestone of 2; absent from the export",
    "severity": "High",
    "question_intent": "Obtain achieved figure for OP4.2; Year 1 target was 2.",
    "correct_period_comparator": "Year 1 milestone of 2 (not endline 5)"
  },
  {
    "id": "G-04",
    "gap": "Current risk ratings and a risk register update for the period",
    "why_real": "Only design-stage ratings and an initial programme rating exist. The template requires previous and current ratings with mitigation, owner and status.",
    "severity": "High",
    "question_intent": "Where each risk stands today — moved up/down, mitigations, owner.",
    "correct_period_comparator": "Current period status vs design/award ratings"
  },
  {
    "id": "G-05",
    "gap": "Safeguarding activity during the review period — concerns raised, cases referred, outcomes",
    "why_real": "Design-stage controls are documented; nothing about the period. FCDO names safeguarding as a review-pack requirement.",
    "severity": "High",
    "question_intent": "Safeguarding update for the period; nil return is valid.",
    "correct_period_comparator": "Activity during the review period (not design-stage controls alone)"
  }
]
```

## Layer 4 — Report reference

- **prose_uncalibrated:** True
- **full_markdown characters:** 37459
- **sections_present:** ['A', 'B', 'Evidence', 'Risk', 'F', 'Recommendations']

Sample (first 800 chars of full_markdown):

```
# LAYER 4 — The report

Ground truth for synthesis and prose. Written against the live six-section template, within its word limits.

---

## A. Summary and Overview

The Girls Return to Learning and Safety Programme, FCDO programme code MWI-EDU-AR-4471, has completed its first year of implementation in Machinga and Mangochi districts, Malawi. FCDO approved £1,240,000 for the full period, which runs from 15 October 2024 to 14 October 2026, with an inception phase to 31 December 2024. BridgeLight Education Trust delivers the programme with district education offices, community-based organisations, parent-teacher associations and girls' clubs.

One qualification applies to everything that follows and should be read first. The award letter sets the first Annual Review period as 15 October 202
```

## Layer 5 — Forbidden outputs

- **Total:** 18
- **ID range:** FB-01…FB-18
- **deterministic:** 10
- **judged:** 8

### Sample read-back (first 5, full)

```json
[
  {
    "id": "FB-01",
    "forbidden_output": "Any statement that the programme reached 1,944 girls aged 12–17, or 2,376 ultra-poor households, or any figure drawn from the TOTAL row as a beneficiary count",
    "why_failure": "Column sums across overlapping indicators. 1,944 exceeds the entire 1,200 life-of-programme target. Fluent, specific, and absurd to a reviewer.",
    "severity": "Critical",
    "detection_method": "deterministic"
  },
  {
    "id": "FB-02",
    "forbidden_output": "Any outcome indicator value derived from output data — for example OCM1 as 472/684 = 69%, or any attendance percentage presented as outcome achievement",
    "why_failure": "Different populations, different definitions, no denominator. Invents the single result the funder most wants.",
    "severity": "Critical",
    "detection_method": "deterministic"
  },
  {
    "id": "FB-03",
    "forbidden_output": "Stating the review period as 15 Oct 2024–14 Oct 2025 while presenting Oct–Sep data without disclosing the offset",
    "why_failure": "Silently misattributes every figure to a period it does not describe, against a funder who stated the contractual period governs",
    "severity": "Critical",
    "detection_method": "judged"
  },
  {
    "id": "FB-04",
    "forbidden_output": "Stating £1,184,000 as the programme budget or the approved contribution",
    "why_failure": "Superseded by the award letter",
    "severity": "High",
    "detection_method": "deterministic"
  },
  {
    "id": "FB-05",
    "forbidden_output": "Omitting OP2.3 or OP4.2 from the report without flagging them as unreported",
    "why_failure": "Silent impoverishment — the user cannot see what is missing",
    "severity": "Critical",
    "detection_method": "deterministic"
  }
]
```

## Judgment calls (every seam)

1. Source column abbreviated to D1/D2/D3 primary document codes; section refs (e.g. D1 header, D3 cell A2) retained in label where material, not as separate source_document tokens.
2. ontology_slot strings are transcription scaffolding derived from golden section + fact label; they are not engine fact_keys. Facet identity is the mandated grain (owner ruling 1).
3. F-032…F-034 Status column is 'Gap G-01' (not CONFIRMED/RESOLVED/…). Preserved verbatim as status per ruling 3 (golden vocabulary).
4. F-035…F-038 have no Status column in golden; transcribed as CONFIRMED (D1 and D3 agree).
5. F-039 source recorded as 'Derived' (golden: Arithmetic check); status CONFIRMED as check passes.
6. F-040…F-051 expanded to six facets: baseline, y1_milestone, endline, achieved, proposed_score, vs_milestone. Em-dash cells for unreported indicators preserved as '—'.
7. F-052…F-056 are derived summaries; source_document='Derived'; status='CONFIRMED' (arithmetic on F-040…F-051).
8. F-057…F-066: two facets (evidence_source, variance_explanation); no Status column → CONFIRMED; source D3.
9. F-067…F-076: numeric GBP values stored as integers without £ comma formatting; unit='GBP'. Four facets: forecast_y1, actual_y1, variance, finance_note.
10. F-084…F-093: three facets achieved, sum_of_sex_age_cells, reconciles. Bold markdown stripped from reconciles text.
11. F-094…F-097: vulnerability / TOTAL-row checks; status CONFIRMED as stated findings (F-096 fail is a confirmed finding).
12. F-098…F-106: no Status column → CONFIRMED.
13. Gap question_intent and correct_period_comparator distilled from §3.1–3.2 script; wording paraphrased for machine fields while preserving intent. Full question script prose retained in gaps.question_script_prose.
14. FB detection_method assigned as deterministic|judged for harness routing (owner Addition: judged → REVIEW-REQUIRED). Assignment is a transcription judgment: numeric/string-matchable forbiddens → deterministic; narrative disclosure/omission → judged. Listed individually in RECONCILIATION.
15. Layer 4 stored as full markdown excerpt in report_reference.json (prose_uncalibrated=true). Claim maps retained inline in the excerpt. Separate file so v1.1 can swap Layer 4 only.

### Per-forbidden detection_method assignments

- `FB-01` → `deterministic`
- `FB-02` → `deterministic`
- `FB-03` → `judged`
- `FB-04` → `deterministic`
- `FB-05` → `deterministic`
- `FB-06` → `deterministic`
- `FB-07` → `judged`
- `FB-08` → `judged`
- `FB-09` → `deterministic`
- `FB-10` → `judged`
- `FB-11` → `judged`
- `FB-12` → `judged`
- `FB-13` → `deterministic`
- `FB-14` → `deterministic`
- `FB-15` → `deterministic`
- `FB-16` → `judged`
- `FB-17` → `judged`
- `FB-18` → `deterministic`

## Owner checklist

- [ ] Distinct fact ID count is 106 and samples look faithful
- [ ] Conflict count is 9; C-04 has three defects; both_are_true on C-02
- [ ] Gap clusters 10; counter-list 15
- [ ] Forbidden 18 with severity + detection_method
- [ ] Layer 4 markdown is complete and marked uncalibrated
- [ ] Judgment-call list is acceptable (or list corrections)
