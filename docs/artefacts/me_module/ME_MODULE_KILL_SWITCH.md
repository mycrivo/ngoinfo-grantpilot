# M&E Module — Kill Switch

**Purpose:** Three independent procedures to disable M&E without affecting the pre-award (proposal) product.
**Status:** Stage C — procedures defined; **verified on empty module (2026-05-24)**; Stage K re-verification before launch.

All three must pass before M&E ships. If any procedure cannot be written without touching core proposal paths, isolation is broken.

---

## Prerequisites

| Item | Path / value |
|------|----------------|
| Backend entry | [`app/main.py`](../../app/main.py) |
| M&E router (Stage C) | `app/reports/router.py` |
| Feature flag (backend) | `ME_MODULE_ENABLED` env var (Stage B/C) |
| Feature flag (frontend, separate repo) | `NEXT_PUBLIC_ME_MODULE_ENABLED` |
| Worker entry (Stage C) | `Procfile` → `worker: python -m app.reports.worker` |
| M&E tables (Stage C migration) | `donor_reports`, `funder_report_templates`, `uploaded_documents`, `report_jobs` |
| Core tables | Unaffected — `users`, `proposals`, `ngo_profiles`, etc. |

---

## Kill switch 1 — Code (un-mount router + flag off UI)

**Effect:** M&E API and UI disappear; GrantPilot proposals/fit-scans/billing/auth continue unchanged.

### Backend steps

1. Set `ME_MODULE_ENABLED=false` (or remove from env) on Railway web service.
2. Remove or comment the **only** seam in [`app/main.py`](../../app/main.py):

   ```python
   # if settings.ME_MODULE_ENABLED:
   #     from app.reports.router import router as reports_router
   #     app.include_router(reports_router)
   ```

3. Redeploy web service.
4. Verify: `GET /api/reports` → **404**; `GET /health` → **200**; `POST /api/proposals` still works for entitled users.

### Frontend steps (separate repo)

1. Set `NEXT_PUBLIC_ME_MODULE_ENABLED=false`.
2. Redeploy frontend.
3. Verify: no `/reports` nav; proposal dashboard unchanged.

### What must NOT change

- [`app/api/routes/proposals.py`](../../app/api/routes/proposals.py)
- [`app/services/proposal_service.py`](../../app/services/proposal_service.py)
- [`app/services/export_service.py`](../../app/services/export_service.py)
- Any core router includes in `main.py` other than removing the M&E block

---

## Kill switch 2 — Runtime (scale worker to 0)

**Effect:** Agent pipeline stops; sync API and proposal generation unaffected.

### Steps

1. On Railway, scale **worker** service to **0** instances (web service stays up).
2. Verify: proposal create/regenerate/export still succeed.
3. Verify: M&E endpoints may return 503 or queue jobs indefinitely — acceptable; proposals must not degrade.

### Worker identification

| File | Role |
|------|------|
| [`Procfile`](../../Procfile) | Today: `web` + `release` only. Stage C adds `worker:` line |
| `app/reports/worker/__main__.py` | Worker entrypoint |
| `app/reports/worker/run_pipeline.py` | Swappable execution interface |

### Forward-compat

Execution sits behind `run_pipeline(report_id)` so worker fabric can change without touching agents.

---

## Kill switch 3 — Data (drop 4 M&E tables)

**Effect:** M&E data removed; core schema intact.

### Steps

1. Ensure kill switches 1 and 2 are active (no code/worker referencing tables).
2. Run downgrade migration (Stage C will provide `0014_me_module_*` with reversible `downgrade()`), **or** manually:

   ```sql
   DROP TABLE IF EXISTS report_jobs;
   DROP TABLE IF EXISTS uploaded_documents;
   DROP TABLE IF EXISTS donor_reports;
   DROP TABLE IF EXISTS funder_report_templates;
   ```

3. Verify core tables unchanged:

   ```sql
   SELECT COUNT(*) FROM proposals;
   SELECT COUNT(*) FROM users;
   SELECT COUNT(*) FROM ngo_profiles;
   ```

4. Verify Alembic head can be reconciled (document revision rollback in runbook).

### FK rule (why this is safe)

- M&E tables FK **to** core (`users`, `proposals`).
- **No** core table FKs **to** M&E.
- Dropping M&E tables cannot orphan core rows.

---

## Rehearsal schedule

| When | Scope |
|------|--------|
| **Stage C exit** | All three kills on **empty** mounted module (no agents) |
| **Stage K exit** | All three kills on **full** module before Impact Pro launch |

---

## Agreement check (Stage A exit gate)

| Document | Seam / boundary stated |
|----------|------------------------|
| `REPO_MAP_ME_MODULE.md` | `app/reports/` + one `main.py` include |
| `.cursor/rules/10-isolation.mdc` | Same |
| `.cursor/hooks/isolation_veto.py` | Blocks core → `app.reports` imports |
| This file | Three kills reference real paths |

**Exit gate: MET** — one boundary (`app/reports/`), one seam (`app/main.py` conditional include), three independent kill switches documented against real repo paths.
