# A-02 — M&E Access Enforcement Changelog

**Work package:** A-02 (enforcement only — no new endpoints, no quota number changes)  
**Date:** 2026-06-06  
**Status:** Complete — **STOP for human git-diff review. Not committed. Not deployed.**

---

## Step 1 — Mechanism summary

### Contract source of truth

| Document | Relevant sections |
|----------|-------------------|
| `docs/artefacts/API_CONTRACT.md` | §10.3 `403 UPGRADE_REQUIRED` (exact body); §10.2 `429 QUOTA_EXCEEDED` with entitlement snapshot for `reports` |
| `docs/artefacts/PRICING_AND_ENTITLEMENTS.md` | M&E Impact-only; 2 reports/cycle; decrement at create |
| A-01 `quota_service.py` | `reports.used` = `REPORT_CREATE` rows in billing window; `REPORT_EXPORT` idempotency-only |

### Existing enforcement pattern (reused)

**Proposals** (`app/services/proposal_service.py`): `enforce_quota(commit=False)` precheck → `add` → `flush` → `record_usage(commit=False)` → `commit`; `rollback` on failure.

**Decision gate:** Pattern is cleanly reusable. Proceeded. Added `SELECT … FOR UPDATE` on `user_plans` during `REPORT_CREATE` record path for cross-transaction serialization (Postgres-safe; mirrors worker job-claim precedent in `job_runner.py`).

### M&E surface

- Mounted via `app/main.py` when `ME_MODULE_ENABLED`.
- `app/reports/router.py`: **health** ungated (unauthenticated infra probe); all authenticated sub-routers on `gated_router` with `require_impact_plan`.

---

## Files changed (before → after)

### 1. `app/reports/api/dependencies/plan_gate.py` **(NEW)**

- **After:** Layer 1 dependency `require_impact_plan` — queries `user_plans` (no auto-create); non-IMPACT or missing plan → exact §10.3 `UPGRADE_REQUIRED` body.

### 2. `app/reports/router.py`

- **Before:** All sub-routers on flat router (no plan gate).
- **After:** `health_routes` on root router; lifecycle, export, gate1/2/3 on `gated_router(dependencies=[Depends(require_impact_plan)])`.

### 3. `app/services/quota_service.py`

- **Before:** Generic `QUOTA_EXCEEDED` with legacy `details.resource` for all actions.
- **After:**
  - `_report_quota_snapshot`, `_raise_report_quota_exceeded`, `enforce_report_create_quota(lock=…)`.
  - `REPORT_CREATE` failures use §10.2 shape: `entitlement`, `limit`, `used`, `remaining`, `period`, `reset_at`.
  - `_lock_user_plan_row` + lock during `REPORT_CREATE` in `record_usage`.
  - `get_or_create_user_plan` sets `id=uuid.uuid4()` on insert (sqlite test robustness).
  - Fit-scan/proposal quota error shapes **unchanged**.

### 4. `app/reports/services/donor_report_lifecycle_service.py`

- **Before:** `create_donor_report` → `db.add` + `db.commit` (no quota, no ledger).
- **After:** validation/template → `enforce_report_create_quota(commit=False, lock=True)` → atomic `add` + `flush` + `REPORT_CREATE` ledger (`idempotency_key=report:create:{id}`) + `commit`; rollback on any failure.

### 5. `tests/worker_validation_seed.py`

- **Before:** M&E tables only (no billing).
- **After:** Adds `UserPlan`, `UsageLedger` tables; `seed_user_plan()` helper.

### 6. `tests/test_me_enforcement.py` **(NEW — 9 tests)**

- Plan gate: FREE create, GROWTH upload → 403 exact body; IMPACT create+upload pass.
- Quota: create decrements `reports.used`; 3rd create → 429 exact body; sequential second create at remaining=1 → 429.
- Atomicity: mocked late quota exhaustion rolls back report row; simulated `record_usage` failure → no ledger/report rows.
- Export route does not change `reports.used`.

### 7. Updated existing tests (legitimate target change — M&E now gated)

| File | Change |
|------|--------|
| `tests/test_report_lifecycle_routes.py` | `lifecycle_api` seeds `UserPlan(IMPACT)`; `other_id` IMPACT for ownership test; service upload seeds IMPACT; autouse `security.get_settings` restore |
| `tests/test_report_export_service.py` | `_seed_gate3_ready_report` seeds IMPACT; autouse settings restore |
| `tests/test_me_enforcement.py` | autouse settings restore (full-suite isolation from `test_auth_google_callback_redirect` leak) |

**Note:** Gate1/gate2 API tests only assert 401 (no valid token) — no fixture change required.

---

## Test results

### A-02 target suites

```
pytest tests/test_me_enforcement.py tests/test_report_lifecycle_routes.py tests/test_report_export_service.py tests/test_quota_service.py tests/test_me_module_mount.py -q
37 passed
```

### Full backend suite

```
pytest tests/ -q
268 passed, 4 failed
```

**A-02 tests:** all green in full suite.

**Remaining 4 failures (pre-existing, unrelated to A-02):**

| Test | Cause |
|------|-------|
| `test_auth_account_linking.py` (×2) | `'tuple' object has no attribute 'id'` |
| `test_gate1_confirmation.py::test_gate1_confirm_endpoint_404_when_module_disabled` | Auth/settings in module-disabled path |
| `test_me_module_worker.py::test_worker_startup_path_registers_mappers_before_claim` | Subprocess sqlite `report_jobs` table |

---

## Acceptance checklist

| Outcome | Status |
|---------|--------|
| FREE/GROWTH → 403 `UPGRADE_REQUIRED` exact body on M&E routes | ✅ |
| IMPACT passes plan gate | ✅ |
| Impact create decrements `reports.used` via `REPORT_CREATE` | ✅ |
| 3rd create → 429 exact `QUOTA_EXCEEDED` reports body | ✅ |
| Second create at remaining=1 → 429; ledger=2, reports=1 | ✅ |
| Failure after gate → no orphan ledger/report row | ✅ |
| Export does not change `reports.used` | ✅ |
| Upload covered by plan gate only (no quota charge) | ✅ |
| No Alembic migration | ✅ |
| No route path changes / no new endpoints | ✅ |

---

## FLAGGED FOR FOUNDER

### 1. Decrement-at-create + pipeline failure tradeoff

Quota is consumed when the report row is created (`REPORT_CREATE` ledger write), **not** when the pipeline completes. If extraction/synthesis fails later, the billing-cycle slot is **not** refunded. This matches the locked brief (simplest race-safe model; no reservation/refund system).

### 2. `report_exports.limit` (carried from A-01)

Export route is plan-gated only; no `REPORT_EXPORT` ledger writes in A-02. Display vs enforcement for `report_exports` block unchanged — audit/idempotency only.

### 3. Health route exclusion

`GET /api/reports/health` remains unauthenticated and **outside** the Impact plan gate (infra probe; `test_me_module_mount` unchanged).

### 4. Concurrency hardening

Added `user_plans` row `FOR UPDATE` lock on `REPORT_CREATE` path (beyond pure proposal mirror). True HTTP concurrent test not run on SQLite (connection isolation limits); sequential + mocked rollback tests verify atomicity semantics. Production Postgres benefits from row lock.

### 5. No contract divergence

Error bodies conform to committed §10.2 / §10.3.

---

## Explicit non-goals honoured

- ❌ No `/api/reports*` path realignment (A-03)
- ❌ No quota number / entitlements computation changes (A-01)
- ❌ No DOCX render changes (A-04)
- ❌ No frontend / pipeline / agent changes
- ❌ No git commit or deploy

**Next package:** A-03 — list/detail/template endpoints + path alignment.
