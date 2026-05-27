# Workstream T2 — Reference Funder Reporting Templates for GrantPilot M&E Module

**Status:** Stage B input artefact  
**Purpose:** Provide build-ready reference template definitions for `funder_report_templates` JSONB schema stress-testing.  
**Applies to:** GrantPilot M&E / Donor Report Writer module  
**Reference funders:**  
1. The National Lottery Community Fund (NLCF) — simple / reflective UK charity reporting pattern  
2. FCDO Annual Review — complex / institutional donor reporting pattern  

---

## 0. How Cursor should use this file

Use this file as **supporting input** for Stage B only.

This file does **not** replace:

- `ME_MODULE_MASTER_MEMORY.md`
- `ME_MODULE_ARCHITECTURE_SPEC.md`
- `ME_MODULE_PROJECT_PLAN.md`
- `API_CONTRACT.md`
- `PRICING_AND_ENTITLEMENTS.md`
- `GUARDRAILS_RUNTIME_AND_SECURITY.md`
- `DB_FIELD_CONTRACT_*.md`
- `FUNDER_TEMPLATE_SCHEMA.md` if it exists

If `FUNDER_TEMPLATE_SCHEMA.md` exists, Cursor must follow it exactly.

If `FUNDER_TEMPLATE_SCHEMA.md` does not exist, use the fallback JSONB structure below as the working basis for Stage B:

```json
{
  "funder_name": "string",
  "template_name": "string",
  "region": "string",
  "reporting_frequency": "string",
  "report_sections_json": [],
  "format_rules_json": {},
  "terminology_map_json": {}
}
```

Each item in `report_sections_json` should follow this minimum shape:

```json
{
  "key": "string",
  "title": "string",
  "archetype": "string",
  "word_limit": 0,
  "required_tables": [],
  "required_indicators": [],
  "tone": "string"
}
```

Recommended Stage B schema additions from the stress test:

```json
{
  "conditional_display": {
    "enabled": true,
    "condition": "string"
  },
  "evidence_rules": {
    "claim_level_citation_required": true,
    "numeric_claims_must_have_source": true,
    "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
  }
}
```

---

## 1. Research discipline and implementation guardrails

Cursor must treat these template definitions as **reference seed data / contract stress-test material**, not as production-certified legal or funder compliance advice.

Rules:

1. Do not invent funder requirements.
2. Keep sourced, inferred, and unknown material separate.
3. If the real funder format does not fit the schema, flag it instead of forcing it.
4. Do not create product code during Stage B.
5. Do not create migrations, models, routes, workers, storage adapters, or agent classes during Stage B.
6. If this file conflicts with canonical Stage B contracts, STOP and report the conflict.
7. Any future seed insertion must happen only after field contracts and `FUNDER_TEMPLATE_SCHEMA.md` are locked.

---

# 2. NLCF Reference Template

## 2.1 Template definition

```json
{
  "funder_name": "The National Lottery Community Fund",
  "template_name": "NLCF Progress Update / End-of-Grant Learning Report",
  "region": "UK",
  "reporting_frequency": "annual_or_end_of_grant",
  "report_sections_json": [
    {
      "key": "project_story",
      "title": "The story of your project this year",
      "archetype": "ARCH_PROGRESS_NARRATIVE",
      "word_limit": null,
      "required_tables": [],
      "required_indicators": [],
      "tone": "plain, reflective, community-centred, non-technical",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "community_involvement",
      "title": "How you involved people from your community",
      "archetype": "ARCH_PARTICIPATION_AND_COMMUNITY_VOICE",
      "word_limit": null,
      "required_tables": [],
      "required_indicators": [
        "community_participation_examples",
        "partner_or_local_collaboration_examples"
      ],
      "tone": "practical, specific, inclusive",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "difference_made",
      "title": "The differences you are making, both big and small",
      "archetype": "ARCH_OUTCOMES_WITH_STORIES_AND_NUMBERS",
      "word_limit": null,
      "required_tables": [
        {
          "key": "outcomes_summary",
          "title": "Outcomes, evidence and examples",
          "columns": [
            "planned_change",
            "evidence_collected",
            "numbers",
            "story_or_quote",
            "what_changed"
          ],
          "required": false
        }
      ],
      "required_indicators": [
        "beneficiary_numbers",
        "community_feedback",
        "staff_or_volunteer_feedback",
        "outcome_indicators_where_available"
      ],
      "tone": "balanced, evidence-informed, accessible",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "learning",
      "title": "What you learned",
      "archetype": "ARCH_LEARNING_REFLECTION",
      "word_limit": null,
      "required_tables": [],
      "required_indicators": [
        "what_worked",
        "what_did_not_work",
        "unexpected_findings",
        "learning_useful_to_others"
      ],
      "tone": "honest, reflective, non-defensive",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "changes_and_next_steps",
      "title": "How you are changing what you do",
      "archetype": "ARCH_ADAPTATION_AND_NEXT_STEPS",
      "word_limit": null,
      "required_tables": [],
      "required_indicators": [
        "changes_made",
        "planned_changes",
        "support_needed"
      ],
      "tone": "practical, forward-looking, grounded in learning",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "spend_summary",
      "title": "What you spent this year",
      "archetype": "ARCH_BUDGET_VARIANCE_SUMMARY",
      "word_limit": null,
      "required_tables": [
        {
          "key": "budget_vs_actual",
          "title": "Budget compared with actual spend",
          "columns": [
            "cost_type",
            "budgeted_amount",
            "actual_spend",
            "variance",
            "variance_explanation"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "budgeted_total",
        "actual_spend_total",
        "revenue_cost_variance",
        "capital_cost_variance"
      ],
      "tone": "simple, factual, transparent",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "final_update_only",
      "title": "If this is your last progress update",
      "archetype": "ARCH_END_OF_GRANT_REFLECTION",
      "word_limit": null,
      "required_tables": [],
      "required_indicators": [
        "overall_project_reflection",
        "unshared_evidence_or_learning",
        "unspent_funds_status"
      ],
      "tone": "reflective, concise, transparent",
      "conditional_display": {
        "enabled": true,
        "condition": "report_type == 'final'"
      },
      "evidence_rules": {
        "claim_level_citation_required": false,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    }
  ],
  "format_rules_json": {
    "submission_style": "flexible_narrative_or_existing_report",
    "allows_existing_reports": true,
    "requires_highlighting_relevant_sections_if_reusing_existing_report": true,
    "requires_numbers_and_stories": true,
    "requires_budget_vs_actual_summary": true,
    "strict_word_limits": false,
    "strict_table_format": false,
    "learning_focus": true,
    "evidence_expectation": "proportionate_to_grant_size_and_project_context",
    "annual_trigger": "for grants over £20,000 lasting two years or more, progress update is normally requested every year",
    "final_update_mode": {
      "enabled": true,
      "additional_focus": [
        "overall project reflection",
        "additional evidence or learning",
        "unspent funds"
      ]
    }
  },
  "terminology_map_json": {
    "project": "project",
    "report": "progress update",
    "outcomes": "differences you are making",
    "beneficiaries": "people you support / community",
    "monitoring": "learning / evidence",
    "variance": "difference between budget and spend",
    "funder": "The National Lottery Community Fund",
    "grant": "National Lottery funding"
  }
}
```

## 2.2 NLCF sourcing note

### Sourced

- NLCF asks grant holders with grants over £20,000 lasting two years or more to provide a yearly progress update.
- NLCF frames the update around how the project is going and what the grantee is learning.
- NLCF’s public progress update guidance includes the following themes:
  - project story
  - community involvement
  - differences made
  - learning
  - changes to practice
  - spending
  - final update reflections
- NLCF asks for numbers and stories when explaining the difference made.
- NLCF encourages evidence from people supported, staff, volunteers and other relevant voices.
- NLCF’s spend section asks for budgeted amount, actual spend and the difference, not every transaction.
- NLCF accepts flexible evidence formats, including annual reports, evaluations, feedback, graphs, statistics, slides, photos, videos, infographics and meeting minutes.
- NLCF allows an existing report written for another funder to be submitted if it covers the funded activity, with relevant sections highlighted.
- NLCF programme-specific guidance confirms indicators are used to track progress towards outcomes and that progress can be numeric or qualitative.

### Source URLs

- `https://www.tnlcommunityfund.org.uk/funding/funding-support/managing-your-funding/reporting-progress/letting-us-know-how-your-projects-going`
- `https://www.tnlcommunityfund.org.uk/funding/funding-support/managing-your-funding/reporting-progress/what-we-usually-like-to-know-in-a-progress-update`
- `https://www.tnlcommunityfund.org.uk/funding/funding-support/managing-your-funding/guidance-for-specific-programmes/guidance-on-tracking-progress-for-people-and-places/`

### Inferred

- This template merges Annual Progress Update and End-of-Grant Update because the public NLCF guidance presents the “last progress update” as a conditional final-report extension, not as a wholly separate universal template.
- Word limits are set to `null` because public guidance does not provide strict section-level word counts.
- Tables are optional except budget variance, because NLCF encourages flexible evidence formats rather than one strict report table.

### Needs real grantee report

- Exact portal field names and field order.
- Whether the portal has locked text boxes, upload-only flows, or structured budget rows.
- Programme-specific mandatory indicators for major NLCF grant lines.
- Real submitted end-of-grant update to confirm how final reflections differ from normal progress updates.

## 2.3 NLCF build quirks

- Generate plain-English reflective narrative.
- Do not produce a technical M&E report unless the uploaded material requires it.
- Ask for missing stories, learning and community voice, not only missing indicators.
- Support a conditional final-update section.
- Later, support a “reuse existing report and highlight relevant sections” mode.

---

# 3. FCDO Reference Template

## 3.1 Template definition

```json
{
  "funder_name": "Foreign, Commonwealth & Development Office",
  "template_name": "FCDO Annual Review",
  "region": "UK / International Development",
  "reporting_frequency": "annual",
  "report_sections_json": [
    {
      "key": "summary_and_overview",
      "title": "A. Summary and Overview",
      "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
      "word_limit": 900,
      "required_tables": [
        {
          "key": "review_summary_sheet",
          "title": "Annual Review Summary Sheet",
          "columns": [
            "programme_title",
            "programme_code",
            "review_date",
            "review_period",
            "budget",
            "overall_score_or_rating",
            "risk_rating",
            "review_team"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "overall_progress",
        "main_results_achieved",
        "main_issues",
        "key_recommendations"
      ],
      "tone": "formal, evidence-led, concise",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "performance_and_conclusions",
      "title": "B. Performance and Conclusions",
      "archetype": "ARCH_PERFORMANCE_CONCLUSIONS",
      "word_limit": 1200,
      "required_tables": [
        {
          "key": "outcome_assessment",
          "title": "Annual Outcome Assessment",
          "columns": [
            "outcome_statement",
            "progress_summary",
            "evidence",
            "issues",
            "assessment"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "outcome_indicators",
        "progress_against_expected_results",
        "major_deviations",
        "gender_age_or_vulnerable_group_disaggregation_where_relevant"
      ],
      "tone": "analytical, transparent, performance-focused",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "detailed_output_scoring",
      "title": "C. Detailed Output Scoring",
      "archetype": "ARCH_OUTPUT_SCORING_TABLE",
      "word_limit": null,
      "required_tables": [
        {
          "key": "output_score_table",
          "title": "Output scoring against logframe",
          "columns": [
            "output",
            "impact_weighting",
            "risk_rating",
            "indicator",
            "baseline",
            "milestone",
            "actual",
            "score",
            "evidence",
            "explanation_for_variance"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "output_indicators",
        "logframe_milestones",
        "actual_results",
        "impact_weightings",
        "risk_ratings",
        "output_scores"
      ],
      "tone": "technical, precise, evidence-linked",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "evidence_and_evaluation",
      "title": "Evidence and Evaluation",
      "archetype": "ARCH_EVIDENCE_AND_EVALUATION_REVIEW",
      "word_limit": 900,
      "required_tables": [
        {
          "key": "evidence_quality_matrix",
          "title": "Evidence quality and gaps",
          "columns": [
            "result_or_claim",
            "evidence_source",
            "evidence_quality",
            "limitations",
            "implication_for_assessment"
          ],
          "required": false
        }
      ],
      "required_indicators": [
        "evidence_base_strength",
        "new_evidence",
        "evaluation_progress",
        "data_quality_limitations"
      ],
      "tone": "critical, factual, transparent about evidence limits",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "risk_and_safeguarding",
      "title": "Risk, Assumptions and Safeguarding",
      "archetype": "ARCH_RISK_ASSUMPTIONS_AND_CONTROLS",
      "word_limit": 900,
      "required_tables": [
        {
          "key": "risk_register_update",
          "title": "Risk update",
          "columns": [
            "risk",
            "previous_rating",
            "current_rating",
            "mitigation",
            "owner",
            "status"
          ],
          "required": false
        }
      ],
      "required_indicators": [
        "new_risks",
        "realised_assumptions",
        "funds_not_used_as_intended_risk",
        "climate_environment_risk",
        "safeguarding_risk_where_relevant"
      ],
      "tone": "clear, candid, control-focused",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "value_for_money",
      "title": "D. Value for Money",
      "archetype": "ARCH_VALUE_FOR_MONEY_4E",
      "word_limit": 1200,
      "required_tables": [
        {
          "key": "vfm_measures",
          "title": "Value for Money measures",
          "columns": [
            "vfm_measure",
            "business_case_proposition_or_baseline",
            "current_performance",
            "evidence",
            "assessment",
            "change_needed"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "economy",
        "efficiency",
        "effectiveness",
        "equity",
        "cost_drivers",
        "forecast_vs_actual_costs",
        "commercial_improvement_where_relevant"
      ],
      "tone": "analytical, cost-aware, evidence-linked",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "programme_management_delivery_commercial_financial",
      "title": "F. Programme Management: Delivery, Commercial and Financial Performance",
      "archetype": "ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW",
      "word_limit": 1200,
      "required_tables": [
        {
          "key": "delivery_financial_performance",
          "title": "Delivery, commercial and financial performance",
          "columns": [
            "area",
            "planned_position",
            "actual_position",
            "variance_or_issue",
            "management_action"
          ],
          "required": false
        }
      ],
      "required_indicators": [
        "partner_performance",
        "supplier_or_consultant_performance",
        "financial_delivery",
        "forecast_vs_actual_spend",
        "commercial_or_procurement_issues",
        "FCDO_management_actions"
      ],
      "tone": "formal, management-focused, concise",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    },
    {
      "key": "recommendations_and_actions",
      "title": "Recommendations and Action Points",
      "archetype": "ARCH_RECOMMENDATIONS_ACTION_PLAN",
      "word_limit": null,
      "required_tables": [
        {
          "key": "recommendations_action_plan",
          "title": "Recommendations and action points",
          "columns": [
            "recommendation",
            "owner",
            "due_date",
            "priority",
            "status",
            "follow_up_required"
          ],
          "required": true
        }
      ],
      "required_indicators": [
        "recommendations_from_current_review",
        "updates_on_previous_recommendations",
        "priorities_for_next_period"
      ],
      "tone": "direct, accountable, implementation-focused",
      "conditional_display": {
        "enabled": false,
        "condition": null
      },
      "evidence_rules": {
        "claim_level_citation_required": true,
        "numeric_claims_must_have_source": true,
        "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
      }
    }
  ],
  "format_rules_json": {
    "submission_style": "structured_institutional_annual_review",
    "requires_logframe_or_equivalent": true,
    "requires_output_scoring": true,
    "requires_outcome_assessment": true,
    "requires_value_for_money_assessment": true,
    "requires_risk_assessment": true,
    "requires_evidence_assessment": true,
    "requires_forecast_vs_actual_cost_review": true,
    "requires_gender_age_or_vulnerability_disaggregation_where_relevant": true,
    "requires_recommendations_action_plan": true,
    "strict_word_limits": true,
    "scoring_system": {
      "type": "five_point_output_scoring",
      "scope": "outputs_at_annual_review",
      "note": "Outcome is assessed at Annual Review; outputs are scored. PCR scoring differs."
    },
    "rag_or_traffic_light": {
      "status": "needs_confirmation_per_programme",
      "note": "Some public FCDO/DevTracker examples refer to green or traffic-light style ratings, but the core cited guidance confirms five-point output scoring rather than a universal RAG-only template."
    },
    "publication": {
      "annual_reviews_published_to_devtracker": true,
      "sensitivity_exclusions_possible": true
    }
  },
  "terminology_map_json": {
    "project": "programme / project",
    "report": "Annual Review",
    "impact": "Impact",
    "outcomes": "Outcome",
    "outputs": "Outputs",
    "indicators": "Indicators",
    "milestones": "Milestones",
    "results_framework": "Results framework / logframe",
    "budget": "Budget / forecast and actual costs",
    "value_for_money": "Value for Money / VfM",
    "risk": "Risk rating / assumptions / controls",
    "funder": "FCDO",
    "review_system": "AMP / DevTracker publication context"
  }
}
```

## 3.2 FCDO sourcing note

### Sourced

- FCDO programme benefits are set out as outputs and outcomes and measured through a results framework across the programme lifecycle.
- Annual Reviews check whether a programme’s benefits are on track.
- Annual Reviews revisit the theory of change, assess whether the programme is on track to meet longer-term objectives or outcomes, and recommend changes.
- Annual Reviews and Project Completion Reviews uploaded to AMP are published to DevTracker, subject to sensitivity exclusions.
- DevTracker programme pages publish real FCDO Annual Review and Logical Framework documents.
- FCDO / DFID review guidance confirms Annual Reviews score achievement against outputs and assess the outcome.
- Project Completion Reviews score both outputs and outcome.
- FCDO / DFID review guidance confirms a five-point scoring system focused on actual achievement of expected results, not probability of future achievement.
- Review guidance requires review against logframe or equivalent data, including baselines, milestones, targets and achieved results.
- Review guidance identifies Value for Money, Evidence and Evaluation, Risk Assessment, costs compared to forecast and funds-not-used-as-intended risk as review components.
- Monitoring data should be disaggregated where possible, including by gender, age and defined vulnerable groups where relevant.
- The Annual Review should test assumptions linking indicators, outputs, outcomes and impact, not merely tick off logframe indicators.
- Value for Money should refer to measures in the Appraisal Case or Business Case and review performance against those measures.
- Public Annual Review examples expose recurring headings including:
  - A. Summary and Overview
  - B. Performance and Conclusions
  - D. Value for Money
  - F. Programme Management: Delivery, Commercial & Financial Performance
  - Detailed Output Scoring

### Source URLs

- `https://assets.publishing.service.gov.uk/media/69381b256a12691d48491c5e/Programme_Operating_Framework_-_October_2025.pdf`
- `https://devtracker.fcdo.gov.uk/programme/GB-1-204322/documents`
- `https://assets.publishing.service.gov.uk/media/5a790676e5274a2acd18ba08/HTN-Reviewing-Scoring-Projects.pdf`
- `https://iati.fcdo.gov.uk/iati_documents/90000956.odt`
- `https://iati.fcdo.gov.uk/iati_documents/44659413.odt`

### Inferred

- The section ordering is a practical composite based on FCDO / DFID public review guidance and public Annual Review examples.
- FCDO templates vary by year, programme type and platform.
- Word limits are working synthesis constraints, not confirmed universal FCDO limits.
- `equity` is included in the VfM indicators because development VfM commonly uses the 4E framing, but this should be verified against the current target FCDO template before locking.
- `rag_or_traffic_light` is marked as needs-confirmation because some examples refer to traffic-light style ratings but public guidance confirms five-point output scoring as the core scoring structure.

### Needs real grantee or programme material

- Current FCDO Annual Review DOCX or ODT template.
- Current FCDO logframe XLSX export.
- Confirmation of RAG / traffic-light field usage for the intended template.
- Confirmation of AMP field names.
- Example implementing-partner report that feeds into the FCDO Annual Review process.

## 3.3 FCDO build quirks

- Requires table-heavy report support.
- Requires logframe or equivalent as a core source document.
- Requires strict evidence grounding for every number, score, milestone, cost statement and risk rating.
- Gap agent must ask for missing milestones, actuals, variance explanations, VfM evidence and risk updates.
- RAG should remain optional until confirmed.
- Fact-safety critic must run before export.
- DOCX export must handle tables cleanly.

---

# 4. Schema stress-test conclusion

## 4.1 Did one schema hold both?

Yes, with two recommended additions.

| Schema area | NLCF fit | FCDO fit | Verdict |
|---|---|---|---|
| `report_sections_json` | Clean | Clean | Works |
| `format_rules_json` | Clean | Clean | Works |
| `terminology_map_json` | Clean | Clean | Works |
| `required_tables` | Light | Heavy | Works |
| `required_indicators` | Flexible | Critical | Works |
| `tone` | Useful | Useful | Works |
| `word_limit` | Mostly null | Needed | Works |
| `conditional_display` | Needed | Useful | Add globally |
| `evidence_rules` | Useful | Critical | Add globally |

## 4.2 Required Stage B schema adjustment

Add `conditional_display` to each report section:

```json
{
  "conditional_display": {
    "enabled": true,
    "condition": "report_type == 'final'"
  }
}
```

Add `evidence_rules` to each report section:

```json
{
  "evidence_rules": {
    "claim_level_citation_required": true,
    "numeric_claims_must_have_source": true,
    "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
  }
}
```

These fields should be supported in `FUNDER_TEMPLATE_SCHEMA.md`, `REPORT_INPUTS_FIELD_MAPPING.md`, and any later critic-agent contract.

---

# 5. Grantee material that would most improve accuracy

| Priority | Material | Why it matters |
|---|---|---|
| P0 | Real NLCF portal progress update screenshots or exported submitted reports | Confirms exact field structure and whether public headings map directly to portal fields. |
| P0 | Current FCDO Annual Review DOCX / ODT template | Confirms section labels, scoring fields and current wording. |
| P0 | Real FCDO logframe XLSX export | Confirms table columns needed for output scoring. |
| P1 | NLCF end-of-grant submitted report | Confirms how final reflections differ from annual progress updates. |
| P1 | FCDO supplier or implementing-partner annual report submitted to FCDO | Confirms what NGOs/suppliers actually provide versus what FCDO programme teams publish. |
| P1 | FCDO VfM example annex | Improves value-for-money synthesis and avoids generic cost narrative. |
| P2 | NLCF programme-specific reporting examples, especially Climate Action Fund / People and Places | Captures programme-level indicator variations. |

---

# 6. STOP conditions for Cursor

Cursor must STOP and report if:

1. `FUNDER_TEMPLATE_SCHEMA.md` already exists and conflicts with these template structures.
2. Stage B prompt asks for product code, models, migrations, routes, workers, storage or agents.
3. Template schema requires fields that cannot represent both NLCF and FCDO.
4. Any proposed M&E API endpoint alters existing GrantPilot proposal, fit scan, auth, billing or profile contracts without explicit instruction.
5. `IMPACT_PRO` conflicts with existing plan enum/check constraints and no contract update is included.
6. Any JSONB field is proposed without `_json` suffix unless an authoritative Stage B contract says otherwise.
7. Any evidence or reporting claim is treated as funder-sourced without a source URL.
8. Any uploaded-document processing assumes autonomous acceptance of extracted facts without human confirmation gates.
