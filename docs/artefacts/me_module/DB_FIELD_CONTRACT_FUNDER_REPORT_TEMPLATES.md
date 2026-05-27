# DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md

**Status:** Canonical (LOCKED — Stage B validation complete)  
**Applies to:** M&E Module — funder report template catalog  
**System of Record:** Railway PostgreSQL — GrantPilot Backend  
**Owner:** M&E Module / Backend  
**Migration:** `alembic/versions/0014_me_module_*.py` (Stage C — not yet applied)

---

## 1. Purpose

This contract defines persistence for **funder report templates** — the post-award equivalent of `funding_opportunities.requirements_json`.

Templates are **global catalog rows** (not user-owned). They encode:
- Ordered report sections (archetypes, limits, required tables/indicators)
- Funder-specific format rules (RAG ratings, ECHO blocks, etc.)
- Terminology mapping for synthesis
- Pointer to docxtpl Word template file

Ten launch templates are seeded at Stage H; schema validated against NLCF (simple) and FCDO (complex) — **Stage B-validation complete** (D-024).

---

## 2. Table: `funder_report_templates`

### 2.1 Identity

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `id` | `id` | UUID | NO | `gen_random_uuid()` | PRIMARY KEY |

---

### 2.2 Funder Metadata

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `funder_name` | `funder_name` | TEXT | NO | — | e.g. `"National Lottery Community Fund"` |
| `template_name` | `template_name` | TEXT | NO | — | e.g. `"End-of-Grant Report"` |
| `region` | `region` | TEXT | NO | — | e.g. `UK`, `US`, `EU`, `IN`, `UNIVERSAL` |
| `reporting_frequency` | `reporting_frequency` | TEXT | NO | — | CHECK — ENUM_REGISTRY §5.5 |

**Allowed `reporting_frequency` values:** `end_of_grant` | `annual` | `quarterly` | `interim` | `final`

---

### 2.3 Template Configuration (JSONB)

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `report_sections_json` | `report_sections_json` | JSONB | NO | `'[]'::jsonb` | Shape: `FUNDER_TEMPLATE_SCHEMA.md` §2 |
| `format_rules_json` | `format_rules_json` | JSONB | NO | `'{}'::jsonb` | Shape: `FUNDER_TEMPLATE_SCHEMA.md` §3 |
| `terminology_map_json` | `terminology_map_json` | JSONB | NO | `'{}'::jsonb` | Shape: `FUNDER_TEMPLATE_SCHEMA.md` §4 |

**Naming (locked):** `_json` suffix on all JSONB columns. Python attribute = DB column (no aliasing).

---

### 2.4 Export & Versioning

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `docx_template_ref` | `docx_template_ref` | TEXT | NO | — | Repo-relative path under `app/reports/templates/docx/` |
| `is_active` | `is_active` | BOOLEAN | NO | `true` | Inactive templates hidden from `GET /api/report-templates` |
| `version` | `version` | INTEGER | NO | `1` | Template schema/content version; bump on material change |

---

### 2.5 Timestamps

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `created_at` | `created_at` | TIMESTAMPTZ | NO | `now()` | — |
| `updated_at` | `updated_at` | TIMESTAMPTZ | NO | `now()` | — |

---

## 3. Indexes

| Index | Purpose |
|-------|---------|
| `(funder_name, template_name)` UNIQUE | Prevent duplicate catalog entries |
| `(region, is_active)` | Filter active templates by region |
| `(is_active)` WHERE `is_active = true` | List endpoint |

---

## 4. FK Direction Rule

This table has **no FKs to core**. Other M&E tables FK **to** this table:

| From table | Column | Direction |
|------------|--------|-----------|
| `donor_reports` | `funder_report_template_id` | M&E → M&E ✓ |

**No core table** references `funder_report_templates`.

---

## 5. Relationship to Other Artefacts

- `FUNDER_TEMPLATE_SCHEMA.md` — JSONB inner shapes
- `REPORT_INPUTS_FIELD_MAPPING.md` — template → synthesis inputs
- `API_CONTRACT.md` §12.1 — `GET /api/report-templates`
- `ENUM_REGISTRY.md` §5.5

---

## 6. Build Enforcement

- JSONB fields MUST use `_json` suffix in migration, model, and contract.
- Do not store template config in `requirements_json` or any core table.
- Canonical template instances: [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json), [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json) — seeded at Stage H.
