
Supported Methods

Google OAuth

Email + password

Password Reset

Token-based

Expiry enforced

Single-use tokens

Email Verification

Required for email/password

Optional for Google OAuth

Sessions

Access token + refresh token

Multi-device allowed

Explicit logout invalidates refresh token

Account Linking

Same email across OAuth and password links accounts

## Token Policy

- Access token TTL: 15 minutes
- Refresh token TTL: 30 days
- Password reset token TTL: 1 hour (single use)

## Refresh Flow
- Frontend retries once on 401 via /auth/refresh
- If refresh fails → redirect to login

## Password Rules
- Min 8 characters
- Must include uppercase, lowercase, number

## Rate Limiting
- Login: 5 failures / 15 min → temporary block
- Password reset: 3/hour per email

## MFA
- Explicitly out of scope for MVP
