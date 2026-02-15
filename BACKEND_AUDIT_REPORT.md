# GrantPilot Backend Audit Report

**Date:** 2026-02-15
**Auditor:** Claude (automated)
**Branch:** `claude/audit-google-oauth-PXTlp`
**Authoritative Refs:** mvp_execution_plan_FINAL_2.md, API_CONTRACT.md, GUARDRAILS_RUNTIME_AND_SECURITY.md, PRICING_AND_ENTITLEMENTS.md, ENUM_REGISTRY.md, DB_FIELD_CONTRACT_*.md

---

## A) PASS/FAIL Summary — Coverage Map (Plan → Code)

### Pre-existing Items (marked "Working" in plan)

| Plan Item | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| FastAPI app structure | **PASS** | `app/main.py` | CORS, error handlers, router registration |
| Health endpoint | **PASS** | `app/api/routes/health.py` | `GET /health` |
| Database + Migrations 0001–0006 | **PASS** | `alembic/versions/0001–0006` | All exist |
| Auth: Magic link request | **PASS** | `app/api/routes/auth.py:341-406` | Rate limited, Resend integration |
| Auth: Magic link consume | **PASS** | `app/api/routes/auth.py:409-463` | Token validation, user create/find |
| Auth: Refresh token rotation | **PASS** | `app/api/routes/auth.py:466-520` | Revoke old, issue new, replaced_by FK |
| Auth: Logout/revocation | **PASS** | `app/api/routes/auth.py:523-544` | Revokes refresh token |
| Auth: Test-mode mint | **PASS** | `app/api/routes/auth.py:547-602` | Gated by `TEST_MODE` + secret |
| JWT creation + validation | **PASS** | `app/core/security.py:27-43`, `app/api/dependencies/auth.py` | HS256, plan claim, audience/issuer |
| Rate limiting (in-memory) | **PASS** | `app/core/rate_limit.py` | Per-IP, per-user, per-email buckets |
| NGO Profile CRUD | **PARTIAL** | `app/api/routes/ngo_profile.py` | **BUG: router prefix `/ngo-profile` not `/api/ngo-profile`** |
| Profile completeness | **PASS** | `app/services/profile_service.py:46-85` | 7-field scoring, status COMPLETE/DRAFT |
| Entitlements endpoint | **PASS** | `app/api/routes/entitlements.py`, `app/services/quota_service.py:112-132` | Returns plan + quotas |
| CORS middleware | **PASS** | `app/main.py:20-26` | Configurable origins |
| Quota enforcement | **PASS** | `app/services/quota_service.py:135-164` | Per plan limits, period-aware |

### C-05: Google OAuth (Authlib + Secure Code Exchange)

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| Authlib dependency | **PASS** | `requirements.txt` | `authlib`, `httpx` present |
| `app/core/oauth.py` | **MISSING** | — | Authlib integration built directly in auth.py routes instead of separate module; functionally equivalent |
| `GET /api/auth/google/start` | **PASS** | `app/api/routes/auth.py:163-198` | PKCE + state, returns authorization_url |
| `GET /api/auth/google/callback` | **PASS** | `app/api/routes/auth.py:201-294` | Redirects with code (no tokens in URL) |
| `POST /api/auth/exchange` | **PASS** | `app/api/routes/auth.py:297-338` | Single-use code, returns tokens+user |
| Auth code DB-backed | **PASS** | `app/models/auth_oauth_exchange_code.py`, migration `0008` | DB-backed (not in-memory), 60s TTL |
| Plan hardcoding fix | **PASS** | `app/services/auth_service.py:90-100` | `resolve_user_plan()` reads from user_plans |
| Redirect URL from config | **PASS** | `app/services/auth_service.py:103-104` | Uses `AUTH_POST_LOGIN_REDIRECT_URL` |
| Redirect allowlist | **PASS** | `app/services/auth_service.py:114-117` | Checks `AUTH_ALLOWED_REDIRECT_URLS` |
| Tests | **PASS** | 8 auth tests pass | account linking, exchange, redirect, start |

### C-06: Smoke Test Update

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| Updated smoke script | **PARTIAL** | `scripts/smoke_test.py` exists | Not verified for Authlib-specific checks |

### C-07A: Proposal Database + Model

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| Migration | **PASS** | `alembic/versions/0011_proposals.py` | Table, indexes correct |
| Model | **PARTIAL** | `app/models/proposal.py` | **BUG: `server_default=text("DRAFT")` is unquoted SQL** (migration is correct) |
| Schemas | **PASS** | `app/schemas/proposal.py` | Create, Response, Detail, Export schemas |
| Registered in __init__ | **PASS** | `app/models/__init__.py:7` | Proposal imported |

### C-07B: Proposal Creation + Retrieval

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| `app/ai/prompt_runner.py` | **PASS** | Lines 53-129 | Thin OpenAI wrapper, JSON validation, DomainError wrapping |
| `app/ai/prompt_inputs_builder.py` | **PASS** | Exists | Builds prompt_inputs per PROMPT_INPUTS_FIELD_MAPPING |
| `app/ai/prompts/` | **PASS** | `fit_scan.py`, `proposal.py`, `user_input_norm.py` | GP-P01, GP-P02, GP-F01, GP-F02, GP-U01 |
| `app/services/proposal_service.py` | **PASS** | Lines 36-153 | Validates opportunity, profile, requirements, quota |
| `POST /api/proposals` | **PASS** | `app/api/routes/proposals.py:21-29` | Auth required |
| `GET /api/proposals/{id}` | **PASS** | `app/api/routes/proposals.py:32-40` | Auth + ownership |
| Partial failure handling | **PASS** | `proposal_service.py:112-117` | >=1 generated → persist; all fail → no persist |
| 5-item generation cap | **PASS** | `proposal_service.py:353-357` | `generatable_items[:5]`, excess → MANUAL_REQUIRED |
| Incomplete profile → 409 | **PASS** | `proposal_service.py:50-58` | PROFILE_INCOMPLETE with missing_fields |
| Invalid requirements → 422 | **PASS** | `proposal_service.py:60-74` | REQUIREMENTS_INVALID |
| Quota enforcement | **PASS** | `proposal_service.py:77-82` | `enforce_quota` before AI call |
| Rate limit (10min) | **PASS** | `proposal_service.py:321-344` | Checks last PROPOSAL_CREATE in usage_ledger |
| Ownership check | **PASS** | `proposal_service.py:163-168` | user_id comparison, 403 FORBIDDEN |

### C-08: Proposal Regeneration

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| `POST /api/proposals/{id}/regenerate` | **PASS** | `app/api/routes/proposals.py:43-51` | Auth required |
| Free plan → 403 | **PASS** | `proposal_service.py:174-179` | REGENERATION_NOT_ALLOWED |
| Max 3 regenerations | **PASS** | `proposal_service.py:180-185` | REGENERATION_LIMIT_REACHED |
| Re-attempts FAILED sections | **PASS** | `proposal_service.py:473-550` | MANUAL_REQUIRED stays, others retried |
| Version + count increment | **PASS** | `proposal_service.py:264-265` | Atomic increment |
| Usage ledger tracking | **PASS** | `proposal_service.py:272-278` | PROPOSAL_REGEN action type |

### C-09: DOCX Export

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| `python-docx` dependency | **PASS** | `requirements.txt` | Present |
| `app/services/export_service.py` | **PASS** | Lines 19-61 | DOCX generation, professional formatting |
| `POST /api/proposals/{id}/export` | **PASS** | `app/api/routes/proposals.py:54-71` | Binary response, correct Content-Type |
| Format validation | **PASS** | `export_service.py:26-31` | Non-DOCX → 422 UNSUPPORTED_FORMAT |
| Ownership check | **PASS** | Via `get_proposal()` | 403 FORBIDDEN |
| Idempotency | **PASS** | `export_service.py:49-58` | Key: `docx_export:{user}:{proposal}:v{version}` |
| Tests (9/9 pass) | **PASS** | `tests/test_c09_docx_export.py` | All 9 tests pass |

### C-10: Stripe Billing

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| `stripe` dependency | **PASS** | `requirements.txt` | Present |
| `stripe_events` migration | **PASS** | `alembic/versions/0009_stripe_events.py` | Table + indexes |
| `stripe_events` model | **PASS** | `app/models/stripe_event.py` | Matches DB_FIELD_CONTRACT |
| `POST /api/billing/checkout` | **PASS** | `app/api/routes/billing.py:46-83` | Auth, plan validation, conflict check |
| `GET /api/billing/portal` | **PASS** | `app/api/routes/billing.py:86-101` | Auth, customer check |
| `POST /api/billing/webhook` | **PASS** | `app/api/routes/billing.py:104-190` | Signature verify, event-store-first |
| Event-store-first | **PASS** | `billing.py:140-152` | Persist → process → update result |
| Idempotency (duplicate events) | **PASS** | `billing_service.py:177-181` | Check stripe_event_id before insert |
| `checkout.session.completed` | **PASS** | `billing_service.py:203-237` | Resolves user, syncs plan |
| `customer.subscription.updated` | **PASS** | `billing_service.py:239-266` | Syncs plan from price_id |
| `customer.subscription.deleted` | **PASS** | `billing_service.py:268-274` | Downgrades to FREE |
| `invoice.payment_failed` | **PASS** | `billing_service.py:276-278` | Logs only (Stripe handles retries) |
| Tests | **PASS** | `tests/test_billing_service.py` | 2 tests pass (persist idempotent, subscription deleted) |

### C-11: Transactional Emails

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| Email service | **MISSING** | No `app/services/email_service.py` | Plan marks P2, defer allowed |
| Proposal ready email | **MISSING** | — | Plan says "Required for launch" |
| Subscription activated email | **MISSING** | — | Plan says "Required for launch" |

**Note per task instructions:** Emails treated as "defer allowed" unless mvp_execution_plan_FINAL_2.md marks as MVP/P0 gating. Plan says P2, so this is flagged but NOT a blocker.

### C-12: Production Hardening

| Sub-item | Status | Evidence | Notes |
|----------|--------|----------|-------|
| Catch-all exception handler | **MISSING** | `app/main.py` | Only DomainError + ValidationError handlers |
| RequestID middleware | **MISSING** | No middleware file | Reads header but doesn't generate |
| Test-mode gating | **PASS** | `auth.py:551-553` | Returns 404 when TEST_MODE=false |
| Config validation | **PASS** | `app/core/config.py:77-195` | Validates all required env vars |

---

## B) Top 10 Issues (Ordered by Severity)

### P0 BLOCKERS

#### 1. Missing Catch-All Exception Handler (GUARDRAILS Rule 5 Violation)
- **File:** `app/main.py` (missing handler)
- **Contract:** GUARDRAILS_RUNTIME_AND_SECURITY.md Section 2, lines 137-149
- **Impact:** Any unhandled exception (e.g., `InvalidActionTypeError`, DB connection errors, unexpected AttributeError) returns a FastAPI default 500 response with **stack trace** visible to the client. This leaks internal implementation details.
- **Severity:** P0 — Security + contract violation

#### 2. NGO Profile Router Prefix Missing `/api` Prefix
- **File:** `app/api/routes/ngo_profile.py:19`
- **Code:** `router = APIRouter(prefix="/ngo-profile", ...)`
- **Contract:** mvp_execution_plan_FINAL_2.md endpoint table lists `POST /api/ngo-profile`, `GET /api/ngo-profile`, `PUT /api/ngo-profile`, `GET /api/ngo-profile/completeness`
- **Impact:** All NGO profile endpoints mount at `/ngo-profile/*` instead of `/api/ngo-profile/*`. Frontend calls to `/api/ngo-profile` will return 404. **This breaks the entire profile CRUD flow.**
- **Severity:** P0 — Frontend-breaking routing error

#### 3. Fit Scan Quota Check + Decrement Not Atomic
- **File:** `app/services/fit_scan_service.py:60,79-84`
- **Contract:** GUARDRAILS_RUNTIME_AND_SECURITY.md Rule 3
- **Code flow:**
  1. Line 60: `enforce_quota(self.db, user.id, ...)` — checks + commits
  2. Lines 62-76: AI call runs (long operation, 5-30 seconds)
  3. Lines 79-84: `record_usage(...)` — decrements + commits
- **Impact:** Between step 1 and step 3, another request could pass the quota check. This enables double-spending on fit scans. (Proposal service handles this better with `commit=False` + `begin()` block, but fit scan does not.)
- **Severity:** P0 — Quota bypass (GUARDRAILS Rule 3 explicitly says "Never split check and decrement into separate transactions")

### P1 HIGH

#### 4. Proposal Model `server_default=text("DRAFT")` Invalid SQL
- **File:** `app/models/proposal.py:37`
- **Code:** `server_default=text("DRAFT")` → generates `DEFAULT DRAFT` (unquoted)
- **Impact:** The Alembic migration (`0011_proposals.py:60`) correctly uses `server_default="DRAFT"` so the table is fine in Railway. But if anyone uses `Base.metadata.create_all()` (e.g., in tests or a fresh setup), it will fail with a PostgreSQL syntax error. Tests work because they use SQLite.
- **Severity:** P1 — Silent divergence between model and DB; breaks direct table creation

#### 5. No RequestID Middleware (GUARDRAILS Section 2)
- **File:** `app/main.py` — middleware section
- **Contract:** GUARDRAILS_RUNTIME_AND_SECURITY.md Section 2 ("Request ID — For Debugging")
- **Impact:** If client doesn't send `X-Request-ID` header, error responses have no `request_id` field. Debugging production issues becomes difficult because there's no way to correlate logs with specific requests.
- **Severity:** P1 — Debugging/operational gap

#### 6. Global `openai.api_key` Assignment (Race Condition)
- **File:** `app/ai/prompt_runner.py:84`
- **Code:** `openai.api_key = settings.OPENAI_API_KEY`
- **Impact:** Sets global state on every prompt call. In async/concurrent contexts, this could cause race conditions. Currently mitigated by single-worker deployment (Section 2.5), but fragile.
- **Note:** `app/integrations/openai_client.py` already has a per-request client pattern that avoids this.
- **Severity:** P1 — Works for MVP single-worker, but technical debt

#### 7. Quota Test Broken
- **File:** `tests/test_quota_service.py::test_enforce_quota_exhausted`
- **Error:** `TypeError: fake_plan() got an unexpected keyword argument 'commit'`
- **Impact:** The mock doesn't match the current function signature after `commit` kwarg was added to `get_or_create_user_plan()`. Test is always failing.
- **Severity:** P1 — Test suite unreliable

### P2 MEDIUM

#### 8. API_CONTRACT.md Internal Inconsistency — Export Endpoint Method
- **File:** `docs/artefacts/API_CONTRACT.md:299` says `GET /api/proposals/{id}/export`
- **File:** `docs/artefacts/API_CONTRACT.md:303` says `POST /api/proposals/{id}/export`
- **Code:** `app/api/routes/proposals.py:54` uses `POST`
- **Impact:** Documentation confusion for frontend dev. POST is correct (needs request body with `format`).
- **Severity:** P2 — Doc inconsistency only

#### 9. Transactional Emails Not Implemented (C-11)
- **Contract:** mvp_execution_plan_FINAL_2.md C-11, marked P2
- **Impact:** No email sent when proposal is ready or subscription activates. Per task instructions, treated as "defer allowed."
- **Severity:** P2 — Deferred

#### 10. `InvalidActionTypeError` Not Handled by Any Exception Handler
- **File:** `app/core/errors.py:24-26`, raised in `app/services/quota_service.py:179`
- **Impact:** If somehow an invalid action_type is passed to `record_usage()`, the `InvalidActionTypeError` (a `ValueError`, not `DomainError`) propagates unhandled. Currently impossible in normal code paths since all callers use `UsageActionType` enum values, but it's a defense-in-depth gap.
- **Severity:** P2 — Defensive gap (amplified by missing catch-all handler #1)

---

## C) Reproduction Steps for Each Issue

### Issue 1: Missing Catch-All Exception Handler
```bash
# Force an unhandled exception (e.g., by making a request that triggers InvalidActionTypeError or DB error)
# Any endpoint that throws a non-DomainError exception will leak a stack trace:
curl -s http://localhost:8000/api/proposals/not-a-uuid | python3 -m json.tool
# If FastAPI's default handler fires, response will include "detail" with traceback info
```

### Issue 2: NGO Profile Router Wrong Prefix
```bash
# These will 404:
curl -s http://localhost:8000/api/ngo-profile -H "Authorization: Bearer $TOKEN"
# → 404 Not Found ({"detail":"Not Found"})

# This would work (wrong path):
curl -s http://localhost:8000/ngo-profile -H "Authorization: Bearer $TOKEN"
```

### Issue 3: Fit Scan Quota Non-Atomic
```bash
# Scenario: Free user has 1 fit scan quota
# Conceptual race (hard to reproduce in single-worker, but the code gap exists):
#   T1: POST /api/fit-scans → passes enforce_quota → starts AI call
#   T2: POST /api/fit-scans → passes enforce_quota → starts AI call
#   T1: AI returns → record_usage → now used=1
#   T2: AI returns → record_usage → now used=2 (should have been blocked)
#
# Code evidence:
#   fit_scan_service.py:60 — enforce_quota commits
#   fit_scan_service.py:62-76 — AI call (outside transaction)
#   fit_scan_service.py:79-84 — record_usage commits
```

### Issue 4: Proposal Model Default
```python
# In a Python shell:
from sqlalchemy import text
print(text("DRAFT").text)  # → "DRAFT" (no SQL quotes)
# DDL would produce: status TEXT NOT NULL DEFAULT DRAFT
# PostgreSQL interprets DRAFT as a column reference → ERROR
```

### Issue 5: No RequestID Middleware
```bash
# Send request without X-Request-ID:
curl -s http://localhost:8000/api/me/entitlements
# Response error (if 401) has no request_id field
```

### Issue 6: Global openai.api_key
```python
# In app/ai/prompt_runner.py:84
openai.api_key = settings.OPENAI_API_KEY  # Global mutation
# Inspect: print(id(openai.api_key))
```

### Issue 7: Broken Quota Test
```bash
cd /home/user/ngoinfo-grantpilot
python -m pytest tests/test_quota_service.py::test_enforce_quota_exhausted -v
# FAILS: TypeError: fake_plan() got unexpected keyword argument 'commit'
```

---

## D) Recommendation: Safe to Proceed to Frontend?

### **VERDICT: CONDITIONAL YES — Fix 3 P0 issues first (< 1 hour total)**

The backend is substantially complete for MVP. The core API flows (auth, proposals, fit scans, export, billing) are implemented and largely correct. However, **3 P0 issues must be fixed before frontend work begins:**

| Fix | Effort | Why Blocking |
|-----|--------|-------------|
| Add catch-all Exception handler in `main.py` | 5 min | Security: stack traces leak to users |
| Fix NGO profile router prefix to `/api/ngo-profile` | 1 min | Routing: frontend can't reach profile CRUD |
| Make fit scan quota atomic (match proposal pattern) | 15 min | Quota: free users could double-spend |

After these 3 fixes, frontend work can proceed safely.

**P1 items (4-7) can be addressed in parallel with frontend development** — they don't block any frontend integration path, and P1-4 (model default) only affects test environments.

---

## E) Minimal Assumptions Frontend Can Make About API Behavior

Once P0 issues 1-3 are fixed, the frontend can rely on:

### Stable Contracts

1. **Auth endpoints** — All working at `/api/auth/*`:
   - Magic link: request → consume → tokens
   - Google OAuth: start → (browser redirect) → exchange → tokens
   - Refresh: send refresh_token → new tokens
   - Logout: send refresh_token → logged out
   - Token shape: `{ access_token, refresh_token, token_type, expires_in, user: { id, email, full_name, plan } }`

2. **Protected endpoints** require `Authorization: Bearer <jwt>` header
   - Missing/invalid → 401 `AUTH_REQUIRED` or `AUTH_INVALID`

3. **NGO Profile** at `/api/ngo-profile` (after fix #2):
   - POST (create), GET (read), PUT (update) — all return full profile object
   - GET `/api/ngo-profile/completeness` — returns `{ profile_status, completeness_score, missing_fields }`

4. **Entitlements** at `GET /api/me/entitlements`:
   - Returns `{ plan, period: { type, start_at, end_at, resets_at }, quotas: { fit_scans: { allowed, used, remaining }, proposals: { ... } } }`

5. **Fit Scans** at `/api/fit-scans`:
   - POST: create (requires complete profile + quota)
   - GET `/{id}`: retrieve (ownership enforced)
   - Response wrapped in `{ fit_scan: { ... } }` envelope

6. **Proposals** at `/api/proposals`:
   - POST: create (requires complete profile + valid opportunity + quota)
   - GET `/{id}`: retrieve with full `content_json`
   - POST `/{id}/regenerate`: Growth/Impact only, max 3
   - POST `/{id}/export`: returns DOCX binary stream

7. **Error envelope** (all endpoints):
   ```json
   { "error_code": "CONSTANT_CASE", "message": "Human readable", "details": {}, "request_id": "optional" }
   ```

8. **Billing** at `/api/billing/*`:
   - POST `/checkout`: `{ "plan": "GROWTH"|"IMPACT" }` → `{ "checkout_url": "..." }`
   - GET `/portal`: → `{ "portal_url": "..." }`
   - Webhook handling is backend-internal (Stripe → backend)

### Known Limitations for Frontend

- Export only supports DOCX (not PDF) — non-DOCX → 422 `UNSUPPORTED_FORMAT`
- Quota reset is tied to billing cycle, not calendar month
- No proposal listing endpoint yet (`GET /api/proposals` not implemented — only single retrieval)
- No transactional emails beyond magic link
- `request_id` in error responses only present if client sends `X-Request-ID` header (until middleware is added)
- Free plan: 1 fit scan + 1 proposal lifetime, no regeneration
- Rate limits: Growth/Impact proposals limited to 1 per 10 minutes

---

## Test Results Summary

| Test File | Tests | Pass | Fail |
|-----------|-------|------|------|
| test_auth_account_linking.py | 3 | 3 | 0 |
| test_auth_exchange.py | 2 | 2 | 0 |
| test_auth_google_callback_redirect.py | 1 | 1 | 0 |
| test_auth_google_start.py | 2 | 2 | 0 |
| test_auth_redirects.py | 2 | 2 | 0 |
| test_billing_service.py | 2 | 2 | 0 |
| test_c09_docx_export.py | 9 | 9 | 0 |
| test_quota_service.py | 2 | 1 | 1 |
| **Total** | **23** | **22** | **1** |

---

**END OF AUDIT REPORT**
