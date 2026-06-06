# A-03 — M&E Read APIs & Path Alignment Changelog

**Work package:** A-03 (read endpoints + path alignment + ownership scoping)  
**Date:** 2026-06-06  
**Status:** Complete — **STOP for human git-diff review. Not committed. Not deployed.**

---

## Step 1 — Mechanism summary

### Contract source (API_CONTRACT.md §12)

| Endpoint | Purpose | Response wrapper |
|----------|---------|------------------|
| `GET /api/report-templates` | Active template catalogue (optional `?region=`) | `{ "report_templates": [...] }` |
| `GET /api/reports` | Owner's report list; `?limit=` default **10**, max **50** | `{ "reports": [summary…] }` |
| `GET /api/reports/{id}` | Full detail at top level (not wrapped); includes JSONB payloads + `current_gate` + `gate3_confirmed_at` | top-level object |

**List item fields (§12.10):** `id`, `funder_name`, `template_name`, `status`, `reporting_period_*`, `current_gate`, `created_at`, `updated_at` — no JSONB blobs.

**PROVISIONAL (not built):** PATCH knowledge-bank, GET gap-check, PATCH gap-answers, PATCH sections/{key}, sync POST generate.

### Current routes before A-03

| Route | Path status |
|-------|-------------|
| `GET /api/reports/health` | OK (ungated infra) |
| `POST /api/reports` | OK |
| `GET /api/reports` | **Missing** |
| `GET /api/reports/{id}` | **Missing** |
| `GET /api/report-templates` | **Missing** |
| `POST /api/reports/{id}/documents` | OK (`donor_report_id` param name only) |
| `POST/GET /api/reports/{id}/job` | OK |
| `GET /api/reports/{id}/knowledge-bank` | OK |
| `GET /api/reports/{id}/export` | OK |
| Gate confirm/responses | **Drift:** `/api/reports/donor-reports/{id}/…` |

### List pagination mirror

Proposals/fit-scans: `limit` query param via FastAPI `Query(default=5, ge=1, le=50)`, ordered by `created_at desc`. Reports list uses same pattern with **default 10** per §12.10.

### Models & ownership

- `donor_reports.user_id` FK → `users.id` (owner).
- `funder_report_templates` — global catalogue (`is_active` filter).

### Ownership findings (pre-A-03)

| Route / service | Pre-A-03 behaviour |
|-----------------|-------------------|
| `get_owned_donor_report` (upload, job, KB, export) | 404 not found; **403** wrong owner |
| `gate1/2/3 confirm services` | Duplicate checks: 404 / **403** |
| Gate route handlers | Delegate to services (no direct DB) |

**Decision gate:** Single shared mechanism applied — `get_owned_donor_report` now returns **404 for both missing and non-owner** (existence not leaked). Gate services refactored to call it (minimal, not a large refactor).

### Internal refs to renamed gate paths

| Location | Updated in A-03 |
|----------|-----------------|
| `tests/test_gate1_confirmation.py` | Yes |
| `tests/test_gate2_gap_answers.py` | Yes |
| `tests/test_report_read_routes.py` | Old-path 404 test |
| `scripts/*prod_walk*.py` | **Not updated** — throwaway dev/prod walk scripts; no production frontend consumer |

**Live consumer gate:** No production frontend or mounted client uses old paths. Scripts flagged for manual update if re-run.

---

## Files changed (before → after)

### New files

| File | Purpose |
|------|---------|
| [`app/reports/services/report_gate_state.py`](app/reports/services/report_gate_state.py) | `compute_current_gate()` from KB/gap stamps |
| [`app/reports/services/report_read_service.py`](app/reports/services/report_read_service.py) | List/detail/templates queries + payload builders |
| [`app/reports/schemas/report_read.py`](app/reports/schemas/report_read.py) | Pydantic models per §12 |
| [`app/reports/api/routes/read.py`](app/reports/api/routes/read.py) | Three GET endpoints |
| [`tests/test_report_read_routes.py`](tests/test_report_read_routes.py) | 7 acceptance tests |

### Modified files

| File | Before → After |
|------|----------------|
| [`app/reports/router.py`](app/reports/router.py) | Added `read_routes` on `gated_router` (inherits A-02 plan gate) |
| [`app/reports/services/report_access.py`](app/reports/services/report_access.py) | Wrong owner: 403 → **404** `DONOR_REPORT_NOT_FOUND` |
| [`app/reports/api/routes/gate1.py`](app/reports/api/routes/gate1.py) | Removed `donor-reports` infix |
| [`app/reports/api/routes/gate2.py`](app/reports/api/routes/gate2.py) | Removed `donor-reports` infix |
| [`app/reports/api/routes/gate3.py`](app/reports/api/routes/gate3.py) | Removed `donor-reports` infix |
| [`app/reports/services/gate1_confirmation_service.py`](app/reports/services/gate1_confirmation_service.py) | Uses `get_owned_donor_report` |
| [`app/reports/services/gate2_gap_answer_service.py`](app/reports/services/gate2_gap_answer_service.py) | Uses `get_owned_donor_report` |
| [`app/reports/services/gate3_confirmation_service.py`](app/reports/services/gate3_confirmation_service.py) | Uses `get_owned_donor_report` |
| [`tests/test_report_lifecycle_routes.py`](tests/test_report_lifecycle_routes.py) | Non-owner job poll: 403 → **404** |
| [`tests/test_gate1_confirmation.py`](tests/test_gate1_confirmation.py) | Canonical gate1 path |
| [`tests/test_gate2_gap_answers.py`](tests/test_gate2_gap_answers.py) | Canonical gate2 path |

**Unchanged (by design):** Gate handler logic, pipeline, quota (A-01/A-02), DOCX render (A-04), lifecycle POST paths.

---

## Implemented shapes

Conform to §12.10 / §12.9 / §12.1. `current_gate` derived from `gate*_confirmed_at` stamps + reconciliation/gap presence (see `report_gate_state.py`). No §12 under-spec flags — contract fields implemented as specified.

---

## Test results

### A-03 target suites

```
pytest tests/test_report_read_routes.py tests/test_report_lifecycle_routes.py \
  tests/test_gate1_confirmation.py tests/test_gate2_gap_answers.py tests/test_me_enforcement.py -q
41 passed
```

### Full backend suite

```
pytest tests/ -q
275 passed, 4 failed
```

**New tests (+7):** `tests/test_report_read_routes.py` (7 tests).

**Updated tests (legitimate target change):**

| Test | Change |
|------|--------|
| `test_unauthorized_and_non_owner_rejected` | Non-owner → 404 not 403 |
| `test_gate1_confirm_endpoint_*` | Canonical gate1 URL |
| `test_gate2_endpoint_requires_auth` | Canonical gate2 URL |

**Pre-existing failures (unchanged):** auth account linking (×2), gate1 module-disabled path, worker subprocess.

---

## Acceptance checklist

| Outcome | Status |
|---------|--------|
| List owner-scoped; empty → 200 [] | ✅ |
| `?limit=` respected | ✅ |
| Detail owner 200; foreign/nonexistent 404 | ✅ |
| Templates catalogue 200 | ✅ |
| FREE/Growth → 403 UPGRADE_REQUIRED on new reads | ✅ |
| Gate paths at `/api/reports/{id}/…`; old `donor-reports` → 404 | ✅ |
| Uniform 404 on foreign report id (via `get_owned_donor_report`) | ✅ |
| No migration | ✅ |
| No provisional endpoints / sync generate | ✅ |

---

## FLAGGED FOR FOUNDER

1. **`scripts/*` prod walk scripts** still call old `donor-reports` URLs — update before next prod walk (not production app consumers).

2. **`current_gate` heuristic** — derived from KB/gap JSON stamps, not live `report_jobs.awaiting_human` stage. Sufficient for dashboard list/detail MVP; may need job-stage overlay if UI requires exact halt state.

3. **404 vs 403 on non-owner** — unified to 404 per §12 and A-03 brief (was 403 on some routes). Frontend should treat as “not found.”

4. **No contract divergence** — shapes match committed §12.

---

## Explicit non-goals honoured

- ❌ Provisional PATCH/GET gate-edit endpoints
- ❌ Sync generate endpoint
- ❌ Pipeline / agent / quota / DOCX render changes
- ❌ Frontend / backward-compat redirects
- ❌ Git commit / deploy

**Next:** Frontend Track B (B-series) after human review/deploy of A-03.
