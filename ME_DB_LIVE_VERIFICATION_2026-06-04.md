# M&E live database verification — production Railway Postgres

**Date:** 2026-06-04  
**Mode:** Read-only (no writes)  
**Reference:** `ME_DB_FUTUREPROOF_AUDIT_2026-06-04.md` §1, §6.3; `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`

---

## Production connection target (guard 1)

| Attribute | Value |
|-----------|--------|
| **Workspace** | mycrivo's Projects |
| **Project** | NGOINfo-GrantPilot AI |
| **Project ID** | `5e9d5d45-985d-45b4-bb25-8c5270665f22` |
| **Environment** | **production** (`RAILWAY_ENVIRONMENT_NAME=production`, ID `c139bc74-dd5e-47ed-ac75-85674599f22b`) |
| **Database service** | Postgres (ID `2ef27b06-9371-4097-b8d8-41ff9c8599ee`) |
| **Linked backend** | `https://ngoinfo-grantpilot-production.up.railway.app` |
| **Database name** | `railway` |
| **Public proxy host** | `hopper.proxy.rlwy.net:33086` (via `DATABASE_PUBLIC_URL`) |

Confirmed via `railway link -p 5e9d5d45-985d-45b4-bb25-8c5270665f22 -e production -s Postgres` and `railway status` before any query.

---

## Read-only session (guard 2)

First statement in session: `SET default_transaction_read_only = on;`  
Post-check: `SHOW default_transaction_read_only` → **`on`**.  
All checklist queries were `SELECT` / `information_schema` / `pg_constraint` / `pg_indexes` reads only.

---

## Per-criterion results

| # | Criterion | Result | Notes |
|---|-----------|--------|-------|
| 1 | `alembic_version = 0015_gap_analysis_json` | **PASS** | `SELECT version_num FROM alembic_version` → `0015_gap_analysis_json` |
| 2 | Four M&E tables present | **PASS** | `donor_reports`, `funder_report_templates`, `report_jobs`, `uploaded_documents` |
| 3 | `donor_reports.gap_analysis_json` (jsonb) + column shape vs audit §1 | **PASS** | Column present; automated compare of all four tables: **0 issues** (`column_issues: []`) |
| 4 | CHECK constraints match §1 closed value sets | **PASS** | See §Check constraints below |
| 5 | Active templates = NLCF + FCDO (+ optional `__default__`) | **FAIL** | Prod has **`__default__`** + **FCDO only** — **NLCF row absent** |
| 6 | FCDO prod row matches `TEMPLATE_INSTANCE_FCDO.json` on template-definition fields | **PASS** | Full structural diff: **0** missing keys, **0** extra keys, **0** value mismatches |

---

## Checklist query results (§6.3)

### Query 1 — Alembic

```
0015_gap_analysis_json
```

### Query 2 — Tables

All four M&E tables present (listed above).

### Query 3–4 — Columns

All columns on all four tables match audit §1 for **name, data_type, is_nullable, column_default** (including `gap_analysis_json` on `donor_reports`).

### Query 5 — CHECK constraints

| Table | Constraint | Prod definition (abbrev.) | §1 match |
|-------|------------|---------------------------|----------|
| `funder_report_templates` | `ck_funder_report_templates_reporting_frequency` | `end_of_grant`, `annual`, `quarterly`, `interim`, `final` | ✓ |
| `donor_reports` | `ck_donor_reports_status` | `DRAFT` … `COMPLETE` (6 values) | ✓ |
| `uploaded_documents` | `ck_uploaded_documents_classification` | NULL or 7 classification values | ✓ |
| `report_jobs` | `ck_report_jobs_stage` | 7 pipeline stages | ✓ |
| `report_jobs` | `ck_report_jobs_status` | 5 status values | ✓ |

Also present (expected): `ck_donor_reports_reporting_period`, `ck_uploaded_documents_extraction_status`, `ck_uploaded_documents_size_bytes`.

### Query 6 — Active funder templates

| id | funder_name | template_name | region | reporting_frequency | section_count | is_active |
|----|-------------|---------------|--------|---------------------|---------------|-----------|
| `fc1a012b-f9c1-459f-a4b2-d71c18116068` | `__default__` | `__lifecycle_default__` | global | annual | **0** | true |
| `55f891ac-bb8b-4137-bc42-6de8ff935064` | Foreign, Commonwealth & Development Office | FCDO Annual Review | UK | annual | **8** | true |

**NLCF row:** not present in production.

### Query 7 — FCDO JSON key probes

**FCDO template id used:** `55f891ac-bb8b-4137-bc42-6de8ff935064` (sole FCDO match from query 6).

| Probe | Result |
|-------|--------|
| `sections_is_array` (`report_sections_json ? 'section_key'`) | `false` (expected — JSONB is an array, not an object with that key) |
| `has_doc_title` | `true` |
| `has_logframe` | `true` |
| `has_vfm` | `true` |
| `has_term_map` | `true` |

### Query 8 — FCDO row diff vs repo

**Fields compared:** `funder_name`, `template_name`, `region`, `reporting_frequency`, `docx_template_ref`, `report_sections_json`, `format_rules_json`, `terminology_map_json`.

| Diff category | Count | Detail |
|---------------|------:|--------|
| Keys/paths in prod not in repo | **0** | — |
| Keys/paths in repo not in prod | **0** | — |
| Scalar or nested value mismatches | **0** | — |

Prod FCDO row is **byte-for-byte equivalent** to `TEMPLATE_INSTANCE_FCDO.json` on those fields (deep JSON compare).

### Query 9 — Indexes

All expected M&E indexes from migration 0014 present, including:

- `uq_funder_report_templates_funder_template`
- `idx_funder_report_templates_region_active`, `idx_funder_report_templates_active`
- `idx_donor_reports_*` (4 indexes)
- `idx_uploaded_documents_*` (3 indexes)
- `idx_report_jobs_*` (3 indexes)

---

## FCDO template id

**Used for queries 7–8:** `55f891ac-bb8b-4137-bc42-6de8ff935064`

Resolved from query 6 (`funder_name` = "Foreign, Commonwealth & Development Office"; `template_name` = "FCDO Annual Review") — not hardcoded.

---

## Verdict

**DRIFT FOUND: NLCF template row absent in production; DDL and FCDO template-definition fields match code/repo.**

- **DDL / alembic / four-table shape:** production matches code-canonical audit §1.
- **FCDO catalog row:** matches `TEMPLATE_INSTANCE_FCDO.json` on all template-definition fields.
- **Catalog gap:** NLCF reference template not loaded — only `__default__` (0 sections) and FCDO (8 sections) exist.

---

*End of verification. No database or repo objects were modified.*
