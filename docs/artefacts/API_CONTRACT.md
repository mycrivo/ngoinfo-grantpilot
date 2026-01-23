# API_CONTRACT.md

## Standards

- RESTful endpoints
- JSON only
- Proposal export: DOCX only (PDF not supported)

## Standard Error Model (All Endpoints)

HTTP status codes: 400/401/403/404/409/422/429/500

Error JSON:
```
{
  "error_code": "string",
  "message": "string",
  "details": {},
  "request_id": "string"
}
```

Notes:
- `details` is optional
- `request_id` is optional if available

## Auth Endpoints (Locked)

### 1) GET /api/auth/google/start
Purpose: returns authorization_url; frontend navigates

Response 200:
```
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "opaque_state_string"
}
```

Errors:
- 500 OAUTH_CONFIG_ERROR

### 2) GET /api/auth/google/callback
Purpose: completes OAuth, issues tokens

Behavior:
- Default: return JSON
- If `?redirect=1` is provided: redirect user agent to `AUTH_POST_LOGIN_REDIRECT_URL`
  with query params: `access_token`, `refresh_token`, `expires_in`

Response 200 (JSON default):
```
{
  "access_token": "jwt",
  "refresh_token": "opaque",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.org",
    "full_name": "Optional Name",
    "plan": "FREE"
  }
}
```

Errors:
- 400 OAUTH_STATE_INVALID
- 400 OAUTH_CODE_MISSING
- 401 OAUTH_EXCHANGE_FAILED
- 500 OAUTH_INTERNAL_ERROR

### 3) POST /api/auth/magic-link/request
Request:
```
{ "email": "user@example.org" }
```

Response 200:
```
{ "status": "sent" }
```

Errors:
- 422 VALIDATION_ERROR
- 429 RATE_LIMITED
- 500 EMAIL_PROVIDER_ERROR

### 4) POST /api/auth/magic-link/consume
Request:
```
{ "token": "opaque_token_from_email" }
```

Response 200 (same as OAuth callback JSON response)

Errors:
- 400 MAGIC_TOKEN_INVALID
- 400 MAGIC_TOKEN_EXPIRED
- 409 MAGIC_TOKEN_ALREADY_USED
- 429 RATE_LIMITED

### 5) POST /api/auth/refresh
Request:
```
{ "refresh_token": "opaque" }
```

Response 200:
```
{
  "access_token": "jwt",
  "refresh_token": "new_opaque",
  "token_type": "Bearer",
  "expires_in": 900
}
```

Errors:
- 401 REFRESH_TOKEN_INVALID
- 401 REFRESH_TOKEN_EXPIRED
- 401 REFRESH_TOKEN_REVOKED
- 429 RATE_LIMITED

### 6) POST /api/auth/logout
Request:
```
{ "refresh_token": "opaque" }
```

Response 200:
```
{ "status": "logged_out" }
```

Errors:
- 401 REFRESH_TOKEN_INVALID