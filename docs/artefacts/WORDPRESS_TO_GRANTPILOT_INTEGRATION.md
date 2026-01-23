App Location

https://app.ngoinfo.org

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
  https://app.ngoinfo.org/start?opportunity_id={id}&source=wp

- Backend issues a signed state token containing:
  - opportunity_id
  - source
  - timestamp

- If user is unauthenticated:
  - Redirect to /login?state={signed_token}

- Post-login:
  - Backend validates state token
  - Redirects user back to /start with context restored
