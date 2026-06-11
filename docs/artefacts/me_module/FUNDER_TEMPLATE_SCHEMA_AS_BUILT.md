# FUNDER_TEMPLATE_SCHEMA_AS_BUILT.md

**Status:** Ground-truth reference (as-built extraction)  
**Purpose:** Authoring guide for new `funder_report_templates` instances — extracted from schema doc, canonical instances, and runtime code only  
**Schema version (doc header):** 1.2.0  
**Extraction date:** 2026-06-08  
**Canonical instances:** [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json), [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json)  
**Schema contract:** [`FUNDER_TEMPLATE_SCHEMA.md`](FUNDER_TEMPLATE_SCHEMA.md)  
**DB contract:** [`DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md`](DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md)

---

## 0. How to use this document

This file records **what the engine actually does today**, not what plans say it should do. Where a plan document and the code disagree, the code wins; divergences are listed in §12.

Sources used (read-only):

- `docs/artefacts/me_module/FUNDER_TEMPLATE_SCHEMA.md` (header v1.2.0)
- `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`, `TEMPLATE_INSTANCE_NLCF.json`
- `docs/artefacts/ENUM_REGISTRY.md` §5.5
- `app/reports/gap/*`, `app/reports/services/*`, `app/reports/export/*`, `app/reports/reconciliation/*`
- `docs/artefacts/me_module/audits/P2_FUNDER_ROW_DELETION_PROPOSAL.md`, `P2_CORRECTIONS_FINDINGS.md`
- Test fixtures under `tests/fixtures/reconciler/`, `tests/fixtures/synthesis/`

---

## 1. Table-level scalar fields (`funder_report_templates`)

| Field | Type | Required | Allowed values / constraint | Default when absent | Validated where |
|-------|------|----------|----------------------------|---------------------|-----------------|
| `id` | UUID | YES (DB) | `gen_random_uuid()` | — | PostgreSQL PK |
| `funder_name` | TEXT | YES | Free text | — | UNIQUE with `template_name` |
| `template_name` | TEXT | YES | Free text | — | UNIQUE with `funder_name` |
| `region` | TEXT | YES | Free text (e.g. `UK`, `EU`) | — | None |
| `reporting_frequency` | TEXT | YES | `end_of_grant` \| `annual` \| `quarterly` \| `interim` \| `final` | — | PostgreSQL CHECK — `ENUM_REGISTRY.md` §5.5; migration `0014_me_module_tables.py` |
| `report_sections_json` | JSONB array | YES | Shape §2 below | `'[]'::jsonb` | **No inner-shape validation** |
| `format_rules_json` | JSONB object | YES | Shape §3 below | `'{}'::jsonb` | **No inner-shape validation** |
| `terminology_map_json` | JSONB object | YES | Shape §4 below | `'{}'::jsonb` | **No inner-shape validation** |
| `docx_template_ref` | TEXT | YES | Repo-relative path under `app/reports/templates/docx/` | — | File existence checked at export only (`docx_renderer.resolve_docx_template_path`) |
| `is_active` | BOOLEAN | YES | `true` \| `false` | `true` | List endpoint filters |
| `version` | INTEGER | YES | Positive integer | `1` | Convention only — bump on material template change |
| `created_at` / `updated_at` | TIMESTAMPTZ | YES | — | `now()` | DB |

**Production catalog IDs (manual inserts, not migration seeds):**

| Template | UUID |
|----------|------|
| FCDO Annual Review | `55f891ac-bb8b-4137-bc42-6de8ff935064` |
| NLCF Progress Update | `2d5d75b7-12f5-46b5-adaa-d5939a5249a8` |
| System sentinel (`__default__` / `__lifecycle_default__`) | `fc1a012b-f9c1-459f-a4b2-d71c18116068` |

Report creation against the sentinel template is blocked (`donor_report_lifecycle_service.is_system_funder_template`).

---

## 2. `report_sections_json` — full field reference (v1.2.0)

**Type:** ordered JSON array. **DB default:** `[]`.

### 2.1 Section object

| Field | Type | Required | Allowed values | Default when absent | Notes |
|-------|------|----------|----------------|---------------------|-------|
| `section_key` | string | **YES** | Unique slug within template | — | Sections without this key are **silently skipped** (`section_visibility.py`, `template_requirements.py`) |
| `label` | string | **YES** | Free text | Falls back to `section_key` in checklist | Used in gap UI, synthesis prompt, DOCX headings |
| `archetype` | string | **YES** | Convention string, e.g. `ARCH_PROGRESS_NARRATIVE`, `ARCH_EXECUTIVE_REVIEW_SUMMARY` | — | **Not** in `ENUM_REGISTRY.md`. FCDO archetypes have dedicated prompt rules in `app/reports/ai/prompts/synthesis.py`; NLCF archetypes fall back to generic rule |
| `word_limit` | integer \| null | NO | Positive integer or null | `null` = no hard limit in prompt | Passed to synthesis and `content_json_v1` |
| `tone` | string | NO | Free text | Omitted from prompt constraints | Serialized into synthesis user prompt |
| `required` | boolean | NO | `true` \| `false` | **`true`** | When `false` and no active `conditional_display`, section still shown unless condition hides it |
| `required_tables` | array | NO | Table specs (§2.2) | `[]` | Only tables with `min_rows >= 1` enter gap checklist |
| `required_indicators` | array[string] | NO | Indicator slug strings | `[]` | Slugs are template-author-defined; satisfaction uses `DATA_BACKED_HINTS` (§8) |
| `owner` | string | NO | `ngo` \| `funder` | **`ngo`** (implicit) | **v1.2.0 / P2.** `funder` sections excluded from NGO synthesis (`visible_sections_for_context(..., include_funder_owned=False)`) and NGO Gate 2 checklist |
| `requirement_type_default` | string | NO | `data` \| `narrative` \| `funder_supplied` | Resolved via fallbacks (§2.1a) | **v1.2.0 / P2.** Section-level default for indicators/tables without per-item override |
| `indicator_requirements` | object | NO | Keys = indicator slugs; values = `{owner?, requirement_type?}` | `{}` | **v1.2.0 / P2.** Per-indicator overrides |
| `table_requirements` | object | NO | Keys = `table_key`; values = `{owner?, requirement_type?}` | `{}` | **v1.2.0 / P2.** Per-table overrides |
| `guidance` | string | NO | Free text | — | Passed via full section JSON in synthesis prompt; not parsed separately |
| `conditional_display` | object | NO | §2.3 | Absent = always visible (subject to `required`) | **v1.1.0** |
| `evidence_rules` | object | NO | §2.4 | — | **v1.1.0** — **defined in schema and instances; not read by runtime code** |
| `extensions` | object | NO | Free-form | `{}` | Passthrough; not read by runtime |

#### 2.1a Owner / requirement_type resolution (as built)

Resolution order (`app/reports/gap/requirement_metadata.py`):

1. Per-item override in `indicator_requirements` / `table_requirements`
2. Section-level `owner` / `requirement_type_default`
3. Hardcoded FCDO fallbacks when template omits metadata:
   - `FUNDER_SUPPLIED_INDICATORS` frozenset (10 slugs including `output_scores`, `economy`, `FCDO_management_actions`, …)
   - `NARRATIVE_INDICATORS` frozenset (30+ slugs including `overall_progress`, `community_feedback`, …)
   - `FUNDER_OWNED_SECTIONS` = `{detailed_output_scoring, value_for_money}`
   - `FUNDER_SUPPLIED_TABLES` = `{output_score_table, vfm_measures}`

Invalid `owner` / `requirement_type` values (not in allowed sets) are **ignored**; resolution falls through to next level.

`is_ngo_checklist_item(owner, requirement_type)` returns `false` when `owner == "funder"` OR `requirement_type == "funder_supplied"`.

`funder_supplied` and `funder`-owned items are **auto-satisfied** in gap evaluation (`requirement_satisfaction.evaluate_requirement_satisfaction`).

### 2.2 Required table spec (`required_tables[]`)

| Field | Type | Required | Allowed values | Default when absent |
|-------|------|----------|----------------|---------------------|
| `table_key` | string | **YES** | Unique slug within section | — | Missing → table omitted from checklist |
| `label` | string | **YES** | Free text | — | DOCX sub-heading; gap display |
| `columns` | array[object] | **YES** (schema) | Column defs (§2.5) | — | **Not read at runtime** for gap/synthesis/export |
| `min_rows` | integer | NO | ≥ 0 | **`0`** | Tables with `min_rows < 1` **excluded** from gap checklist |
| `max_rows` | integer \| null | NO | Positive or null | `null` | **Not enforced** at runtime |
| `data_source` | string | NO | `indicators` \| `financials` \| `knowledge_bank` \| `manual` | — | Drives synthesis fact-prefix routing (`report_inputs_builder._TABLE_DATA_SOURCE_PREFIXES`) and logframe section resolution |

### 2.3 `conditional_display` (v1.1.0)

| Field | Type | Required | Allowed values | Default when absent |
|-------|------|----------|----------------|---------------------|
| `enabled` | boolean | **YES** when object present | `true` \| `false` | `false` behavior: section always shown |
| `condition` | string \| null | NO | Expression string | `null` | Only `"report_type == 'final'"` is evaluated (`section_visibility.section_visible`); **any other expression is ignored and section is shown** |

`report_type` comes from `report_context` dict; default **`"annual"`** when not supplied (`section_visibility.py`, `gap_analysis_json.report_context`). Not persisted on `donor_reports` (decision log 2026-06-04).

### 2.4 `evidence_rules` (v1.1.0 — contract only)

| Field | Type | Required | Allowed values |
|-------|------|----------|----------------|
| `claim_level_citation_required` | boolean | YES (schema) | `true` \| `false` |
| `numeric_claims_must_have_source` | boolean | YES (schema) | `true` \| `false` |
| `allowed_sources` | array[string] | YES (schema) | Subset of: `uploaded_documents`, `human_confirmed_gap_answers`, `knowledge_bank_facts` |

**Runtime:** No consumer reads `evidence_rules`. Fact-safety critic does not load template JSON.

### 2.5 Column definition (`columns[]`)

| Field | Type | Required | Allowed values | Default |
|-------|------|----------|----------------|---------|
| `column_key` | string | **YES** | Stable id | — |
| `label` | string | **YES** | Header text | — |
| `data_type` | string | NO | `text` \| `number` \| `date` \| `enum` \| `rag_rating` | `text` (convention) |
| `enum_values` | array[string] | NO | When `data_type` is `enum` or `rag_rating` | — |
| `required` | boolean | NO | `true` \| `false` | `false` |

**Runtime:** Column definitions are documentation/authoring metadata only in current engine.

---

## 3. `format_rules_json` — full field reference

**Type:** JSON object. **DB default:** `{}`. All top-level blocks are optional.

### 3.1 Top-level keys

| Key | Type | Purpose | Runtime consumed? |
|-----|------|---------|-------------------|
| `document_title` | string | Export cover title | **YES** — `docx_renderer.render_donor_report_docx` |
| `header_fields` | array[object] | Cover metadata fields | **NO** — passed to LLM prompts only |
| `rag` | object | RAG rating system (§3.2) | **NO** — passed to LLM prompts only |
| `logframe` | object | Logframe block (§3.3) | **`logframe.enabled` only** — `logframe_completeness.is_logframe_enabled` |
| `echo_blocks` | array[object] | ECHO Single Form mapping (§3.4) | **NO** |
| `value_for_money` | object | VfM metrics block (§3.5) | **NO** — passed to LLM prompts only |
| `narrative_constraints` | object | Global voice/tense rules | **NO** — passed to LLM prompts only |
| `extensions` | object | Funder-specific passthrough | **NO** |

### 3.2 `rag` block

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `enabled` | boolean | `false` when absent | FCDO instance sets `enabled: false` with note; section-level `rag_rating` columns used instead |
| `scale` | array[string] | — | Not consumed |
| `dimensions` | array[object] | — | Not consumed |
| `require_justification_for` | array[string] | — | Not consumed |

### 3.3 `logframe` block

| Field | Type | Default | Consumed |
|-------|------|---------|----------|
| `enabled` | boolean | `false` | **YES** — gates `derive_missing_logframe_actuals` |
| `levels` | array[string] | — | Not consumed |
| `columns` | array[object] | — | Not consumed |
| `source` | string | — | Not consumed (convention: `indicator_actuals_json`) |

When `logframe.enabled: true`, engine derives additional checklist items `logframe_row:op{N}_{N}` for proposal targets missing indicator-data actuals (`logframe_completeness.py`).

### 3.4 `echo_blocks` block

Array of `{block_key, block_type, section_key?, table_key?, word_limit?, required?}`. **Not consumed** at runtime.

### 3.5 `value_for_money` block

| Field | Type | Notes |
|-------|------|-------|
| `enabled` | boolean | Not consumed (FCDO instance: `true`) |
| `metrics` | array[object] | `{metric_key, label, required?}` — not consumed |
| `narrative_section_key` | string | Not consumed |
| `word_limit` | integer | Not consumed |

### 3.6 `narrative_constraints` block

Free-form object (e.g. `voice`, `tense`, `learning_focus`, `strict_word_limits`). **Passed to synthesis LLM** via `report_inputs.template.format_rules_json`; not parsed server-side.

### 3.7 `extensions` block

Free-form funder metadata (submission flags, scoring notes, publication rules). **Not consumed** by gap/synthesis/export logic.

---

## 4. `terminology_map_json` — full field reference

| Key | Type | Required | Runtime consumed? |
|-----|------|----------|-------------------|
| `canonical_to_funder` | object (canonical → funder label) | NO (but expected) | **YES** — `docx_renderer._terminology_substitutions` (word-boundary regex replace on headings and body); also passed to synthesis/gap LLM prompts |
| `forbidden_terms` | array[string] | NO | **NO** |
| `preferred_terms` | object | NO | **NO** |

---

## 5. Validation reality

### 5.1 What is enforced

| Layer | What | Where | On failure |
|-------|------|-------|------------|
| PostgreSQL | `reporting_frequency` enum | `0014_me_module_tables.py` CHECK | INSERT/UPDATE rejected |
| PostgreSQL | UNIQUE `(funder_name, template_name)` | migration | INSERT rejected |
| Application | Block report create on sentinel template | `donor_report_lifecycle_service` | HTTP error |
| Gap pipeline | `owner` / `requirement_type` enum membership | `requirement_metadata.py` | Invalid values ignored; fallbacks apply |
| Gap pipeline | `conditional_display.condition` | `section_visibility.py` | Unknown conditions → section shown |
| Gap pipeline | Section/table skip rules | `template_requirements.py` | Silent omission |
| Gap pipeline | Data-ref satisfaction | `requirement_satisfaction.py` | Unmapped slug → **unsatisfied gap** (`suggested_action: "provide"`) |
| Gap output | LLM gap `item_key` ∈ checklist | `gap_compliance_v1.validate_gap_compliance_output` | Gap rejected / merge corrected |
| Gap output | Pydantic enums on persisted gaps | `GapComplianceGapItem` | Validation error on persist |
| Export | DOCX template file exists | `docx_renderer.resolve_docx_template_path` | Falls back or errors |

### 5.2 What is convention only (not validated at ingest)

- Entire inner shape of `report_sections_json`, `format_rules_json`, `terminology_map_json`
- `archetype` string validity (unknown archetype → generic synthesis rule)
- `required_indicators` slug naming
- `evidence_rules`, `forbidden_terms`, `preferred_terms`
- `columns[]`, `data_type`, `enum_values` on tables
- `format_rules_json` sub-blocks except `logframe.enabled` and `document_title` at export
- Template `version` INTEGER vs schema doc version (1.2.0)

### 5.3 Unknown fields

Extra keys at any level are **stored and passed through** (e.g. to LLM prompts as serialized JSON). No reject-on-unknown behavior.

---

## 6. Consumption map

One line per schema field → engine component → behavior.

### 6.1 `report_sections_json` section fields

| Field | Consumer | Behavior |
|-------|----------|----------|
| `section_key` | `template_requirements.enumerate_template_requirements` | Checklist identity; synthesis/export section order |
| `label` | `template_requirements`, `docx_renderer`, `gap_compliance_agent` | Human-facing labels |
| `archetype` | `report_inputs_builder._fact_prefixes_for_section`, `synthesis.archetype_rule_for` | Fact-namespace trim; prompt structure rules (FCDO archetypes only have explicit rules) |
| `word_limit` | `report_synthesis_service`, `content_json_v1` | Synthesis constraint |
| `tone` | `synthesis.build_synthesis_user_prompt` | Prompt text |
| `required` | `section_visibility.section_visible` | Default visibility when no conditional |
| `required_indicators[]` | `template_requirements`, `report_inputs_builder._indicator_match_tokens` | Gap checklist items; fact token matching |
| `required_tables[]` | `template_requirements`, `report_inputs_builder`, `docx_renderer`, `logframe_completeness.resolve_logframe_output_section` | Gap checklist (if `min_rows >= 1`); fact prefixes via `data_source`; export table headings |
| `owner` | `requirement_metadata.resolve_owner`, `section_visibility.visible_sections_for_context` | Gate 2 filtering; synthesis exclusion when `funder` |
| `requirement_type_default` | `requirement_metadata.resolve_requirement_type` | Default typing for checklist items |
| `indicator_requirements` | `requirement_metadata._indicator_meta` | Per-indicator owner/type overrides |
| `table_requirements` | `requirement_metadata._table_meta` | Per-table owner/type overrides |
| `conditional_display` | `section_visibility.section_visible` | Hide/show sections by `report_type` |
| `guidance` | `synthesis` (via serialized section JSON) | LLM context only |
| `evidence_rules` | — | **Not consumed** |
| `extensions` | — | **Not consumed** |

### 6.2 Table sub-fields

| Field | Consumer | Behavior |
|-------|----------|----------|
| `table_key` | `template_requirements` | Checklist item ref; satisfaction token match |
| `label` | `docx_renderer` | Table sub-heading in export |
| `min_rows` | `template_requirements` | `>= 1` required for checklist inclusion |
| `data_source` | `report_inputs_builder`, `logframe_completeness` | `indicators`/`financials` fact prefixes; logframe section pick |
| `columns[]` | — | **Not consumed** at runtime |

### 6.3 `format_rules_json`

| Field | Consumer | Behavior |
|-------|----------|----------|
| `document_title` | `docx_renderer` | Cover title |
| `logframe.enabled` | `logframe_completeness.is_logframe_enabled` | Derive `logframe_row:*` gaps |
| All other keys | `report_inputs_builder`, `gap_compliance_agent` | Serialized into LLM context only |

### 6.4 `terminology_map_json`

| Field | Consumer | Behavior |
|-------|----------|----------|
| `canonical_to_funder` | `docx_renderer`, synthesis/gap LLM inputs | Word substitution on export; prompt context |
| `forbidden_terms` | — | **Not consumed** |
| `preferred_terms` | — | **Not consumed** |

---

## 7. Fact-key namespace reference

Knowledge-bank `facts` keys are chosen by the **reconciler LLM** from deterministic **candidates** built by `input_builder.py`. Hint-map authoring (§8) must target these emitted shapes.

### 7.1 Candidate grammar (pre-reconciler)

| Namespace | Pattern | Example `field_path` |
|-----------|---------|---------------------|
| Grant terms | `{name}` | `funder`, `grant_reference` |
| Grant terms | `award_budget.{amount\|currency}` | `award_budget.amount` |
| Grant terms | `{grant_period\|reporting_period}.{start\|end}` | `grant_period.start` |
| Grant terms | `reporting_obligations[{i}]` | `reporting_obligations[0]` |
| Grant terms | `reporting_deadlines[{i}]` | `reporting_deadlines[0]` |
| Proposal objectives | `objectives.{objective_key}` | `objectives.impact_girls_basic_education` |
| Proposal indicators | `indicators.{indicator_key}.target` | `indicators.ocm1_attendance_80pct.target` |
| Indicator data rows | `indicators.{row_id}.{target\|actual}` | `indicators.op1_1.actual` |
| Financials | `financials.currency` | `financials.currency` |
| Financials lines | `financials.lines.{line_key}.{budget\|actual}` | `financials.lines.op1_1.y1_actual` |

### 7.2 Reconciled KB keys (post-E1)

Reconciler stores LLM-chosen `fact_key` verbatim. Real examples from `tests/fixtures/reconciler/recorded/fcdo_bridgelight_recorded_knowledge_bank.json`:

```
objectives.impact_girls_basic_education
objectives.outcome_retention_attendance_continuity
indicators.ocm1_attendance_80pct.target
indicators.ocm1_attendance_80pct.actual
indicators.op1_1_girls_reenrolled.target
financials.total_programme_budget.actual_spend
financials.total_programme_budget.budget
```

Synthesis-trimmed namespace from `tests/fixtures/synthesis/bridgelight_6643d922_cited_keys.json` (reconciler may flatten grant paths):

```
grant.funder
grant.reference
grant.period.end
indicators.op1_1.actual
financials.lines.op1_1.y1_actual
financials.lines.op1_1.y1_budget
```

### 7.3 Target vs actual facets (gap/logframe)

`logframe_completeness.py` classifies facets:

- **Target facets:** `.target`, `.proposal_target`, `ar1_target`, `.milestone`, `_milestone_target`
- **Actual facets:** `.actual`, `ar1_actual`, `_actual` (excluding target-like keys)
- **Indicator ID regex:** `op(\d+)_(\d+)` → canonical `op1_1`
- **Derived gap refs:** `logframe_row:op1_1`

### 7.4 Degraded path

When reconciliation degrades: `degraded_pass_through:{candidate_id}` (`degrade_resilience.py`).

### 7.5 Narrative-support keys

Narrative requirements (`requirement_type: "narrative"`) are satisfied when any citable fact key **contains the normalized section_key token** (`requirement_satisfaction._section_has_citable_facts`), or when the item is typed `indicator` under a narrative section (auto-satisfied). No separate narrative namespace — authors rely on section-scoped fact presence.

---

## 8. Hint-map contract (`DATA_BACKED_HINTS`)

### 8.1 Location and shape

**Canonical definition:** `app/reports/gap/requirement_satisfaction.py` → `DATA_BACKED_HINTS`

```python
DATA_BACKED_HINTS: dict[str, list[str]] = {
    "actual_results": ["ar1_actual", "indicators."],
    "output_indicators": ["indicators.", "ar1_milestone_target"],
    # ... 14 slugs total
}
```

**Shape:** `required_item_ref` (indicator slug from template) → list of **substring hints** matched against citable KB `fact_key` values (case-sensitive substring: `hint in fact_key`).

**Audit subset:** `scripts/audit/analyze_run.py` duplicates a subset for run analysis — not authoritative for authoring.

### 8.2 Full slug map (as built)

| `required_item_ref` | Hint substrings |
|---------------------|-----------------|
| `actual_results` | `ar1_actual`, `indicators.` |
| `output_indicators` | `indicators.`, `ar1_milestone_target` |
| `outcome_indicators` | `indicators.`, `proposal_target` |
| `logframe_milestones` | `ar1_milestone_target` |
| `progress_against_expected_results` | `ar1_actual`, `ar1_milestone_target` |
| `forecast_vs_actual_costs` | `financials.lines`, `financials.` |
| `forecast_vs_actual_spend` | `financials.lines`, `financials.` |
| `financial_delivery` | `financials.lines`, `financials.` |
| `cost_drivers` | `financials.lines`, `financials.` |
| `beneficiary_numbers` | `indicators.`, `beneficiar` |
| `outcome_indicators_where_available` | `indicators.`, `outcome` |
| `review_summary_sheet` | `programme_title`, `programme_code`, `review_date` |
| `outcome_assessment` | `indicators.`, `outcome` |
| `delivery_financial_performance` | `financials.` |

**Table satisfaction** (`_table_satisfied`): normalised `table_key` token matched as substring in `fact_key` or `semantic_label` — no separate hint map.

**Logframe row refs** (`logframe_row:op1_1`): satisfied via `has_indicator_data_actual_for_id` — not hint map.

### 8.3 Adding mappings for a new funder

1. For each **data-typed** `required_indicators` slug, add an entry to `DATA_BACKED_HINTS` in `requirement_satisfaction.py` pointing at KB fact-key substrings the extractors/reconciler emit for that funder's documents.
2. Optionally add slugs to `NARRATIVE_INDICATORS` or `FUNDER_SUPPLIED_INDICATORS` in `requirement_metadata.py` if using fallbacks without per-template `indicator_requirements`.
3. Add pytest coverage mirroring `tests/test_gap_compliance_agent.py::test_unmapped_data_ref_emits_gap`.

**There is no template-JSON field for hint maps** — hints are engine code, not per-template JSON.

### 8.4 Unmapped data ref behavior

When `requirement_type == "data"` and `required_item_ref` is **not** in `DATA_BACKED_HINTS` (and not `logframe_row:*`):

1. `evaluate_requirement_satisfaction` returns `satisfied=False`, `suggested_action="provide"`
2. Item appears in Gate 2 gap checklist
3. NGO must answer via gap responses or upload documents that populate matching KB facts

Confirmed by `tests/test_gap_compliance_agent.py::test_unmapped_data_ref_emits_gap`.

**New templates must either:** (a) reuse slugs already in `DATA_BACKED_HINTS`, or (b) extend the hint map in code before expecting data gaps to auto-close.

---

## 9. Annotated exemplars

### 9.1 FCDO (`TEMPLATE_INSTANCE_FCDO.json`)

**Schema-required structure (same for any funder):**

- 8 ordered sections with `section_key`, `label`, `archetype`, `required_indicators`, `required_tables`, `evidence_rules`, `conditional_display`
- `format_rules_json` with `document_title`, `logframe.enabled: true`, `value_for_money`, `narrative_constraints`, `extensions`
- `terminology_map_json.canonical_to_funder` (12 entries)
- `reporting_frequency: "annual"` (ENUM_REGISTRY §5.5)
- `docx_template_ref: "app/reports/templates/docx/fcdo-annual-review.docx"`

**Funder-specific data (FCDO content choices):**

| Pattern | Example in instance |
|---------|---------------------|
| Section slugs / labels | `summary_and_overview`, `performance_and_conclusions`, … |
| Indicator slugs | `overall_progress`, `actual_results`, `output_scores`, … |
| Table slugs | `review_summary_sheet`, `output_score_table`, `vfm_measures` |
| Archetypes | `ARCH_EXECUTIVE_REVIEW_SUMMARY`, `ARCH_OUTPUT_SCORING_TABLE`, … |
| Logframe columns | impact/outcome/output levels in `format_rules_json.logframe` |
| Terminology | `results_framework` → `Results framework / logframe` |
| Extensions | FCDO scoring system, DevTracker publication flags |

**P2 funder-owned tagging (v1.2.0 — runtime filter, rows still present in repo instance):**

| Section | `owner` | `requirement_type_default` | Funder-supplied items |
|---------|---------|---------------------------|----------------------|
| `detailed_output_scoring` | `funder` | `data` | `impact_weightings`, `risk_ratings`, `output_scores` via `indicator_requirements` |
| `value_for_money` | `funder` | `narrative` | `economy`, `efficiency`, `effectiveness`, `equity`, `vfm_measures` table |
| `programme_management_delivery_commercial_financial` | (default `ngo`) | — | `FCDO_management_actions` only |

NGO-side items in funder-owned sections remain in checklist, e.g. `actual_results`, `cost_drivers`, `forecast_vs_actual_costs` with explicit `{owner: "ngo", requirement_type: "data"}`.

**Slated for deletion (prod template row only — not yet executed):**

Per `P2_FUNDER_ROW_DELETION_PROPOSAL.md`, these **template definition** entries will be removed from prod row `55f891ac…`:

- Sections: `detailed_output_scoring`, `value_for_money`
- Indicators: `output_scores`, `impact_weightings`, `risk_ratings`, `economy`, `efficiency`, `effectiveness`, `equity`, `commercial_improvement_where_relevant`, `FCDO_management_actions`
- Tables: `output_score_table`, `vfm_measures`

**New templates must NOT include funder-owned requirements.** Author NGO-side content only. Runtime `owner`/`requirement_type` fields remain in schema for defense-in-depth after deletion.

### 9.2 NLCF (`TEMPLATE_INSTANCE_NLCF.json`)

**Schema-required structure:**

- 7 ordered sections; same core section fields as §2.1
- `format_rules_json`: `document_title`, `narrative_constraints`, `extensions` only (no logframe/rag/vfm)
- `terminology_map_json`: 8 `canonical_to_funder` entries
- `reporting_frequency: "annual"` — **not** composite `annual_or_end_of_grant` (D-022)

**Funder-specific data:**

| Pattern | Example |
|---------|---------|
| Plain-language section labels | `"The story of your project this year"` |
| NLCF archetypes | `ARCH_PROGRESS_NARRATIVE`, `ARCH_LEARNING_REFLECTION`, … (no dedicated prompt rules — generic fallback) |
| Indicator slugs | `community_participation_examples`, `what_worked`, `budgeted_total`, … |
| Budget table | `budget_vs_actual` with `data_source: "financials"`, `min_rows: 1` |
| Extensions | NLCF submission flexibility, £20k/2yr annual trigger note |

**`conditional_display` (only conditional section in either exemplar):**

```json
{
  "section_key": "final_update_only",
  "required": false,
  "conditional_display": {
    "enabled": true,
    "condition": "report_type == 'final'"
  }
}
```

- When `report_context.report_type` is `"annual"` (default): section **hidden** from checklist and synthesis
- When `"final"`: section **included**; indicators `overall_project_reflection`, `unshared_evidence_or_learning`, `unspent_funds_status` enter NGO checklist
- `report_type` is not yet persisted on `donor_reports`; engine defaults to `"annual"`

**No P2 owner tags** — all sections NGO-facing.

---

## 10. Authoring checklist

Minimal decisions to produce a valid new template instance:

### 10.1 Required decisions

| # | Decision | Guidance |
|---|----------|----------|
| 1 | **Catalog metadata** | `funder_name`, `template_name`, `region`, `reporting_frequency` (ENUM_REGISTRY §5.5 only) |
| 2 | **Section roster** | Ordered `report_sections_json[]` with unique `section_key`, `label`, `archetype` per section |
| 3 | **Archetypes** | Use existing `ARCH_*` strings where possible; unknown archetypes get generic synthesis rules |
| 4 | **Word limits & tone** | Per-section `word_limit`, `tone` (optional) |
| 5 | **Required indicators** | Slug list per section; map each **data** slug in `DATA_BACKED_HINTS` (§8) or accept Gate 2 asks |
| 6 | **Required tables** | `table_key`, `label`, `columns[]`, `min_rows` (≥1 for checklist), `data_source` |
| 7 | **Requirement typing** | Set `owner`, `requirement_type_default`, `indicator_requirements`, `table_requirements` for any non-default items — **do not author funder-owned rows** (P2) |
| 8 | **Conditionality** | `conditional_display` only if needed; only `report_type == 'final'` works today |
| 9 | **Format rules** | At minimum `document_title`; set `logframe.enabled: true` only if logframe-row gaps desired |
| 10 | **Terminology** | `canonical_to_funder` map for export label substitution |
| 11 | **DOCX ref** | `docx_template_ref` pointing to file under `app/reports/templates/docx/` |
| 12 | **Hint map (code)** | Extend `DATA_BACKED_HINTS` for new data indicator slugs |
| 13 | **Version bump** | Increment template `version` INTEGER on material change |

### 10.2 Known invalid patterns

| Pattern | Why invalid |
|---------|-------------|
| `reporting_frequency: "annual_or_end_of_grant"` | Not in ENUM_REGISTRY §5.5; fails DB CHECK (D-022) |
| Funder-owned sections/indicators/tables in new templates | P2 policy — runtime filter exists but new templates must be NGO-only |
| Data indicator slug with no `DATA_BACKED_HINTS` entry and no `logframe_row:` prefix | Permanent Gate 2 gap until hint map extended |
| `conditional_display.condition` other than `report_type == 'final'` | Ignored — section always shown |
| Tables with `min_rows: 0` expecting gap enforcement | Excluded from checklist |
| Relying on `evidence_rules` for critic behavior | Not wired — critic ignores template |
| Relying on `forbidden_terms` / `preferred_terms` | Not wired |
| Assuming `format_rules_json.rag` or `value_for_money` drive server logic | LLM context only (except `logframe.enabled`) |

### 10.3 Post-authoring verification

1. Insert row (manual — no Alembic seed); validate `reporting_frequency` CHECK
2. Run gap enumeration tests with instance JSON
3. Run `scripts/audit/phase2_owner_validation.py` if FCDO-class
4. Confirm each data slug has hint coverage or expected gap behavior

---

## 11. `docx_template_ref`

| Aspect | As built |
|--------|----------|
| Type | TEXT, not JSONB |
| Path convention | `app/reports/templates/docx/{slug}.docx` |
| Resolution | `docx_renderer.resolve_docx_template_path` — repo-relative from backend root |
| Context assembly | `content_json` sections + `format_rules_json.document_title` + terminology substitutions |

---

## 12. Plan / code divergences

| Topic | Plan / schema doc says | Code / instances as built |
|-------|------------------------|---------------------------|
| Schema version | `FUNDER_TEMPLATE_SCHEMA.md` header **1.2.0** | §8 changelog stops at **1.1.0** — no 1.2.0 changelog row |
| P2 owner fields | Documented in schema §2.1 | `REPORT_INPUTS_FIELD_MAPPING.md` does not map `owner` / `requirement_type` fields |
| `evidence_rules` | v1.1.0 first-class section field; instances populated | **No runtime consumer**; critic does not read template |
| `forbidden_terms` / `preferred_terms` | Schema §4 | **Not consumed** |
| `report_type` | NLCF conditional sections depend on it | Default `"annual"` only; **not persisted** on `donor_reports` (decision 2026-06-04) |
| FCDO prod row `55f891ac` | Repo instance has P2 owner tags | Prod row may **predate P2 tags** unless manually updated (`P2_CORRECTIONS_FINDINGS.md`, `me_capture/230290ce/template.json`) |
| FCDO funder-owned rows | `P2_FUNDER_ROW_DELETION_PROPOSAL.md` proposes deletion | Repo `TEMPLATE_INSTANCE_FCDO.json` **still contains** funder-owned sections for defense-in-depth testing |
| Template seeding | `DB_FIELD_CONTRACT` mentions Stage H seeding | **No Alembic seed** — FCDO/NLCF manually inserted |
| `DATA_BACKED_HINTS` | Implied template-driven satisfaction | **Hardcoded Python dict** — not in template JSON |
| NLCF archetypes | Listed in instance | **No dedicated synthesis prompt rules** — generic fallback |
| `format_rules_json` blocks | Schema describes rag/vfm/echo | Only `logframe.enabled` and `document_title` affect server behavior |
| Column `data_type` / `enum_values` | Schema §2.3–2.5 | **Not enforced** at runtime |
| Archetype enum | Schema requires `archetype` string | **No closed enum** in `ENUM_REGISTRY.md` |

---

## 13. Related artefacts

- [`FUNDER_TEMPLATE_SCHEMA.md`](FUNDER_TEMPLATE_SCHEMA.md) — canonical schema contract (header v1.2.0)
- [`DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md`](DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md) — table columns
- [`REPORT_INPUTS_FIELD_MAPPING.md`](REPORT_INPUTS_FIELD_MAPPING.md) — synthesis input mapping (pre-P2 fields)
- [`ENUM_REGISTRY.md`](../ENUM_REGISTRY.md) §5.5 — `reporting_frequency`
- [`audits/P2_FUNDER_ROW_DELETION_PROPOSAL.md`](audits/P2_FUNDER_ROW_DELETION_PROPOSAL.md) — prod deletion scope
- [`audits/P2_CORRECTIONS_FINDINGS.md`](audits/P2_CORRECTIONS_FINDINGS.md) — P2 validation state

---

*As-built extraction only. No schema or code changes implied.*
