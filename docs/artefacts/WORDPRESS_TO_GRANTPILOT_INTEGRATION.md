App Location

https://grantpilot.ngoinfo.org

Deep Link Format /start?opportunity_id={id}&utm_source=ngoinfo

Behavior

Preserve context through auth

Resume original intent post-login

Auth options: Google OAuth or Email Magic Link (no passwords)

Failure Handling

Invalid opportunity → safe error + redirect to browse

App down → fallback message on WP

## Context Preservation

- WordPress links to:
  
  https://grantpilot.ngoinfo.org/start?opportunity_id={id}&source=wp

- Backend issues a signed state token containing:
  - opportunity_id
  - source
  - timestamp

- If user is unauthenticated:
  - Redirect to /login?state={signed_token}

- Post-login:
  - Backend validates state token
  - Redirects user back to /start with context restored
  
  State Token Implementation:
  - Format: JWT (HS256)
  - Signing key: AUTH_JWT_SIGNING_KEY (same as access tokens)
  - Expiry: 15 minutes
  - Claims: { "opportunity_id": "uuid", "source": "wp", "iat": timestamp, "exp": timestamp }