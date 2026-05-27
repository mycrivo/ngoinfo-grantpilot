# REPORT_INPUTS_FIELD_MAPPING.md

**Status:** Canonical (LOCKED — Stage B validation complete)  
**Scope:** Input contract for M&E report section synthesis (and gap/compliance agents)  
**Version:** 1.0.0  
**Last updated:** 2026-05-24  
**Mirrors:** `docs/artefacts/PROMPT_INPUTS_FIELD_MAPPING.md` (proposal product)

---

## 0. Non-Negotiable Contract

### 0.1 Single input object only

All report synthesis prompts MUST receive exactly one serialized object:

- `report_inputs_json`

No other top-level objects (e.g. raw `knowledge_bank_json`, `requirements_json`) may be passed directly to prompts.

### 0.2 Where data comes from

`report_inputs_json` is assembled by `app/reports/services/report_inputs_builder.py` from:

| Source | DB / artefact |
|--------|---------------|
| NGO profile | `ngo_profiles` (core) |
| Funder template | `funder_report_templates.report_sections_json`, `format_rules_json`, `terminology_map_json` |
| Confirmed facts | `donor_reports.knowledge_bank_json` (post–Gate 1) |
| Indicator actuals | `donor_reports.indicator_actuals_json` |
| Gap answers | `donor_reports.knowledge_bank_json.gap_answers` (post–Gate 2) |
| Report metadata | `donor_reports` scalar fields + template metadata |
| Linked proposal (optional) | `proposals.content_json` when `linked_proposal_id` set |

### 0.3 Defaulting rules

| Missing data | Default |
|--------------|---------|
| Scalar | `null` |
| Array | `[]` |
| Object | `{}` |

Gap/compliance agent MUST flag missing required indicators/sections — synthesis MUST NOT invent specifics.

### 0.4 User vs derived

- **`report_inputs.user`**: Human-provided gap answers and explicit section edits (from API)
- **`report_inputs.derived`**: Backend-computed (period labels, template resolution, gate state)

---

## 1. Canonical Shape: `report_inputs_json`

### 1.1 Top-level keys

```json
{
  "report_inputs": {
    "ngo": {},
    "template": {},
    "report": {},
    "knowledge_bank": {},
    "indicators": {},
    "section": {},
    "user": {},
    "derived": {}
  }
}
```

No other top-level keys permitted.

### 1.2 Invocation context

- **Per-section synthesis:** `report_inputs.section` populated for the target section only; builder called once per section.
- **Gap/compliance agent:** `report_inputs.section` omitted; full template + knowledge bank provided.

---

## 2. `report_inputs.ngo` (from `ngo_profiles`)

Same canonical fields as `prompt_inputs.ngo` in `PROMPT_INPUTS_FIELD_MAPPING.md` §2.

| report_inputs.ngo field | Type | Source (DB: ngo_profiles) | Default |
|-------------------------|------|---------------------------|---------|
| organization_name | string | organization_name | null |
| country_of_registration | string | country_of_registration | null |
| website | string | website | null |
| mission_statement | string | mission_statement | null |
| focus_sectors | array[string] | focus_sectors | [] |
| geographic_areas_of_work | array[string] | geographic_areas_of_work | [] |
| target_groups | array[string] | target_groups | [] |
| past_projects | array[object] | past_projects | [] |
| annual_budget_amount | number | annual_budget_amount | null |
| annual_budget_currency | string | annual_budget_currency | "USD" |
| full_time_staff | integer | full_time_staff | null |
| year_of_establishment | integer | year_of_establishment | null |
| contact_person_name | string | contact_person_name | null |
| contact_email | string | contact_email | null |
| monitoring_and_evaluation_practices | string | monitoring_and_evaluation_practices | null |
| funders_worked_with_before | array[string] | funders_worked_with_before | [] |
| knowledge_bank | object | knowledge_bank | {} |

**Note:** Profile `knowledge_bank` (org-level, reusable evidence) is distinct from report `knowledge_bank_json` (grant-specific confirmed facts). Both may be used; report-level takes precedence for grant specifics.

---

## 3. `report_inputs.template` (from `funder_report_templates`)

| report_inputs.template field | Type | Source | Default |
|------------------------------|------|--------|---------|
| template_id | string (uuid) | funder_report_templates.id | — |
| funder_name | string | funder_name | null |
| template_name | string | template_name | null |
| region | string | region | null |
| reporting_frequency | string | reporting_frequency | null |
| report_sections | array[object] | report_sections_json | [] |
| format_rules | object | format_rules_json | {} |
| terminology_map | object | terminology_map_json | {} |
| docx_template_ref | string | docx_template_ref | null |

Inner shapes: `FUNDER_TEMPLATE_SCHEMA.md`.

---

## 4. `report_inputs.report` (from `donor_reports`)

| report_inputs.report field | Type | Source | Default |
|----------------------------|------|--------|---------|
| report_id | string (uuid) | donor_reports.id | — |
| reporting_period_start | string (date) | reporting_period_start | null |
| reporting_period_end | string (date) | reporting_period_end | null |
| status | string | donor_reports.status | null |
| linked_proposal_id | string (uuid) or null | linked_proposal_id | null |
| version | integer | version | 1 |

---

## 5. `report_inputs.knowledge_bank` (from `donor_reports.knowledge_bank_json`)

Only **confirmed** facts (`facts[].confirmed = true`) and **resolved** conflicts enter synthesis.

| report_inputs.knowledge_bank field | Type | Source path | Default |
|------------------------------------|------|-------------|---------|
| facts | object | knowledge_bank_json.facts (filtered) | {} |
| conflicts_resolved | array[object] | knowledge_bank_json.conflicts where resolved | [] |
| gap_answers | object | knowledge_bank_json.gap_answers | {} |
| gate1_confirmed_at | string | knowledge_bank_json.gate1_confirmed_at | null |
| gate2_confirmed_at | string | knowledge_bank_json.gate2_confirmed_at | null |

**Rule:** Synthesis MUST NOT run until `gate1_confirmed_at` is set. Gap answers required before synthesis when gap agent flagged items (Gate 2).

---

## 6. `report_inputs.indicators` (from `donor_reports.indicator_actuals_json`)

| report_inputs.indicators field | Type | Source path | Default |
|--------------------------------|------|-------------|---------|
| indicators | array[object] | indicator_actuals_json.indicators | [] |
| financials | object | indicator_actuals_json.financials | {} |
| beneficiary_summary | object | indicator_actuals_json.beneficiary_summary | {} |

Cross-reference: section `required_indicators[]` in template must find matching `indicator_key` here or in confirmed `facts`.

---

## 7. `report_inputs.section` (per synthesis invocation)

| report_inputs.section field | Type | Source | Default |
|-----------------------------|------|--------|---------|
| section_key | string | Current section from report_sections_json | — |
| label | string | section.label | null |
| archetype | string | section.archetype | null |
| word_limit | integer | section.word_limit | null |
| tone | string | section.tone | null |
| required_tables | array | section.required_tables | [] |
| required_indicators | array[string] | section.required_indicators | [] |
| guidance | string | section.guidance | null |
| conditional_display | object | section.conditional_display | {"enabled": false, "condition": null} |
| evidence_rules | object | section.evidence_rules | {} |
| format_overrides | object | Merged from format_rules_json for this section | {} |

`conditional_display` drives UI/API section visibility (e.g. NLCF `final_update_only` when `report_type == 'final'`).

`evidence_rules` feeds fact-safety critic and gap agent strictness for this section.

`format_overrides` examples:
- RAG dimension labels when section is RAG summary
- ECHO block constraints when section maps to echo_blocks

---

## 8. `report_inputs.user` (runtime human inputs)

| report_inputs.user field | Type | Source | Default |
|--------------------------|------|--------|---------|
| gap_answers | object | API PATCH gap-answers (also persisted to knowledge_bank_json) | {} |
| section_edits | object | API PATCH sections/{key} pending edits | {} |
| regeneration_requested | boolean | API POST generate | false |

---

## 9. `report_inputs.derived` (backend-computed)

| report_inputs.derived field | Type | Source / computation | Default |
|-----------------------------|------|----------------------|---------|
| reporting_period_label | string | Formatted start–end | null |
| funder_display_name | string | funder_name + template_name | null |
| terminology_resolved | object | Apply terminology_map to labels | {} |
| linked_proposal_summary | string or null | Truncate linked proposal content_json | null |
| evidence_index | array[object] | Index of confirmed facts + upload ids | [] |
| synthesis_prompt_version | string | OPENAI_PROMPTS_LIBRARY report version | null |
| gate_state | string | From report_jobs.stage + status | null |

---

## 10. Complete Synthesis Input Map

Every field consumed by synthesis agents:

| Synthesis consumes | Mapped from |
|--------------------|-------------|
| NGO identity & mission | §2 — `report_inputs.ngo` |
| Org-level reusable evidence | §2 — `report_inputs.ngo.knowledge_bank` |
| Funder section order & labels | §3 — `report_inputs.template.report_sections` |
| Word limits & tone | §7 — `report_inputs.section` |
| Archetype / humaniser rules | §7 — `report_inputs.section.archetype` → prompts library |
| Funder terminology | §3 — `terminology_map` + §9 — `terminology_resolved` |
| RAG / logframe / ECHO / VfM rules | §3 — `format_rules` + §7 — `format_overrides` |
| Confirmed grant facts | §5 — `knowledge_bank.facts` |
| Resolved conflicts | §5 — `conflicts_resolved` |
| Human gap-fill text | §5 + §8 — `gap_answers` |
| Indicator targets/actuals | §6 — `indicators.indicators` |
| Financials | §6 — `indicators.financials` |
| Beneficiary counts | §6 — `beneficiary_summary` |
| Reporting period | §4 + §9 — `reporting_period_*`, `reporting_period_label` |
| Required tables data | §7 `required_tables` ← §6 + §5 by `data_source` |
| Linked winning proposal context | §4 `linked_proposal_id` → §9 `linked_proposal_summary` |
| Evidence traceability | §9 — `evidence_index` |
| Section visibility | §7 — `report_inputs.section.conditional_display` + §4 `report_type` |
| Per-section evidence strictness | §7 — `report_inputs.section.evidence_rules` |
| Prior section content (regen) | `donor_reports.content_json.sections[]` (same section_key) |

**Gap/compliance agent** consumes §3 (full template), §5, §6, §2 (ngo capacity context), plus per-section `evidence_rules` from §7 when evaluating section-level gaps.

**Fact-safety critic** consumes generated text + §5 facts + §6 indicators + upload `extracted_json` excerpts (via evidence_index), applying §7 `evidence_rules` for the section under review (`claim_level_citation_required`, `numeric_claims_must_have_source`, `allowed_sources`).

---

## 11. Parity with Proposal Product

| Proposal | Report equivalent |
|----------|-------------------|
| `prompt_inputs_json` | `report_inputs_json` |
| `prompt_inputs.opportunity` | `report_inputs.template` |
| `prompt_inputs.requirements` | `report_inputs.template.report_sections` + `format_rules` |
| `prompt_inputs.ngo` | `report_inputs.ngo` (shared shape) |
| `build_prompt_inputs()` | `build_report_inputs()` (Stage F) |
| GP-P02 per section | Report synthesis prompt per section (Stage F) |

---

## 12. Build Enforcement

- Adapter MUST assemble deterministically from DB — no prompt-side DB access.
- Synthesis on unconfirmed knowledge bank → `409 GATE_NOT_SATISFIED`.
- Missing required indicator → gap agent flags before synthesis; synthesis must not fabricate values.

---

## 13. Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-24 | Stage B structure lock; full source mapping |
| 1.0.1 | 2026-05-24 | Map `conditional_display` and `evidence_rules` per FUNDER_TEMPLATE_SCHEMA v1.1.0 |
