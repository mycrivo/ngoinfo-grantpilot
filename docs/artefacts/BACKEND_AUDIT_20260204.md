# GrantPilot Backend Audit Report

**Date:** 2026-02-04
**Branch:** `claude/audit-grantpilot-backend-bMXL4`
**Mode:** Read-Only
**Auditor:** CTO Audit (Automated)

---

## Table of Contents

- [Section A: Critical Blockers (P0)](#section-a-critical-blockers-p0)
- [Section B: Missing Features (P1)](#section-b-missing-features-p1)
- [Section C: Schema Mismatches (P0/P1)](#section-c-schema-mismatches-p0p1)
- [Section D: Endpoint Gap Analysis](#section-d-endpoint-gap-analysis)
- [Section E: Dependency Gaps](#section-e-dependency-gaps)
- [Section F: Configuration Issues](#section-f-configuration-issues)
- [Section G: Recommended Execution Order](#section-g-recommended-execution-order)

---

## Section A: Critical Blockers (P0)

These issues will cause **runtime errors** or **prevent core features** from functioning.

### A1. `user_plans` column name mismatch — RUNTIME CRASH

The model and migration use **different column names** for the period columns:

| Column Purpose | Migration (`0005`) | Model (`user_plan.py`) |
|---|---|---|
| Period start | `billing_period_start` | `current_period_start` (line 34) |
| Period end | `billing_period_end` | `current_period_end` (line 37) |
| Activation time | *(not present)* | `plan_activated_at` (line 31) |
| Stripe sub ID | `stripe_subscription_id` | *(not present)* |

SQLAlchemy will emit SQL referencing `current_period_start`, `current_period_end`, and `plan_activated_at` — none of which exist in the database. **Every query touching `UserPlan` will fail with a PostgreSQL column-not-found error.**

**Files:**
- `app/models/user_plan.py:31-38`
- `alembic/versions/0005_commercial_spine.py`

---

### A2. `NGOProfile` model attribute vs DB column mismatch — RUNTIME CRASH

The model at `app/models/ngo_profile.py:24` defines:

```python
organization_country_of_registration: Mapped[str] = mapped_column(Text, nullable=False)
```

But migration `0003` created the column as `country_of_registration`. Since no explicit column name is passed to `mapped_column()`, SQLAlchemy will look for a DB column called `organization_country_of_registration` which **does not exist**.

Every operation on `ngo_profiles` will fail. Additionally, `profile_service.py:78` creates profiles with `country_of_registration=...` (the old name), meaning the mapped column `organization_country_of_registration` stays NULL and hits the NOT NULL constraint on commit.

**Cascading impact — this breaks:**
- Profile creation
- Profile reads
- Completeness checks
- Fit scans (which require complete profiles)
- Prompt input building (`fit_scan_prompt_inputs.py:35` accesses `profile.country_of_registration`)

**Files:**
- `app/models/ngo_profile.py:24`
- `app/services/profile_service.py:42,78,120`
- `app/api/routes/ngo_profile.py:34,70,109`
- `app/services/fit_scan_prompt_inputs.py:35`

---

### A3. `UsageLedger` ghost columns `period_start` / `period_end` — RUNTIME CRASH

`quota_service.py:167-168` sets `period_start` and `period_end` on `UsageLedger` objects:

```python
ledger = UsageLedger(
    ...
    period_start=plan.current_period_start if plan.plan_name != PLAN_FREE else None,
    period_end=plan.current_period_end if plan.plan_name != PLAN_FREE else None,
    ...
)
```

Neither `period_start` nor `period_end` exist in the `UsageLedger` model or the `usage_ledger` migration. SQLAlchemy will silently accept these as instance attributes but never persist them. However, the primary issue is that this function also depends on `plan.current_period_start` which triggers the A1 crash.

**Files:**
- `app/services/quota_service.py:167-168`

---

### A4. Entitlements endpoint infinite recursion — RUNTIME CRASH

`app/api/routes/entitlements.py:13` defines a route handler named `get_entitlements` which shadows the imported `get_entitlements` from `quota_service`:

```python
from app.services.quota_service import get_entitlements  # line 7

@router.get("/me/entitlements", ...)
def get_entitlements(db, current_user):  # shadows import at line 13
    return get_entitlements(db, current_user.id)  # calls itself → RecursionError
```

Hitting `GET /api/me/entitlements` will crash with a `RecursionError` (infinite recursion).

**File:**
- `app/api/routes/entitlements.py:13-17`

---

### A5. CORS middleware completely missing — FRONTEND BLOCKED

`app/main.py` does **not** import or add CORS middleware. There is no `CORSMiddleware` anywhere in the application setup. Config validates `CORS_ALLOWED_ORIGINS` (`config.py:134`) but the value is never consumed by any middleware. **The frontend will be blocked by the browser's same-origin policy.**

**File:**
- `app/main.py` (missing entirely)

---

### A6. OpenAI errors not caught by domain error handler — UNSTRUCTURED 500s

`app/integrations/openai_client.py:45` raises `RuntimeError` on API failures:

```python
raise RuntimeError(f"OpenAI request failed: {resp.status_code} {resp.text}")
```

But `app/main.py` only handles `DomainError` and `RequestValidationError`. A `RuntimeError` will produce a bare FastAPI 500 response without the error contract format (`error_code`, `message`, `details`, `request_id`). This violates the API contract and makes client-side error handling impossible for AI failures.

**Files:**
- `app/integrations/openai_client.py:44-45`
- `app/main.py:23-50`

---

## Section B: Missing Features (P1)

Per `docs/artefacts/MVP_SCOPE_LOCK.md`, these features are **in scope** for MVP but have **zero implementation**:

| Feature | Status | Evidence |
|---|---|---|
| **Proposal drafting** | NOT STARTED | No `proposals` table, model, migration, route, or service. Only enum value `PROPOSAL_CREATE` in `usage_ledger.py:15` |
| **Proposal regeneration** | NOT STARTED | No regeneration endpoint or logic. Only enum value `PROPOSAL_REGEN` in `usage_ledger.py:16` |
| **DOCX export** | NOT STARTED | No export route, service, or `python-docx` dependency. Only enum value `DOCX_EXPORT` in `usage_ledger.py:17` |
| **Stripe subscription lifecycle** | NOT STARTED | Config env vars exist (`config.py:43-49`), `stripe_subscription_id` column in migration `0005`, but NO Stripe SDK, no webhook handler, no checkout session flow |
| **Transactional emails** (beyond magic link) | NOT STARTED | Resend is used only for magic link (`auth.py:316-326`). No email service for fit scan results, proposal ready, subscription events, etc. |

**Scope gap summary:** 5 of 6 MVP features are unbuilt. Only Fit Scan has implementation (with caveats from Section A bugs).

---

## Section C: Schema Mismatches (P0/P1)

### C1. `users` table — missing `stripe_customer_id`

`DB_FIELD_CONTRACT_USERS.md` specifies a `stripe_customer_id` column. Neither migration `0002` nor model `user.py` includes it. This is required for Stripe integration.

**Severity:** P1 (blocks Stripe feature, which is itself unbuilt)

---

### C2. `user_plans` table — 4 column mismatches

*(see A1 for full details)*

| Contract / Migration | Model | Issue |
|---|---|---|
| `billing_period_start` | `current_period_start` | Name mismatch |
| `billing_period_end` | `current_period_end` | Name mismatch |
| `stripe_subscription_id` | *(absent)* | Missing in model |
| *(absent)* | `plan_activated_at` | Missing in migration |

**Severity:** P0 (runtime crash)

---

### C3. `ngo_profiles` table — attribute name mismatch

*(see A2 for full details)*

| Migration column | Model attribute | Issue |
|---|---|---|
| `country_of_registration` | `organization_country_of_registration` | Implicit column name derived from attribute name doesn't match DB |

**Severity:** P0 (runtime crash)

---

### C4. `usage_ledger` table — phantom columns in service layer

*(see A3 for full details)*

`quota_service.py` attempts to set `period_start` and `period_end` on `UsageLedger` — columns that don't exist in the model or migration.

**Severity:** P0 (data silently not persisted; dependent on A1 crash path)

---

### C5. Column alias mapping in `UsageLedger` — correctly handled

The `UsageLedger` model uses column aliases that **do** match the migration:

| Model attribute | DB column (via alias) | Status |
|---|---|---|
| `event_type` | `action_type` | Correct |
| `occurred_at` | `created_at` | Correct |
| `metadata_json` | `metadata` | Correct |

No issue here — included for completeness.

---

## Section D: Endpoint Gap Analysis

### Implemented Routes

| Endpoint | Method | File | Line | Status |
|---|---|---|---|---|
| `/health` | GET | `health.py` | 9 | Working |
| `/api/auth/google/start` | GET | `auth.py` | 141 | Working |
| `/api/auth/google/callback` | GET | `auth.py` | 175 | Working |
| `/api/auth/magic-link/request` | POST | `auth.py` | 285 | Working |
| `/api/auth/magic-link/consume` | POST | `auth.py` | 340 | Working |
| `/api/auth/refresh` | POST | `auth.py` | 398 | Working |
| `/api/auth/logout` | POST | `auth.py` | 445 | Working |
| `/api/auth/test-mode/mint` | POST | `auth.py` | 464 | Working (test-only) |
| `/api/me/entitlements` | GET | `entitlements.py` | 12 | **BROKEN** (A4: infinite recursion) |
| `/api/fit-scans` | POST | `fit_scans.py` | 18 | **BROKEN** (blocked by A1/A2) |
| `/api/fit-scans/{id}` | GET | `fit_scans.py` | 31 | **BROKEN** (blocked by A1/A2) |
| `/ngo-profile` | POST | `ngo_profile.py` | 22 | **BROKEN** (A2: column mismatch) |
| `/ngo-profile` | GET | `ngo_profile.py` | 60 | **BROKEN** (A2: column mismatch) |
| `/ngo-profile` | PUT | `ngo_profile.py` | 97 | **BROKEN** (A2: column mismatch) |
| `/ngo-profile/completeness` | GET | `ngo_profile.py` | 135 | **BROKEN** (A2: column mismatch) |

### Missing per API_CONTRACT.md

| Endpoint | Method | Contract Section | Status |
|---|---|---|---|
| `POST /api/proposals` | POST | Proposals | NOT IMPLEMENTED |
| `GET /api/proposals/{id}` | GET | Proposals | NOT IMPLEMENTED |
| `POST /api/proposals/{id}/regenerate` | POST | Proposals | NOT IMPLEMENTED |
| `GET /api/proposals/{id}/export` | GET | Document Export | NOT IMPLEMENTED |

### Additional Route Issues

- **Inconsistent prefix:** NGO profile routes are mounted at `/ngo-profile` not `/api/ngo-profile`, inconsistent with all other API routes under `/api/`.
- **Auth plan hardcoding:** All auth endpoints hardcode `plan="FREE"` in access tokens (`auth.py:258,377,430,492`). Paid users will always appear as FREE in JWT claims.

---

## Section E: Dependency Gaps

**Current `requirements.txt` contents:**

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic-settings==2.12.0
SQLAlchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
PyJWT==2.8.0
httpx==0.25.2
pytest==7.4.3
```

| Package | Required For | Status | Notes |
|---|---|---|---|
| `stripe` | Billing / subscriptions | **MISSING** | No implementation exists either |
| `python-docx` | DOCX export | **MISSING** | No implementation exists either |
| `resend` | Transactional emails | Not needed | `auth.py` uses raw `httpx` calls to Resend API directly |
| `openai` | AI calls | Not needed | Custom `httpx`-based client at `app/integrations/openai_client.py` |
| `slowapi` or rate-limit lib | Production rate limiting | **MISSING** | Current rate limiter is an in-memory dict; won't work across multiple workers/instances |

---

## Section F: Configuration Issues

### F1. CORS middleware not applied (P0)

See [A5](#a5-cors-middleware-completely-missing--frontend-blocked). `config.py` validates `CORS_ALLOWED_ORIGINS` but `main.py` never imports or adds `CORSMiddleware`. The setting is validated then discarded.

### F2. Rate limiting is in-memory only

`app/core/rate_limit.py` uses an in-memory dict. With multiple uvicorn workers or Railway instances, each worker has its own state. Rate limits are not enforced globally. Acceptable for MVP single-worker deploy, but fragile.

### F3. Test-mode endpoint properly guarded

`POST /api/auth/test-mode/mint` (`auth.py:464`) is gated behind `TEST_MODE=true` + `x-test-mode-secret` header + rate limiting (3/hour). Has a TODO comment to remove post-launch. Acceptable for smoke testing.

### F4. Hardcoded redirect URL

`auth.py:26-27` hardcodes:

```python
AUTH_POST_LOGIN_REDIRECT_URL = "https://grantpilot.ngoinfo.org/auth/callback"
```

This line is also duplicated. The URL should come from config for environment flexibility (dev/staging/prod).

### F5. Auth always emits plan="FREE"

All auth endpoints pass `"FREE"` to `create_access_token()`. If the frontend reads plan from JWT claims, paid users will appear as free-tier.

---

## Section G: Recommended Execution Order

Based on `mvp_execution_plan_FINAL.md` and findings above, this is the recommended execution order with audit-informed priorities.

### Day 1: Fix the foundation (everything else is blocked)

| Priority | Task | Ref | Blocks |
|---|---|---|---|
| 1 | **Schema alignment migration** — fix `user_plans` column names, add `plan_activated_at`, add `stripe_customer_id` to `users` | C-00, A1, C1, C2 | Quota, entitlements, Stripe |
| 2 | **Fix `ngo_profiles` model** — rename `organization_country_of_registration` → `country_of_registration` to match migration, fix all service/route references | A2, C3 | Profiles, fit scans, prompts |
| 3 | **Fix entitlements recursion bug** — rename route function or use import alias | A4 | Entitlements endpoint |
| 4 | **Add CORS middleware** to `app/main.py` using `CORS_ALLOWED_ORIGINS` from config | A5, C-01A | Frontend access |
| 5 | **Remove phantom columns** from `record_usage()` in `quota_service.py` | A3, C4 | Usage recording |

### Day 2: Stabilize existing features

| Priority | Task | Ref |
|---|---|---|
| 6 | **Auth hardening** — fix hardcoded redirect URL, fix plan="FREE" hardcoding in tokens | C-01, F4, F5 |
| 7 | **AI degradation handling** — catch `RuntimeError` from OpenAI client, convert to `DomainError` | A6, C-02 |
| 8 | **Quota enforcement correctness** — verify after schema fixes | C-03 |

### Day 3: Complete Fit Scan certification

| Priority | Task | Ref |
|---|---|---|
| 9 | **Fit Scan end-to-end test** — verify full flow after A1/A2 fixes | C-04 |

### Day 4-5: Build missing features

| Priority | Task | Ref |
|---|---|---|
| 10 | **Proposals** — new migration, model, routes, service, AI prompts | C-05A/B |
| 11 | **Proposal regeneration** | C-06 |
| 12 | **DOCX export** — add `python-docx` dependency | C-07 |

### Day 6: Billing

| Priority | Task | Ref |
|---|---|---|
| 13 | **Stripe integration** — add `stripe` dependency, webhook handler, checkout flow | C-08 |

### Day 7: Polish

| Priority | Task | Ref |
|---|---|---|
| 14 | **Transactional emails** — email service beyond magic link | C-09 |
| 15 | **Production hardening** — remove test-mode endpoint for prod, verify rate limiting | C-10 |

### Critical Path Diagram

```
Schema fixes (A1,A2,A3) → Entitlements fix (A4) → CORS (A5) → AI error handling (A6)
         │
         ▼
Profile CRUD works → Fit Scan works → Quota works
         │
         ▼
Proposals (new build) → Regeneration → Export → Stripe → Emails → Launch
```

---

## Summary

| Category | Count |
|---|---|
| P0 Critical Blockers | 6 |
| P1 Missing Features | 5 |
| Schema Mismatches | 4 distinct issues |
| Missing Endpoints | 4 (all proposal-related) |
| Broken Endpoints | 6 (profile + entitlements + fit scans) |
| Missing Dependencies | 2 (stripe, python-docx) |
| Configuration Issues | 5 |

**Bottom line:** The codebase has solid architectural patterns (service layer, domain errors, typed schemas, prompt input builder), but **6 P0 runtime bugs prevent any feature beyond basic auth from functioning** against a real database. The schema alignment fix (C-00 in the execution plan) is correctly identified as the first priority. Five of six MVP features (proposals, regeneration, export, Stripe, transactional emails) are entirely unbuilt and represent the bulk of remaining work.
