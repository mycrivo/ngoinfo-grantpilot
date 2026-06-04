# M&E data model & funder-template future-proofing audit

**Date:** 2026-06-04  
**Mode:** Read-only (no schema, code, or DB changes)  
**Canonical sources read:** `app/reports/models/*.py`, `alembic/versions/0014_me_module_tables.py`, `alembic/versions/0015_donor_reports_gap_analysis_json.py`, four `DB_FIELD_CONTRACT_*.md`, `FUNDER_TEMPLATE_SCHEMA.md`, `TEMPLATE_INSTANCE_NLCF.json`, `TEMPLATE_INSTANCE_FCDO.json`, `WORKSTREAM_T2_NLCF_FCDO_REFERENCE_TEMPLATES.md`, `ENUM_REGISTRY.md` §5, `API_CONTRACT.md` §12, `ME_MODULE_MASTER_MEMORY.md` (data-model sections)

---

## Verdict

The **four M&E tables are structurally sound for a template-catalog model**: funder-specific layout lives in JSONB on `funder_report_templates`, and NLCF + FCDO reference instances fit that JSON shape with no missing top-level columns. **They are not 10-funder-ready under the strict claim “funders 3–10 = pure template-row inserts, zero schema change, zero new branching code.”** PostgreSQL `CHECK` constraints on closed vocabularies (`reporting_frequency`, document `classification`, job `stage`/`status`, report `status`), a **single** `(reporting_period_start, reporting_period_end)` pair per report, and **code-side** limits (one `conditional_display` expression, `report_type` not persisted on `donor_reports`) will force migration or application changes for milestone cadences, new upload types, multi-period/consolidated reports, and non-trivial conditional sections. **Contract docs lag code** on `gap_analysis_json`, migration status, and `agent_trace_json` shape. **Production template rows were not queried in this pass** — confirm via checklist below.

---

## 1. Actual shape (code + migrations canonical)

Alembic head: `0015_gap_analysis_json` (revises `0014_me_module_tables`).  
Migration parity test (`tests/test_me_module_migration_parity.py`): **passes** (models ↔ 0014/0015 columns).

SQLAlchemy models define columns only; **CHECK constraints, UNIQUE, and indexes exist in migration 0014**, not in model `__table_args__`.

### 1.1 `funder_report_templates`

| Column | Type | Null | Default | Constraints / indexes |
|--------|------|------|---------|------------------------|
| `id` | UUID | NO | `gen_random_uuid()` | PK |
| `funder_name` | TEXT | NO | — | UNIQUE with `template_name` (`uq_funder_report_templates_funder_template`) |
| `template_name` | TEXT | NO | — | UNIQUE with `funder_name` |
| `region` | TEXT | NO | — | idx `(region, is_active)` |
| `reporting_frequency` | TEXT | NO | — | CHECK: `end_of_grant`, `annual`, `quarterly`, `interim`, `final` |
| `report_sections_json` | JSONB | NO | `'[]'::jsonb` | — |
| `format_rules_json` | JSONB | NO | `'{}'::jsonb` | — |
| `terminology_map_json` | JSONB | NO | `'{}'::jsonb` | — |
| `docx_template_ref` | TEXT | NO | — | — |
| `is_active` | BOOLEAN | NO | `true` | partial idx WHERE `is_active = true` |
| `version` | INTEGER | NO | `1` | — |
| `created_at` | TIMESTAMPTZ | NO | `now()` | — |
| `updated_at` | TIMESTAMPTZ | NO | `now()` | — |

**FKs:** none (inward FK from `donor_reports` only).

### 1.2 `donor_reports`

| Column | Type | Null | Default | Constraints / indexes |
|--------|------|------|---------|------------------------|
| `id` | UUID | NO | `gen_random_uuid()` | PK |
| `user_id` | UUID | NO | — | FK → `users.id` ON DELETE CASCADE |
| `funder_report_template_id` | UUID | NO | — | FK → `funder_report_templates.id` ON DELETE RESTRICT; idx |
| `linked_proposal_id` | UUID | YES | NULL | FK → `proposals.id` ON DELETE SET NULL; partial idx |
| `reporting_period_start` | DATE | NO | — | CHECK `reporting_period_end >= reporting_period_start` |
| `reporting_period_end` | DATE | NO | — | same CHECK |
| `status` | TEXT | NO | `'DRAFT'` | CHECK: `DRAFT`, `EXTRACTING`, `AWAITING_REVIEW`, `GENERATING`, `DEGRADED`, `COMPLETE` |
| `knowledge_bank_json` | JSONB | NO | `'{}'::jsonb` | — |
| `gap_analysis_json` | JSONB | NO | `'{}'::jsonb` | added in **0014**; 0015 is idempotent re-add if missing |
| `indicator_actuals_json` | JSONB | NO | `'{}'::jsonb` | — |
| `content_json` | JSONB | NO | `'{}'::jsonb` | — |
| `version` | INTEGER | NO | `1` | — |
| `created_at` | TIMESTAMPTZ | NO | `now()` | — |
| `updated_at` | TIMESTAMPTZ | NO | `now()` | — |

**Indexes:** `(user_id, created_at DESC)`, `(user_id, status)`, `(funder_report_template_id)`, `(linked_proposal_id)` WHERE NOT NULL.

### 1.3 `uploaded_documents`

| Column | Type | Null | Default | Constraints / indexes |
|--------|------|------|---------|------------------------|
| `id` | UUID | NO | `gen_random_uuid()` | PK |
| `donor_report_id` | UUID | NO | — | FK → `donor_reports.id` CASCADE |
| `user_id` | UUID | NO | — | FK → `users.id` CASCADE; idx |
| `storage_ref` | TEXT | NO | — | — |
| `original_filename` | TEXT | NO | — | — |
| `mime_type` | TEXT | NO | — | — |
| `size_bytes` | BIGINT | NO | — | CHECK `size_bytes > 0` |
| `classification` | TEXT | YES | NULL | CHECK nullable: `proposal`, `grant_letter`, `mou`, `indicator_data`, `photo`, `deck`, `other` |
| `extracted_json` | JSONB | NO | `'{}'::jsonb` | — |
| `extraction_status` | TEXT | NO | `'PENDING'` | CHECK: `PENDING`, `PROCESSING`, `COMPLETE`, `FAILED` |
| `created_at` | TIMESTAMPTZ | NO | `now()` | — |

**No `updated_at`** (matches contract).

**Indexes:** `(donor_report_id, created_at)`, `(user_id)`, `(donor_report_id, classification)`.

### 1.4 `report_jobs`

| Column | Type | Null | Default | Constraints / indexes |
|--------|------|------|---------|------------------------|
| `id` | UUID | NO | `gen_random_uuid()` | PK |
| `donor_report_id` | UUID | NO | — | FK → `donor_reports.id` CASCADE |
| `stage` | TEXT | NO | `'classify'` | CHECK: `classify`, `extract`, `reconcile`, `gap`, `synthesise`, `critique`, `export` |
| `status` | TEXT | NO | `'queued'` | CHECK: `queued`, `running`, `awaiting_human`, `failed`, `done` |
| `agent_trace_json` | JSONB | NO | `'{}'::jsonb` | — |
| `error` | TEXT | YES | NULL | — |
| `started_at` | TIMESTAMPTZ | YES | NULL | — |
| `finished_at` | TIMESTAMPTZ | YES | NULL | — |

**Indexes:** `(donor_report_id, started_at DESC)`, `(status)` partial active statuses, `(donor_report_id)`.

### 1.5 Python enums (`app/reports/models/enums.py`)

Mirror CHECK values for: `DonorReportStatus`, `ReportingFrequency`, `DocumentClassification`, `ExtractionStatus`, `ReportJobStage`, `ReportJobStatus`. **Not enforced at ORM layer** — DB CHECK is authoritative.

---

## 2. Contract drift

| # | Finding | Canonical | Drifting artefact |
|---|---------|-----------|-------------------|
| D1 | **`gap_analysis_json` column missing** from donor_reports field contract and master memory table list | Model + 0014/0015 | `DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.5; `ME_MODULE_MASTER_MEMORY.md` §318 |
| D2 | **`gap_analysis_json` shape undocumented** in field contracts (runtime shape in `app/reports/schemas/gap_compliance_v1.py`) | Code (`GapCompliancePersistedEnvelope` / flattened persist) | Field contracts; `API_CONTRACT.md` §12.9 (detail response omits column) |
| D3 | **Migration status stale** — contracts say 0014 “not yet applied” | Deployed prod + alembic head `0015_gap_analysis_json` | All four `DB_FIELD_CONTRACT_*.md` headers |
| D4 | **`agent_trace_json` shape** — contract documents `runs[]` array; orchestrator writes **`stages{}`** map keyed by pipeline stage | `app/reports/orchestration/pipeline.py`, worker | `DB_FIELD_CONTRACT_REPORT_JOBS.md` §2.4 |
| D5 | **0015 revision id vs filename** — file `0015_donor_reports_gap_analysis_json.py`, revision string `0015_gap_analysis_json` | Alembic revision table | Filename (cosmetic; chain works) |
| D6 | **0015 redundant on fresh install** — `gap_analysis_json` already in 0014 `create_table`; 0015 only adds if column absent | 0014 migration | 0015 (harmless idempotency) |
| D7 | **Constraints/indexes not mirrored in models** — UNIQUE/CHECK/index definitions live only in migration | 0014 migration | SQLAlchemy models (expected pattern; document only) |
| D8 | **`GET /api/reports/{id}`** contract lists `knowledge_bank_json`, `indicator_actuals_json`, `content_json` but not `gap_analysis_json` | Model + gap services | `API_CONTRACT.md` §12.9 |
| D9 | **Gate mapping nuance** — contract says Gate 1 halt at `reconcile`; prod walks halt at `stage=gap` with `awaiting_human` after Gate 1 confirm | Observed job stages in prod | `DB_FIELD_CONTRACT_REPORT_JOBS.md` §2.2 gate table (informative drift) |

All other column names, types, nullability, defaults, and FK directions **match** contracts and `FUNDER_TEMPLATE_SCHEMA.md` top-level template columns.

---

## 3. Full exercise — NLCF + FCDO vs `FUNDER_TEMPLATE_SCHEMA.md`

Reference instances inspected:  
`docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` (7 sections),  
`docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` (8 sections).

### 3.1 Top-level template columns — fully exercised

Both instances populate every **table column** on `funder_report_templates`: metadata, all three JSONB blobs, `docx_template_ref`, `is_active`, `version`.

### 3.2 `report_sections_json` — exercised vs unused schema fields

| Schema field | NLCF | FCDO | Notes |
|--------------|------|------|-------|
| `section_key`, `label`, `archetype`, `required` | ✓ | ✓ | Core path |
| `word_limit`, `tone` | ✓ | ✓ | |
| `required_indicators[]` | ✓ | ✓ | Free-form strings; includes funder tokens e.g. `FCDO_management_actions` |
| `required_tables[]` + column specs | ✓ | ✓ | NLCF: narrative + budget table; FCDO: logframe/scoring/VfM tables |
| `data_type` `text` / `number` / `date` / `enum` / `rag_rating` | number/text | all five | FCDO exercises `rag_rating` and 1–5 `enum` on score column |
| `conditional_display` | ✓ enabled (`report_type == 'final'`) | present, disabled | NLCF end-of-grant section |
| `evidence_rules` | ✓ | ✓ | Strict vs proportionate |
| `guidance` | **unused** | **unused** | Optional in schema; not in instances |
| `max_rows` (table) | **unused** | **unused** | |
| Section-level `extensions` | **unused** | **unused** | Both use `format_rules_json.extensions` instead |

### 3.3 `format_rules_json` — exercised vs unused

| Schema block | NLCF | FCDO | Notes |
|--------------|------|------|-------|
| `document_title` | ✓ | ✓ | |
| `narrative_constraints` | ✓ | ✓ | |
| `extensions` | ✓ | ✓ | Rich funder-specific flags (submission style, scoring notes) |
| `logframe` | absent | ✓ enabled | |
| `value_for_money` | absent | ✓ enabled | |
| `rag` (global block) | absent | present **`enabled: false`** | Section-level `rag_rating` columns used instead |
| `header_fields` | **unused** | **unused** | Cover metadata not modeled in instances |
| `echo_blocks` | **unused** | **unused** | EU ECHO pattern not stress-tested by NLCF/FCDO |

### 3.4 `terminology_map_json` — fully exercised

Both use `canonical_to_funder`, `forbidden_terms`, `preferred_terms` (mostly empty forbidden/preferred).

### 3.5 Gaps — templates need something schema lacks?

**No missing columns** for NLCF/FCDO as normalized in WORKSTREAM T2. **Latent needs not carried on `donor_reports`:**

- **`report_type`** for NLCF `conditional_display` (`final` vs `annual`) — lives in `gap_analysis_json.report_context` and code defaults (`{"report_type": "annual"}`), **not** a report column or template-only field.
- **Per-report template version pin** — `donor_reports.funder_report_template_id` points at catalog row; editing template JSON affects semantics of existing reports (no snapshot FK).

---

## 4. Future-proofing stress test

Goal tested: **funders 3–10 as manual template rows only, zero schema change, zero new branching code.**

| Assumption / funder variation | Absorbed as template data? | Forces schema and/or code change? |
|------------------------------|----------------------------|-----------------------------------|
| Different section count/order/labels | ✓ `report_sections_json` | — |
| Different archetypes / word limits / tone | ✓ section fields | Code must already support archetype strings in prompt library (not DB) |
| Numeric vs qualitative vs mixed indicators | ✓ `required_indicators`, table `data_type` | — |
| Custom scoring scale (e.g. 1–5) or no scoring | ✓ column `enum_values` / omit score columns | — |
| RAG / traffic-light ratings | ✓ `rag_rating` columns + optional `format_rules_json.rag` | Global `rag` block optional |
| Logframe / VfM / ECHO block layouts | ✓ `format_rules_json` blocks + tables | **`echo_blocks` untested** by NLCF/FCDO — data-only but export/synthesis must understand block |
| Terminology / forbidden words | ✓ `terminology_map_json` | — |
| Annual vs quarterly vs interim vs final vs end-of-grant | ✓ **`reporting_frequency`** enum (5 values) | **Schema:** new cadence (e.g. `milestone`, `six_monthly`, `ad_hoc`) requires CHECK migration |
| Milestone-based reporting (non-calendar) | Partial — narrative sections only | **Schema/code:** no milestone period model; single `reporting_period_*` pair |
| Multi-period report (one submission covering Q1–Q4) | Partial — one date range | **Schema:** one start/end only; consolidated periods need convention or JSONB |
| Multi-grant consolidated report | — | **Schema:** one `funder_report_template_id` per report |
| Conditional sections (NLCF final-only) | ✓ `conditional_display` in JSON | **Code:** only `report_type == 'final'` evaluated (`template_requirements.py`); other conditions **force code** |
| `report_type` distinct from `reporting_frequency` | Stored in gap envelope context only | **Schema/code:** not on `donor_reports`; create/report API does not set it |
| New upload doc type (e.g. `audit_report`, `survey_export`) | — | **Schema:** `classification` CHECK migration + classifier enum |
| New pipeline stage (e.g. separate `validate` before export) | — | **Schema:** `report_jobs.stage` CHECK + worker |
| New report lifecycle status | — | **Schema:** `donor_reports.status` CHECK |
| Funder with no numeric indicators (pure narrative) | ✓ empty `required_indicators`, no number columns | — |
| Region / currency / language variants | ✓ free-text `region`, JSONB content | — |
| Multiple templates same funder (annual + final) | ✓ separate rows; UNIQUE on `(funder_name, template_name)` | Must use distinct `template_name` |
| Template content change after reports exist | ✓ update row | **Risk:** no version pin on `donor_reports` — operational not schema |

**Summary:** Template **JSONB** is flexible enough for diverse layouts; **closed CHECK enums** and **single-period report identity** are the main schema blockers for “zero migration.” **Conditional logic** and **`report_type`** are the main code blockers for “zero branching.”

---

## 5. Surface vs canonical

| Layer | Surface (funder-specific) | Canonical (meaning-level) | Assessment |
|-------|---------------------------|----------------------------|------------|
| Template `label` / table column `label` | Funder wording (“Annual Review”, “Tell us how it's going”) | `section_key`, `table_key`, `column_key` | **Clean separation** in schema |
| `terminology_map_json.canonical_to_funder` | Display labels | Canonical keys in map | **By design** |
| `archetype` | `ARCH_*` strings in template data | Prompt-library roles | **Data-driven**, not DB enum — good |
| `required_indicators[]` | Mixed — mostly semantic keys, some funder tokens (`FCDO_management_actions`) | No separate canonical indicator registry in DB | **Leaky** — funder tokens in keys are still template data, not schema |
| `reporting_frequency` | Funder cadence vocabulary | Closed DB enum | **Hard-coded in CHECK** — not free template data |
| `uploaded_documents.classification` | Doc type labels | Closed CHECK aligned to extractor routing | **Hard-coded** — global not per-funder |
| `report_jobs.stage` | — | Fixed pipeline | **Global canonical** — correct for product, not funder-specific |
| `donor_reports.status` | — | Product lifecycle | **Global canonical** |
| `report_type` (final vs annual) | NLCF “last progress update” | Not a column; default `annual` in code | **Gap** — surface concept without persisted canonical field |

**Finding:** Table design **does** separate headings (`label`) from stable keys (`section_key`, etc.). **Enums on template/report/job tables encode product-wide vocabularies**, not funder surface labels — appropriate for pipeline stability, but they **contradict** “pure template-row” expansion for new cadences and doc types.

---

## 6. Production & migration safety

### 6.1 Migration history (M&E only)

| Revision | Effect |
|----------|--------|
| `0014_me_module_tables` | Creates all four tables, indexes, CHECK constraints; `CREATE EXTENSION IF NOT EXISTS pgcrypto`; includes `gap_analysis_json` on create |
| `0015_gap_analysis_json` | Idempotent add of `gap_analysis_json` if missing |

Chain: `… → 0013_ngo_profiles_knowledge_bank → 0014_me_module_tables → 0015_gap_analysis_json (head)`.

### 6.2 Harness / clean upgrade

- **`tests/test_me_module_migration_parity.py`:** passes (model columns match 0014+0015).
- **Fresh Postgres `alembic upgrade head`:** 0014 requires **`pgcrypto`** for `gen_random_uuid()` defaults (`CREATE EXTENSION IF NOT EXISTS pgcrypto`). On managed Postgres (Railway) this usually succeeds; on **scratch/local harness without extension privileges**, upgrade fails — known class of issue; not M&E-specific beyond 0014.
- **0015 on fresh DB:** no-op if 0014 already created column — safe.
- **Live vs code drift risk:** medium for **template row content** (manual inserts) and low for **DDL** if prod alembic version = head. Confirm with checklist.

### 6.3 Live Railway Postgres — READ-ONLY confirmation checklist

Run against production (replace `{fcdo_id}` with prod FCDO template UUID, e.g. `55f891ac-bb8b-4137-bc42-6de8ff935064` from prod walks):

```sql
-- 1) Alembic at head
SELECT version_num FROM alembic_version;
-- Expect: 0015_gap_analysis_json

-- 2) Four tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'funder_report_templates', 'donor_reports',
    'uploaded_documents', 'report_jobs'
  )
ORDER BY 1;

-- 3) Column-level shape (donor_reports — includes gap_analysis_json)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'donor_reports'
ORDER BY ordinal_position;

-- 4) Repeat for other three tables
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'funder_report_templates'
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'uploaded_documents'
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'report_jobs'
ORDER BY ordinal_position;

-- 5) CHECK constraints on closed enums (sample)
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'funder_report_templates'::regclass AND contype = 'c';

SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'donor_reports'::regclass AND contype = 'c';

-- 6) Active funder templates (expect NLCF + FCDO + possible __default__)
SELECT id, funder_name, template_name, region, reporting_frequency,
       version, is_active,
       jsonb_array_length(report_sections_json) AS section_count,
       docx_template_ref
FROM funder_report_templates
ORDER BY funder_name, template_name;

-- 7) FCDO template JSON keys vs repo reference (manual diff)
SELECT id, funder_name, template_name,
       report_sections_json ? 'section_key' AS sections_is_array,
       format_rules_json ? 'document_title' AS has_doc_title,
       format_rules_json ? 'logframe' AS has_logframe,
       format_rules_json ? 'value_for_money' AS has_vfm,
       terminology_map_json ? 'canonical_to_funder' AS has_term_map
FROM funder_report_templates
WHERE id = '{fcdo_id}'::uuid;

-- 8) Deep compare: export prod row and diff to docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json
SELECT jsonb_pretty(row_to_json(t)::jsonb)
FROM (
  SELECT funder_name, template_name, region, reporting_frequency,
         report_sections_json, format_rules_json, terminology_map_json,
         docx_template_ref, version
  FROM funder_report_templates
  WHERE id = '{fcdo_id}'::uuid
) t;

-- 9) Index presence (sample)
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN (
  'funder_report_templates', 'donor_reports',
  'uploaded_documents', 'report_jobs'
)
ORDER BY tablename, indexname;
```

---

## 7. Prioritised gaps for the eventual build prompt

1. **Document `gap_analysis_json`** in `DB_FIELD_CONTRACT_DONOR_REPORTS.md`, `API_CONTRACT.md` §12.9, and master memory — shape from `gap_compliance_v1.py`.
2. **Reconcile `agent_trace_json` contract** with `stages{}` runtime shape (or document both views).
3. **Decide `report_type` persistence** — column on `donor_reports`, derive from `reporting_frequency`, or expand conditional evaluator — required for NLCF final section without code defaults.
4. **Cadence vocabulary** — extend `reporting_frequency` CHECK (migration) or document mapping rules for milestone/ad-hoc funders.
5. **Template version pin** — whether `donor_reports` should snapshot `template.version` or template JSON hash at create time.
6. **Stress-test `echo_blocks` + `header_fields`** with a third reference template (EU-class) before claiming ECHO-ready.
7. **Classification enum policy** — process for new doc types (migration vs `other` + extensions).
8. **Refresh contract headers** (“migration applied”, alembic ids).
9. **Live DB diff** — prod FCDO/NLCF rows vs `TEMPLATE_INSTANCE_*.json` (checklist §6.3).
10. **Multi-period / consolidated reports** — product decision: convention on date fields vs new JSONB vs out of scope.

---

## Readiness statement

**Schema readiness for 10 funders (template-catalog model):** **Partial — suitable for launch catalog rows, not fully future-proof under zero-migration/zero-code rules.**

- **Ready now (data-only):** Adding funders whose cadence fits existing `reporting_frequency` values, whose uploads fit the seven classifications, and whose forms fit `report_sections_json` / `format_rules_json` / `terminology_map_json` — **no DDL required**.
- **Not ready without follow-up build:** Milestone/ad-hoc cadences, new document classes, non-trivial conditional sections, multi-period/consolidated reports, ECHO `echo_blocks` path, contract/doc sync for `gap_analysis_json` and agent trace, and prod template row parity verification.

**Recommended gate before claiming “Stage B schema complete for funders 3–10”:** run checklist §6.3 on Railway, diff FCDO row against `TEMPLATE_INSTANCE_FCDO.json`, then close drift items D1–D4 in contracts (documentation-only tranche — separate from this audit).

---

*End of audit. No files, models, migrations, or database objects were modified.*
