# A-01 — Entitlements & Quota Accounting Changelog

**Work package:** A-01 (accounting/read layer only)  
**Date:** 2026-05-30  
**Status:** Complete — **STOP for human git-diff review. Not committed. Not deployed.**

---

## Step 1 — Mechanism summary (pre-build diagnosis)

### Contract source of truth (A-00 locked)

| Document | Relevant sections |
|----------|-------------------|
| `docs/artefacts/API_CONTRACT.md` | §4 entitlements shape (`reports` + `report_exports` blocks); §10 error model (enforcement deferred to A-02) |
| `docs/artefacts/ENUM_REGISTRY.md` | §3.3 `usage_ledger.action_type` (TEXT + app validation); §5.10 M&E quota mapping |
| `docs/artefacts/PRICING_AND_ENTITLEMENTS.md` | Two-plan quotas; Impact 2 M&E reports/month; billing-cycle reset |

**Canonical plan → quota target:**

| Plan | fit_scans | proposals | reports | proposal_regenerations |
|------|-----------|-----------|---------|------------------------|
| FREE | 1 (LIFETIME) | 1 (LIFETIME) | 0 | 0/proposal |
| GROWTH | 10 (BILLING_CYCLE) | 3 (BILLING_CYCLE) | 0 | 3/proposal |
| IMPACT | **10** (BILLING_CYCLE, was 20) | 5 (BILLING_CYCLE) | **2** (BILLING_CYCLE) | 3/proposal |

**New ledger action types:** `REPORT_CREATE`, `REPORT_EXPORT` (application-validated TEXT; no Alembic migration).

### Existing code mechanism

| Component | Location | Behaviour |
|-----------|----------|-----------|
| Plan → quota source | `app/services/quota_service.py` — `PLAN_QUOTAS` | Frozen dataclass per plan; single source of numeric limits |
| Entitlements builder | `quota_service.get_entitlements()` | Counts ledger rows in billing window; builds limit/used/remaining/period/reset_at |
| Entitlements schema | `app/schemas/entitlements.py` | Pydantic response model for `GET /api/me/entitlements` |
| Usage ledger | `app/models/usage_ledger.py` — `UsageActionType`, `UsageLedger` | `action_type` is TEXT; Python enum + `record_usage()` validation |
| Billing-cycle reset | `app/services/billing_service.py` — Stripe webhook | Updates `user_plans.billing_period_start/end`; **no per-resource counter zeroing** |

**How `used` is computed:** `_usage_count()` counts `usage_ledger` rows for a given `action_type` where `created_at` ∈ `[billing_period_start, billing_period_end)` for paid plans, or all-time for FREE lifetime resources. **Reset is window-based** — when Stripe advances the period, older rows fall outside the window automatically.

**Proposals nuance (unchanged):** `proposals.used` = `PROPOSAL_CREATE` + `DOCX_EXPORT` counts in cycle; `DOCX_EXPORT` shares the proposals limit.

**Decision gate:** Mechanism is **cleanly mirror-able** for `reports` — same `PLAN_QUOTAS` structure, same `_usage_count` window, same Stripe period advance. **No migration required.** Proceeded to build.

---

## Files changed (before → after)

### 1. `app/models/usage_ledger.py`

- **Before:** `UsageActionType` had FIT_SCAN, PROPOSAL_CREATE, PROPOSAL_REGEN, DOCX_EXPORT only.
- **After:** Added `REPORT_CREATE`, `REPORT_EXPORT`; updated column comment to document all six values and TEXT validation strategy.

### 2. `app/schemas/entitlements.py`

- **Before:** `EntitlementsPayload` had fit_scans, proposals, proposal_regenerations only.
- **After:** Added required `reports: EntitlementQuota` and `report_exports: EntitlementQuota` per API §4.

### 3. `app/services/quota_service.py` (primary change)

- **`PlanQuota` / `PLAN_QUOTAS`:**
  - Added `reports: int` field.
  - IMPACT `fit_scans`: 20 → **10** (A-00 decision).
  - Added `reports`: FREE 0, GROWTH 0, IMPACT 2.
  - Proposals and proposal_regenerations **unchanged**.

- **`get_entitlements()`:**
  - Added `reports` block: `used` = current-cycle `REPORT_CREATE` count; `period` = `BILLING_CYCLE` on paid plans, `LIFETIME` on FREE.
  - Added `report_exports` block: `used` = current-cycle `REPORT_EXPORT` count; `limit` mirrors `reports.limit` (see founder flag below).

- **`enforce_quota()` / `record_usage()`:**
  - Refactored with `_QUOTA_ENFORCED_ACTIONS` and `_IDEMPOTENCY_ONLY_ACTIONS`.
  - `REPORT_CREATE` participates in quota math (same as FIT_SCAN/PROPOSAL_CREATE) — **accounting only**; no routes wired (A-02).
  - `REPORT_EXPORT` and `PROPOSAL_REGEN` skip quota enforcement (idempotency/audit).
  - `record_usage()` now sets `id=uuid.uuid4()` and `metadata_json={}` on insert (required for sqlite test harness where server defaults are stripped).

- **Billing-cycle reset:** No code change needed — `reports.used` inherits window-based reset via `billing_period_start/end` exactly like fit_scans and proposals.

### 4. `tests/test_quota_service.py`

- **Before:** 2 tests (stale `_build_quota_payload` signature using `allowed=`; monkeypatched enforce test).
- **After:** 10 tests including sqlite in-memory harness, Impact/Growth/Free entitlements, REPORT_CREATE increment/cycle exclusion, action_type accept/reject, report_exports block.
- **20→10 update:** New test `test_plan_quotas_impact_fit_scans_ten` asserts IMPACT fit_scans == 10 (no prior test asserted 20 in this file).

### Not in A-01 scope (do not stage)

- `smoke_test_export.docx` — binary drift unrelated to entitlements; exclude from A-01 commit.

---

## Test results

### Quota / entitlements (target suite)

```
pytest tests/test_quota_service.py -q
10 passed in 0.60s
```

| Test | Result |
|------|--------|
| `test_build_quota_payload` | PASS (fixed stale `allowed=` → `limit=` + full shape) |
| `test_enforce_quota_exhausted` | PASS |
| `test_plan_quotas_impact_fit_scans_ten` | PASS (**new** — asserts Impact fit_scans 10, reports 2) |
| `test_get_entitlements_impact_reports_default` | PASS (**new**) |
| `test_get_entitlements_growth_and_free_reports_zero` | PASS (**new**) |
| `test_report_create_increments_reports_used` | PASS (**new**) |
| `test_report_create_excludes_prior_cycle_rows` | PASS (**new**) |
| `test_usage_action_type_accepts_report_actions` | PASS (**new**) |
| `test_usage_action_type_rejects_invalid` | PASS (**new**) |
| `test_get_entitlements_includes_report_exports_block` | PASS (**new**) |

### Full backend suite (`pytest tests/`)

```
249 passed, 5 failed, 9 errors in 21.60s
```

**Failures/errors are pre-existing and unrelated to A-01** (missing `AUTH_ACCESS_TOKEN_TTL_MIN` in test settings namespace, auth account-linking tuple regression, M&E worker mapper test, module-disabled route tests). No entitlements/quota assertions failed.

**Note:** No other Python test file asserted Impact fit_scans == 20; the only code assertion was `PLAN_QUOTAS[IMPACT].fit_scans = 20` in `quota_service.py` (now 10).

---

## Acceptance checklist (A-01 outcomes)

| Outcome | Status |
|---------|--------|
| Impact user, no report activity: reports limit=2, used=0, remaining=2, period=BILLING_CYCLE | ✅ |
| Growth/Free: reports.limit=0 | ✅ |
| Impact fit_scans.limit=10; Growth=10; Free=1; proposals unchanged | ✅ |
| After one REPORT_CREATE this cycle: used=1, remaining=1 | ✅ |
| Ledger accepts REPORT_CREATE/REPORT_EXPORT; rejects invalid action_type | ✅ |
| reports.used excludes prior-cycle rows | ✅ |
| No Alembic migration added | ✅ |
| Full suite green | ⚠️ Pre-existing failures only (see above) |

---

## FLAGGED FOR FOUNDER

### 1. `report_exports.limit` semantics (contract vs enforcement)

- **API §4** includes a `report_exports` block with the same numeric shape as `reports` (limit/used/remaining/period/reset_at).
- **API §4 note:** "report_exports idempotent per report version (mirrors proposal DOCX_EXPORT pattern)."
- **ENUM_REGISTRY §5.10:** `report_exports` → `REPORT_EXPORT` → "Idempotent per report version" (not a separate monthly cap).
- **Implementation:** `report_exports.limit` is set to `quota.reports` (2 on Impact) for response shape parity; `REPORT_EXPORT` is in `_IDEMPOTENCY_ONLY_ACTIONS` — **no quota enforcement** on export (A-02 will wire idempotency keys on routes).
- **Question:** Should `report_exports.limit` be `2` (mirroring §4 JSON placeholder), `null`/omitted, or match a different contract interpretation? Proposal DOCX exports count toward `proposals.used` but there is no separate `docx_exports` block — M&E has an explicit block which may confuse UI if limit=2 implies "2 exports/month" rather than audit-only.

### 2. Alembic migration

- **Not required.** `action_type` remains TEXT; new values validated in Python only.

### 3. Contract vs brief — no divergence

- Brief and committed §4 agree on `reports` + `report_exports` blocks and Impact 2/month. Conformed to committed contract.

### 4. Pre-existing test suite debt

- 14 failing/erroring tests in full `tests/` run appear environmental/regression unrelated to quota. Recommend separate triage; not blocking A-01 accounting deliverable.

---

## Explicit non-goals honoured (A-01 scope fence)

- ❌ No route enforcement on `/api/reports*`
- ❌ No M&E endpoint create/modify
- ❌ No frontend changes
- ❌ No DOCX export / M&E pipeline / agent changes
- ❌ No git commit or deploy

**Next package:** A-02 — wire `REPORT_CREATE` enforcement and `403 UPGRADE_REQUIRED` on M&E entry points.
