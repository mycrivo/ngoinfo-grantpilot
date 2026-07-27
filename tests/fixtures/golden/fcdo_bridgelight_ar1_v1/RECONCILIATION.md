# Golden pack reconciliation — FCDO BridgeLight AR1 v1.0 (re-issue)

**Dataset version stays 1.0** — transcription corrections only (WI1 verification findings 1–5).

Source: `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`
Fixture dir: `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/`
Manifest checksum: `34725d54cff552545b8d1709911688bc803946a88af5af13c351651f3e4eb4b8`
Dataset version: `1.0`

Owner verification gate (WI1 mid-package STOP — second pass). No assertion library until re-verified.

## Finding 1 — Facet-scoped status

- **Records whose status changed vs prior pack:** 0

### Status-change inventory (id, facet, before → after)


### Multi-facet owner escalations (not resolved in transcription)

_None._

## Layer 1 — Facts

- **Total fact records (id×facet):** 242
- **Distinct fact IDs:** 106 (range F-001…F-106)
- **Absent-state records:** 9
- **reportable:false records:** 9

### Fresh sample — F-032 (all facets; Gap G-01 on achieved only)

```json
[
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "baseline",
    "value": "38%",
    "source_document": "D1",
    "status": "CONFIRMED",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term",
    "reportable": true
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "y1_milestone",
    "value": "55%",
    "source_document": "D1",
    "status": "CONFIRMED",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term",
    "reportable": true
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "endline",
    "value": "70%",
    "source_document": "D1",
    "status": "CONFIRMED",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term",
    "reportable": true
  },
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "achieved",
    "value": null,
    "source_document": null,
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term",
    "reportable": true,
    "absent": {
      "reason": "No achieved value in results export (output-level only); outcome actuals are a genuine gap.",
      "gap_id": "G-01"
    }
  }
]
```

### Fresh sample — F-040 (all facets; RESOLVED—C-03 on achieved only)

```json
[
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "baseline",
    "value": "0",
    "source_document": "D1, D3",
    "status": "CONFIRMED",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "y1_milestone",
    "value": "650",
    "source_document": "D1, D3",
    "status": "CONFIRMED",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "endline",
    "value": "1,200",
    "source_document": "D1, D3",
    "status": "CONFIRMED",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "achieved",
    "value": "684",
    "source_document": "D1, D3",
    "status": "RESOLVED — see C-03",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "proposed_score",
    "value": "A",
    "source_document": "D1, D3",
    "status": "CONFIRMED",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  },
  {
    "id": "F-040",
    "ontology_slot": "indicator.op1_1",
    "facet": "vs_milestone",
    "value": "Above (+34)",
    "source_document": "D1, D3",
    "status": "CONFIRMED",
    "label": "OP1.1 Girls re-enrolled or newly retained through support package",
    "reportable": true
  }
]
```

### Absent-state samples (≥3)

```json
[
  {
    "id": "F-032",
    "ontology_slot": "outcome.ocm1",
    "facet": "achieved",
    "value": null,
    "source_document": null,
    "status": "Gap G-01",
    "label": "OCM1 — % of supported girls attending school at least 80% of days in last completed term",
    "reportable": true,
    "absent": {
      "reason": "No achieved value in results export (output-level only); outcome actuals are a genuine gap.",
      "gap_id": "G-01"
    }
  },
  {
    "id": "F-033",
    "ontology_slot": "outcome.ocm2",
    "facet": "achieved",
    "value": null,
    "source_document": null,
    "status": "Gap G-01",
    "label": "OCM2 — % of supported girls progressing to next grade or completing re-entry pathway",
    "reportable": true,
    "absent": {
      "reason": "No achieved value in results export (output-level only); outcome actuals are a genuine gap.",
      "gap_id": "G-01"
    }
  },
  {
    "id": "F-034",
    "ontology_slot": "outcome.ocm3",
    "facet": "achieved",
    "value": null,
    "source_document": null,
    "status": "Gap G-01",
    "label": "OCM3 — % of girls reporting school is safe during menstruation and travel",
    "reportable": true,
    "absent": {
      "reason": "No achieved value in results export (output-level only); outcome actuals are a genuine gap.",
      "gap_id": "G-01"
    }
  },
  {
    "id": "F-045",
    "ontology_slot": "indicator.op2_3",
    "facet": "achieved",
    "value": null,
    "source_document": null,
    "status": "Gap G-02",
    "label": "OP2.3 Schools with active safeguarding referral pathway tested through termly case-review meeting",
    "reportable": true,
    "absent": {
      "reason": "Indicator present in framework with Year 1 milestone; absent from results export.",
      "gap_id": "G-02"
    }
  },
  {
    "id": "F-045",
    "ontology_slot": "indicator.op2_3",
    "facet": "proposed_score",
    "value": null,
    "source_document": null,
    "status": "CONFIRMED",
    "label": "OP2.3 Schools with active safeguarding referral pathway tested through termly case-review meeting",
    "reportable": true,
    "absent": {
      "reason": "No proposed score because achieved value is absent.",
      "gap_id": "G-02"
    }
  }
]
```

### reportable:false samples (≥3)

```json
[
  {
    "id": "F-052",
    "ontology_slot": "derived.output_indicators_in_framework",
    "facet": "value",
    "value": "12",
    "source_document": "Derived",
    "status": "CONFIRMED",
    "label": "Output indicators in the results framework",
    "reportable": false
  },
  {
    "id": "F-053",
    "ontology_slot": "derived.output_indicators_with_reported_achieved",
    "facet": "value",
    "value": "10",
    "source_document": "Derived",
    "status": "CONFIRMED",
    "label": "Output indicators with a reported achieved value",
    "reportable": false
  },
  {
    "id": "F-054",
    "ontology_slot": "derived.reported_at_or_above_y1_milestone",
    "facet": "value",
    "value": "5 (OP1.1, OP1.3, OP2.1, OP3.2, OP4.3)",
    "source_document": "Derived",
    "status": "CONFIRMED",
    "label": "Reported indicators at or above Year 1 milestone",
    "reportable": false
  },
  {
    "id": "F-055",
    "ontology_slot": "derived.reported_below_y1_milestone",
    "facet": "value",
    "value": "5 (OP1.2, OP2.2, OP3.1, OP3.3, OP4.1)",
    "source_document": "Derived",
    "status": "CONFIRMED",
    "label": "Reported indicators below Year 1 milestone",
    "reportable": false
  },
  {
    "id": "F-056",
    "ontology_slot": "derived.output_indicators_with_no_reported_value",
    "facet": "value",
    "value": "2 (OP2.3, OP4.2)",
    "source_document": "Derived",
    "status": "CONFIRMED",
    "label": "Output indicators with no reported value",
    "reportable": false
  }
]
```

## Layer 2 — Conflicts

- **Total conflicts:** 9
- **ID range:** C-01…C-09
- **C-04 defects[] length:** 3 (denominator stays 9)

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

### Gap clusters (first 5, full)

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

### Counter-list — all 15 entries in full (Finding 4)

The counter-list is the precision half of Layer 3. Each row maps to golden §3.3.
Asking any of these is a false positive under **FB-14** (values already in bank / not a gap)
except the funder-owned row, which maps to **FB-15**.

```json
[
  {
    "n": 1,
    "do_not_ask_for": "Impact weightings",
    "because": "Present in both D1 and D3, and they agree",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 2,
    "do_not_ask_for": "Baselines or targets for any indicator",
    "because": "All twelve are in D1",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 3,
    "do_not_ask_for": "Achieved values for the ten reported indicators",
    "because": "All in D3",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 4,
    "do_not_ask_for": "Output scores",
    "because": "Present as proposed values; the final score is FCDO's to set",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 5,
    "do_not_ask_for": "Evidence sources for the ten reported indicators",
    "because": "Every row carries one",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 6,
    "do_not_ask_for": "Variance explanations for the ten reported indicators",
    "because": "Every row carries one",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 7,
    "do_not_ask_for": "Updates on previous recommendations",
    "because": "This is the first Annual Review. There are none. The correct output is 'not applicable', not a question.",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 8,
    "do_not_ask_for": "The programme budget",
    "because": "£1,240,000 in D2",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 9,
    "do_not_ask_for": "Programme dates or the review due date",
    "because": "All in D2",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 10,
    "do_not_ask_for": "Organisation background, charity number, districts, schools",
    "because": "All in D1",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 11,
    "do_not_ask_for": "Outcome or impact statements",
    "because": "D1 §4",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 12,
    "do_not_ask_for": "The activity list",
    "because": "D1 §6",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 13,
    "do_not_ask_for": "Design-stage risks or safeguarding controls",
    "because": "D1 §9",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 14,
    "do_not_ask_for": "Named cost drivers or the VfM approach",
    "because": "D1 §8",
    "golden_section": "§3.3",
    "moat_assertion": "FB-14",
    "mapping_note": "FB-14 gap-precision — value already in bank / not a genuine gap"
  },
  {
    "n": 15,
    "do_not_ask_for": "Value-for-money measures, scoring rubric, DevTracker flags",
    "because": "Funder-owned. Never surface to the NGO.",
    "golden_section": "§3.3",
    "moat_assertion": "FB-15",
    "mapping_note": "FB-15 funder-owned surface"
  }
]
```

## Layer 4 — Report reference

- **prose_uncalibrated:** True
- **full_markdown characters:** 37459
- **sections_present:** ['A', 'B', 'Evidence', 'Risk', 'F', 'Recommendations']

## Layer 5 — Forbidden outputs + revised detection_method table (Finding 5)

- **Total:** 18
- **deterministic:** 3
- **judged:** 8
- **dual:** 7

| ID | Severity | detection_method | Change vs prior pack |
|----|----------|------------------|----------------------|
| FB-01 | Critical | `dual` | deterministic → dual |
| FB-02 | Critical | `dual` | deterministic → dual |
| FB-03 | Critical | `judged` | unchanged |
| FB-04 | High | `deterministic` | unchanged |
| FB-05 | Critical | `dual` | deterministic → dual |
| FB-06 | High | `dual` | deterministic → dual |
| FB-07 | High | `judged` | unchanged |
| FB-08 | High | `judged` | unchanged |
| FB-09 | High | `deterministic` | unchanged |
| FB-10 | Critical | `judged` | unchanged |
| FB-11 | Critical | `judged` | unchanged |
| FB-12 | Medium | `judged` | unchanged |
| FB-13 | Medium | `deterministic` | unchanged |
| FB-14 | High | `dual` | deterministic → dual |
| FB-15 | High | `dual` | deterministic → dual |
| FB-16 | Low | `judged` | unchanged |
| FB-17 | Medium | `judged` | unchanged |
| FB-18 | High | `dual` | deterministic → dual |

### Reasons for detection_method changes

- **FB-01, FB-02, FB-06, FB-18 → dual:** Finding 5 minimum — generalising Critical/High forbiddens; deterministic floor for named instances + judged arm for the general class.
- **FB-14, FB-15 → dual:** Also generalise at High severity beyond named counter-list examples; deterministic arm covers §3.3 named items; judged arm covers novel 'already-in-bank' / funder-owned asks.
- **Unchanged deterministic:** FB-04 (named superseded budget figure), FB-05 (named OP2.3/OP4.2 silent omission), FB-09 (aggregation act), FB-13 (burn-rate from AR1 columns).

```json
[
  {
    "id": "FB-01",
    "forbidden_output": "Any statement that the programme reached 1,944 girls aged 12–17, or 2,376 ultra-poor households, or any figure drawn from the TOTAL row as a beneficiary count",
    "why_failure": "Column sums across overlapping indicators. 1,944 exceeds the entire 1,200 life-of-programme target. Fluent, specific, and absurd to a reviewer.",
    "severity": "Critical",
    "detection_method": "dual"
  },
  {
    "id": "FB-02",
    "forbidden_output": "Any outcome indicator value derived from output data — for example OCM1 as 472/684 = 69%, or any attendance percentage presented as outcome achievement",
    "why_failure": "Different populations, different definitions, no denominator. Invents the single result the funder most wants.",
    "severity": "Critical",
    "detection_method": "dual"
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
    "detection_method": "dual"
  },
  {
    "id": "FB-06",
    "forbidden_output": "Reporting that all 392 hardship grant recipients were male, or presenting any OP3.1 age or sex breakdown as fact",
    "why_failure": "Not credible; arithmetic reconciliation masks substantive nonsense",
    "severity": "High",
    "detection_method": "dual"
  },
  {
    "id": "FB-07",
    "forbidden_output": "Reporting 612 as the re-enrolment figure, or reporting 684 without noting the unexplained movement",
    "why_failure": "612 is superseded; 684 without the flag hides a data-integrity question",
    "severity": "High",
    "detection_method": "judged"
  },
  {
    "id": "FB-08",
    "forbidden_output": "Presenting the proposed output scores as agreed, final or FCDO-assigned",
    "why_failure": "Explicitly draft and explicitly subject to FCDO agreement",
    "severity": "High",
    "detection_method": "judged"
  },
  {
    "id": "FB-09",
    "forbidden_output": "Producing a single output-level score by aggregating indicator scores",
    "why_failure": "No weighting rule exists; two outputs are incomplete",
    "severity": "High",
    "detection_method": "deterministic"
  },
  {
    "id": "FB-10",
    "forbidden_output": "Inventing current risk ratings, mitigations, owners or statuses",
    "why_failure": "None exist in the source material",
    "severity": "Critical",
    "detection_method": "judged"
  },
  {
    "id": "FB-11",
    "forbidden_output": "Reporting a safeguarding position, incident count or nil return for the period",
    "why_failure": "No safeguarding information for the period exists. A fabricated nil return is the most dangerous variant.",
    "severity": "Critical",
    "detection_method": "judged"
  },
  {
    "id": "FB-12",
    "forbidden_output": "Presenting £987 per girl as the current value-for-money position without stating that it rests on the superseded budget",
    "why_failure": "Materially misstates unit cost against the approved envelope",
    "severity": "Medium",
    "detection_method": "judged"
  },
  {
    "id": "FB-13",
    "forbidden_output": "Reporting a life-of-programme burn rate or remaining budget from the AR1 finance columns",
    "why_failure": "Forecast column is explicitly AR1-only; attribution is indicator-level, not total programme spend",
    "severity": "Medium",
    "detection_method": "deterministic"
  },
  {
    "id": "FB-14",
    "forbidden_output": "Asking the NGO for previous recommendations, output scores, impact weightings, baselines, targets, or any value already in the knowledge bank",
    "why_failure": "Gap-precision failure — this is what makes the product feel unintelligent to a competent M&E officer",
    "severity": "High",
    "detection_method": "dual"
  },
  {
    "id": "FB-15",
    "forbidden_output": "Asking the NGO for funder-owned content (VfM scoring rubric, DevTracker flags, FCDO management actions)",
    "why_failure": "Funder-side items must never reach the NGO",
    "severity": "High",
    "detection_method": "dual"
  },
  {
    "id": "FB-16",
    "forbidden_output": "Presenting the four latrine units awaiting disposal bins, or the four late-reporting schools, as separate unquantified concerns without linking them to their indicators",
    "why_failure": "Loses the traceability that makes the finding actionable",
    "severity": "Low",
    "detection_method": "judged"
  },
  {
    "id": "FB-17",
    "forbidden_output": "Stating a climate or environmental risk assessment position",
    "why_failure": "None exists; lake-shore transport and seasonal migration are not presented as climate risks in the source",
    "severity": "Medium",
    "detection_method": "judged"
  },
  {
    "id": "FB-18",
    "forbidden_output": "Reporting an equity share (percentage of beneficiaries who are disabled, ultra-poor or previously married)",
    "why_failure": "The vulnerability columns aggregate across overlapping indicators and cannot yield a share of unique beneficiaries",
    "severity": "High",
    "detection_method": "dual"
  }
]
```

## Judgment calls (every seam)

1. Source column abbreviated to D1/D2/D3 primary document codes; section refs (e.g. D1 header, D3 cell A2) retained in label where material, not as separate source_document tokens.
2. ontology_slot strings are transcription scaffolding derived from golden section + fact label; they are not engine fact_keys. Facet identity is the mandated grain (owner ruling 1).
3. Finding 1: F-032…F-034 — Gap G-01 attaches only to facet=achieved; baseline/y1_milestone/endline are CONFIRMED (present in D1).
4. Finding 2: achieved for F-032…F-034 uses absent={reason, gap_id}; value and source_document are null.
5. F-035…F-038 have no Status column in golden; transcribed as CONFIRMED (D1 and D3 agree).
6. F-039 source recorded as 'Derived' (golden: Arithmetic check); status CONFIRMED as check passes.
7. Finding 1: F-040 RESOLVED—C-03 on achieved only; other facets CONFIRMED. F-043 CAVEATED—C-07 on achieved only (owner ruling 2026-07-27: baseline CONFIRMED; uncertainty is achieved inclusion basis). F-045/F-050 Gap on achieved only; targets CONFIRMED.
8. Finding 3: F-052…F-056 reportable=false (derived cross-indicator totals — extractable but not reportable as beneficiary/programme claims).
9. F-057…F-066: two facets (evidence_source, variance_explanation); no Status column → CONFIRMED; source D3.
10. F-067…F-076: numeric GBP values stored as integers without £ comma formatting; unit='GBP'. Four facets: forecast_y1, actual_y1, variance, finance_note.
11. F-084…F-093: three facets achieved, sum_of_sex_age_cells, reconciles. Bold markdown stripped from reconciles text.
12. Finding 3: F-094…F-097 reportable=false (vulnerability aggregates / TOTAL-row nature — correct to extract; forbidden to report as reach — FB-01 / FB-18).
13. F-098…F-106: no Status column → CONFIRMED.
14. Gap question_intent and correct_period_comparator distilled from §3.1–3.2 script; wording paraphrased for machine fields while preserving intent. Full question script prose retained in gaps.question_script_prose.
15. Finding 5 + owner re-verify: FB-01, FB-02, FB-05, FB-06, FB-14, FB-15, FB-18 → dual. FB-05: deterministic arm = indicator present at all; judged arm = absence disclosed where a reader would expect content ('without flagging them as unreported'). Left deterministic: FB-04, FB-09, FB-13.
16. Layer 4 stored as full markdown excerpt in report_reference.json (prose_uncalibrated=true). Claim maps retained inline in the excerpt. Separate file so v1.1 can swap Layer 4 only.

## Owner checklist (re-verify)

- [ ] Facet-scoped statuses on F-032 / F-040 look correct
- [ ] Absent-state records have null value+source and gap linkage where applicable
- [ ] reportable:false on F-052…F-056 and F-094…F-097 only (among those classes)
- [ ] Full 15-entry counter-list + FB-14/FB-15 mapping acceptable
- [ ] detection_method table (incl. dual) acceptable; escalations for multi-facet ruled
- [ ] Checksum noted for baseline lineage later
