# NLCF funder template — production one-off insert

**Date:** 2026-06-04  
**Source:** `docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` (verbatim)  
**Target:** Production Railway Postgres — `NGOINfo-GrantPilot AI` / `production` / Postgres / `railway`

---

## Production connection target (guard 1)

| Attribute | Value |
|-----------|--------|
| Project | NGOINfo-GrantPilot AI (`5e9d5d45-985d-45b4-bb25-8c5270665f22`) |
| Environment | **production** (`c139bc74-dd5e-47ed-ac75-85674599f22b`) |
| Service | Postgres |
| Database | `railway` |
| Backend | `ngoinfo-grantpilot-production.up.railway.app` |

Confirmed via `railway status` (`RAILWAY_ENVIRONMENT_NAME=production` from service variables).

---

## Pre-flight checks (read-only session)

| Check | Result | Detail |
|-------|--------|--------|
| **A** Production target | **PASS** | Environment = `production` |
| **B** NLCF row absent | **PASS** | Count for `The National Lottery Community Fund` + `NLCF Progress Update / End-of-Grant Learning Report` = **0** |
| **C** Repo JSON valid | **PASS** | `TEMPLATE_INSTANCE_NLCF.json` parsed successfully |
| **D** Required NOT NULL columns | **PASS** | All present and non-null: `funder_name`, `template_name`, `region`, `reporting_frequency`, `report_sections_json`, `format_rules_json`, `terminology_map_json`, `docx_template_ref` |
| **E** `reporting_frequency` in CHECK set | **PASS** | Value = `annual` ∈ {`end_of_grant`, `annual`, `quarterly`, `interim`, `final`} |
| **F** JSON container types | **PASS** | `report_sections_json` = array (7 sections); `format_rules_json` = object; `terminology_map_json` = object |

Pre-flight session used `SET default_transaction_read_only = on`.

**Template count before insert:** 2 (`__default__` + FCDO).

---

## Insert

- **Table:** `funder_report_templates` only  
- **Rows written:** 1  
- **Columns set from repo file:** `funder_name`, `template_name`, `region`, `reporting_frequency`, `report_sections_json`, `format_rules_json`, `terminology_map_json`, `docx_template_ref` (JSONB loaded programmatically from parsed file)  
- **Defaults used:** `id` (`gen_random_uuid()`), `is_active` (`true`), `version` (`1`), `created_at`, `updated_at`  
- **Transaction:** single `INSERT` … `RETURNING id`, committed alone

---

## Generated NLCF template id

**`2d5d75b7-12f5-46b5-adaa-d5939a5249a8`**

---

## Post-insert verification

| Check | Result | Detail |
|-------|--------|--------|
| Exactly one NLCF row | **PASS** | Count = 1 for NLCF funder/template name pair |
| JSONB round-trip | **PASS** | All three blobs parse-equal to repo file |
| Scalar definition fields | **PASS** | `funder_name`, `template_name`, `region`, `reporting_frequency`, `docx_template_ref` match repo |
| Section count | **PASS** | 7 sections (matches repo array length) |
| Defaults | **PASS** | `is_active=true`, `version=1` |
| Template count delta | **PASS** | 2 → **3** (+1 exactly) |
| FCDO row untouched | **PASS** | `55f891ac-bb8b-4137-bc42-6de8ff935064` — all template-definition fields unchanged vs pre-insert snapshot |
| Other tables written | **PASS** | Only `funder_report_templates` modified |

Post-verify session used `SET default_transaction_read_only = on`.

---

## Pass criteria summary

| Criterion | Result |
|-----------|--------|
| NLCF present, parse-equal to repo | **PASS** |
| FCDO untouched | **PASS** |
| Count N → N+1, no other writes | **PASS** |

---

## Verdict

**NLCF INSERTED & VERIFIED**

---

*One-off insert only. No seeder/loader committed. Temp invocation script removed from `%TEMP%` after run.*
