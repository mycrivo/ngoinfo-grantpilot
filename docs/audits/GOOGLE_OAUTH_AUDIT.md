# Google OAuth Audit — GrantPilot

**Date:** 2026-02-07
**Auditor:** Contract-first backend architect
**Scope:** Full code + config + deployment audit of Google OAuth login flow
**Contracts used:** API_CONTRACT.md, AUTH_AND_SSO_STRATEGY.md, ENV_VARS_REFERENCE.md, LAUNCH_JOURNEYS_SPEC.md, GUARDRAILS_RUNTIME_AND_SECURITY.md, DEPLOYMENT_HARDENING.md

---

## A) Current State — OAuth Flow Diagram

```
BROWSER (grantpilot.ngoinfo.org)
  │
  │  1. GET https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start?redirect=1
  │     ↳ Backend returns JSON: { authorization_url, state }
  │     ↳ redirect_uri sent to Google = GOOGLE_OAUTH_REDIRECT_URI + "?redirect=1"
  │       = "https://grantpilot.ngoinfo.org/api/auth/google/callback?redirect=1"
  │
  │  2. Browser navigates to authorization_url
  │     → https://accounts.google.com/o/oauth2/v2/auth
  │       ?client_id=<GOOGLE_OAUTH_CLIENT_ID>
  │       &redirect_uri=https://grantpilot.ngoinfo.org/api/auth/google/callback?redirect=1
  │       &response_type=code
  │       &scope=openid+email+profile
  │       &state=<opaque>
  │
  │  3. User authenticates at Google
  │
  │  4. Google redirects → https://grantpilot.ngoinfo.org/api/auth/google/callback
  │       ?code=<google_auth_code>&state=<opaque>&redirect=1
  │     ┌──────────────────────────────────────────────────────┐
  │     │  *** THIS IS WHERE THE 404 OCCURS ***               │
  │     │  grantpilot.ngoinfo.org → Cloudflare → FRONTEND     │
  │     │  (Next.js) which has NO /api/auth/google/callback    │
  │     │  route → returns 404 Not Found                       │
  │     └──────────────────────────────────────────────────────┘
  │
  │  ── If callback DID reach the backend ──
  │
  │  5. Backend exchanges code for tokens with Google
  │     POST https://oauth2.googleapis.com/token
  │       redirect_uri = GOOGLE_OAUTH_REDIRECT_URI (base, WITHOUT ?redirect=1)
  │       *** BUG: redirect_uri mismatch — Google sent ?redirect=1 but token
  │           exchange sends base URI → Google rejects with redirect_uri_mismatch ***
  │
  │  6. (redirect=1 path) Backend creates one-time exchange code,
  │     redirects → AUTH_POST_LOGIN_REDIRECT_URL?code=<exchange_code>
  │     = https://grantpilot.ngoinfo.org/docs?code=<exchange_code>
  │
  │  7. Frontend calls POST https://ngoinfo-grantpilot-production.up.railway.app/api/auth/exchange
  │     { "code": "<exchange_code>" }
  │     → Receives { access_token, refresh_token, user }
```

### Actual domains in play

| Role | Domain | Infrastructure |
|---|---|---|
| Frontend (canonical) | `https://grantpilot.ngoinfo.org` | Cloudflare → Railway (Next.js) |
| Backend (direct) | `https://ngoinfo-grantpilot-production.up.railway.app` | Railway (FastAPI/Uvicorn) |
| Google OAuth | `https://accounts.google.com` | Google |

---

## B) Mismatch Table

### B.1 — GOOGLE_OAUTH_REDIRECT_URI (CRITICAL)

| Source | Value | Citation |
|---|---|---|
| AUTH_AND_SSO_STRATEGY.md (Locked) | `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback` | Line 24 |
| ENV_VARS_REFERENCE.md | `https://ngoinfo-grantpilot-production.up.railway.app/auth/google/callback` (**missing `/api` prefix — typo**) | Line 61 |
| GUARDRAILS.md | `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback` | Line 358 |
| **Actual Railway env** | `https://grantpilot.ngoinfo.org/api/auth/google/callback` | Railway config |
| **Google Console (assumed)** | Unknown — must verify | — |

**Conflict:** All three contracts specify the **backend Railway domain** (`ngoinfo-grantpilot-production.up.railway.app`). The actual Railway env var uses the **frontend Cloudflare domain** (`grantpilot.ngoinfo.org`). The frontend does not proxy `/api/*` to the backend, so Google's redirect hits the Next.js frontend and returns 404.

**Secondary conflict:** ENV_VARS_REFERENCE.md:61 has a typo — it says `/auth/google/callback` instead of `/api/auth/google/callback`. The actual FastAPI route is mounted at `prefix="/api/auth"` (`app/api/routes/auth.py:31`), so the correct path is `/api/auth/google/callback`.

### B.2 — AUTH_POST_LOGIN_REDIRECT_URL

| Source | Value | Citation |
|---|---|---|
| AUTH_AND_SSO_STRATEGY.md (Locked) | `https://grantpilot.ngoinfo.org/auth/callback` | Line 25 |
| ENV_VARS_REFERENCE.md | `https://grantpilot.ngoinfo.org/auth/callback` | Line 130 |
| Code default (config.py) | `https://grantpilot.ngoinfo.org/auth/callback` | Line 28 |
| **Actual Railway env** | `https://grantpilot.ngoinfo.org/docs` | Railway config |

**Conflict:** The Railway env var overrides the default to `/docs`, which contradicts all three contracts that specify `/auth/callback`. The `/auth/callback` route is where the frontend would handle the exchange code and call `POST /api/auth/exchange`. Redirecting to `/docs` means the exchange code arrives at a page that doesn't process it.

### B.3 — APP_BASE_URL

| Source | Value | Citation |
|---|---|---|
| ENV_VARS_REFERENCE.md | `https://ngoinfo-grantpilot-production.up.railway.app` ("Must be public URL" of backend) | Line 35 |
| **Actual Railway env** | `https://grantpilot.ngoinfo.org` | Railway config |

**Conflict:** The contract defines `APP_BASE_URL` as the backend's own public URL. The Railway env has it set to the frontend domain. If any backend code uses `APP_BASE_URL` to construct self-referencing URLs (e.g., health check links, webhook URLs), they would point to the wrong service.

### B.4 — AUTH_ALLOWED_REDIRECT_URLS

| Source | Value | Citation |
|---|---|---|
| ENV_VARS_REFERENCE.md | `https://grantpilot.ngoinfo.org/auth/callback` | Line 53 |
| GUARDRAILS.md | `https://grantpilot.ngoinfo.org/auth/callback` | Line 350 |
| **Actual Railway env** | `https://grantpilot.ngoinfo.org/docs,https://grantpilot.ngoinfo.org/auth/callback,https://ngoinfo-grantpilot-production.up.railway.app/docs` | Railway config |

**Note:** The actual env includes three URLs vs the contract's one. The extra entries (`/docs`, Railway `/docs`) are not in any contract. This is not strictly a bug — the allowlist is additive — but it expands the attack surface beyond what contracts specify, and the Railway internal URL should never appear in redirects per ENV_VARS_REFERENCE.md:134 ("Never use internal Railway URLs in OAuth").

### B.5 — redirect_uri mismatch in token exchange (CODE BUG)

| Component | redirect_uri value |
|---|---|
| `/api/auth/google/start?redirect=1` sends to Google | `GOOGLE_OAUTH_REDIRECT_URI` + `?redirect=1` (e.g., `...callback?redirect=1`) — `app/api/routes/auth.py:171-176` |
| `/api/auth/google/callback` sends to Google token endpoint | `settings.GOOGLE_OAUTH_REDIRECT_URI` (base, no `?redirect=1`) — `app/api/routes/auth.py:214` |

**Bug:** Google requires the `redirect_uri` in the token exchange to **exactly match** the one used in the authorization request. When `redirect=1` is used, the authorization request includes `?redirect=1` in the redirect_uri, but the token exchange always sends the base URI without it. Google will reject the token exchange with `redirect_uri_mismatch`.

### B.6 — IP extraction does not follow contract

| Source | Behavior | Citation |
|---|---|---|
| AUTH_AND_SSO_STRATEGY.md (Locked) | Use `CF-Connecting-IP` → fallback `X-Forwarded-For` → fallback `request.remote_addr`; validate IP format | Lines 80-83 |
| **Code** | Uses `request.client.host` only | `app/api/routes/auth.py:76-77` |

**Conflict:** Behind Cloudflare, `request.client.host` will be a Cloudflare edge IP, not the real user IP. All users will share rate limit buckets by Cloudflare edge IP, making per-IP rate limiting ineffective.

### B.7 — FRONTEND_BASE_URL (undocumented env var)

The Railway env has `FRONTEND_BASE_URL=https://grantpilot.ngoinfo.org` but this variable:
- Is NOT in ENV_VARS_REFERENCE.md
- Is NOT in the `Settings` class (`app/core/config.py`)
- Is NOT referenced anywhere in backend code

This is an unused, undocumented env var. Per ENV_VARS_REFERENCE.md:24 ("Do not introduce new env var names without updating this file"), this should be removed or documented.

### B.8 — Missing FRONTEND_BASE_URL in Settings class

The code default `AUTH_POST_LOGIN_REDIRECT_URL` in `config.py:28` is hardcoded to `https://grantpilot.ngoinfo.org/auth/callback`. The env var `FRONTEND_BASE_URL` exists in Railway but is never used. If the intent is to dynamically construct the post-login redirect URL, this is disconnected.

---

## C) Prioritized Fix Plan

### P0 — Must-Fix (Blocking: OAuth flow completely broken)

#### P0-1: Fix GOOGLE_OAUTH_REDIRECT_URI to point to backend domain

**Problem:** The callback URL points to the frontend domain which does not handle `/api/*` routes, causing a 404 on every OAuth login attempt.

**File(s) to change:** Railway environment variables (not code)

**What to change:**
Set `GOOGLE_OAUTH_REDIRECT_URI` to `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback` — matching AUTH_AND_SSO_STRATEGY.md:24 and GUARDRAILS.md:358.

**Also required:** Update Google Cloud Console → Credentials → OAuth 2.0 Client → Authorized redirect URIs to include exactly `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback`.

**How to test:**
```bash
# 1. Verify start returns correct authorization_url
curl -s https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start | jq .authorization_url
# Verify redirect_uri parameter contains the backend domain

# 2. Open the authorization_url in a browser, authenticate,
#    and verify the callback hits the backend (not 404)
```

#### P0-2: Fix redirect_uri mismatch in token exchange when redirect=1 is used

**Problem:** When `redirect=1` is passed to `/start`, the authorization request uses `redirect_uri=...?redirect=1`, but the callback token exchange always uses the base `GOOGLE_OAUTH_REDIRECT_URI` without `?redirect=1`. Google rejects this with `redirect_uri_mismatch`.

**File(s) to change:** `app/api/routes/auth.py`

**What to change (Option A — recommended):** In the `google_oauth_callback` function (line 207-218), reconstruct the `redirect_uri` sent to Google's token endpoint to match what was sent in the authorization request. If `redirect` query param is `"1"`, append `?redirect=1` to the `redirect_uri` in the token exchange POST data, mirroring the logic in `google_oauth_start` (lines 171-176).

Specifically, in `google_oauth_callback` around line 214, change the token exchange `redirect_uri` from:
```
"redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI
```
to a value that includes `?redirect=1` when the callback's own query params include `redirect=1`.

**What to change (Option B — simpler):** Remove the redirect_uri modification from `google_oauth_start` entirely. Instead of appending `?redirect=1` to the redirect_uri sent to Google, pass `redirect=1` exclusively through the `state` parameter (encode it in state or use a separate mechanism). This way the redirect_uri always matches exactly.

**How to test:**
```bash
# 1. Start OAuth with redirect=1
curl -s 'https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start?redirect=1' | jq .
# 2. Complete flow in browser; verify no redirect_uri_mismatch error from Google
# 3. Verify redirect to AUTH_POST_LOGIN_REDIRECT_URL with ?code= param
```

#### P0-3: Fix AUTH_POST_LOGIN_REDIRECT_URL to match contract

**Problem:** Railway env has `https://grantpilot.ngoinfo.org/docs` but contracts specify `https://grantpilot.ngoinfo.org/auth/callback`. The `/auth/callback` page is the frontend route designed to extract the exchange code and call `POST /api/auth/exchange`. Redirecting to `/docs` means the exchange code goes unused.

**File(s) to change:** Railway environment variables (not code)

**What to change:**
Set `AUTH_POST_LOGIN_REDIRECT_URL` to `https://grantpilot.ngoinfo.org/auth/callback` per AUTH_AND_SSO_STRATEGY.md:25 and ENV_VARS_REFERENCE.md:130.

**How to test:**
```bash
# After completing OAuth flow with redirect=1, verify browser lands on
# https://grantpilot.ngoinfo.org/auth/callback?code=<exchange_code>
# and NOT on /docs
```

#### P0-4: Register correct redirect URI in Google Cloud Console

**Problem:** Google Console must have the exact redirect URI(s) that the application uses. Currently the flow is broken regardless of what's registered, but after fixing P0-1, the Console must match.

**File(s) to change:** Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs → `<GOOGLE_OAUTH_CLIENT_ID>`

**What to change:**
Add (or update to) the following Authorized redirect URI:
- `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback`

If Option A from P0-2 is used (redirect=1 appended to redirect_uri), also add:
- `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback?redirect=1`

If Option B from P0-2 is used (redirect_uri never modified), only the first URI is needed.

**How to test:**
```bash
# Complete full OAuth flow in browser. If Google shows
# "Error 400: redirect_uri_mismatch" the console config is wrong.
```

---

### P1 — Hardening (Not blocking but violates contracts / weakens security)

#### P1-1: Fix IP extraction to use CF-Connecting-IP

**Problem:** Rate limiting uses `request.client.host` instead of Cloudflare headers, making all users share rate limit buckets by CF edge IP.

**File(s) to change:** `app/api/routes/auth.py`

**What to change:** Update `_get_client_ip` (line 76-77) to check `CF-Connecting-IP` first, fall back to `X-Forwarded-For`, then `request.client.host`, per AUTH_AND_SSO_STRATEGY.md:80-83. Add basic IP format validation.

**How to test:**
```bash
# Send request with CF-Connecting-IP header
curl -H "CF-Connecting-IP: 1.2.3.4" \
  https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start
# Verify via logs that rate limit key uses 1.2.3.4
```

#### P1-2: Fix APP_BASE_URL to match contract

**Problem:** Railway env has `APP_BASE_URL=https://grantpilot.ngoinfo.org` (frontend domain) but ENV_VARS_REFERENCE.md:35 defines it as the backend public URL.

**File(s) to change:** Railway environment variables

**What to change:**
Set `APP_BASE_URL` to `https://ngoinfo-grantpilot-production.up.railway.app`.

**How to test:**
```bash
# Verify health endpoint returns correct self-URL if applicable
curl https://ngoinfo-grantpilot-production.up.railway.app/api/health
```

#### P1-3: Tighten AUTH_ALLOWED_REDIRECT_URLS

**Problem:** Current Railway value includes `https://ngoinfo-grantpilot-production.up.railway.app/docs` which violates ENV_VARS_REFERENCE.md:134 ("Never use internal Railway URLs in OAuth, Stripe, or email links").

**File(s) to change:** Railway environment variables

**What to change:**
Set `AUTH_ALLOWED_REDIRECT_URLS` to `https://grantpilot.ngoinfo.org/auth/callback` only (per ENV_VARS_REFERENCE.md:53 and GUARDRAILS.md:350). If `/docs` needs to be a valid redirect target post-login, add `https://grantpilot.ngoinfo.org/docs` — but never the Railway internal URL.

**How to test:**
```bash
# Attempt OAuth with redirect=1 when AUTH_POST_LOGIN_REDIRECT_URL is /auth/callback
# Verify redirect succeeds. Attempt to manipulate redirect target to unlisted URL;
# verify it returns OAUTH_EXCHANGE_FAILED.
```

#### P1-4: Add Google Console Authorized JavaScript Origins

**Problem:** Google OAuth consent screen may require JavaScript origins for any client-side interactions.

**File(s) to change:** Google Cloud Console

**What to change:** Add Authorized JavaScript Origins:
- `https://grantpilot.ngoinfo.org`
- `https://ngoinfo-grantpilot-production.up.railway.app`

**How to test:** Complete OAuth flow in browser; no "origin not allowed" errors.

#### P1-5: In-memory oauth_state_store lacks cleanup

**Problem:** `oauth_state_store` (`app/api/routes/auth.py:33`) is an unbounded dict. Expired entries are only removed on consumption (`_consume_oauth_state`). If many users start OAuth but never complete it, the dict grows without bound. Over days/weeks on a long-running Railway instance, this is a memory leak.

**File(s) to change:** `app/api/routes/auth.py`

**What to change:** Add periodic cleanup of expired entries in `_store_oauth_state` — e.g., every 100 inserts, purge entries older than 10 minutes.

**How to test:** Unit test that inserts 200 states, advances time past expiry, inserts one more, and asserts dict size is small.

---

### P2 — Cleanup / Refactor (Non-blocking, contractual hygiene)

#### P2-1: Fix typo in ENV_VARS_REFERENCE.md

**Problem:** Line 61 says `https://ngoinfo-grantpilot-production.up.railway.app/auth/google/callback` (missing `/api` prefix). The actual route is `/api/auth/google/callback`.

**File(s) to change:** `docs/artefacts/ENV_VARS_REFERENCE.md`

**What to change:** Line 61: change `/auth/google/callback` to `/api/auth/google/callback`.

**How to test:** Manual review.

#### P2-2: Remove unused FRONTEND_BASE_URL env var

**Problem:** `FRONTEND_BASE_URL` is set in Railway but is not declared in `Settings` (config.py), not referenced in any code, and not documented in ENV_VARS_REFERENCE.md.

**File(s) to change:** Railway environment variables

**What to change:** Remove `FRONTEND_BASE_URL` from Railway env vars, or document it in ENV_VARS_REFERENCE.md and add it to the `Settings` class if it serves a purpose.

**How to test:** Deploy without the variable; verify no startup errors.

#### P2-3: Add CORS_ALLOWED_ORIGINS for backend domain

**Problem:** `CORS_ALLOWED_ORIGINS` only includes `https://grantpilot.ngoinfo.org`. If any direct browser requests are made to the backend domain (e.g., during OAuth callback redirect, or Swagger/docs at the Railway URL), CORS will block them.

**File(s) to change:** Railway environment variables (optionally)

**What to change:** If the backend's own Swagger docs at `https://ngoinfo-grantpilot-production.up.railway.app/docs` needs to make API calls, add that origin. Otherwise, current config is correct — frontend-only origin is the right CORS policy.

**How to test:**
```bash
curl -H "Origin: https://grantpilot.ngoinfo.org" -I \
  https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start
# Verify Access-Control-Allow-Origin header is present
```

#### P2-4: Consider encoding redirect=1 in state instead of redirect_uri

**Problem:** Appending `?redirect=1` to `redirect_uri` requires registering a second URI in Google Console and matching it precisely in the token exchange. This is fragile.

**File(s) to change:** `app/api/routes/auth.py`

**What to change:** Instead of modifying `redirect_uri`, encode the `redirect` flag in the OAuth `state` parameter (e.g., as a JSON payload: `{"nonce": "...", "redirect": true}`). The callback can then read the state to determine behavior without affecting redirect_uri.

**How to test:** Full OAuth flow with and without redirect mode; verify both produce correct behavior with a single registered redirect URI.

---

## D) Gold Configuration

### D.1 — Google Cloud Console Settings

**Authorized Redirect URIs (exactly):**

```
https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback
```

If P2-4 is NOT implemented (i.e., `redirect=1` is still appended to redirect_uri), add a second entry:

```
https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback?redirect=1
```

**Authorized JavaScript Origins:**

```
https://grantpilot.ngoinfo.org
https://ngoinfo-grantpilot-production.up.railway.app
```

### D.2 — Railway Environment Variables (Backend Service)

```bash
APP_BASE_URL=https://ngoinfo-grantpilot-production.up.railway.app
APP_NAME=grantpilot

# Auth
AUTH_ACCESS_TOKEN_TTL_MIN=15
AUTH_ALLOWED_REDIRECT_URLS=https://grantpilot.ngoinfo.org/auth/callback
AUTH_POST_LOGIN_REDIRECT_URL=https://grantpilot.ngoinfo.org/auth/callback

# CORS
CORS_ALLOWED_ORIGINS=https://grantpilot.ngoinfo.org

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=<your-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<your-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback

# Remove these:
# FRONTEND_BASE_URL  (unused, undocumented)
```

### D.3 — Canonical Callback Domain: Backend

**Decision:** The OAuth callback MUST live on the **backend domain** (`ngoinfo-grantpilot-production.up.railway.app`), NOT the frontend domain (`grantpilot.ngoinfo.org`).

**Justification grounded in contracts and deployment reality:**

1. **AUTH_AND_SSO_STRATEGY.md:24 (Locked):** Explicitly specifies `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback` as the callback URL.

2. **Routing reality:** `grantpilot.ngoinfo.org` resolves via Cloudflare to the frontend Railway service (Next.js). There is no reverse proxy or Next.js rewrite that forwards `/api/*` to the backend. The backend only listens on its own Railway domain.

3. **DEPLOYMENT_HARDENING.md:180:** "The frontend service does not perform business logic, entitlement checks, quota enforcement, or AI execution; the backend remains the single source of truth." OAuth token exchange is business logic that belongs on the backend.

4. **ENV_VARS_REFERENCE.md:118:** Frontend uses `NEXT_PUBLIC_API_BASE_URL=https://ngoinfo-grantpilot-production.up.railway.app` to reach the backend, confirming the frontend and backend are separate services with no path-based routing at the frontend domain.

5. **Security:** The callback handles `GOOGLE_OAUTH_CLIENT_SECRET` to exchange the authorization code. This must never transit through the frontend (ENV_VARS_REFERENCE.md:126: "GOOGLE_OAUTH_CLIENT_SECRET" is forbidden on frontend).

**Alternative considered and rejected:** Adding a Next.js API route or rewrite rule at the frontend to proxy `/api/auth/google/callback` to the backend. This would:
- Add unnecessary complexity and latency
- Require the frontend to handle auth-related routing it shouldn't own
- Contradict DEPLOYMENT_HARDENING.md:180
- Risk leaking secrets if misconfigured

---

## E) Contract Conflict Report

The following conflicts exist **between contracts themselves** (not just code-vs-contract):

### E.1 — ENV_VARS_REFERENCE.md:61 vs AUTH_AND_SSO_STRATEGY.md:24

| Document | GOOGLE_OAUTH_REDIRECT_URI path |
|---|---|
| ENV_VARS_REFERENCE.md:61 | `/auth/google/callback` (missing `/api`) |
| AUTH_AND_SSO_STRATEGY.md:24 | `/api/auth/google/callback` (correct) |
| GUARDRAILS.md:358 | `/api/auth/google/callback` (correct) |

**Resolution:** ENV_VARS_REFERENCE.md:61 has a typo. The `/api` prefix is present in the actual route definition (`app/api/routes/auth.py:31`: `prefix="/api/auth"`) and in two other contracts. Fix the typo in ENV_VARS_REFERENCE.md.

### E.2 — No conflicts found between other contract pairs

All other contract documents are consistent on:
- Post-login redirect URL = `/auth/callback`
- Token format and claims
- Rate limiting rules
- Refresh token rotation pattern
- OAuth exchange flow

---

## F) Summary of Root Cause: 404 on Callback

The most likely cause of 404 "Not Found" on the OAuth callback is:

1. `GOOGLE_OAUTH_REDIRECT_URI` in Railway is set to `https://grantpilot.ngoinfo.org/api/auth/google/callback`
2. `grantpilot.ngoinfo.org` resolves (via Cloudflare) to the **frontend** Next.js service
3. The frontend has no route handler for `/api/auth/google/callback`
4. Next.js returns 404

**To confirm with minimal manual testing:**

```bash
# Test 1: Verify frontend returns 404 for the callback path
curl -s -o /dev/null -w "%{http_code}" \
  "https://grantpilot.ngoinfo.org/api/auth/google/callback"
# Expected: 404

# Test 2: Verify backend handles the callback path
curl -s -o /dev/null -w "%{http_code}" \
  "https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback"
# Expected: 400 (missing code/state, but NOT 404 — proves route exists)

# Test 3: Verify start endpoint works on backend
curl -s "https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/start" | python3 -m json.tool
# Expected: 200 with authorization_url
```

If Test 1 returns 404 and Test 2 returns 400, the diagnosis is confirmed: the redirect URI must use the backend domain.

---

## G) Implementation Order

```
P0-1 (fix GOOGLE_OAUTH_REDIRECT_URI env var)
  ↓
P0-4 (register correct URI in Google Console)
  ↓
P0-2 (fix redirect_uri mismatch in token exchange code)
  ↓
P0-3 (fix AUTH_POST_LOGIN_REDIRECT_URL env var)
  ↓
── OAuth flow now works end-to-end ──
  ↓
P1-1 (fix IP extraction)
P1-2 (fix APP_BASE_URL)
P1-3 (tighten redirect allowlist)
P1-4 (add JS origins in Console)
P1-5 (state store cleanup)
  ↓
P2-* (cleanup items)
```
