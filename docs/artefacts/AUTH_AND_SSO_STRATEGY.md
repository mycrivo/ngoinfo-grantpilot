# AUTH_AND_SSO_STRATEGY.md

## Supported Methods

- Google OAuth
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

Frontend hosting note
- The frontend is hosted on Railway and served via https://grantpilot.ngoinfo.org (Cloudflare fronted).
- Post-login redirects must always target grantpilot.ngoinfo.org routes, never Railway service URLs.


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
- Return format: JSON body only (never cookies)

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

## Rate Limiting (Locked)
Enforced only if `AUTH_RATE_LIMIT_ENABLED=true`.

- Magic link request:
  - Per email: 5 per hour
  - Per IP: 20 per hour
- Magic link consume:
  - Per IP: 30 per hour
  IP Extraction (Behind Cloudflare):
	- Use CF-Connecting-IP header (Cloudflare)
	- Fallback to X-Forwarded-For if CF header missing
	- Fallback to request.remote_addr
	- Validate IP format before using as rate limit key
- Google OAuth start:
  - Per IP: 60 per hour
- Refresh:
  - Per user: 120 per hour (fallback to IP if user not resolved)

On limit exceeded:
- HTTP 429
- error_code="RATE_LIMITED"

Rate Limiting Implementation (MVP):
  - Use in-memory dict with expiry (acceptable for single-instance Railway)
  - Structure: { "key": (count, expiry_timestamp) }
  - Post-MVP: migrate to Redis for multi-instance support

## MFA
- Explicitly out of scope for MVP
