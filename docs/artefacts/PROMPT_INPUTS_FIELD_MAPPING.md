# PROMPT_INPUTS_FIELD_MAPPING.md

**Status:** Canonical (LOCKED FOR BUILD)  
**Scope:** Prompt input contract for all AI calls (Fit Scan + Proposal generation)  
**Version:** 1.0.2  
**Last updated:** 2026-01-24

---

## 0. Non-Negotiable Contract

### 0.1 Single input object only
All AI prompts MUST receive exactly one serialized object:

- `prompt_inputs_json`

No other top-level objects are allowed (for example: `ngo_profile_json`, `funding_opportunity_json`, `requirements_json`, `user_inputs_json`).  
If those names appear anywhere in prompt specs or backend wiring, it is a contract violation.

### 0.2 Where data comes from
`prompt_inputs_json` is assembled by the backend from:
- DB records (ngo_profiles, funding_opportunities, users/user_plans as needed)
- Funding opportunity's `requirements_json` (stored in DB)
- Runtime user inputs (variant selection, preferences, uploads)

### 0.3 Defaulting rules
If a source field is missing:
- Use `null` for scalars
- Use `[]` for list-like fields
- Use `{}` for objects
…and flag the missingness inside the AI output using the relevant "MISSING_DATA" / warnings logic (as defined in OPENAI_PROMPTS_LIBRARY.md).

### 0.4 User vs Derived Distinction
The prompt input object separates runtime user inputs from backend-computed values:

- **`prompt_inputs.user`**: Runtime user inputs (variant selection, preferences, uploads metadata)
- **`prompt_inputs.derived`**: Backend-computed fields (dates, display strings, extracted data, deterministic selections)

This separation ensures clarity about what the user controls vs what the system computes.

---

## 1. Canonical Shape: `prompt_inputs_json`

### 1.1 Top-level keys
`prompt_inputs_json` MUST contain:

```json
{
  "prompt_inputs": {
    "ngo": {},
    "opportunity": {},
    "requirements": {},
    "user": {},
    "derived": {}
  }
}
```

No other top-level keys are permitted.

### 1.2 Prompt Boundary Contract
- `prompt_inputs_json` is the **only** object passed to AI prompts
- The adapter must assemble this object deterministically
- Prompts may reference only fields explicitly listed in Sections 2–6
- No raw DB objects (e.g., `ngo_profile_json`, `funding_opportunity_json`) may be passed

---

## 2. `prompt_inputs.ngo` (from `ngo_profiles`)

### 2.1 Canonical fields (MVP-aligned to current DB)

| prompt_inputs.ngo field | Type | Source (DB: ngo_profiles) | Default |
|---|---:|---|---|
| **Identity & Footprint** ||||
| organization_name | string | organization_name | null |
| country_of_registration | string | country_of_registration | null |
| website | string | website | null |
| **Mission & Thematic Focus** ||||
| mission_statement | string | mission_statement | null |
| focus_sectors | array[string] | focus_sectors (JSONB array) | [] |
| **Operating Model** ||||
| geographic_areas_of_work | array[string] | geographic_areas_of_work (JSONB array) | [] |
| target_groups | array[string] | target_groups (JSONB array) | [] |
| past_projects | array[object] | past_projects (JSONB array) | [] |
| **Capacity Signals** ||||
| annual_budget_amount | number | annual_budget_amount | null |
| annual_budget_currency | string | annual_budget_currency | "USD" (DB default) |
| full_time_staff | integer | full_time_staff | null |
| **Optional Profile Fields** ||||
| year_of_establishment | integer | year_of_establishment | null |
| contact_person_name | string | contact_person_name | null |
| contact_email | string | contact_email | null |
| monitoring_and_evaluation_practices | string | monitoring_and_evaluation_practices | null |
| funders_worked_with_before | array[string] | funders_worked_with_before (JSONB array) | [] |

### 2.2 Field Usage Notes

**annual_budget_amount:**
- Numeric value used for scale comparison only (Fit Scan CAPACITY layer)
- No "range" concept exists in MVP
- Display-friendly formats must be derived (see `annual_budget_display` in Section 5)

**annual_budget_currency:**
- Used only for currency-match checks in CAPACITY layer
- No FX conversion permitted in MVP
- If currencies mismatch (opportunity vs NGO), CAPACITY cannot be computed

**full_time_staff:**
- Represents total number of full-time staff
- Used as a capacity signal in Fit Scan

**past_projects:**
- Stored as JSONB array of objects
- AI must not assume a fixed schema beyond "it is a list of past projects"
- Each project may have: title, duration, location, beneficiaries_reached, budget, outcomes, funder (all optional)

### 2.3 Source Mapping (DB → prompt_inputs)

The adapter should map from the `ngo_profiles` table row as follows:

```
prompt_inputs.ngo.organization_name ← ngo_profile.organization_name
prompt_inputs.ngo.country_of_registration ← ngo_profile.country_of_registration
prompt_inputs.ngo.website ← ngo_profile.website
prompt_inputs.ngo.mission_statement ← ngo_profile.mission_statement
prompt_inputs.ngo.focus_sectors ← ngo_profile.focus_sectors
prompt_inputs.ngo.geographic_areas_of_work ← ngo_profile.geographic_areas_of_work
prompt_inputs.ngo.target_groups ← ngo_profile.target_groups
prompt_inputs.ngo.past_projects ← ngo_profile.past_projects
prompt_inputs.ngo.annual_budget_amount ← ngo_profile.annual_budget_amount
prompt_inputs.ngo.annual_budget_currency ← ngo_profile.annual_budget_currency
prompt_inputs.ngo.full_time_staff ← ngo_profile.full_time_staff
prompt_inputs.ngo.year_of_establishment ← ngo_profile.year_of_establishment
prompt_inputs.ngo.contact_person_name ← ngo_profile.contact_person_name
prompt_inputs.ngo.contact_email ← ngo_profile.contact_email
prompt_inputs.ngo.monitoring_and_evaluation_practices ← ngo_profile.monitoring_and_evaluation_practices
prompt_inputs.ngo.funders_worked_with_before ← ngo_profile.funders_worked_with_before
```

---

## 3. `prompt_inputs.opportunity` (from `funding_opportunities`)

### 3.1 Canonical fields (MVP-aligned to current DB)

| prompt_inputs.opportunity field | Type | Source (DB: funding_opportunities) | Default |
|---|---:|---|---|
| **Identifiers & URLs** ||||
| id | string (uuid) | id | null |
| source_url | string | source_url | null |
| application_url | string | application_url | null |
| **Core Listing Fields** ||||
| title | string | title | null |
| donor_organization | string | donor_organization | null |
| funding_type | string | funding_type | null |
| applicant_type | string (enum) | applicant_type | null |
| location_text | string | location_text | null |
| focus_areas | string | focus_areas | null |
| **Deadline & Amount** ||||
| deadline_type | string (enum) | deadline_type | null |
| application_deadline | string (date) | application_deadline | null |
| currency | string | currency | null |
| amount_min | number | amount_min | null |
| amount_max | number | amount_max | null |
| total_funding_available | number | total_funding_available | null |
| **Narrative Context** ||||
| short_summary | string | short_summary | null |
| overview_text | string | overview_text | null |
| eligibility_criteria | string | eligibility_criteria | null |
| application_process | string | application_process | null |
| contact_information | string | contact_information | null |
| **Operational Fields** ||||
| status | string (enum) | status | null |
| is_active | boolean | is_active | true (DB default) |
| is_archived | boolean | is_archived | false (DB default) |
| last_verified | string (date) | last_verified | null |
| organization_types | string | organization_types | null |
| geographic_focus | string | geographic_focus | null |
| processing_status | string | processing_status | null |
| parsing_confidence | number | parsing_confidence | null |
| internal_notes | string | internal_notes | null |
| created_at | string (timestamp) | created_at | null |
| updated_at | string (timestamp) | updated_at | null |
| **Requirements Payload** ||||
| requirements_json | object (JSONB) | requirements_json | {} |

### 3.2 Field Usage Notes

**requirements_json:**
- This field is duplicated into `prompt_inputs.requirements` (Section 4) for clarity
- AI must treat `prompt_inputs.requirements` as the authoritative source
- See DB_FIELD_CONTRACT_FUNDING_OPPORTUNITY.md for full schema

**Operational fields:**
- `status`, `processing_status`, `parsing_confidence`, `internal_notes` are for workflow/QA
- NOT intended for use in proposal narrative generation
- Used for filtering, validation, and curator workflows

### 3.3 Source Mapping (DB → prompt_inputs)

```
prompt_inputs.opportunity.<field> ← funding_opportunities.<field>
```

Direct 1:1 mapping for all fields listed in Section 3.1.

---

## 4. `prompt_inputs.requirements` (from funding_opportunities.requirements_json)

### 4.1 Canonical Contract
`prompt_inputs.requirements` MUST be set to the full `requirements_json` object from DB (unchanged).

```
prompt_inputs.requirements = funding_opportunities.requirements_json
```

**No transformation is permitted** except alias normalization (Section 7).

### 4.2 Degradation Rule
If `funding_opportunities.requirements_json` is null/empty/invalid for a READY opportunity, the adapter must still pass:

```
prompt_inputs.requirements = null
```

Downstream prompts must degrade gracefully per OPENAI_PROMPTS_LIBRARY.md (return `DEGRADED_MISSING_REQUIREMENTS`).

### 4.3 Schema Reference
See DB_FIELD_CONTRACT_FUNDING_OPPORTUNITY.md Section 2 for the authoritative `requirements_json` schema, including:
- `version`
- `opportunity_mode` (SINGLE | VARIANTS)
- `variants[]` (eligibility_rules, submission_items, required_documents, process_notes)
- `global_notes`

---

## 5. `prompt_inputs.user` (runtime inputs)

### 5.1 Purpose
`prompt_inputs.user` contains runtime user inputs that control prompt behavior but are not derived by the backend.

### 5.2 Canonical Structure

| prompt_inputs.user field | Type | Source | Default |
|---|---:|---|---|
| selected_variant_id | string | User selection or deterministic fallback | null |
| user_goal | string | User-provided intent (optional) | null |
| user_overrides | object | User preferences object | {} |
| uploaded_documents_index | array[object] | Metadata for uploaded files (MVP: empty) | [] |

### 5.3 user_overrides Schema

```json
{
  "preferred_focus": [],
  "deprioritise_focus": [],
  "tone_preference": "STANDARD",
  "must_include_points": [],
  "must_avoid_points": []
}
```

**Fields:**
- `preferred_focus`: array[string] - Topics to emphasize
- `deprioritise_focus`: array[string] - Topics to minimize
- `tone_preference`: "STANDARD" | "FORMAL" | "DIRECT"
- `must_include_points`: array[string] - Mandatory content to include
- `must_avoid_points`: array[string] - Content to exclude

### 5.4 uploaded_documents_index Schema (MVP)

In MVP, `uploads_supported = false` (see Section 6.2), so this array is always empty:

```json
[]
```

Post-MVP, when uploads are enabled, each entry will have:
```json
{
  "doc_name": "string",
  "doc_type": "PDF|DOCX|XLSX|OTHER",
  "notes": "string"
}
```

### 5.5 Canonical Minimum (MVP)

```json
{
  "selected_variant_id": null,
  "user_goal": null,
  "user_overrides": {
    "preferred_focus": [],
    "deprioritise_focus": [],
    "tone_preference": "STANDARD",
    "must_include_points": [],
    "must_avoid_points": []
  },
  "uploaded_documents_index": []
}
```

### 5.6 Migration Note from V1
In previous version (1.0.1), `user_overrides` was located at `prompt_inputs.derived.user_overrides`.  
As of version 1.0.2, all runtime user inputs are consolidated under `prompt_inputs.user` for clarity.

---

## 6. `prompt_inputs.derived` (backend-computed only)

### 6.1 Purpose
Derived fields exist to:
- Eliminate ambiguity inside prompts
- Provide deterministic values (dates, display strings, selected variant resolution)
- Avoid the AI having to compute business logic from raw text

**Critical Rule:** Derived fields MUST NOT be stored in DB as separate columns. They are computed at runtime by the adapter.

### 6.2 Required Derived Fields

| prompt_inputs.derived field | Type | How it is computed | Default |
|---|---:|---|---|
| today_utc_date | string (YYYY-MM-DD) | Backend sets current date in UTC (ISO format) | required |
| uploads_supported | boolean | MVP_SCOPE_LOCK: always false in MVP | false |
| grant_amount_display | string | Formatted grant amount string (see 6.3.1) | "" |
| annual_budget_display | string | Formatted NGO budget string (see 6.3.2) | "" |
| opportunity_priorities_phrases | array[string] | Extracted priority phrases (see 6.3.3) | [] |
| selected_variant_id | string | Deterministic variant selection (see 6.3.4) | null |
| selected_variant | object | Extracted variant object from requirements | {} |
| deadline_days_remaining | integer | Days until deadline from today_utc_date (see 6.3.5) | null |
| applicant_type | string | MVP constant for all NGO profiles | "NGO" |

### 6.3 Detailed Computation Rules

#### 6.3.1 grant_amount_display
Compute a display-safe amount string from opportunity fields:

**Logic:**
1. If `currency` + `amount_min` + `amount_max` are present:  
   → `"{currency} {min}–{max}"`  
   Example: `"USD 50,000–100,000"`

2. Else if `currency` + `amount_max` are present:  
   → `"Up to {currency} {max}"`  
   Example: `"Up to EUR 75,000"`

3. Else if `currency` + `amount_min` are present:  
   → `"From {currency} {min}"`  
   Example: `"From GBP 25,000"`

4. Else if `currency` + `total_funding_available` are present:  
   → `"{currency} {total_funding_available} total"`  
   Example: `"USD 500,000 total"`

5. Else:  
   → `"Amount not specified"`

**Storage:**
```
prompt_inputs.derived.grant_amount_display = computed_string
```

---

#### 6.3.2 annual_budget_display
Compute a display-safe NGO budget string:

**Logic:**
1. If `ngo.annual_budget_amount` + `ngo.annual_budget_currency` are present:  
   → `"{currency} {amount}"`  
   Example: `"USD 250,000"`

2. Else:  
   → `""` (empty string)

**Storage:**
```
prompt_inputs.derived.annual_budget_display = computed_string
```

**Note:** This is for display only. Fit Scan CAPACITY layer uses raw `annual_budget_amount` for ratio calculations.

---

#### 6.3.3 opportunity_priorities_phrases[]
**Purpose:** Supply "exact phrases" that mirror funder language without inventing new fields.

**Computation:**
Construct as a **de-duplicated list** from the following sources (in order):

1. `prompt_inputs.requirements.variants[*].eligibility_rules.themes_required[]`  
   (Extract all themes_required from all variants)

2. `prompt_inputs.requirements.global_notes.review_criteria[]`  
   (If present; extract review criteria phrases)

3. `prompt_inputs.opportunity.focus_areas`  
   (Split by comma if stored as a string; e.g., "Health, Education, Agriculture" → ["Health", "Education", "Agriculture"])

**De-duplication:**
- Remove exact duplicates (case-sensitive)
- Preserve order (first occurrence wins)

**If Empty:**
Set to `[]` and require downstream prompts to degrade/assume rather than invent phrases.

**Storage:**
```
prompt_inputs.derived.opportunity_priorities_phrases = ["phrase1", "phrase2", ...]
```

**Example:**
```
Input:
- themes_required: ["Climate Resilience", "Women Empowerment"]
- review_criteria: ["Gender Equity", "Climate Resilience"]
- focus_areas: "Agriculture, Women Empowerment"

Output:
["Climate Resilience", "Women Empowerment", "Gender Equity", "Agriculture"]
```

---

#### 6.3.4 selected_variant_id & selected_variant
**Purpose:** Deterministically select which variant to use for generation when user hasn't explicitly chosen.

**Computation Logic:**
See OPENAI_PROMPTS_LIBRARY.md GP-U01 for full deterministic selection algorithm.

**Summary:**
1. If `prompt_inputs.user.selected_variant_id` is provided and exists in `requirements.variants[]`:  
   → Use it

2. Else apply deterministic selection:
   - a. Prefer variant whose `eligibility_rules.applicant_type` matches `ngo.organization_type`
   - b. Prefer variant with matching geography (`ngo.country_of_registration` in `eligibility_rules.geographies`)
   - c. If still ambiguous → select first variant and flag warning: `"VARIANT_SELECTION_AMBIGUOUS"`

**Storage:**
```
prompt_inputs.derived.selected_variant_id = "variant_id_string"
prompt_inputs.derived.selected_variant = {full_variant_object}
```

**Example:**
```json
{
  "selected_variant_id": "track_1_ngo",
  "selected_variant": {
    "variant_id": "track_1_ngo",
    "variant_name": "NGO Track",
    "deadline_type": "FIXED",
    "application_deadline": "2026-06-30",
    "eligibility_rules": {...},
    "submission_items": [...],
    "required_documents": [...]
  }
}
```

---

#### 6.3.5 deadline_days_remaining
**Purpose:** Compute days until deadline for TIMING risk flags.

**Computation Logic:**
1. If `opportunity.deadline_type` = "FIXED" AND `opportunity.application_deadline` is present:
   ```
   deadline_days_remaining = (application_deadline - today_utc_date).days
   ```

2. Else:
   ```
   deadline_days_remaining = null
   ```

**Storage:**
```
prompt_inputs.derived.deadline_days_remaining = integer | null
```

**Example:**
```
today_utc_date = "2026-01-24"
application_deadline = "2026-02-15"
deadline_days_remaining = 22
```

**Usage in Fit Scan:**
- If `deadline_days_remaining < 14` → TIMING risk = HIGH
- If `deadline_days_remaining < 30` → TIMING risk = MEDIUM

---

#### 6.3.6 applicant_type (MVP Constant)
**Purpose:** Provide a stable applicant_type for prompts to reference.

**Computation:**
```
prompt_inputs.derived.applicant_type = "NGO"
```

**Rationale:**
MVP only supports NGO profiles. Future versions may support INDIVIDUAL, ACADEMIC_INSTITUTION, etc.

**Note:** Some prompts may reference `prompt_inputs.ngo.organization_type` (see Section 7.1 aliases). Both resolve to "NGO" in MVP.

---

## 7. Alias Rules (Legacy Field Names)

### 7.1 Purpose
Older prompt templates may reference legacy field names. These are NOT canonical but are treated as aliases to maintain backward compatibility.

**Rule:** If any prompt template references a legacy field name, treat it as an alias to the canonical field.

### 7.2 NGO Aliases

| Legacy Field Reference | Canonical Field | Notes |
|---|---|---|
| `prompt_inputs.ngo.country` | `prompt_inputs.ngo.country_of_registration` | Country alias for brevity |
| `prompt_inputs.ngo.beneficiaries` | `prompt_inputs.ngo.target_groups` | Legacy terminology |
| `prompt_inputs.ngo.focus_areas` | `prompt_inputs.ngo.focus_sectors` | Sector/area interchangeable |
| `prompt_inputs.ngo.sectors` | `prompt_inputs.ngo.focus_sectors` | Same as above |
| `prompt_inputs.ngo.geographic_areas` | `prompt_inputs.ngo.geographic_areas_of_work` | Shortened reference |
| `prompt_inputs.ngo.organization_type` | `prompt_inputs.derived.applicant_type` | MVP constant "NGO" |
| `prompt_inputs.ngo.annual_budget_range` | `prompt_inputs.ngo.annual_budget_amount` | **Critical:** No range exists in MVP; use numeric amount only |

### 7.3 Opportunity Aliases

| Legacy Field Reference | Canonical Field | Notes |
|---|---|---|
| `prompt_inputs.opportunity.grant_amount` | `prompt_inputs.derived.grant_amount_display` | Display-friendly string |
| `prompt_inputs.opportunity.priorities` | `prompt_inputs.derived.opportunity_priorities_phrases` | Extracted phrases array |
| `prompt_inputs.opportunity.target_regions` | `prompt_inputs.requirements.variants[*].eligibility_rules.geographies` OR `prompt_inputs.opportunity.location_text` | Fallback to location_text if geographies unavailable |

### 7.4 Requirements Aliases

| Legacy Field Reference | Canonical Field | Notes |
|---|---|---|
| `eligibility_rules.eligible_countries` | `eligibility_rules.geographies` | Countries/regions |
| `eligibility_rules.eligible_sectors` | `eligibility_rules.themes_required` | Thematic eligibility |
| `eligibility_rules.excluded_sectors` | `eligibility_rules.themes_excluded` | Thematic exclusions |

### 7.5 User/Derived Aliases (Migration from V1.0.1)

| Legacy Field Reference (V1.0.1) | Canonical Field (V1.0.2+) | Notes |
|---|---|---|
| `prompt_inputs.derived.user_overrides` | `prompt_inputs.user.user_overrides` | Moved to user section |
| `prompt_inputs.derived.uploaded_documents_index` | `prompt_inputs.user.uploaded_documents_index` | Moved to user section |

### 7.6 Important Note on annual_budget_range
**Legacy:** `prompt_inputs.ngo.annual_budget_range`  
**Canonical:** `prompt_inputs.ngo.annual_budget_amount` (numeric)

**Critical Clarification:**
- No "range" concept exists in MVP
- The field is a single numeric value (e.g., `250000`)
- If a range is required for downstream UX display, it must be derived outside the prompt layer
- For prompts: use `annual_budget_amount` for calculations, `annual_budget_display` for display

---

## 8. Enforcement Rule

### 8.1 Contract Violations
If any implementation or prompt:

1. References DB fields **not** listed in this document, OR
2. References separate raw objects at the prompt boundary (e.g., `ngo_profile_json`, `requirements_json`) instead of `prompt_inputs_json`, OR
3. Invents missing values rather than deriving or returning null, OR
4. Stores derived fields in the database as persistent columns

…it **violates** this artefact and must not be merged.

### 8.2 Validation Checklist
Before deploying any prompt or adapter code:

- ✅ All AI prompts receive exactly **one** object: `prompt_inputs_json`
- ✅ All field references exist in Sections 2-6 of this document
- ✅ Derived fields are computed at runtime (not stored in DB)
- ✅ Missing DB fields default to `null` / `[]` / `{}` as specified
- ✅ No raw DB objects passed to prompts
- ✅ Alias mappings respected for backward compatibility

---

## 9. Change Log

### 1.0.2 (2026-01-24) - CURRENT
**Changes:**
- Added `prompt_inputs.user` structure (Section 5) with full schema
- Added `opportunity_priorities_phrases[]` to derived fields (Section 6.2, 6.3.3)
- Restored all 9 derived fields with detailed computation rules (Section 6.3)
- Restored table format for NGO (Section 2.1) and opportunity (Section 3.1) fields
- Added semantic grouping headers (Identity, Mission, Capacity, etc.)
- Moved `user_overrides` from `derived` → `user` (breaking change documented)
- Moved `uploaded_documents_index` from `derived` → `user`
- Added comprehensive alias rules (Section 7)
- Added detailed field usage notes (Sections 2.2, 3.2)
- Added user vs derived distinction clarification (Section 0.4)
- Added enforcement rule (Section 8)

**Rationale:**
- Resolve audit findings from OPENAI_PROMPTS_LIBRARY V1→V2 migration
- Eliminate contract ambiguities blocking Cursor implementation
- Provide complete implementation guidance with examples
- Maintain backward compatibility via alias rules

**Breaking Changes:**
- `prompt_inputs.derived.user_overrides` → `prompt_inputs.user.user_overrides`
- `prompt_inputs.derived.uploaded_documents_index` → `prompt_inputs.user.uploaded_documents_index`

**Migration Path:**
- Update all prompt templates to use `prompt_inputs.user.*` for user inputs
- Aliases provided for legacy references in Section 7.5

### 1.0.1 (2026-01-24) - SUPERSEDED
- Enforced single-input-object contract (`prompt_inputs_json` only)
- Canonicalized annual budget to `annual_budget_amount` (numeric) and currency
- Added derived selected variant fields and deterministic date fields
- Added `uploads_supported=false` (MVP) to prevent upload-driven penalties

### 1.0.0 (2026-01-23) - INITIAL
- Initial prompt inputs field mapping

---

## 10. Implementation Example

### 10.1 Backend Adapter Function (Pseudocode)

```python
def build_prompt_inputs(
    ngo_profile: NGOProfile,
    funding_opportunity: FundingOpportunity,
    user_inputs: dict = None
) -> dict:
    """
    Assemble prompt_inputs_json per canonical contract.
    """
    from datetime import datetime, date
    
    # Section 2: NGO
    ngo = {
        "organization_name": ngo_profile.organization_name,
        "country_of_registration": ngo_profile.country_of_registration,
        "website": ngo_profile.website,
        "mission_statement": ngo_profile.mission_statement,
        "focus_sectors": ngo_profile.focus_sectors or [],
        "geographic_areas_of_work": ngo_profile.geographic_areas_of_work or [],
        "target_groups": ngo_profile.target_groups or [],
        "past_projects": ngo_profile.past_projects or [],
        "annual_budget_amount": ngo_profile.annual_budget_amount,
        "annual_budget_currency": ngo_profile.annual_budget_currency or "USD",
        "full_time_staff": ngo_profile.full_time_staff,
        "year_of_establishment": ngo_profile.year_of_establishment,
        "contact_person_name": ngo_profile.contact_person_name,
        "contact_email": ngo_profile.contact_email,
        "monitoring_and_evaluation_practices": ngo_profile.monitoring_and_evaluation_practices,
        "funders_worked_with_before": ngo_profile.funders_worked_with_before or [],
    }
    
    # Section 3: Opportunity (all fields from DB)
    opportunity = {
        "id": str(funding_opportunity.id),
        "source_url": funding_opportunity.source_url,
        "application_url": funding_opportunity.application_url,
        "title": funding_opportunity.title,
        "donor_organization": funding_opportunity.donor_organization,
        "funding_type": funding_opportunity.funding_type,
        "applicant_type": funding_opportunity.applicant_type,
        "location_text": funding_opportunity.location_text,
        "focus_areas": funding_opportunity.focus_areas,
        "deadline_type": funding_opportunity.deadline_type,
        "application_deadline": funding_opportunity.application_deadline.isoformat() if funding_opportunity.application_deadline else None,
        "currency": funding_opportunity.currency,
        "amount_min": funding_opportunity.amount_min,
        "amount_max": funding_opportunity.amount_max,
        "total_funding_available": funding_opportunity.total_funding_available,
        "short_summary": funding_opportunity.short_summary,
        "overview_text": funding_opportunity.overview_text,
        "eligibility_criteria": funding_opportunity.eligibility_criteria,
        "application_process": funding_opportunity.application_process,
        "contact_information": funding_opportunity.contact_information,
        "status": funding_opportunity.status,
        "is_active": funding_opportunity.is_active,
        "is_archived": funding_opportunity.is_archived,
        "last_verified": funding_opportunity.last_verified.isoformat() if funding_opportunity.last_verified else None,
        "organization_types": funding_opportunity.organization_types,
        "geographic_focus": funding_opportunity.geographic_focus,
        "processing_status": funding_opportunity.processing_status,
        "parsing_confidence": funding_opportunity.parsing_confidence,
        "internal_notes": funding_opportunity.internal_notes,
        "created_at": funding_opportunity.created_at.isoformat() if funding_opportunity.created_at else None,
        "updated_at": funding_opportunity.updated_at.isoformat() if funding_opportunity.updated_at else None,
        "requirements_json": funding_opportunity.requirements_json or {},
    }
    
    # Section 4: Requirements
    requirements = funding_opportunity.requirements_json or {}
    
    # Section 5: User
    user = {
        "selected_variant_id": user_inputs.get("selected_variant_id") if user_inputs else None,
        "user_goal": user_inputs.get("user_goal") if user_inputs else None,
        "user_overrides": user_inputs.get("user_overrides", {
            "preferred_focus": [],
            "deprioritise_focus": [],
            "tone_preference": "STANDARD",
            "must_include_points": [],
            "must_avoid_points": []
        }) if user_inputs else {
            "preferred_focus": [],
            "deprioritise_focus": [],
            "tone_preference": "STANDARD",
            "must_include_points": [],
            "must_avoid_points": []
        },
        "uploaded_documents_index": []  # MVP: always empty
    }
    
    # Section 6: Derived
    today_utc = datetime.utcnow().date()
    
    derived = {
        "today_utc_date": today_utc.isoformat(),
        "uploads_supported": False,  # MVP
        "grant_amount_display": compute_grant_amount_display(opportunity),
        "annual_budget_display": compute_annual_budget_display(ngo),
        "opportunity_priorities_phrases": extract_opportunity_priorities(requirements, opportunity),
        "selected_variant_id": select_variant_deterministic(requirements, ngo, user),
        "selected_variant": extract_selected_variant(requirements, derived["selected_variant_id"]),
        "deadline_days_remaining": compute_deadline_days_remaining(opportunity, today_utc),
        "applicant_type": "NGO",  # MVP constant
    }
    
    return {
        "prompt_inputs": {
            "ngo": ngo,
            "opportunity": opportunity,
            "requirements": requirements,
            "user": user,
            "derived": derived,
        }
    }


def compute_grant_amount_display(opportunity: dict) -> str:
    """Section 6.3.1"""
    currency = opportunity.get("currency")
    amount_min = opportunity.get("amount_min")
    amount_max = opportunity.get("amount_max")
    total = opportunity.get("total_funding_available")
    
    if currency and amount_min and amount_max:
        return f"{currency} {amount_min:,.0f}–{amount_max:,.0f}"
    elif currency and amount_max:
        return f"Up to {currency} {amount_max:,.0f}"
    elif currency and amount_min:
        return f"From {currency} {amount_min:,.0f}"
    elif currency and total:
        return f"{currency} {total:,.0f} total"
    else:
        return "Amount not specified"


def compute_annual_budget_display(ngo: dict) -> str:
    """Section 6.3.2"""
    amount = ngo.get("annual_budget_amount")
    currency = ngo.get("annual_budget_currency")
    
    if amount and currency:
        return f"{currency} {amount:,.0f}"
    else:
        return ""


def extract_opportunity_priorities(requirements: dict, opportunity: dict) -> list:
    """Section 6.3.3"""
    phrases = []
    
    # From variants themes_required
    for variant in requirements.get("variants", []):
        themes = variant.get("eligibility_rules", {}).get("themes_required", [])
        phrases.extend(themes)
    
    # From global_notes review_criteria
    review_criteria = requirements.get("global_notes", {}).get("review_criteria", [])
    phrases.extend(review_criteria)
    
    # From opportunity focus_areas
    focus_areas = opportunity.get("focus_areas", "")
    if focus_areas:
        phrases.extend([area.strip() for area in focus_areas.split(",")])
    
    # De-duplicate (preserve order)
    seen = set()
    result = []
    for phrase in phrases:
        if phrase and phrase not in seen:
            seen.add(phrase)
            result.append(phrase)
    
    return result


def compute_deadline_days_remaining(opportunity: dict, today: date) -> int | None:
    """Section 6.3.5"""
    deadline_type = opportunity.get("deadline_type")
    deadline_str = opportunity.get("application_deadline")
    
    if deadline_type == "FIXED" and deadline_str:
        deadline = date.fromisoformat(deadline_str)
        return (deadline - today).days
    else:
        return None
```

---

## END OF FILE
