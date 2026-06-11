# P3 Phase B — B1 mutation staging (STOP: await GO MUTATION)

**Date:** 2026-06-11  
**Owner tokens received:** `GO PHASE B` · NLCF regression pin ratified · Holds 1/2/5/6 cleared  
**Phase:** B1 complete (read-only prod) — **B2 not executed**

---

## B1 snapshot artefact

| Field | Value |
|-------|-------|
| Template ID | `55f891ac-bb8b-4137-bc42-6de8ff935064` |
| Snapshot | [`snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json`](snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json) |
| SHA256 | `aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0` |
| Rollback SQL stub | [`snapshots/fcdo_55f891ac_rollback_2026-06-11.sql`](snapshots/fcdo_55f891ac_rollback_2026-06-11.sql) |
| Prod `version` | 1 |
| Prod alembic | `0018_usage_ledger_uq` (B2 alembic step = **verify-only**) |

---

## Intended JSONB replace (repo source)

**Source:** [`docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`](../../TEMPLATE_INSTANCE_FCDO.json)

### Diff summary (prod snapshot → repo)

| Change area | Detail |
|-------------|--------|
| Section keys | **Parity** — same keys prod and repo |
| Tag coverage delta | Repo adds `indicator_requirements` / `table_requirements` owner tags prod lacks |
| `summary_and_overview.table_requirements` | Prod: absent · Repo: `review_summary_sheet` → `owner: funder`, `requirement_type: funder_supplied` |
| `performance_and_conclusions.table_requirements` | Prod: absent · Repo: tagged (incl. `outcome_assessment` narrative typing) |
| `detailed_output_scoring` | Prod: no section `owner` / no indicator tags · Repo: `owner: funder` + tagged indicators |
| `value_for_money` | Prod: no section `owner` / no indicator or table tags · Repo: `owner: funder` + tagged indicators/tables |
| `programme_management_delivery_commercial_financial.indicator_requirements` | Prod vs repo tag delta |
| `format_rules_json` | **Equal** |
| `terminology_map_json` | **Equal** |

**Fact:** Mutation applies P2 owner-tag metadata to prod row; section removal kill-list items remain present in repo instance (funder-owned sections retained with explicit tags for visibility filtering).

---

## Exact UPDATE (single row, transactional)

```sql
BEGIN;

UPDATE funder_report_templates
SET
  report_sections_json = :report_sections_json::jsonb,
  format_rules_json = :format_rules_json::jsonb,
  terminology_map_json = :terminology_map_json::jsonb,
  version = version + 1,
  updated_at = now()
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';

-- Require ROW_COUNT = 1; read back and diff JSONB against repo bind params; COMMIT only on exact match else ROLLBACK.
COMMIT;
```

Bind `:report_sections_json`, `:format_rules_json`, `:terminology_map_json` from verified [`TEMPLATE_INSTANCE_FCDO.json`](../../TEMPLATE_INSTANCE_FCDO.json).

---

## A9 in-flight exposure (unchanged at B1 time)

| Report status | Job status | Count |
|---------------|------------|-------|
| DRAFT | awaiting_human | 8 |
| DEGRADED | awaiting_human | 7 |
| COMPLETE | awaiting_human | 1 |

**Distinct in-flight reports:** 16 · **Strand risk:** live-reference FK — JSONB replace affects all on next engine read (see pack §7 B1 addenda).

---

## B3 designated test account

| Field | Value |
|-------|-------|
| Email | `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` |
| Plan | IMPACT (confirmed prod `user_plans`) |
| Rationale | Audit-mint FCDO full-docset walk account; prior in-flight report reached `synthesise` stage (`9606f25a…`) |

Fresh mint acceptable for B3 live walks if quota exhausted on designated account.

---

## STOP

Owner reply required before B2:

```
GO MUTATION
```

No prod writes until that token. B3 live walks follow B2.
