# PROMPT_INPUTS_FIELD_MAPPING.md

**Status:** Canonical (LOCKED FOR BUILD)  
**Scope:** Prompt input contract for all AI calls (Fit Scan + Proposal generation)  
**Version:** 1.0.1  
**Last updated:** 2026-01-24

---

## 0. Non-Negotiable Contract (Option A)

### 0.1 Single input object only
All AI prompts MUST receive exactly one serialized object:

- `prompt_inputs_json`

No other top-level objects are allowed (for example: `ngo_profile_json`, `funding_opportunity_json`, `requirements_json`, `user_inputs_json`).  
If those names appear anywhere in prompt specs or backend wiring, it is a contract violation.

### 0.2 Where data comes from
`prompt_inputs_json` is assembled by the backend from:
- DB records (ngo_profiles, funding_opportunities, users/user_plans as needed)
- Funding opportunity’s `requirements_json` (stored in DB)
- Optional user preferences (when UI exists) — injected ONLY under `prompt_inputs.derived.user_overrides`

### 0.3 Defaulting rules
If a source field is missing:
- Use `null` for scalars
- Use `[]` for list-like fields
- Use `{}` for objects
…and flag the missingness inside the AI output using the relevant “MISSING_DATA” / warnings logic (as defined in OPENAI_PROMPTS_LIBRARY.md).

---

## 1. Canonical Shape: `prompt_inputs_json`

### 1.1 Top-level keys
`prompt_inputs_json` MUST contain:

- `ngo` (object)
- `opportunity` (object)
- `requirements` (object)
- `derived` (object)

No other top-level keys.

---

## 2. `prompt_inputs.ngo` (from `ngo_profiles`)

### 2.1 Canonical fields (MVP-aligned to current DB)
| prompt_inputs.ngo field | Type | Source (DB: ngo_profiles) | Default |
|---|---:|---|---|
| organization_name | string | organization_name | null |
| country_of_registration | string | country_of_registration | null |
| mission_statement | string | mission_statement | null |
| focus_sectors | array[string] | focus_sectors (JSONB array) | [] |
| geographic_areas_of_work | array[string] | geographic_areas_of_work (JSONB array) | [] |
| target_groups | array[string] | target_groups (JSONB array) | [] |
| past_projects | array[object] | past_projects (JSONB array) | [] |
| year_of_establishment | integer | year_of_establishment | null |
| contact_person_name | string | contact_person_name | null |
| contact_email | string | contact_email | null |
| website | string | website | null |
| full_time_staff | integer | full_time_staff | null |
| annual_budget_amount | number | annual_budget_amount | null |
| annual_budget_currency | string | annual_budget_currency | "USD" (DB default) |
| monitoring_and_evaluation_practices | string | monitoring_and_evaluation_practices | null |
| funders_worked_with_before | array[string] | funders_worked_with_before (JSONB array) | [] |

### 2.2 Notes on `past_projects`
Each past project object is stored as-is (JSONB). The AI must not assume a fixed schema beyond “it is a list of past projects”.

---

## 3. `prompt_inputs.opportunity` (from `funding_opportunities`)

| prompt_inputs.opportunity field | Type | Source (DB: funding_opportunities) | Default |
|---|---:|---|---|
| id | string (uuid) | id | null |
| source_url | string | source_url | null |
| application_url | string | application_url | null |
| title | string | title | null |
| donor_organization | string | donor_organization | null |
| funding_type | string | funding_type | null |
| applicant_type | string | applicant_type (enum) | null |
| location_text | string | location_text | null |
| focus_areas | string | focus_areas | null |
| deadline_type | string | deadline_type (enum) | null |
| application_deadline | string (date) | application_deadline | null |
| currency | string | currency | null |
| amount_min | number | amount_min | null |
| amount_max | number | amount_max | null |
| total_funding_available | number | total_funding_available | null |
| short_summary | string | short_summary | null |
| overview_text | string | overview_text | null |
| eligibility_criteria | string | eligibility_criteria | null |
| application_process | string | application_process | null |
| status | string | status (enum) | null |
| is_active | boolean | is_active | true (DB default) |
| is_archived | boolean | is_archived | false (DB default) |
| last_verified | string (date) | last_verified | null |
| organization_types | string | organization_types | null |
| geographic_focus | string | geographic_focus | null |
| contact_information | string | contact_information | null |
| processing_status | string | processing_status | null |
| parsing_confidence | number | parsing_confidence | null |
| internal_notes | string | internal_notes | null |
| requirements_json | object | requirements_json (JSONB) | {} |

**Important:** `requirements_json` is duplicated into `prompt_inputs.requirements` (below) for clarity; the AI must treat them as the same content.

---

## 4. `prompt_inputs.requirements` (from funding_opportunities.requirements_json)

- This is the canonical, full requirements object used by Fit Scan and proposal generation.
- The backend should set:

`prompt_inputs.requirements = prompt_inputs.opportunity.requirements_json` (exact copy)

Default: `{}`

---

## 5. `prompt_inputs.derived` (backend-computed only)

### 5.1 Purpose
Derived fields exist to:
- eliminate ambiguity inside prompts
- provide deterministic values (dates, display strings, selected variant resolution)
- avoid the AI having to compute business logic from raw text

Derived fields MUST NOT be stored in DB as separate columns.

### 5.2 Derived fields (required)
| prompt_inputs.derived field | Type | How it is computed | Default |
|---|---:|---|---|
| today_utc_date | string (YYYY-MM-DD) | backend sets “today” | required |
| uploads_supported | boolean | MVP_SCOPE_LOCK: always false in MVP | false |
| uploaded_documents_index | array[object] | only if uploads exist; MVP empty | [] |
| grant_amount_display | string | if opportunity.total_funding_available + opportunity.currency present → formatted string; else empty marker | "" |
| annual_budget_display | string | if ngo.annual_budget_amount + ngo.annual_budget_currency present → formatted string; else "" | "" |
| selected_variant_id | string | deterministic selection from requirements.variants; see OPENAI_PROMPTS_LIBRARY GP-U01 rules | null |
| selected_variant | object | backend extracts the chosen variant object from requirements.variants | {} |
| deadline_days_remaining | integer | if deadline_type=FIXED and application_deadline present: date diff vs today_utc_date | null |

### 5.3 Optional user overrides (future UI)
All user preference inputs MUST live under:

`prompt_inputs.derived.user_overrides`

Allowed keys (all optional):
- `user_goal` (string)
- `tone_preference` (STANDARD | FORMAL | DIRECT)
- `must_include_points` (array[string])
- `must_avoid_points` (array[string])

Default: `{}`

---

## 6. Backward Compatibility / Alias Rules (to prevent Cursor blocks)

The following legacy field names may appear in older specs. They are NOT canonical. If they appear, treat them as aliases and update the spec to canonical names:

- `prompt_inputs.ngo.annual_budget_range` → **REPLACE WITH** `prompt_inputs.ngo.annual_budget_amount` + `prompt_inputs.ngo.annual_budget_currency`
- `prompt_inputs.ngo.country` → **REPLACE WITH** `prompt_inputs.ngo.country_of_registration`
- Any mention of `*_json` top-level objects (ngo_profile_json, requirements_json, etc.) → **REPLACE WITH** `prompt_inputs_json` only

---

## 7. Change Log

### 1.0.1 (2026-01-24)
- Enforced single-input-object contract (`prompt_inputs_json` only).
- Canonicalized annual budget to `annual_budget_amount` (numeric) and currency.
- Added derived selected variant fields and deterministic date fields.
- Added `uploads_supported=false` (MVP) to prevent upload-driven penalties.
