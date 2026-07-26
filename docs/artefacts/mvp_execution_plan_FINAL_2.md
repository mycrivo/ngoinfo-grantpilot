# GrantPilot MVP Execution Plan

Status: **Canonical — LOCKED FOR BUILD**  
Version: **4.0 (Strategic Rewrite)**  
Last updated: **2026-02-07**  
Timeline: **5 Days from restart**  
Supersedes: Version 3.1 (2026-02-04)

## Authoritative Inputs
- All DB_FIELD_CONTRACT_*.md (field contracts — unchanged)
- API_CONTRACT.md (endpoint contracts — auth + export updates pending)
- MVP_SCOPE_LOCK.md, PRICING_AND_ENTITLEMENTS.md (business rules — unchanged)
- LLM_PROMPTS_LIBRARY.md, PROMPT_INPUTS_FIELD_MAPPING.md (AI contracts — unchanged)
- AUTH_AND_SSO_STRATEGY.md (auth policy — implementation section updated)
- STRIPE_INTEGRATION_SPEC.md (billing — rewritten for Stripe-as-SOT)

---

## 0. Purpose & Rules

This file is the **single source of truth** for all remaining work until public go-live.

### What Changed (v3.1 → v4.0) and Why

Version 3.1 assumed hand-rolled implementations for Google OAuth, Stripe billing, and proposal generation. After multiple days stuck on OAuth token exchange bugs, we made a strategic decision:

**Use proven libraries for commodity infrastructure. Reserve custom code for our IP.**

| Area | v3.1 Approach | v4.0 Approach | Rationale |
|------|---------------|---------------|-----------|
| Google OAuth | Manual `httpx` token exchange | **Authlib** (FastAPI integration) | Standard library; eliminates handshake bugs |
| OAuth post-login | Tokens in redirect URL query params | **One-time code exchange** | Security: tokens never appear in URLs |
| Stripe billing | Custom subscription state machine | **Stripe Python SDK + Customer Portal** (Stripe as source of truth) | Stripe owns billing state; our DB caches it |
| Stripe webhooks | Implied custom processing | **Event-store-first** (persist raw event → process → 200 only after persist) | Prevents silent billing event loss |
| DOCX export | Signed URL + storage | **Direct byte streaming** (no storage layer) | MVP simplicity; no S3/R2 needed at our volume |
| Proposal AI | Custom OpenAI wrapper | **Simple prompt runner** (thin wrapper over `openai` SDK) | Our prompts are the IP, not the runner |
| Magic link auth | Custom implementation | **Keep as-is** (already working) | No change needed |
| JWT + refresh tokens | Custom implementation | **Keep as-is** (already working) | No change needed |

### What We Are NOT Changing
- **LLM_PROMPTS_LIBRARY.md** — Our crown jewel. Untouched.
- **All DB field contracts** — Schema is schema. Untouched.
- **PRICING_AND_ENTITLEMENTS.md** — Business rules don't change.
- **FIT_SCAN_CRITERIA_MATRIX.md** — Evaluation logic untouched.
- **PROMPT_INPUTS_FIELD_MAPPING.md** — Data contract untouched.
- **LAUNCH_JOURNEYS_SPEC.md** — User journeys don't change.

### Execution Rules
1. Each **C-XX** corresponds to **exactly one Cursor prompt**, **one GitHub commit**, and **one Railway deploy**
2. Work **must follow the order listed** — no skipping, no reordering
3. Cursor must **STOP and report** if a section cannot be completed without violating contracts
4. Dependencies must be satisfied before starting a commit
5. Exit criteria must ALL pass before marking complete

### How to Use in New Cursor Chats
```
"We are working on GrantPilot. Use `mvp_execution_plan_FINAL_2.md` as the
authoritative execution plan. We are currently at **C-XX**. Do not analyse
prior chats. Read the file and continue from current state."
```

---

## 1. Current State (As of 2026-02-07)

### What is Built and Working

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app structure | ✅ Working | `app/main.py`, config validation, error envelope, logging |
| Health endpoint | ✅ Working | `GET /health` |
| Database + Migrations | ✅ Working | Alembic 0001–0006 applied (includes fit_scans table) |
| Auth: Magic link (request + consume) | ✅ Working | Resend integration functional |
| Auth: Refresh token rotation | ✅ Working | Single active token per user |
| Auth: Logout / revocation | ✅ Working | Invalidates refresh token |
| Auth: Test-mode mint | ✅ Working | Properly gated by TEST_MODE |
| JWT creation + validation | ✅ Working | HS256, claims per AUTH_AND_SSO_STRATEGY |
| Rate limiting (in-memory) | ✅ Working | Acceptable for single-instance Railway (see Section 2.5) |
| NGO Profile CRUD | ✅ Working | After C-00 schema fix (applied) |
| Profile completeness | ✅ Working | Scoring per DB_FIELD_CONTRACT_USERS rules |
| Entitlements endpoint | ✅ Working | After C-00B recursion fix (applied) |
| CORS middleware | ✅ Working | After C-01A (applied) |
| Quota enforcement | ✅ Working | After C-03 fixes (applied) |
| Fit Scan (POST + GET) | ✅ Working | After C-04 certification (applied) |
| AI degradation handling | ✅ Working | Structured errors, no quota on failure |

### What is Broken / Being Replaced

| Component | Status | Action |
|-----------|--------|--------|
| Google OAuth (hand-rolled) | ❌ BROKEN | **Replace entirely with Authlib** (C-05) |

### What is Not Built Yet

| Feature | Priority | Commit |
|---------|----------|--------|
| Google OAuth (via Authlib) | P0 | C-05 |
| Proposal creation | P0 | C-07A, C-07B |
| Proposal regeneration | P1 | C-08 |
| DOCX export | P1 | C-09 |
| Stripe billing (SDK + webhooks) | P1 | C-10 |
| Transactional emails (beyond magic link) | P2 | C-11 |

### Database State

Migrations applied: `0001` through `0006` (fit_scans table)

Tables exist and working:
- `users` (includes `stripe_customer_id`)
- `auth_refresh_tokens`
- `auth_magic_link_tokens`
- `ngo_profiles`
- `funding_opportunities`
- `user_plans`
- `usage_ledger`
- `fit_scans`

Tables not yet created:
- `proposals` (C-07A)
- `stripe_events` (C-10)

### Endpoint Status

| Endpoint | Status |
|----------|--------|
| `GET /health` | ✅ Working |
| `POST /api/auth/magic-link/request` | ✅ Working |
| `POST /api/auth/magic-link/consume` | ✅ Working |
| `POST /api/auth/refresh` | ✅ Working |
| `POST /api/auth/logout` | ✅ Working |
| `POST /api/auth/test-mode/mint` | ✅ Working (gated) |
| `GET /api/auth/google/start` | ❌ Replace with Authlib |
| `GET /api/auth/google/callback` | ❌ Replace with Authlib |
| `POST /api/auth/exchange` | ❌ New endpoint (C-05) |
| `GET /api/me/entitlements` | ✅ Working |
| `POST /api/ngo-profile` | ✅ Working |
| `GET /api/ngo-profile` | ✅ Working |
| `PUT /api/ngo-profile` | ✅ Working |
| `GET /api/ngo-profile/completeness` | ✅ Working |
| `POST /api/fit-scans` | ✅ Working |
| `GET /api/fit-scans/{id}` | ✅ Working |
| `POST /api/proposals` | ❌ Not implemented |
| `GET /api/proposals/{id}` | ❌ Not implemented |
| `POST /api/proposals/{id}/regenerate` | ❌ Not implemented |
| `POST /api/proposals/{id}/export` | ❌ Not implemented |
| `POST /api/billing/checkout` | ❌ Not implemented |
| `POST /api/billing/webhook` | ❌ Not implemented |
| `GET /api/billing/portal` | ❌ Not implemented |

---

## 2. Strategic Decisions (Locked)

### 2.1 Google OAuth: Authlib + Secure Code Exchange

**Decision:** Replace hand-rolled Google OAuth with Authlib's FastAPI integration. Post-login handoff uses a one-time code exchange — tokens never appear in URLs.

**What Authlib handles:**
- OAuth 2.0 authorization URL generation (with state, PKCE)
- Token exchange (authorization code → access token + id_token)
- Google user info retrieval
- Error handling for OAuth edge cases

**What we keep (unchanged):**
- Our JWT minting (access tokens with plan claim)
- Our refresh token rotation (opaque tokens, hashed in DB)
- Our user creation / account linking logic (same email = same account)
- Our magic link flow (completely separate, already working)
- Our rate limiting on auth endpoints

**Post-login redirect flow (secure):**
1. Frontend initiates OAuth → backend generates Google authorization URL
2. `state` parameter encodes redirect intent (e.g., opportunity_id from WordPress deep link, per WORDPRESS_TO_GRANTPILOT_INTEGRATION.md)
3. Google redirects to backend callback with `code` + `state`
4. Backend exchanges code with Google via Authlib, creates/finds user, mints tokens
5. Backend generates a short-lived one-time `auth_code` (random string, stored hashed in DB with 60-second TTL)
6. Backend redirects browser to `{AUTH_POST_LOGIN_REDIRECT_URL}?code={auth_code}&state={original_state}`
7. Frontend calls `POST /api/auth/exchange` with `{ "code": auth_code }` to receive tokens in JSON response body

**Why not tokens in URL:**
- Tokens in URLs leak via browser history, Cloudflare access logs, referrer headers, and server logs
- One-time code exchange is the standard secure SaaS pattern (same pattern Stripe, Auth0, and others use)

**API contract impact:**
- `GET /api/auth/google/start` — response shape unchanged: `{ authorization_url, state }`
- `GET /api/auth/google/callback` — no longer returns JSON; always redirects to frontend with `code` param
- `POST /api/auth/exchange` — **new endpoint**: accepts `{ "code": "..." }`, returns tokens + user (same shape as magic link consume)
- The `?redirect=1` query parameter is **removed** (callback always redirects)
- AUTH_AND_SSO_STRATEGY.md and API_CONTRACT.md will be updated to reflect this

**Library:** `authlib` with `httpx` (Authlib with httpx backend, no Flask dependency)

### 2.2 Stripe: SDK + Customer Portal as Source of Truth

**Decision:** Stripe owns the subscription lifecycle. Our DB is a synchronized cache.

**Architecture:**
```
User clicks "Upgrade" → Backend creates Stripe Checkout Session → User pays on Stripe
    → Stripe fires webhook → Backend persists raw event → Processes event → Updates user_plans → Returns 200

User clicks "Manage Billing" → Backend generates Stripe Customer Portal link → User manages on Stripe
    → Stripe fires webhook on changes → Same persist-first flow → Done
```

**What Stripe owns:**
- Subscription state machine (active, past_due, canceled, trialing)
- Payment retry logic
- Invoice generation
- Plan change / upgrade / downgrade
- Cancellation + grace period
- Customer portal UI (payment methods, invoices, plan management)

**What we build (minimal):**
- `POST /api/billing/checkout` — creates Stripe Checkout Session, returns URL
- `POST /api/billing/webhook` — receives Stripe events, persists then processes
- `GET /api/billing/portal` — generates Customer Portal session URL, returns URL
- Webhook signature verification (using `stripe.Webhook.construct_event`)
- Event-store-first persistence (see Section 2.2.1)

**What we do NOT build:**
- Subscription state machine logic
- Payment retry logic
- Invoice management UI
- Plan change validation (Stripe handles this)
- Cancellation flow UI (Customer Portal handles this)

#### 2.2.1 Webhook Processing: Event-Store-First (Non-Negotiable)

Billing events are high-stakes. A lost webhook means a user pays but never gets access. The processing pattern is:

```
1. Verify signature (reject if invalid → return 400)
2. Parse event
3. Check stripe_events table for event.id (if already processed → return 200 immediately)
4. INSERT raw event into stripe_events table (event_id, event_type, payload, received_at, processed_at=NULL)
5. If INSERT fails → return 500 (Stripe will retry)
6. Process event (update user_plans, etc.)
7. UPDATE stripe_events SET processed_at=now(), processing_result='SUCCESS'|'FAILED'
8. Return 200 to Stripe
```

**Key rules:**
- Return 200 ONLY after the raw event is persisted to `stripe_events`
- If persistence fails, return 500 — Stripe will retry (up to ~3 days)
- If processing fails after persistence, the event is stored and can be replayed manually
- Idempotency: `event.id` is unique in `stripe_events` — duplicate deliveries are safe

**DB sync rules:**
- `user_plans.plan_name` is updated ONLY by webhook handlers
- `user_plans.stripe_subscription_id` links to Stripe subscription
- `user_plans.billing_period_start/end` is synced from Stripe subscription period
- On webhook failure or doubt, Stripe is source of truth (query via SDK if needed)

### 2.3 Proposal Generation: Simple Prompt Runner

**Decision:** Use the `openai` Python SDK directly with a thin wrapper. No LangChain.

**Rationale:**
Our prompt library (LLM_PROMPTS_LIBRARY.md) is meticulously engineered with specific temperatures, frequency penalties, token limits, and strict JSON schemas per prompt ID. LangChain's abstractions would fight this precision rather than help it.

**What the prompt runner does:**
1. Accept `prompt_inputs_json` (assembled by the backend adapter per PROMPT_INPUTS_FIELD_MAPPING.md)
2. Select system prompt and user prompt template based on prompt ID (GP-F01/F02, GP-P01/P02, etc.)
3. Call OpenAI API with exact parameters from LLM_PROMPTS_LIBRARY.md Section 1
4. Parse JSON response
5. Validate response is valid JSON
6. Return structured result or raise `DomainError` on failure

**What the prompt runner does NOT do:**
- Chain multiple LLM calls (each prompt is a single call)
- Maintain conversation history
- Use vector stores or embeddings
- Implement retry/fallback logic beyond simple error handling

**The `build_prompt_inputs()` adapter** (per PROMPT_INPUTS_FIELD_MAPPING.md Section 10.1) is pure Python data mapping — no framework needed.

### 2.4 DOCX Export: Direct Byte Streaming

**Decision:** Generate DOCX in memory and stream bytes directly to the client. No storage layer.

**Rationale:**
At MVP volume (5–20 exports/day), introducing S3/R2 with presigned URLs, TTL policies, and cleanup jobs is premature infrastructure. The `python-docx` library generates DOCX in memory; we return it as a file download response.

**Implementation:**
- `POST /api/proposals/{id}/export` returns the DOCX file directly
- Response headers: `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition: attachment; filename="proposal-{id}.docx"`
- No URL, no signed link, no storage bucket
- Multiple downloads of the same version are fine — the file is regenerated from stored `content_json` each time (cheap operation)

**API contract impact:**
- The export endpoint returns a binary file response, NOT a JSON with `export_url`
- API_CONTRACT.md will be updated to reflect this

**Post-MVP upgrade path:**
If generation becomes slow or files become large, introduce S3/R2 with signed URLs and a background generation job. But not now.

### 2.5 Deployment Constraint: Single Instance

**Decision:** Railway deployment is pinned to 1 replica and 1 Uvicorn worker for MVP.

**Rationale:**
In-memory rate limiting (already working) requires shared memory across all request handlers. Multiple workers or replicas would bypass rate limits silently.

**Constraint:**
- Railway service must be configured with 1 replica
- Uvicorn start command must use `--workers 1` (or omit the flag, which defaults to 1)
- If scaling is needed post-MVP, migrate rate limiting to Redis first

**This is a known trade-off.** Acceptable for MVP volume. If we see performance issues before Redis is ready, we increase the single instance's memory/CPU allocation on Railway.

### 2.6 Proposal Generation Safety Caps

**Decision:** Enforce hard limits on proposal generation to prevent runaway cost and token overflow.

**Caps (non-negotiable):**

| Cap | Limit | Rationale |
|-----|-------|-----------|
| Max generatable submission items per proposal | **5** | Items where `generation_allowed=true`. If opportunity has more, generate first 5 (by array order from requirements_json), mark rest as `MANUAL_REQUIRED` |
| Max `prompt_inputs_json` payload size | **12,000 tokens** (estimated) | If over, truncate `overview_text` and `internal_notes` first (operational fields, not generation-critical) |
| Cost ceiling per complete proposal | **$1.25 USD** | Per LLM_PROMPTS_LIBRARY.md Section 1. Includes fit scan + all sections + up to 3 regenerations |

**If cap is hit:**
- Items beyond the 5-item limit get `generation_status: "MANUAL_REQUIRED"` with a note: "This section exceeds the generation limit. Please write it manually."
- Payload truncation is silent (operational fields only; user-facing data is never truncated)

### 2.7 Proposal Partial Failure Handling

**Decision:** Persist and show whatever succeeded. The user deserves 70% if that's the best we can do.

**Rules:**
- Each submission item in `content_json` has its own `generation_status`: `GENERATED` | `FAILED` | `MANUAL_REQUIRED`
- If **at least 1 section is successfully generated** → persist the proposal, consume quota
- If **ALL sections fail** → do NOT persist, do NOT consume quota, return error
- Failed sections include `generation_status: "FAILED"` with a reason (e.g., "AI service timeout")
- `MANUAL_REQUIRED` sections (over the 5-item cap or `generation_allowed=false`) are included with empty content and a note

**`content_json` schema:**
```json
{
  "sections": [
    {
      "submission_item_id": "string",
      "label": "string",
      "generation_status": "GENERATED | FAILED | MANUAL_REQUIRED",
      "archetype": "ARCH_EXEC_SUMMARY | ARCH_PROBLEM | ... | null",
      "content": {
        "text": "string (generated content or empty)",
        "assumptions": ["string"],
        "evidence_used": ["string"]
      },
      "failure_reason": "string or null",
      "constraints_applied": {
        "word_limit": 0,
        "word_limit_respected": true
      }
    }
  ],
  "generation_summary": {
    "total_items": 8,
    "generated": 4,
    "failed": 1,
    "manual_required": 3,
    "warnings": ["string"]
  }
}
```

**Frontend rendering guidance:**
- `GENERATED` → show content normally
- `FAILED` → show "This section could not be generated. Please write it manually." with retry option
- `MANUAL_REQUIRED` → show "This section requires manual input. AI generation is not available for this item."

---

## 3. Global Execution Invariants

After every C-XX completion, these must hold true:

| Invariant | Verification |
|-----------|--------------|
| No 500s for expected states | Manual test + smoke script |
| No quota consumption when ALL sections fail | Check usage_ledger |
| Quota consumed on partial success (≥1 section generated) | Check usage_ledger |
| API_CONTRACT-compliant error responses | Swagger validation |
| CORS allows only configured origins | Browser preflight test |
| No test endpoints in prod | Check `APP_ENV` gating |
| Auth tokens contain actual user plan (not hardcoded) | Decode JWT and verify |
| Railway pinned to 1 replica, 1 worker | Check Railway dashboard |
| Tokens never appear in URLs | Check browser network tab during OAuth flow |

**Violation of any invariant requires rollback before proceeding.**

---

## 4. Commit-Driven Execution Plan

---

### DAY 1: Auth Replacement + Auth Hardening

---

#### C-05: Replace Google OAuth with Authlib + Secure Code Exchange
**Priority:** P0 — Users cannot sign in via Google without this  
**Estimated Time:** 3-4 hours  
**Dependencies:** None (all prior C-00 through C-04 are complete)

**Context for Cursor:**

The existing Google OAuth implementation in `app/api/routes/auth.py` uses manual `httpx` calls to Google's token endpoint and has proven unreliable. We are replacing ONLY the Google OAuth handshake with Authlib, AND switching to a secure one-time code exchange pattern for the post-login redirect. Everything else in `auth.py` (magic link, refresh, logout, test-mode mint, JWT creation) stays untouched.

**Scope:**

**Part 1: Add dependencies**
- Add `authlib` and `httpx` to `requirements.txt`

**Part 2: Configure Authlib in existing auth modules** (`app/api/routes/auth.py` + `app/services/auth_service.py`)
- Initialize OAuth client flow in auth routes
- Use `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` from existing config
- Scopes: `openid email profile`
- Persist one-time OAuth exchange codes in DB as hashed, single-use records with 60-second TTL

**Part 3: Rewrite Google OAuth routes in `app/api/routes/auth.py`**

`GET /api/auth/google/start`:
- Use Authlib to generate authorization URL
- The `state` parameter must encode redirect intent (e.g., opportunity_id from WordPress deep link, per WORDPRESS_TO_GRANTPILOT_INTEGRATION.md)
- Store state in an in-memory dict with 60-second TTL for verification on callback
- Return `{ "authorization_url": "...", "state": "..." }`

`GET /api/auth/google/callback`:
- Use Authlib to exchange authorization code for Google tokens
- Extract user info (email, name, google sub ID) from Authlib's parsed response
- Find or create user by email (account linking — existing logic)
- Set `google_sub` on user if not already set
- Fetch actual plan from `user_plans` table (NOT hardcoded "FREE")
- Mint JWT access token + create refresh token (existing logic)
- Generate a one-time `auth_code`: random 64-char string, store hashed in DB with 60-second TTL (single-use)
- Redirect browser to: `{AUTH_POST_LOGIN_REDIRECT_URL}?code={auth_code}&state={forwarded_state}`
- Tokens are NEVER placed in the redirect URL

`POST /api/auth/exchange` **(NEW endpoint)**:
- Accepts `{ "code": "string" }`
- Looks up auth_code hash in DB-backed one-time code store
- If found and not expired (60-second TTL): return tokens + user JSON (same shape as magic link consume response)
- Mark code consumed after use (single-use)
- If not found, expired, or already used: return 401 `OAUTH_EXCHANGE_FAILED`
- Rate limit: 30 per IP per hour

**Part 4: Fix auth hardcoding issues (carry-forward from v3.1)**
- Replace hardcoded `plan="FREE"` in ALL token minting locations (magic link consume, refresh, OAuth callback) with actual plan lookup from `user_plans`
- Replace hardcoded redirect URL with `settings.AUTH_POST_LOGIN_REDIRECT_URL`

**Part 5: Verify magic link email format**
- Ensure magic link email contains clickable link: `{FRONTEND_URL}/auth/magic-link?token={token}`
- Not raw token text

**What must NOT change:**
- `POST /api/auth/magic-link/request` — untouched
- `POST /api/auth/magic-link/consume` — untouched (except plan hardcoding fix)
- `POST /api/auth/refresh` — untouched (except plan hardcoding fix)
- `POST /api/auth/logout` — untouched
- `POST /api/auth/test-mode/mint` — untouched
- JWT creation logic in `app/core/security.py` — untouched
- Refresh token rotation logic — untouched
- Rate limiting — untouched

**OAuth URLs (from AUTH_AND_SSO_STRATEGY.md):**
- OAuth callback URL: `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback`
- Post-login redirect URL: `https://grantpilot.ngoinfo.org/auth/callback`

**Exit Criteria:**
- [ ] `GET /api/auth/google/start` returns valid Google authorization URL
- [ ] `GET /api/auth/google/callback` redirects to frontend with `code` param (no tokens in URL)
- [ ] `POST /api/auth/exchange` returns tokens + user when given valid code
- [ ] `POST /api/auth/exchange` returns 401 for expired/invalid/reused code
- [ ] New user creation works via OAuth
- [ ] Existing user login works via OAuth (account linking by email)
- [ ] Access token contains actual plan (not hardcoded "FREE")
- [ ] Redirect URL uses config (not hardcoded)
- [ ] Magic link flow still works (regression check)
- [ ] Refresh flow still works (regression check)
- [ ] Rate limiting still applies to auth endpoints

**Verification:**
```bash
# 1. Start OAuth flow
curl -s $BASE_URL/api/auth/google/start | jq .authorization_url
# Should return Google authorization URL

# 2. After completing OAuth in browser, verify redirect has code param (not tokens)
# Browser should land on: https://grantpilot.ngoinfo.org/auth/callback?code=xxx&state=yyy

# 3. Exchange code for tokens
curl -X POST $BASE_URL/api/auth/exchange \
  -H "Content-Type: application/json" \
  -d '{"code": "xxx"}'
# Should return { access_token, refresh_token, token_type, expires_in, user }

# 4. Reuse same code
curl -X POST $BASE_URL/api/auth/exchange \
  -H "Content-Type: application/json" \
  -d '{"code": "xxx"}'
# Should return 401 OAUTH_EXCHANGE_FAILED

# 5. Regression: magic link still works
curl -X POST $BASE_URL/api/auth/magic-link/request \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.org"}'
# Should return {"status": "sent"}
```

---

#### C-06: Smoke Test Update for Auth
**Priority:** P1  
**Estimated Time:** 1 hour  
**Dependencies:** C-05

**Scope:**
- Update `scripts/smoke_test.py` to verify Authlib-based OAuth endpoints
- Verify Track A (no auth required) still passes
- Verify Track B (with test-mode mint) still passes
- Add OAuth start check (returns valid URL shape)
- Add exchange endpoint check (invalid code returns 401)

**Exit Criteria:**
- [ ] Track A smoke tests pass
- [ ] Track B smoke tests pass
- [ ] OAuth start returns valid response shape
- [ ] Exchange endpoint rejects invalid codes

---

### DAY 2: Proposal Foundation

---

#### C-07A: Proposal Database + Model
**Priority:** P0 — Revenue feature foundation  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-05 (auth must work for integration testing)

**Scope:**

**Part 1: Create migration** (next available number after current head)

Table: `proposals`
```
id                       UUID, PK, default gen_random_uuid()
user_id                  UUID, FK → users.id, ON DELETE CASCADE, NOT NULL
funding_opportunity_id   UUID, FK → funding_opportunities.id, NOT NULL
fit_scan_id              UUID, FK → fit_scans.id, NULLABLE
version                  INTEGER, NOT NULL, default 1
status                   TEXT, NOT NULL, default 'DRAFT'
plan_at_creation         TEXT, NOT NULL (FREE | GROWTH | IMPACT)
prompt_version           TEXT, NOT NULL
selected_variant_id      TEXT, NULLABLE
content_json             JSONB, NOT NULL
regeneration_count       INTEGER, NOT NULL, default 0
created_at               TIMESTAMPTZ, NOT NULL, default now()
updated_at               TIMESTAMPTZ, NOT NULL, default now()
```

`content_json` must conform to the schema defined in Section 2.7 of this document.

Indexes:
- `(user_id, created_at DESC)` — user's proposal history
- `(funding_opportunity_id)` — opportunity-level queries

**Part 2: Create model `app/models/proposal.py`**

**Part 3: Create schemas `app/schemas/proposal.py`**
- `ProposalCreateRequest`: `{ funding_opportunity_id, fit_scan_id (optional), selected_variant_id (optional), user_overrides (optional) }`
- `ProposalResponse`: summary (id, status, opportunity title, recommendation, created_at, generation_summary)
- `ProposalDetailResponse`: full content_json with per-section status

**Part 4: Register model in `app/models/__init__.py`**

**Persistence rules:**
- Proposals are versioned: regeneration updates `content_json`, increments `version` and `regeneration_count`, updates `updated_at`
- `plan_at_creation` captured at first creation time (never updated)
- `prompt_version` must match LLM_PROMPTS_LIBRARY.md version string
- If ALL sections fail during generation → do NOT persist, do NOT consume quota
- If at least 1 section succeeds → persist (partial success), consume quota

**Exit Criteria:**
- [ ] Migration runs without error on Railway
- [ ] Model imports cleanly
- [ ] Schemas validate correctly

---

#### C-07B: Proposal Creation + Retrieval Endpoints
**Priority:** P0 — This is what users pay for  
**Estimated Time:** 5-6 hours  
**Dependencies:** C-07A

**Scope:**

**Part 1: Create `app/ai/prompt_runner.py`** — Simple OpenAI wrapper

This is a THIN wrapper over the `openai` Python SDK. It must:
- Accept: prompt_id, system_prompt, user_prompt, model parameters
- Call `openai.chat.completions.create()` with exact parameters from LLM_PROMPTS_LIBRARY.md Section 1:
  - Model: `gpt-5.2` (hardcoded constant, not env var, per LLM_PROMPTS_LIBRARY.md)
  - Temperature, top_p, frequency_penalty, presence_penalty, max_tokens: per prompt ID table
  - `response_format: {"type": "json_object"}`
- Parse JSON response
- Validate response is valid JSON
- Return parsed dict or raise `DomainError("AI_SERVICE_ERROR", ...)`
- Handle OpenAI API errors (rate limit, timeout, invalid response) as `DomainError`

**Part 2: Create `app/ai/prompt_inputs_builder.py`** — The adapter

Implements `build_prompt_inputs()` per PROMPT_INPUTS_FIELD_MAPPING.md Section 10.1 pseudocode.
This is the critical data mapping layer:
- `prompt_inputs.ngo` ← ngo_profiles table (Section 2 of field mapping)
- `prompt_inputs.opportunity` ← funding_opportunities table (Section 3)
- `prompt_inputs.requirements` ← funding_opportunities.requirements_json (Section 4)
- `prompt_inputs.user` ← runtime user inputs: variant selection, overrides (Section 5)
- `prompt_inputs.derived` ← computed fields (Section 6):
  - `today_utc_date`
  - `uploads_supported` = false (MVP)
  - `grant_amount_display` (Section 6.3.1 logic)
  - `annual_budget_display` (Section 6.3.2 logic)
  - `opportunity_priorities_phrases` (Section 6.3.3 logic)
  - `selected_variant_id` + `selected_variant` (Section 6.3.4 logic)
  - `deadline_days_remaining` (Section 6.3.5 logic)
  - `applicant_type` = "NGO" (MVP constant)

**Part 3: Create `app/ai/prompts/` directory** with prompt templates

Store system and user prompt templates as Python constants, matching LLM_PROMPTS_LIBRARY.md exactly:
- `fit_scan.py` — GP-F01 (system) + GP-F02 (user template)
- `proposal.py` — GP-P01 (system) + GP-P02 (user template)
- `user_input_norm.py` — GP-U01 (system + user template)

**Part 4: Create `app/services/proposal_service.py`**

This service:
1. Validates funding opportunity exists and is READY/PUBLISHED
2. Validates NGO profile is COMPLETE (reuse profile completeness check)
3. Validates requirements_json is present and usable
4. Checks quota (Free: 1 lifetime, Growth: 3/month, Impact: 5/month)
5. Builds `prompt_inputs_json` using the adapter (Part 2)
6. Identifies generatable submission items from selected variant:
   - Filter to items where `generation_allowed=true`
   - **Cap at 5 items** (Section 2.6). Mark excess items as `MANUAL_REQUIRED`
   - Items where `generation_allowed=false` → mark as `MANUAL_REQUIRED`
7. For each generatable item (up to 5), call prompt runner with GP-P02
8. Track per-item status: `GENERATED`, `FAILED`, or `MANUAL_REQUIRED`
9. Assemble `content_json` per schema in Section 2.7
10. **Partial failure rule:** If ≥1 section generated → persist + consume quota. If ALL fail → don't persist, don't consume quota
11. Persist proposal row + decrement quota atomically (if persisting)
12. Return proposal response

**Part 5: Create `app/api/routes/proposals.py`**

`POST /api/proposals`:
- Auth required
- Accepts `ProposalCreateRequest`
- Calls `proposal_service.create_proposal()`
- Returns `ProposalResponse` with `generation_summary`
- Errors per API_CONTRACT.md: 401, 403, 404, 409 (PROFILE_INCOMPLETE with `missing_fields`), 429 (QUOTA_EXCEEDED), 500

`GET /api/proposals/{id}`:
- Auth required
- Returns `ProposalDetailResponse` (includes full content_json with per-section status)
- Ownership check: only owning user can access
- Errors: 401, 403, 404

**Part 6: Register router in `app/main.py`**

**Quota rules (from PRICING_AND_ENTITLEMENTS.md):**
- Free: 1 proposal lifetime (no regeneration)
- Growth: 3 proposals/month, max 1 new proposal every 10 minutes
- Impact: 5 proposals/month, max 1 new proposal every 10 minutes
- Quota decremented ONLY after successful persistence (≥1 section generated)
- Total failure (0 sections) does NOT consume quota

**Exit Criteria:**
- [ ] `POST /api/proposals` creates proposal from valid opportunity + complete profile
- [ ] `GET /api/proposals/{id}` retrieves proposal with per-section status
- [ ] Partial failure: 4/5 sections generated → proposal persisted, failed section marked
- [ ] Total failure: 0/5 sections → no proposal persisted, no quota consumed
- [ ] Opportunities with >5 generatable items: first 5 generated, rest marked MANUAL_REQUIRED
- [ ] Incomplete profile returns 409 with `missing_fields`
- [ ] Missing/invalid requirements_json returns degraded response (no quota consumed)
  - Degraded output must include safe placeholders only (no hallucinated requirements)
  - Mark non-generatable sections as `MANUAL_REQUIRED` (or equivalent placeholder status)
  - Quota must not be consumed on degraded result
- [ ] Quota enforcement works per plan
- [ ] Ownership check prevents cross-user access (403)

**Verification:**
```bash
# Create proposal
curl -X POST $BASE_URL/api/proposals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"funding_opportunity_id": "uuid-here"}'
# Check generation_summary in response

# Retrieve proposal
curl -X GET $BASE_URL/api/proposals/{id} \
  -H "Authorization: Bearer $TOKEN"
# Check per-section generation_status
```

---

### DAY 3: Proposal Completion + Export

---

#### C-08: Proposal Regeneration
**Priority:** P1  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-07B

**Scope:**

`POST /api/proposals/{id}/regenerate`:
- Auth required, ownership check
- Plan gating: Free plan → 403 FORBIDDEN (regeneration not allowed)
- Growth/Impact: max 3 regenerations per proposal (check `regeneration_count`)
- Re-run prompt with same inputs for all previously `GENERATED` sections (content should vary due to temperature=0.65)
- Previously `FAILED` sections get another attempt
- `MANUAL_REQUIRED` sections stay as-is (still over cap or `generation_allowed=false`)
- Update `content_json`, increment `version` and `regeneration_count`, update `updated_at`
- Track in `usage_ledger` with action_type=PROPOSAL_REGEN
- Partial failure rules apply same as initial generation

**Rate limit (from PRICING_AND_ENTITLEMENTS.md):**
- Growth: max 3 regenerations per proposal
- Impact: max 3 regenerations per proposal

**Exit Criteria:**
- [ ] Free plan gets 403 on regeneration attempt
- [ ] Growth/Impact can regenerate up to 3 times
- [ ] 4th regeneration attempt returns clear error (regeneration limit reached)
- [ ] Content actually differs between regenerations
- [ ] Previously FAILED sections are retried
- [ ] MANUAL_REQUIRED sections remain unchanged
- [ ] Failed regeneration (all sections fail) does not increment count

---

#### C-09: DOCX Export (Direct Streaming)
**Priority:** P1 — Without export, proposals have no tangible output  
**Estimated Time:** 3-4 hours  
**Dependencies:** C-07B

**Scope:**

**Part 1: Add `python-docx` to `requirements.txt`**

**Part 2: Create `app/services/export_service.py`**
- Accept proposal `content_json` and metadata (opportunity title, NGO name, date)
- Generate professional DOCX document with:
  - Title page (opportunity title, NGO name, generation date)
  - Each `GENERATED` section as a chapter with heading + content
  - `FAILED` and `MANUAL_REQUIRED` sections listed as placeholders: "[Section Title] — To be completed manually"
  - Assumptions appendix (if any sections have assumptions)
  - Professional formatting: consistent font (Arial or similar), 12pt body, proper headings, page numbers
- Return DOCX as bytes (in-memory generation via `python-docx`)

**Part 3: Create `POST /api/proposals/{id}/export`**
- Auth required, ownership check
- Request body: `{ "format": "DOCX" }` (only format supported)
- If format != "DOCX" → 422 UNSUPPORTED_FORMAT
- Generate DOCX from stored `content_json`
- Return file directly as binary response:
  - `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `Content-Disposition: attachment; filename="proposal-{id}.docx"`
- Track in `usage_ledger` with action_type=DOCX_EXPORT
- First export of a proposal version consumes proposal quota
- Multiple downloads do NOT re-consume quota (idempotency key: user_id + proposal_id + version)

**Exit Criteria:**
- [ ] Export returns downloadable DOCX file
- [ ] Downloaded file opens in Word/Google Docs without errors
- [ ] DOCX contains all GENERATED sections with correct content
- [ ] FAILED/MANUAL_REQUIRED sections appear as placeholders
- [ ] Re-download same version doesn't consume additional quota
- [ ] Non-DOCX format returns 422

---

### DAY 4: Stripe Billing

---

#### C-10: Stripe Integration (SDK + Customer Portal + Event Store)
**Priority:** P1 — Gates revenue  
**Estimated Time:** 4-5 hours  
**Dependencies:** C-05 (auth working), users.stripe_customer_id column (exists)

**Context for Cursor:**

Stripe is the source of truth for billing. Our `user_plans` table is a synchronized cache. We use Stripe's official Python SDK and Customer Portal — we do NOT build subscription state management, payment retry logic, or billing UI. Webhook processing uses the event-store-first pattern (Section 2.2.1).

**Scope:**

**Part 1: Add `stripe` to `requirements.txt`**

**Part 2: Create migration for `stripe_events` table**

```
stripe_events table:
  id                UUID, PK, default gen_random_uuid()
  stripe_event_id   TEXT, NOT NULL, UNIQUE
  event_type        TEXT, NOT NULL
  payload           JSONB, NOT NULL
  received_at       TIMESTAMPTZ, NOT NULL, default now()
  processed_at      TIMESTAMPTZ, NULLABLE
  processing_result TEXT, NULLABLE (SUCCESS | FAILED | SKIPPED)
  error_message     TEXT, NULLABLE
```

Index: `(stripe_event_id)` — idempotency lookup

**Part 3: Create `app/api/routes/billing.py`**

`POST /api/billing/checkout`:
- Auth required
- Request: `{ "plan": "GROWTH" | "IMPACT" }`
- Creates or retrieves Stripe Customer (using `users.stripe_customer_id`)
- Creates Stripe Checkout Session with:
  - `price`: `STRIPE_PRICE_ID_GROWTH` or `STRIPE_PRICE_ID_IMPACT` (from env)
  - `success_url`: `STRIPE_CHECKOUT_SUCCESS_URL`
  - `cancel_url`: `STRIPE_CHECKOUT_CANCEL_URL`
  - `customer`: Stripe customer ID
  - `metadata`: `{ "user_id": str(user.id), "plan": "GROWTH" | "IMPACT" }`
  - `mode`: "subscription"
- Saves `stripe_customer_id` to user record if newly created
- Returns `{ "checkout_url": session.url }`

`POST /api/billing/webhook`:
- NO auth required (Stripe calls this directly)
- Signature verification using `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`
- On signature failure → return 400 + log security event
- **Event-store-first flow (Section 2.2.1):**
  1. Check `stripe_events` for `event.id` — if exists, return 200 (already processed)
  2. INSERT raw event into `stripe_events` (stripe_event_id, event_type, payload)
  3. If INSERT fails → return 500 (Stripe retries)
  4. Process event based on type:

  **`checkout.session.completed`:**
  - Extract `customer`, `subscription`, `metadata.user_id`, `metadata.plan`
  - Create/update `user_plans`: set `plan_name`, `stripe_subscription_id`, `billing_period_start/end`, `plan_activated_at`

  **`customer.subscription.updated`:**
  - Sync: update `plan_name`, `billing_period_start/end` from subscription

  **`customer.subscription.deleted`:**
  - Downgrade to FREE: set `plan_name='FREE'`, clear `stripe_subscription_id`

  **`invoice.payment_failed`:**
  - Log event. Do not immediately downgrade (Stripe handles retries)

  5. UPDATE `stripe_events` SET `processed_at=now()`, `processing_result`
  6. Return 200

`GET /api/billing/portal`:
- Auth required
- If user has no `stripe_customer_id` → 400 "No billing account"
- Creates Stripe Customer Portal session
- Returns `{ "portal_url": session.url }`

**Part 4: Create `app/services/billing_service.py`**
- `create_checkout_session(user, plan)` — creates Stripe customer + checkout
- `handle_webhook_event(event, db)` — event-store-first processing
- `create_portal_session(user)` — portal URL generation
- `sync_plan_from_subscription(user_id, subscription, db)` — shared sync helper

**Env vars required (from ENV_VARS_REFERENCE.md):**
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_GROWTH`
- `STRIPE_PRICE_ID_IMPACT`
- `STRIPE_CHECKOUT_SUCCESS_URL`
- `STRIPE_CHECKOUT_CANCEL_URL`

**Exit Criteria:**
- [ ] Checkout creates valid Stripe session and returns URL
- [ ] Webhook verifies signature (rejects invalid → 400)
- [ ] Raw event persisted to `stripe_events` before processing
- [ ] `checkout.session.completed` activates plan in `user_plans`
- [ ] `customer.subscription.updated` syncs plan state
- [ ] `customer.subscription.deleted` downgrades to FREE
- [ ] Duplicate webhook delivery returns 200 without re-processing
- [ ] Portal URL redirects to Stripe Customer Portal
- [ ] All events tested in Stripe test mode

**Verification:**
```bash
# Create checkout
curl -X POST $BASE_URL/api/billing/checkout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan": "GROWTH"}'
# Should return checkout_url

# After payment, check entitlements
curl -X GET $BASE_URL/api/me/entitlements \
  -H "Authorization: Bearer $TOKEN"
# Should show GROWTH plan

# Check event was stored
# SELECT * FROM stripe_events ORDER BY received_at DESC LIMIT 5;

# Stripe CLI for webhook testing
stripe listen --forward-to $BASE_URL/api/billing/webhook
stripe trigger checkout.session.completed
```

---

### DAY 5: Emails + Production Hardening

---

#### C-11: Transactional Emails
**Priority:** P2 — Nice to have for launch, not a hard blocker  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-07B, C-10

**Scope:**

Extend existing Resend integration (already working for magic link) to cover:

**Required for launch:**
- Proposal draft ready (proposal_link, opportunity_title)
- Subscription activated (plan_name, billing_portal_link)

**Nice to have (can defer to Week 2):**
- Welcome / first login
- Fit scan result ready
- Payment failed
- DOCX export ready

**Implementation:**
- Create `app/services/email_service.py` with template-based sending
- Reuse existing Resend config (EMAIL_API_KEY, EMAIL_FROM_ADDRESS, etc.)
- Idempotency: use event key (e.g., proposal_id + "draft_ready") to prevent duplicates
- Non-prod suppression via `EMAIL_SUPPRESS_SENDING` env var

**Exit Criteria:**
- [ ] Proposal ready email fires on successful creation
- [ ] Subscription activated email fires on webhook
- [ ] Non-prod emails suppressed
- [ ] No duplicate emails for same event

---

#### C-12: Production Hardening + Go-Live
**Priority:** P0 — Launch gate  
**Estimated Time:** 3-4 hours  
**Dependencies:** All previous

**Scope:**

**Part 1: Security checklist**
- [ ] Remove/gate `POST /api/auth/test-mode/mint` (return 404 when `TEST_MODE=false` or absent)
- [ ] Remove `TEST_MODE` and `TEST_MODE_SECRET` from production env vars
- [ ] Verify no secrets in frontend env
- [ ] Verify Stripe webhook secret is set
- [ ] Verify CORS only allows `grantpilot.ngoinfo.org`
- [ ] Verify tokens never appear in redirect URLs (test OAuth flow in browser)

**Part 2: Environment variable audit**
- [ ] All required vars from ENV_VARS_REFERENCE.md are set in Railway
- [ ] No internal Railway URLs in OAuth, Stripe, or email links
- [ ] `APP_ENV=prod`
- [ ] `AUTH_RATE_LIMIT_ENABLED=true`
- [ ] Stripe in correct mode (test for soft launch, live for full launch)

**Part 3: Deployment constraints**
- [ ] Railway pinned to 1 replica
- [ ] Uvicorn running with 1 worker
- [ ] Confirm no autoscaling configured

**Part 4: Schema verification**
- [ ] `alembic upgrade head` succeeds cleanly
- [ ] All tables exist with correct columns (verify via `\d+ tablename`)
- [ ] `stripe_events` table exists
- [ ] At least 3 funding opportunities seeded with valid requirements_json

**Part 5: Smoke test suite**
Run full smoke test against production:
- [ ] Health check passes
- [ ] OAuth flow completes (real Google account) — code exchange pattern
- [ ] Magic link flow completes
- [ ] Profile CRUD works
- [ ] Fit scan runs and returns result
- [ ] Proposal generates with per-section status
- [ ] DOCX export downloads valid file
- [ ] Quota enforcement blocks over-limit requests
- [ ] Stripe checkout creates session (test mode)

**Part 6: User journey verification (J1-J6 from LAUNCH_JOURNEYS_SPEC.md)**
- [ ] J1: Discovery → Fit Scan (WordPress deep link → auth → fit scan result)
- [ ] J2: Free User → First Proposal (one-time evaluation, partial success handled)
- [ ] J3: Growth User → Ongoing workflow (multiple fit scans + proposals)
- [ ] J4: Impact User → Consultant-grade workflow
- [ ] J5: Proposal regeneration (retry failed sections)
- [ ] J6: Export + submission readiness (DOCX download)

**Exit Criteria:**
- [ ] All smoke tests pass
- [ ] All user journeys complete end-to-end
- [ ] Security checklist complete
- [ ] No unhandled 500 errors in logs

---

## 5. Dependency Graph

```
C-05 (Authlib OAuth + Code Exchange) ──→ C-06 (Smoke Tests)
         │
         ├──→ C-07A (Proposal DB) ──→ C-07B (Proposal API) ──→ C-08 (Regen) ──→ C-09 (Export)
         │                                       │
         │                                       └──→ C-11 (Emails)
         │
         └──→ C-10 (Stripe + Event Store) ──→ C-11 (Emails)

All ──────────────────────────────────────────────────────────────→ C-12 (Hardening)
```

---

## 6. Commit Status Tracker

| Commit | Description | Status | Blocks | Est. Hours |
|--------|-------------|--------|--------|------------|
| C-05 | Authlib OAuth + code exchange + auth hardening | ⬜ Not Started | C-06, all downstream | 3-4h |
| C-06 | Smoke test update | ⬜ Not Started | — | 1h |
| C-07A | Proposal DB + model | ⬜ Not Started | C-07B | 2-3h |
| C-07B | Proposal creation + retrieval + prompt runner | ⬜ Not Started | C-08, C-09, C-11 | 5-6h |
| C-08 | Proposal regeneration | ⬜ Not Started | — | 2-3h |
| C-09 | DOCX export (direct streaming) | ⬜ Not Started | — | 3-4h |
| C-10 | Stripe (SDK + Portal + event store) | ⬜ Not Started | C-11 | 4-5h |
| C-11 | Transactional emails | ⬜ Not Started | — | 2-3h |
| C-12 | Production hardening | ⬜ Not Started | Launch | 3-4h |

**Total Estimated: 26-33 hours across 5 days**

---

## 7. Definition of Go-Live

### Soft Launch (end of Day 5)
- C-05 through C-09 COMPLETE (auth, proposals, export)
- C-12 smoke tests pass
- Stripe in test mode OR manual plan assignment for first customers
- At least 3 funding opportunities seeded

### Full Launch (Day 6-7)
- C-10 (Stripe) in live mode
- C-11 (Emails) complete
- C-12 fully verified
- WordPress CTAs pointing to production

---

## 8. Library Versions (Pin for Reproducibility)

| Library | Version | Purpose |
|---------|---------|---------|
| authlib | >=1.3.0 | Google OAuth |
| httpx | >=0.27.0 | Authlib transport |
| stripe | >=8.0.0 | Billing SDK |
| openai | >=1.40.0 | AI prompt runner |
| python-docx | >=1.1.0 | DOCX export |

**Existing (already in requirements.txt):**
- fastapi, uvicorn, sqlalchemy, alembic, pydantic, python-jose, passlib, resend

---

## 9. Change Control

This file may only be modified if:
1. Pranab explicitly approves a change, AND
2. The change is committed before further development

Any deviation without update is considered drift.

---

**END OF DOCUMENT**
