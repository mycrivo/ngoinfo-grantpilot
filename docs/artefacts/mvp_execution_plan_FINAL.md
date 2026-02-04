# GrantPilot MVP Execution Plan (FINAL)

Status: **Canonical — LOCKED FOR BUILD**  
Version: **3.0 (FINAL)**  
Last updated: **2026-02-04**  
Timeline: **7 Days**

## Authoritative Inputs
- AS_IS_AUDIT_20260202.md (Cursor audit, repo-based)
- CTO Gap Analysis (Claude, 2026-02-03)
- Railway Swagger snapshot (current deployed surface)
- API_CONTRACT.md, MVP_SCOPE_LOCK.md, PRICING_AND_ENTITLEMENTS.md
- DB_FIELD_CONTRACT_*.md (all field contracts)
- OPENAI_PROMPTS_LIBRARY.md, PROMPT_INPUTS_FIELD_MAPPING.md

---

## 0. Purpose & Rules (Non-Negotiable)

This file is the **single source of truth** for all work until public go-live.

### Execution Rules
1. Each **C-XX** corresponds to **exactly one Cursor prompt**, **one GitHub commit**, and **one Railway deploy**
2. Work **must follow the order listed** — no skipping, no reordering
3. Cursor must **STOP and report** if a section cannot be completed without violating contracts
4. Dependencies must be satisfied before starting a commit
5. Exit criteria must ALL pass before marking complete

### How to Use in New Chats
```
"We are working on GrantPilot. Use `mvp_execution_plan_FINAL.md` as the 
authoritative execution plan. We are currently at **C-XX**. Do not analyse 
prior chats. Read the file and continue from current state."
```

---

## 1. Current As-Is State (Baseline from AS_IS_AUDIT)

### ✅ What Is Built & Working
| Component | Status | Evidence |
|-----------|--------|----------|
| Auth: Google OAuth start/callback | ✅ Complete | `app/api/routes/auth.py:L141-L290` |
| Auth: Magic link request/consume | ✅ Complete | `app/api/routes/auth.py:L293-L421` |
| Auth: Refresh/logout | ✅ Complete | `app/api/routes/auth.py:L424-L501` |
| Entitlements endpoint | ✅ Complete | `app/api/routes/entitlements.py:L9-L17` |
| NGO Profile CRUD + completeness | ✅ Complete | `app/api/routes/ngo_profile.py:L19-L146` |
| Fit Scan POST/GET | ✅ Partial | `app/api/routes/fit_scans.py:L15-L39` |
| Health endpoint | ✅ Complete | `app/api/routes/health.py:L6-L16` |
| AI prompt_inputs builder | ✅ Complete | `app/services/fit_scan_prompt_inputs.py` |
| Quota service (structure) | ✅ Partial | `app/services/quota_service.py` |

### ⚠️ Known Schema Mismatches (P0 — Must Fix First)
| Issue | Model Says | Migration Says | Impact |
|-------|-----------|----------------|--------|
| user_plans period columns | `plan_activated_at`, `current_period_start`, `current_period_end` | `billing_period_start`, `billing_period_end` (no `plan_activated_at`) | Quota service will crash |
| usage_ledger period fields | Service writes `period_start`, `period_end` | Columns don't exist in migration/model | Usage recording will fail |
| users.stripe_customer_id | Required per DB contract | Column missing from migration | Stripe billing will fail |

### ❌ Missing Features (P0/P1)
| Feature | Status | Contract Reference |
|---------|--------|-------------------|
| Proposal endpoints (create/get/regenerate) | ❌ Not implemented | `API_CONTRACT.md:L227-L231` |
| Proposal export (DOCX) | ❌ Not implemented | `API_CONTRACT.md:L233-L249` |
| proposals table | ❌ No migration/model | Required for C-05 |
| Stripe checkout + webhooks | ❌ Not implemented | `STRIPE_INTEGRATION_SPEC.md` |
| CORS middleware | ❌ Not configured | Blocks all browser testing |
| Degraded AI handling | ❌ Not implemented | `OPENAI_PROMPTS_LIBRARY.md` Section 9 |
| Transactional emails (beyond magic link) | ❌ Not implemented | `TRANSACTIONAL_EMAILS_SPEC.md` |

### ⚠️ Security/UX Issues
- Magic link email sends raw token (should be clickable link)
- Test-mode mint endpoint exists (must be gated/removed for prod)

---

## 2. Global Execution Invariants (Apply to ALL Commits)

After every C-XX completion, these must hold true:

| Invariant | Verification Method |
|-----------|-------------------|
| No 500s for expected states (AI failure, missing requirements, quota exhaustion) | Manual test + smoke script |
| No quota consumption on failed or degraded AI runs | Check usage_ledger after failed call |
| Only API_CONTRACT-allowed status codes and error envelopes | Swagger validation |
| No probabilistic or success-claim language in AI outputs | Review generated content |
| No prod deployment with test-only endpoints enabled | Check `APP_ENV` gating |
| CORS allows only configured origins | Browser preflight test |

**Violation of any invariant requires rollback before proceeding.**

---

## 3. Commit-Driven Execution Plan (7-Day Schedule)

### Day 1: Foundation Fixes

---

#### C-00: Database Schema Alignment (P0 — BLOCKER)
**Status:** ⬜ Not Started  
**Priority:** P0 — All subsequent commits depend on this  
**Estimated Time:** 2-3 hours  
**Dependencies:** None

**Scope:**
1. Create single corrective migration `0007_schema_alignment.py`:
   - Add `stripe_customer_id` (text, nullable, unique) to `users` table
   - Align `user_plans` columns:
     - Add `plan_activated_at` (timestamptz, nullable)
     - Rename or add `current_period_start` / `current_period_end` to match model
     - Keep `stripe_subscription_id` and `billing_period_*` if needed for Stripe
   - Add `period_start` / `period_end` (timestamptz, nullable) to `usage_ledger` OR remove references from service

2. Update SQLAlchemy models to match migration:
   - `app/models/user.py` — add `stripe_customer_id`
   - `app/models/user_plan.py` — align column names
   - `app/models/usage_ledger.py` — align column names

3. Update service layer to use canonical column names:
   - `app/services/quota_service.py` — fix period field references

**Exit Criteria:**
- [ ] Migration runs without error on fresh DB
- [ ] Migration runs without error on existing DB (Railway)
- [ ] `alembic upgrade head` succeeds
- [ ] Quota service can create usage_ledger entries without error
- [ ] Entitlements endpoint returns valid response

**Verification Commands:**
```bash
# After deploy to Railway
alembic upgrade head
python -c "from app.models import User, UserPlan, UsageLedger; print('Models OK')"
curl -X GET $BASE_URL/api/me/entitlements -H "Authorization: Bearer $TOKEN"
```

---

#### C-01A: CORS & Security Headers (P0 — BLOCKER)
**Status:** ⬜ Not Started  
**Priority:** P0 — Blocks all browser-based testing  
**Estimated Time:** 1-2 hours  
**Dependencies:** None (can parallel with C-00)

**Scope:**
1. Add CORS middleware to `app/main.py`:
   ```python
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. Verify `CORS_ALLOWED_ORIGINS` env var is set in Railway:
   - Production: `https://grantpilot.ngoinfo.org`
   - Staging: `https://staging.grantpilot.ngoinfo.org` (if exists)

3. Add security headers middleware (optional but recommended):
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`

**Exit Criteria:**
- [ ] Frontend can make authenticated API calls without CORS errors
- [ ] Preflight (OPTIONS) requests return correct headers
- [ ] No wildcard (`*`) in production CORS config

**Verification:**
```bash
# Test CORS preflight
curl -X OPTIONS $BASE_URL/api/me/entitlements \
  -H "Origin: https://grantpilot.ngoinfo.org" \
  -H "Access-Control-Request-Method: GET" \
  -v
```

---

### Day 2: Auth Hardening & AI Safety

---

#### C-01: Auth End-to-End Hardening
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-00, C-01A

**Scope:**
1. Magic link email improvement:
   - Change from raw token to clickable link
   - Link format: `{FRONTEND_URL}/auth/magic-link?token={token}`
   - Include expiry time in email body
   - Template per `TRANSACTIONAL_EMAILS_SPEC.md`

2. Google OAuth callback verification:
   - Verify redirect to `AUTH_POST_LOGIN_REDIRECT_URL`
   - Verify token issuance matches contract

3. Test-mode endpoint security:
   - Verify `POST /api/auth/test-mode/mint` returns 404 when `TEST_MODE=false`
   - Add explicit check: `if settings.APP_ENV == "prod": return 404`

4. Rate limiting verification:
   - Magic link request: 5/hour per email, 20/hour per IP
   - Confirm 429 response on limit exceeded

5. Error envelope validation:
   - All auth errors return `API_CONTRACT.md` error shape
   - No stack traces in responses

**Exit Criteria:**
- [ ] Magic link email contains clickable link (not raw token)
- [ ] Google OAuth flow completes end-to-end
- [ ] Test-mode mint returns 404 in prod environment
- [ ] Rate limiting returns 429 with correct error code
- [ ] All error responses match API_CONTRACT schema

**Verification:**
```bash
# Magic link flow
curl -X POST $BASE_URL/api/auth/magic-link/request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.org"}'
# Check email for link format

# Test-mode should fail in prod
curl -X POST $BASE_URL/api/auth/test-mode/mint \
  -H "X-Test-Mode-Secret: wrong" # Should return 404
```

---

#### C-02: AI Degradation & Safety Guarantees
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-00

**Scope:**
1. Implement `DEGRADED_*` response handling per `OPENAI_PROMPTS_LIBRARY.md` Section 9:
   - `DEGRADED_MISSING_REQUIREMENTS` — requirements_json missing/invalid
   - `DEGRADED_INVALID_VARIANT` — selected variant not found
   - `DEGRADED_INVALID_JSON` — AI returned unparseable JSON
   - `DEGRADED_MISSING_INPUTS` — critical inputs missing

2. Update `app/ai/fit_scan_executor.py`:
   - Wrap AI call in try/except
   - Parse response and check for `status: "DEGRADED"`
   - Return degraded response to user (not 500)

3. Update `app/services/fit_scan_service.py`:
   - Do NOT consume quota on degraded responses
   - Do NOT persist degraded results to fit_scans table
   - Return user-friendly error with `error_code`

4. Add pre-flight validation in `app/services/fit_scan_prompt_inputs.py`:
   - Check requirements_json exists and is valid
   - Check selected variant exists
   - Return early with degraded status if validation fails

**Exit Criteria:**
- [ ] Missing requirements_json returns degraded response (not 500)
- [ ] Invalid AI JSON returns degraded response (not 500)
- [ ] Quota is NOT consumed on any degraded path
- [ ] usage_ledger has no entries for failed/degraded runs
- [ ] User receives actionable error message

**Verification:**
```bash
# Test with opportunity missing requirements_json
curl -X POST $BASE_URL/api/fit-scans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"funding_opportunity_id": "uuid-with-missing-requirements"}'
# Should return error, not 500
# Check usage_ledger is unchanged
```

---

### Day 3: Quota & Fit Scan Certification

---

#### C-03: Quota Enforcement Correctness
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-00 (schema alignment required)

**Scope:**
1. Atomic quota check + decrement:
   - Use database transaction for check + decrement
   - Prevent race conditions on concurrent requests
   - Pattern: `SELECT ... FOR UPDATE` or optimistic locking

2. HTTP status correctness:
   - Quota exhausted → 429 (not 403)
   - Include `error_code: "QUOTA_EXCEEDED"`
   - Include plan-specific upgrade message

3. Plan-specific messaging per `PRICING_AND_ENTITLEMENTS.md`:
   - Free exhausted → "Upgrade to Growth for 10 Fit Scans/month"
   - Growth exhausted → "Upgrade to Impact for 20 Fit Scans/month"
   - Impact exhausted → "Quota resets on {date}"

4. Prevent double consumption:
   - Idempotency key per request (optional for MVP)
   - At minimum: quota decrement only after successful persistence

5. Period boundary handling:
   - Free plan: lifetime limits (no reset)
   - Growth/Impact: monthly limits based on billing cycle
   - Use `current_period_start` / `current_period_end` for calculation

**Exit Criteria:**
- [ ] Concurrent requests cannot over-consume quota
- [ ] Quota exhaustion returns 429 with correct message
- [ ] Free plan lifetime limits work correctly
- [ ] Growth/Impact monthly limits reset on period boundary
- [ ] usage_ledger entries reconcile with quota consumed

**Verification:**
```bash
# Exhaust quota on test account
for i in {1..5}; do
  curl -X POST $BASE_URL/api/fit-scans \
    -H "Authorization: Bearer $FREE_USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"funding_opportunity_id": "valid-uuid"}'
done
# 6th request should return 429
```

---

#### C-04: Fit Scan Certification
**Status:** ⛔ Blocked by C-02 and C-03  
**Priority:** P1  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-02, C-03

**Scope:**
1. Re-verify Fit Scan against C-02 guarantees:
   - Degraded paths tested
   - No 500s on edge cases

2. Re-verify against C-03 guarantees:
   - Quota enforcement working
   - 429 on exhaustion

3. Verify persisted fields match `DB_FIELD_CONTRACT_FIT_SCANS.md`:
   - `model_rating` (STRONG | MODERATE | WEAK)
   - `overall_recommendation` (RECOMMENDED | APPLY_WITH_CAVEATS | NOT_RECOMMENDED)
   - `subscores` (eligibility, alignment, readiness)
   - `result_json` (complete GP-F02 output)
   - `plan_at_time_of_scan`
   - `prompt_version`

4. Verify `prompt_inputs_json` is sole AI input:
   - No raw DB objects passed to prompt
   - All fields per `PROMPT_INPUTS_FIELD_MAPPING.md`

5. End-to-end test matrix:
   | Scenario | Expected Outcome |
   |----------|-----------------|
   | Valid opportunity, complete profile | Fit Scan persisted, quota decremented |
   | Missing requirements_json | Degraded response, no quota consumed |
   | Quota exhausted | 429, no AI call made |
   | AI timeout/error | Degraded response, no quota consumed |

**Exit Criteria:**
- [ ] All test matrix scenarios pass
- [ ] Fit Scan marked as "production certified"
- [ ] No changes to Fit Scan after this commit (feature freeze)

---

### Day 4: Proposal Foundation

---

#### C-05A: Proposal Database Foundation (P0)
**Status:** ⬜ Not Started  
**Priority:** P0 — Required before C-05B  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-00

**Scope:**
1. Create `DB_FIELD_CONTRACT_PROPOSALS.md` artefact defining:
   - `proposals` table schema
   - `proposal_sections` table schema (if needed)
   - Relationships, indexes, constraints

2. Create migration `0008_proposals.py`:
   ```
   proposals:
   - id (UUID, PK)
   - user_id (UUID, FK → users.id, ON DELETE CASCADE)
   - funding_opportunity_id (UUID, FK → funding_opportunities.id)
   - fit_scan_id (UUID, FK → fit_scans.id, nullable)
   - version (integer, default 1)
   - status (text: DRAFT | COMPLETE | EXPORTED)
   - plan_at_time_of_creation (text: FREE | GROWTH | IMPACT)
   - prompt_version (text)
   - content_json (JSONB) — full proposal content
   - regeneration_count (integer, default 0)
   - created_at (timestamptz)
   - updated_at (timestamptz)
   
   Indexes:
   - (user_id, created_at DESC)
   - (funding_opportunity_id)
   - (user_id, funding_opportunity_id)
   ```

3. Create SQLAlchemy model `app/models/proposal.py`

4. Create Pydantic schemas `app/schemas/proposal.py`:
   - `ProposalCreate`
   - `ProposalResponse`
   - `ProposalListResponse`

5. Register model in `app/models/__init__.py`

**Exit Criteria:**
- [ ] Migration runs successfully
- [ ] Model can be imported without error
- [ ] `DB_FIELD_CONTRACT_PROPOSALS.md` committed to docs/artefacts

**Verification:**
```bash
alembic upgrade head
python -c "from app.models import Proposal; print('Proposal model OK')"
```

---

#### C-05B: Proposal Creation Endpoint
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 4-5 hours  
**Dependencies:** C-05A, C-02, C-03

**Scope:**
1. Create `app/api/routes/proposals.py`:
   - `POST /api/proposals` — create initial draft
   - `GET /api/proposals/{id}` — retrieve proposal

2. Create `app/services/proposal_service.py`:
   - Generate proposal from `requirements_json.submission_items`
   - Use archetype detection per `OPENAI_PROMPTS_LIBRARY.md` Section 6.2
   - Persist only after successful generation

3. Create `app/ai/proposal_executor.py`:
   - Call GP-P02 prompt for each submission item
   - Aggregate responses into `content_json`
   - Handle degraded responses

4. Quota enforcement:
   - Check proposal quota before generation
   - Decrement only after successful persistence
   - Free: 1 lifetime, Growth: 3/month, Impact: 5/month

5. Register router in `app/main.py`

**Exit Criteria:**
- [ ] `POST /api/proposals` creates proposal
- [ ] `GET /api/proposals/{id}` returns proposal
- [ ] Proposal content generated from submission_items
- [ ] Quota consumed only on success
- [ ] Degraded response if requirements incomplete
- [ ] Response matches API_CONTRACT schema

---

### Day 5: Proposal Completion & Export

---

#### C-06: Proposal Regeneration
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-05B

**Scope:**
1. Add endpoint `POST /api/proposals/{id}/regenerate`

2. Plan gating:
   - Free: regeneration NOT allowed (return 403)
   - Growth/Impact: up to 3 regenerations per proposal

3. Regeneration logic:
   - Increment `regeneration_count`
   - Generate new content
   - Update `content_json` (overwrite or version — TBD)
   - Update `updated_at`

4. Quota tracking:
   - Regeneration consumes `PROPOSAL_REGEN` action type
   - Track in usage_ledger

5. Version handling (MVP decision):
   - Option A: Overwrite content (simpler)
   - Option B: Append-only versions (audit trail)
   - **Recommend Option A for MVP**

**Exit Criteria:**
- [ ] Free plan cannot regenerate (403)
- [ ] Growth/Impact can regenerate up to 3 times
- [ ] 4th regeneration returns 429 with message
- [ ] Content actually changes on regeneration
- [ ] usage_ledger tracks regenerations

---

#### C-07: DOCX Export
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 4-5 hours  
**Dependencies:** C-05B

**Scope:**
1. Add endpoint `POST /api/proposals/{id}/export`

2. DOCX generation:
   - Use `python-docx` library
   - Template with GrantPilot branding (minimal)
   - Include all proposal sections
   - Professional formatting

3. File storage:
   - Generate DOCX to temp file
   - Upload to S3-compatible storage (or Railway volume)
   - Generate signed URL with expiry (24 hours)

4. Response per API_CONTRACT:
   ```json
   {
     "export_url": "https://...",
     "expires_at": "ISO-8601",
     "format": "DOCX"
   }
   ```

5. Quota handling:
   - First export consumes `DOCX_EXPORT` action
   - Subsequent downloads of same version: no quota consumption
   - Track via `proposal.status = EXPORTED`

**Exit Criteria:**
- [ ] Export returns valid signed URL
- [ ] URL downloads valid DOCX file
- [ ] DOCX contains all proposal content
- [ ] Link expires after 24 hours
- [ ] Re-export of same version doesn't consume quota

---

### Day 6: Stripe & Billing

---

#### C-08: Stripe Subscription Lifecycle
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 6-8 hours  
**Dependencies:** C-00 (stripe_customer_id column)

**Scope:**
1. Add Stripe routes `app/api/routes/stripe.py`:
   - `POST /api/billing/checkout` — create checkout session
   - `POST /api/billing/webhook` — handle Stripe webhooks
   - `GET /api/billing/portal` — customer portal redirect

2. Checkout session creation:
   - Create Stripe customer if not exists
   - Store `stripe_customer_id` on user
   - Create checkout session for selected plan
   - Return checkout URL

3. Webhook handling per `STRIPE_INTEGRATION_SPEC.md`:
   - `checkout.session.completed` → activate plan
   - `invoice.payment_failed` → mark payment failed
   - `customer.subscription.updated` → update plan/period
   - `customer.subscription.deleted` → downgrade to FREE

4. Security:
   - Signature verification: `stripe.Webhook.construct_event()`
   - Idempotency: check `stripe_event_id` before processing
   - Reject unverified webhooks with 400

5. Entitlement sync:
   - Update `user_plans` on webhook
   - Set `plan_name`, `current_period_start`, `current_period_end`
   - Entitlements endpoint reflects new plan immediately

**Exit Criteria:**
- [ ] Checkout creates Stripe session and redirects
- [ ] Webhook activates plan on successful payment
- [ ] Webhook downgrades on cancellation
- [ ] Signature verification rejects invalid webhooks
- [ ] Duplicate events are handled idempotently
- [ ] Entitlements reflect Stripe state

**Test Mode Note:**
- Use Stripe test mode for all pre-launch testing
- Switch to live mode only at go-live

---

### Day 7: Emails, Hardening & Launch

---

#### C-09: Transactional Emails (MVP)
**Status:** ⬜ Not Started  
**Priority:** P2  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-01 (magic link), C-05B (proposal), C-07 (export)

**Scope:**
1. Email templates per `TRANSACTIONAL_EMAILS_SPEC.md`:
   - Magic link login (already exists, just verify format)
   - Proposal draft ready
   - Export ready
   - Subscription activated (optional for MVP)

2. Email service `app/services/email_service.py`:
   - Resend integration
   - Template rendering
   - Idempotency (don't send duplicates)

3. Trigger points:
   - Proposal created → send "draft ready" email
   - Export completed → send "export ready" email

4. Non-prod safety:
   - `EMAIL_SUPPRESS_SENDING=true` in non-prod
   - Log email content instead of sending

**Exit Criteria:**
- [ ] Emails sent on correct events
- [ ] No duplicate emails for same event
- [ ] Non-prod doesn't send real emails
- [ ] Email links are correct (not raw tokens)

---

#### C-10: Production Hardening & Verification
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 4-5 hours  
**Dependencies:** All previous commits

**Scope:**
1. Schema verification:
   - Run `psql` against Railway Postgres
   - Verify all tables match contracts
   - Document any discrepancies

2. Test-mode endpoint removal:
   - Remove `POST /api/auth/test-mode/mint` from prod
   - Or: ensure it returns 404 when `APP_ENV=prod`

3. Environment variable audit:
   - All required vars set per `ENV_VARS_REFERENCE.md`
   - No test/dev values in prod

4. Smoke test suite:
   - Run `scripts/smoke_test.py` against production
   - All Track A tests must pass
   - Track B tests informational

5. User journey verification (manual):
   - J1: Discovery → Fit Scan
   - J2: Free User → First Proposal
   - J3: Growth User → Ongoing usage
   - J5: Proposal Regeneration
   - J6: Export & Download

6. Security checklist:
   - [ ] No secrets in logs
   - [ ] No stack traces in error responses
   - [ ] CORS restricted to allowed origins
   - [ ] Rate limiting active
   - [ ] Stripe webhook signature verification active

**Exit Criteria:**
- [ ] All smoke tests pass
- [ ] All user journeys complete successfully
- [ ] No P0/P1 risks remaining
- [ ] Production environment variables correct
- [ ] Security checklist complete

---

## 4. Definition of Go-Live

### Soft Launch Ready (Day 7)
GrantPilot is **Soft Launch Ready** when:
- C-00 through C-07 are COMPLETE
- C-10 smoke tests pass
- At least one paid plan can be activated (Stripe test mode OR manual override)

### Full Launch Ready
GrantPilot is **Full Launch Ready** when:
- C-08 (Stripe) is COMPLETE with live mode
- C-09 (Emails) is COMPLETE
- C-10 passes with live Stripe

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema migration fails on prod DB | Medium | High | Test on staging first; have rollback ready |
| AI degradation edge cases | Medium | Medium | Comprehensive test matrix in C-02 |
| Stripe webhook edge cases | Medium | High | Use Stripe CLI for local testing |
| CORS issues block frontend | High | High | C-01A early in sequence |
| Quota race conditions | Low | High | Database-level locking in C-03 |

---

## 6. Seed Data Requirements

For testing, ensure Railway DB has:

| Data | Minimum Count | Notes |
|------|--------------|-------|
| Funding opportunities | 3 | One each: strong fit, moderate fit, weak fit |
| Test users | 3 | One each: Free, Growth, Impact plan |
| NGO profiles | 3 | Complete profiles for test users |

**Seed data must be created before C-04 verification.**

---

## 7. Change Control

This file may only be modified if:
1. You (Pranab) explicitly approve a change, AND
2. The change is committed before further development

Any deviation without update is considered drift.

---

## 8. Commit Status Tracker

| Commit | Status | Started | Completed | Blocker |
|--------|--------|---------|-----------|---------|
| C-00 | ⬜ Not Started | | | None |
| C-01A | ⬜ Not Started | | | None |
| C-01 | ⬜ Not Started | | | C-00, C-01A |
| C-02 | ⬜ Not Started | | | C-00 |
| C-03 | ⬜ Not Started | | | C-00 |
| C-04 | ⛔ Blocked | | | C-02, C-03 |
| C-05A | ⬜ Not Started | | | C-00 |
| C-05B | ⬜ Not Started | | | C-05A, C-02, C-03 |
| C-06 | ⬜ Not Started | | | C-05B |
| C-07 | ⬜ Not Started | | | C-05B |
| C-08 | ⬜ Not Started | | | C-00 |
| C-09 | ⬜ Not Started | | | C-01, C-05B, C-07 |
| C-10 | ⬜ Not Started | | | All |

---

## 9. Claude Code Audit Prompt

Before starting execution, run this audit prompt in Claude Code:

```
You are acting as CTO performing a read-only audit of the GrantPilot backend.
DO NOT make any changes. Only read and analyze.

Compare the actual codebase against mvp_execution_plan_FINAL.md and report:

1. SCHEMA VERIFICATION: Compare migrations vs models vs DB contracts
2. ENDPOINT INVENTORY: Compare API_CONTRACT.md vs actual routes
3. MISSING FEATURES: Search for proposal, stripe, export, email implementations
4. SERVICE LAYER: Verify column name references are correct
5. MIDDLEWARE: Check CORS and rate limiting configuration
6. DEPENDENCIES: Check requirements.txt for missing packages

Output a structured report with:
- Section A: Critical Blockers (P0)
- Section B: Missing Features (P1)
- Section C: Schema Mismatches
- Section D: Endpoint Gaps
- Section E: Dependency Gaps
- Section F: Configuration Issues
```

---

**END OF DOCUMENT**
