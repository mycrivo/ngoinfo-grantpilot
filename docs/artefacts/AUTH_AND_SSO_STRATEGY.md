
Supported Methods

Google OAuth

Email Magic Link (no passwords)

Token-based

Expiry enforced

Single-use tokens

Email Verification: Not used in MVP (auth is Google OAuth + Email Magic Link)

Sessions

Access token + refresh token

Multi-device allowed

Explicit logout invalidates refresh token

Account Linking

Same email across OAuth and Email Magic Link: links accounts

## Token Policy

- Access token TTL: 15 minutes
- Refresh token TTL: 30 days

## Refresh Flow
- Frontend retries once on 401 via /auth/refresh
- If refresh fails → redirect to login

## Rate Limiting
- Login: 5 failures / 15 min → temporary block

## MFA
- Explicitly out of scope for MVP
