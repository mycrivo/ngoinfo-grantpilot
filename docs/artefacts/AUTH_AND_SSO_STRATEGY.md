# AUTH_AND_SSO_STRATEGY.md

**Status:** Canonical (LOCKED FOR BUILD)  
**Version:** 1.1  
**Last Updated:** 2026-02-07

---

## Supported Methods

- Google OAuth (via Authlib — see Implementation Strategy below)
- Email Magic Link (Resend)
  - Token-based
  - Expiry enforced
  - Single-use tokens
- Email Verification: Not used in MVP (auth is Google OAuth + Email Magic Link)

## Sessions

- Access token + refresh token
- Single active refresh token per user (MVP). Logging in on another device invalidates prior sessions.
- Explicit logout invalidates refresh token
- Account Linking: same email across OAuth and Email Magic Link links accounts

Post-MVP option (out of scope):
- True multi-device support via per-device refresh tokens, a sessions table, and per-device revoke.

## OAuth URLs (Locked)

- OAuth callback URL: `https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback`
- Post-login redirect URL: `https://grantpilot.ngoinfo.org/auth/callback`

Frontend hosting note:
- The frontend is hosted on Railway and served via https://grantpilot.ngoinfo.org (Cloudflare fronted).
- Post-login redirects must always target grantpilot.ngoinfo.org routes, never Railway service URLs.

Callback behaviour:
- The callback endpoint always redirects the browser to the post-login redirect URL.
- Tokens are never included in redirect URL query parameters (see OAuth Post-Login Flow below).

---

## Google OAuth Implementation Strategy (MVP)

### Library: Authlib

Google OAuth is implemented using **Authlib** (with httpx transport). Authlib handles:
- Authorization URL generation (with state and PKCE)
- Authorization code → token exchange with Google
- Google user info / ID token parsing
- Error handling for OAuth edge cases (expired codes, invalid state, network errors)

We do NOT use Authlib for session management, JWT minting, or refresh tokens. Those remain custom (see Token Policy below).

### OAuth Post-Login Flow (Secure Code Exchange)

Tokens must never appear in browser URLs. The post-login handoff uses a one-time authorization code exchange:

```
1. Frontend calls GET /api/auth/google/start
   → Backend generates Google authorization URL via Authlib
   → Backend encodes redirect intent into `state` parameter (see State Parameter below)
   → Returns { authorization_url, state }

2. Frontend redirects browser to Google authorization URL

3. Google authenticates user, redirects to callback:
   GET /api/auth/google/callback?code={google_code}&state={state}

4. Backend (callback handler):
   a. Validates state parameter
   b. Uses Authlib to exchange Google code for Google tokens + user info
   c. Finds or creates GrantPilot user (account linking by email)
   d. Sets google_sub on user if not already set
   e. Fetches actual plan from user_plans table
   f. Mints GrantPilot JWT access token + creates refresh token (existing logic)
   g. Generates a one-time auth_code (64-char random string)
   h. Stores auth_code (hashed, DB-backed, 60-second TTL) mapped to the minted tokens
   i. Redirects browser to: {AUTH_POST_LOGIN_REDIRECT_URL}?code={auth_code}&state={forwarded_state}

5. Frontend (on /auth/callback page):
   a. Extracts code and state from URL query params
   b. Calls POST /api/auth/exchange with { "code": auth_code }
   c. Receives tokens + user in JSON response body
   d. Stores tokens in memory (not localStorage)
   e. Redirects user to intended destination (decoded from state, e.g., opportunity page)

6. Auth code is deleted from server store after use (single-use, 60-second TTL)
```

**Security properties:**
- GrantPilot tokens (JWT + refresh) never appear in URLs, browser history, referrer headers, or Cloudflare logs
- Auth code is single-use, hashed, and expires in 60 seconds
- State parameter is validated on callback to prevent CSRF

### State Parameter

The `state` parameter serves two purposes:
1. **CSRF protection:** validated on callback to ensure the request originated from our app
2. **Redirect intent preservation:** encodes where the user wanted to go (per WORDPRESS_TO_GRANTPILOT_INTEGRATION.md)

State encoding (MVP):
- Format: JWT (HS256), signed with AUTH_JWT_SIGNING_KEY
- Claims: `{ "redirect_intent": { "opportunity_id": "uuid or null", "source": "wp or null" }, "nonce": "random", "iat": timestamp, "exp": timestamp }`
- Expiry: 10 minutes
- On callback, validate signature and expiry before processing

### Auth Code Store (Implementation Detail)

The one-time auth code is stored in the database (hashed) to support persistence:

Rules:
- Auth code is a 64-character cryptographically random string
- Stored as SHA-256 hash (never plain)
- TTL: 60 seconds (entries older than 60s are rejected and cleaned up)
- Single-use: deleted after successful exchange
- DB-backed storage is the approved MVP implementation

### Account Linking (Unchanged)

- If a user signs in via Google and their email matches an existing Magic Link user → same account, google_sub is set
- If a user signs in via Magic Link and their email matches an existing Google user → same account
- `users.id` is the canonical ownership key regardless of auth method
- `users.auth_provider` is descriptive only and must not be used as an authorization gate

---

## Token Policy (Locked)

### Access Token (JWT)
- TTL: 15 minutes
- Algorithm: HS256
- Required claims:
  - iss: "grantpilot"
  - aud: "grantpilot-web"
  - sub: user id (UUID string)
  - email: user email
  - plan: "FREE" | "GROWTH" | "IMPACT" (snapshot only; backend is source of truth)
  - iat, nbf, exp, jti
- Return format: JSON body only (never cookies, never URL query parameters)

**Plan claim source (non-negotiable):**
- The `plan` claim must be fetched from `user_plans` table at token minting time
- If no `user_plans` record exists for the user, default to "FREE"
- This applies to ALL token minting paths: OAuth callback, Magic Link consume, and token refresh
- Hardcoding `plan="FREE"` is a contract violation

### Refresh Token (Opaque)
- Opaque string (not JWT)
- Stored hashed in DB
- TTL: 30 days
- Rotation: enabled (single-use)
- Each successful refresh invalidates prior refresh token and issues a new refresh token
- Revocation: `POST /api/auth/logout` revokes the presented refresh token immediately

### Refresh Token Rotation (implementation detail):
  1. Generate new refresh token
  2. Insert new token row (token_hash, user_id, issued_at, expires_at)
  3. Update old token row:
     - SET revoked_at = now()
     - SET replaced_by_token_id = new_token.id
  4. Return new access + refresh tokens

## Refresh Flow (Locked)
- Frontend retries once on 401 via `/api/auth/refresh`
- If refresh fails → redirect to login

---

## Rate Limiting (Locked)
Enforced only if `AUTH_RATE_LIMIT_ENABLED=true`.

- Magic link request:
  - Per email: 5 per hour
  - Per IP: 20 per hour
- Magic link consume:
  - Per IP: 30 per hour
- Auth code exchange:
  - Per IP: 30 per hour
- Google OAuth start:
  - Per IP: 60 per hour
- Refresh:
  - Per user: 120 per hour (fallback to IP if user not resolved)

IP Extraction (Behind Cloudflare):
  - Use CF-Connecting-IP header (Cloudflare)
  - Fallback to X-Forwarded-For if CF header missing
  - Fallback to request.remote_addr
  - Validate IP format before using as rate limit key

On limit exceeded:
- HTTP 429
- error_code="RATE_LIMITED"

Rate Limiting Implementation (MVP):
  - Use in-memory dict with expiry (acceptable for single-instance Railway)
  - Structure: { "key": (count, expiry_timestamp) }
  - Railway must be pinned to 1 replica, 1 worker (see mvp_execution_plan_FINAL_2.md Section 2.5)
  - Post-MVP: migrate to Redis for multi-instance support

## MFA
- Explicitly out of scope for MVP

---

## Auth Endpoints Summary

| Endpoint | Method | Auth Required | Purpose |
|----------|--------|---------------|---------|
| `/api/auth/google/start` | GET | No | Returns Google authorization URL |
| `/api/auth/google/callback` | GET | No | Handles Google redirect, issues auth code, redirects to frontend |
| `/api/auth/exchange` | POST | No | Exchanges one-time auth code for tokens (NEW in v1.1) |
| `/api/auth/magic-link/request` | POST | No | Sends magic link email |
| `/api/auth/magic-link/consume` | POST | No | Exchanges magic link token for tokens |
| `/api/auth/refresh` | POST | No | Rotates refresh token, issues new access token |
| `/api/auth/logout` | POST | No | Revokes refresh token |
| `/api/auth/test-mode/mint` | POST | No (gated) | Test-only token minting (removed pre-launch) |

Full request/response schemas: see API_CONTRACT.md

---

## Changelog

### v1.1 (2026-02-07)
- Added: Google OAuth Implementation Strategy section (Authlib + secure code exchange)
- Added: Auth Code Store implementation detail
- Added: State Parameter specification (CSRF + redirect intent)
- Added: Rate limit for `/api/auth/exchange` endpoint (30/IP/hour)
- Added: Plan claim source rule (must fetch from user_plans, never hardcode)
- Added: Auth Endpoints Summary table
- Changed: Callback behaviour note — callback always redirects, tokens never in URLs
- Changed: Access token return format — explicitly prohibits URL query parameters
- Changed: Rate limiting note — references single-instance deployment constraint
- Unchanged: Token Policy, Refresh Token Rotation, Refresh Flow, Sessions, Account Linking, MFA

### v1.0 (2026-01-20)
- Initial locked version
