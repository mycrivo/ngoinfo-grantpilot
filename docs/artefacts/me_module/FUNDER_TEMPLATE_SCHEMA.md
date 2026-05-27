# FUNDER_TEMPLATE_SCHEMA.md

**Status:** Canonical (LOCKED — Stage B validation complete)  
**Scope:** JSONB shapes inside `funder_report_templates`  
**Version:** 1.1.0  
**Last updated:** 2026-05-24

---

## 0. Non-Negotiable Rules

1. All three JSONB columns use the **`_json` suffix** in DB, models, and API:  
   `report_sections_json`, `format_rules_json`, `terminology_map_json`.
2. Shapes defined here MUST fit both:
   - **Simple funders** (e.g. NLCF — narrative learning sections, minimal tables)
   - **Complex funders** (e.g. FCDO — logframe, RAG ratings, value-for-money blocks)
3. **Template instances** (canonical JSON):  
   - [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json) — simple funder stress test  
   - [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json) — complex funder stress test  
   Source: `WORKSTREAM_T2_NLCF_FCDO_REFERENCE_TEMPLATES.md` (normalized 2026-05-24).
4. This schema is abstract by design — funders express complexity via optional blocks in `format_rules_json`, not separate column sets.

---

## 1. Design Principles

| Principle | Rationale |
|-----------|-----------|
| Ordered sections array | Synthesis runs one agent per section; order matches funder form |
| Archetype per section | Reuses proposal humaniser/archetype library (`OPENAI_PROMPTS_LIBRARY.md` extensions) |
| Optional format blocks | FCDO RAG, ECHO Single Form blocks attach without schema change |
| Terminology map | Same data, funder-specific labels in output |
| Extensibility via `extensions` | Unknown funder quirks without migration |

---

## 2. `report_sections_json`

**Type:** JSON array (ordered).  
**DB default:** `'[]'::jsonb`

### 2.1 Section object (required fields)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_key` | string | YES | Stable identifier; unique within template; used in API paths and `content_json` |
| `label` | string | YES | Human-facing heading (funder wording) |
| `archetype` | string | YES | Maps to report archetype in prompts library (Stage F) |
| `word_limit` | integer | NO | Max words; null = no hard limit |
| `tone` | string | NO | e.g. `formal`, `reflective`, `technical` |
| `required` | boolean | NO | Default `true`; if false, section skippable when gap agent allows |
| `required_tables` | array | NO | Table specs this section must include (§2.2) |
| `required_indicators` | array[string] | NO | Indicator keys that MUST appear (cross-ref `indicator_actuals_json`) |
| `guidance` | string | NO | Funder-specific writing guidance for synthesis agent |
| `conditional_display` | object | NO | Show section only when condition met — §2.1a |
| `evidence_rules` | object | NO | Critic/gap rules for this section — §2.1b |
| `extensions` | object | NO | Funder-specific keys without schema migration |

### 2.1a `conditional_display` (optional, v1.1.0)

```json
{
  "enabled": true,
  "condition": "report_type == 'final'"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | YES | When false, section always shown (subject to `required`) |
| `condition` | string or null | NO | Expression evaluated server-side; null when disabled |

**Use case:** NLCF end-of-grant section shown only when `report_type == 'final'` (Decision D-022).

### 2.1b `evidence_rules` (optional, v1.1.0)

```json
{
  "claim_level_citation_required": true,
  "numeric_claims_must_have_source": true,
  "allowed_sources": ["uploaded_documents", "human_confirmed_gap_answers"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `claim_level_citation_required` | boolean | YES | Fact-safety critic requires per-claim source |
| `numeric_claims_must_have_source` | boolean | YES | All numbers traceable before export |
| `allowed_sources` | array[string] | YES | Subset of: `uploaded_documents`, `human_confirmed_gap_answers`, `knowledge_bank_facts` |

### 2.2 Required table spec (items in `required_tables[]`)

Supports simple (one narrative table) and complex (multi-column logframe) funders:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table_key` | string | YES | Stable id |
| `label` | string | YES | Table heading |
| `columns` | array[object] | YES | Column definitions (§2.3) |
| `min_rows` | integer | NO | Default 0 |
| `max_rows` | integer | NO | null = unlimited |
| `data_source` | string | NO | `indicators` \| `financials` \| `knowledge_bank` \| `manual` |

### 2.3 Column definition (items in `columns[]`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `column_key` | string | YES | Stable id |
| `label` | string | YES | Header text (may use terminology_map) |
| `data_type` | string | NO | `text` \| `number` \| `date` \| `enum` \| `rag_rating` |
| `enum_values` | array[string] | NO | When `data_type = enum` or `rag_rating` |
| `required` | boolean | NO | Default false |

### 2.4 Simple funder expressiveness (NLCF-class)

A simple template uses:

- 3–6 sections with `archetype` values like `learning_narrative`, `activities_summary`, `outcomes_reflection`
- Empty or minimal `required_tables` (optional single progress table)
- Empty `format_rules_json.rag` and `format_rules_json.logframe`
- Short `terminology_map_json` remapping 2–3 terms

**Abstract example (not NLCF instance):**

```json
[
  {
    "section_key": "progress_summary",
    "label": "Tell us how it's going",
    "archetype": "learning_narrative",
    "word_limit": 800,
    "tone": "reflective",
    "required": true,
    "required_tables": [],
    "required_indicators": ["beneficiaries_reached"],
    "guidance": "Focus on learning and adaptation, not marketing language."
  }
]
```

---

## 3. `format_rules_json`

**Type:** JSON object.  
**DB default:** `'{}'::jsonb`

All blocks are **optional** — simple funders omit them; complex funders populate relevant blocks.

### 3.1 Top-level keys

| Key | Type | Purpose |
|-----|------|---------|
| `document_title` | string | Override default export title |
| `header_fields` | array[object] | Fixed metadata fields on cover (project name, grant ref, period) |
| `rag` | object | RAG / traffic-light rating system (FCDO-class) — §3.2 |
| `logframe` | object | Logframe / results framework (FCDO-class) — §3.3 |
| `echo_blocks` | array[object] | ECHO Single Form block sequence (EU-class) — §3.4 |
| `value_for_money` | object | VfM narrative + metrics (FCDO-class) — §3.5 |
| `narrative_constraints` | object | Global constraints (voice, tense, person) |
| `extensions` | object | Funder-specific passthrough — NLCF/FCDO submission flags, scoring notes, source metadata (§3.7) |

### 3.2 `rag` block (complex — FCDO-class)

```json
{
  "enabled": true,
  "scale": ["GREEN", "AMBER", "RED"],
  "dimensions": [
    {
      "dimension_key": "delivery",
      "label": "Delivery",
      "guidance": "Rate progress against logframe milestones."
    }
  ],
  "require_justification_for": ["AMBER", "RED"]
}
```

When `enabled: false` or key absent, synthesis omits RAG tables.

### 3.3 `logframe` block (complex — FCDO-class)

```json
{
  "enabled": true,
  "levels": ["impact", "outcome", "output"],
  "columns": [
    {"column_key": "indicator", "label": "Indicator"},
    {"column_key": "baseline", "label": "Baseline"},
    {"column_key": "target", "label": "Target"},
    {"column_key": "actual", "label": "Actual"},
    {"column_key": "commentary", "label": "Commentary"}
  ],
  "source": "indicator_actuals_json"
}
```

### 3.4 `echo_blocks` block (complex — EU ECHO-class)

```json
[
  {
    "block_key": "context",
    "block_type": "narrative",
    "section_key": "context",
    "word_limit": 500
  },
  {
    "block_key": "results_table",
    "block_type": "table",
    "table_key": "results_indicators",
    "required": true
  }
]
```

Maps ECHO Single Form sections to internal `section_key` / table specs.

### 3.5 `value_for_money` block (complex — FCDO-class)

```json
{
  "enabled": true,
  "metrics": [
    {"metric_key": "cost_per_beneficiary", "label": "Cost per beneficiary", "required": false}
  ],
  "narrative_section_key": "value_for_money",
  "word_limit": 600
}
```

### 3.6 Simple funder expressiveness

Simple funders use:

```json
{
  "document_title": "Grant Progress Report",
  "narrative_constraints": {
    "voice": "first_person_plural",
    "tense": "past_for_activities_present_for_plans"
  }
}
```

No `rag`, `logframe`, `echo_blocks`, or `value_for_money` keys required.

### 3.7 `extensions` block (funder-specific passthrough)

Funder-specific flags that do not warrant schema migration live here:

```json
{
  "extensions": {
    "submission_style": "flexible_narrative_or_existing_report",
    "allows_existing_reports": true,
    "scoring_system": { "type": "five_point_output_scoring" },
    "source_note": "Reference-only metadata for builders"
  }
}
```

**Rule:** Known cross-funder concepts use first-class keys (`rag`, `logframe`, `value_for_money`). Everything else → `extensions`.

---

## 4. `terminology_map_json`

**Type:** JSON object — maps **canonical keys** → **funder-preferred labels**.

### 4.1 Structure

```json
{
  "canonical_to_funder": {
    "outputs": "Results",
    "outcomes": "Outcomes",
    "impact": "Long-term change",
    "beneficiaries": "People reached",
    "activities": "Deliverables"
  },
  "forbidden_terms": ["client", "vendor"],
  "preferred_terms": {
    "beneficiary": "participant"
  }
}
```

| Key | Type | Purpose |
|-----|------|---------|
| `canonical_to_funder` | object | Replace labels in synthesis output |
| `forbidden_terms` | array[string] | Humaniser/critic must not use |
| `preferred_terms` | object | Word-level replacements |

### 4.2 Simple vs complex usage

- **NLCF-class:** 3–5 entries in `canonical_to_funder`
- **FCDO-class:** full results-chain mapping + `forbidden_terms` for UK aid vocabulary

---

## 5. `docx_template_ref`

Not JSONB — TEXT column pointing to repo path:

```
app/reports/templates/docx/{template_slug}.docx
```

docxtpl context dict assembled from `content_json` + `format_rules_json` at export (Stage H).

---

## 6. Schema Stress-Test Results (Stage B-validation — COMPLETE)

Validated 2026-05-24 against [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json) and [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json).

| Criterion | Simple (NLCF) | Complex (FCDO) | Verdict |
|-----------|---------------|----------------|---------|
| Ordered narrative sections | ✓ 7 sections | ✓ 8 sections | **Pass** |
| Required indicators | ✓ flexible lists | ✓ logframe-linked | **Pass** |
| Tables | ✓ optional + 1 required budget | ✓ multi-column logframe/scoring | **Pass** |
| `conditional_display` | ✓ final section | not required | **Pass** |
| `evidence_rules` | ✓ proportionate | ✓ strict citation | **Pass** |
| Logframe block | absent (by design) | ✓ enabled in format_rules | **Pass** |
| RAG block | absent | disabled pending P0 template; section-level `rag_rating` columns | **Pass (deferred)** |
| VfM block | absent | ✓ enabled + dedicated section | **Pass** |
| Terminology map | ✓ `canonical_to_funder` | ✓ full results-chain | **Pass** |
| `format_rules_json.extensions` | ✓ NLCF submission flags | ✓ FCDO scoring/publication flags | **Pass** |

**P0 grantee material** (portal screenshots, FCDO DOCX, logframe XLSX) still improves Stage H export accuracy — not required for B-validation exit.

---

## 7. Relationship to Other Artefacts

- `DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md`
- `REPORT_INPUTS_FIELD_MAPPING.md`
- `OPENAI_PROMPTS_LIBRARY.md` (report archetypes — Stage F extension)
- `ME_MODULE_DECISION_LOG.md` D-006, D-021

---

## 8. Versioning

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-24 | Stage B structure lock; abstract schema; instances deferred to B-validation |
| 1.1.0 | 2026-05-24 | Add `conditional_display`, `evidence_rules` on sections; document `format_rules_json.extensions`; NLCF + FCDO instances validated |
