# API_CONTRACT.md

## Standards

- RESTful endpoints
- JSON only
- Proposal export: DOCX only (PDF not supported)

## Standard Error Model (All Endpoints)

HTTP status codes: 400/401/403/404/409/422/429/500

Error JSON:
{
"error_code": "string",
"message": "string",
"details": {},
"request_id": "string"
}

Notes:
- `details` is optional
- `request_id` is optional if available

## Auth Endpoints (Locked)

### 1) GET /api/auth/google/start
Purpose: returns authorization_url; frontend navigates

Response 200:
{
"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth
?...",
"state": "opaque_state_string"
}

Errors:
- 500 OAUTH_CONFIG_ERROR

### 2) GET /api/auth/google/callback
Purpose: completes OAuth, issues tokens

Behavior:
- Always redirect user agent to `AUTH_POST_LOGIN_REDIRECT_URL`
  with query params: `code` (short-lived one-time exchange code)
- Callback NEVER returns tokens or JSON payloads

Errors:
- 400 OAUTH_STATE_INVALID
- 400 OAUTH_CODE_MISSING
- 401 OAUTH_EXCHANGE_FAILED
- 500 OAUTH_INTERNAL_ERROR

### 3) POST /api/auth/exchange
Purpose: exchange short-lived OAuth redirect code for tokens

Code semantics:
- One-time OAuth exchange codes are stored server-side in a DB-backed store
- Codes are single-use and short-lived (60 seconds)

Request:
{ "code": "opaque_one_time_code" }

Response 200 (same as OAuth callback JSON response):
{
"access_token": "jwt",
"refresh_token": "opaque",
"token_type": "Bearer",
"expires_in": 900,
"user": {
"id": "uuid",
"email": "user@example.org
",
"full_name": "Optional Name",
"plan": "FREE | GROWTH | IMPACT"
}
}


Errors:
- 400 OAUTH_CODE_MISSING
- 401 OAUTH_EXCHANGE_FAILED
- 500 OAUTH_INTERNAL_ERROR

### 4) POST /api/auth/magic-link/request
Request:

{ "email": "user@example.org
" }


Response 200:

{ "status": "sent" }


Errors:
- 422 VALIDATION_ERROR
- 429 RATE_LIMITED
- 500 EMAIL_PROVIDER_ERROR

### 5) POST /api/auth/magic-link/consume
Request:

{ "token": "opaque_token_from_email" }


Response 200 (same as OAuth callback JSON response)

Errors:
- 400 MAGIC_TOKEN_INVALID
- 400 MAGIC_TOKEN_EXPIRED
- 409 MAGIC_TOKEN_ALREADY_USED
- 429 RATE_LIMITED

### 6) POST /api/auth/refresh
Request:

{ "refresh_token": "opaque" }


Response 200:

{
"access_token": "jwt",
"refresh_token": "new_opaque",
"token_type": "Bearer",
"expires_in": 900
}


Errors:
- 401 REFRESH_TOKEN_INVALID
- 401 REFRESH_TOKEN_EXPIRED
- 401 REFRESH_TOKEN_REVOKED
- 429 RATE_LIMITED

### 7) POST /api/auth/logout
Request:

{ "refresh_token": "opaque" }


Response 200:

{ "status": "logged_out" }


Errors:
- 401 REFRESH_TOKEN_INVALID

## Billing API (Stripe)

### A) POST /api/billing/checkout
Purpose: create a Stripe Checkout session for subscription.

Auth: REQUIRED (Bearer JWT)

Request:

{ "plan": "GROWTH" | "IMPACT" }


Response 200:

{ "checkout_url": "<string>" }


Errors:
- 400 BAD_REQUEST (invalid or missing plan)
- 401 UNAUTHORIZED
- 409 CONFLICT (already has an active paid subscription or checkout not allowed)
- 500 INTERNAL_SERVER_ERROR

### B) GET /api/billing/portal
Purpose: create a Stripe Customer Portal session for self-service billing.

Auth: REQUIRED (Bearer JWT)

Request: none

Response 200:

{ "portal_url": "<string>" }


Errors:
- 400 BAD_REQUEST (no Stripe customer / no billing account)
- 401 UNAUTHORIZED
- 500 INTERNAL_SERVER_ERROR

### C) POST /api/billing/webhook
Purpose: receive Stripe webhook events.

Auth: NONE (Stripe-signed request)

Request: raw Stripe webhook payload

Response 200: acknowledged (processed or duplicate)

Errors:
- 400 BAD_REQUEST (signature verification failed / invalid payload)
- 500 INTERNAL_SERVER_ERROR (persistence failure or transient processing error)

Note: Stripe is the billing source of truth; subscription state is synchronized via webhooks; DB stores a cache/projection for entitlements.

## Me / Entitlements (MVP — Locked)

### 1) GET /api/me/entitlements
Purpose: return current plan + quota counters for gating CTAs (QuotaGate) and /start preflight.

Auth: REQUIRED (Bearer access token)

Response 200:

{
"plan": "FREE" | "GROWTH" | "IMPACT",
"entitlements": {
"fit_scans": {
"limit": 0,
"used": 0,
"remaining": 0,
"period": "LIFETIME" | "BILLING_CYCLE",
"reset_at": "ISO-8601 timestamp or null"
},
"proposals": {
"limit": 0,
"used": 0,
"remaining": 0,
"period": "LIFETIME" | "BILLING_CYCLE",
"reset_at": "ISO-8601 timestamp or null"
},
"proposal_regenerations": {
"limit_per_proposal": 0
}
}
}


Errors:
- 401 UNAUTHORIZED
- 500 INTERNAL_SERVER_ERROR

## NGO Profile Endpoints (MVP — Locked)

### 1) GET /api/ngo-profile
Purpose: return the authenticated user’s NGO profile.

Auth: REQUIRED (Bearer access token)

Response 200:

{
"ngo_profile": {
"id": "uuid",

"organization_name": "string",
"country_of_registration": "string",
"year_of_establishment": 0,

"website": "string or null",
"contact_person_name": "string or null",
"contact_email": "string or null",

"mission_statement": "string",

"focus_sectors": [
  "EDUCATION | HEALTH | AGRICULTURE | WASH | GOVERNANCE | CLIMATE | GENDER | LIVELIHOODS | PROTECTION | OTHER"
],
"geographic_areas_of_work": ["string"],
"target_groups": ["string"],

"past_projects": [
  {
    "id": "uuid",
    "project_title": "string",
    "donor_funder": "string or null",
    "duration": "string or null",
    "location": "string or null",
    "summary": "string or null"
  }
],

"full_time_staff": 0,
"annual_budget_amount": 0,
"annual_budget_currency": "USD | GBP | EUR | INR | KES | string or null",
"me_practices": "string or null",
"previous_funders": ["string"],

"created_at": "ISO-8601 timestamp",
"updated_at": "ISO-8601 timestamp"

}
}


Notes:
- All fields are persisted; frontend may save partial profiles (DRAFT) via POST/PUT.
- `focus_sectors`, `geographic_areas_of_work`, `target_groups`, `previous_funders` may be empty arrays.
- `past_projects` may be an empty array; completeness requires at least 1 item with a non-empty `project_title`.

Errors:
- 401 UNAUTHORIZED
- 404 PROFILE_NOT_FOUND
- 500 INTERNAL_SERVER_ERROR

### 2) POST /api/ngo-profile
Purpose: create the authenticated user’s NGO profile.

Auth: REQUIRED (Bearer access token)

Request:

{
"organization_name": "string",
"country_of_registration": "string",
"year_of_establishment": 0,

"website": "string or null",
"contact_person_name": "string or null",
"contact_email": "string or null",

"mission_statement": "string",

"focus_sectors": ["EDUCATION | HEALTH | AGRICULTURE | WASH | GOVERNANCE | CLIMATE | GENDER | LIVELIHOODS | PROTECTION | OTHER"],
"geographic_areas_of_work": ["string"],
"target_groups": ["string"],

"past_projects": [
{
"project_title": "string",
"donor_funder": "string or null",
"duration": "string or null",
"location": "string or null",
"summary": "string or null"
}
],

"full_time_staff": 0,
"annual_budget_amount": 0,
"annual_budget_currency": "USD | GBP | EUR | INR | KES | string or null",
"me_practices": "string or null",
"previous_funders": ["string"]
}


Response 200:
- Same as `GET /api/ngo-profile`

Errors:
- 401 UNAUTHORIZED
- 409 PROFILE_ALREADY_EXISTS
- 422 VALIDATION_ERROR
- 500 INTERNAL_SERVER_ERROR

### 3) PUT /api/ngo-profile
Purpose: update the authenticated user’s NGO profile.

Auth: REQUIRED (Bearer access token)

Request:
- Same shape as POST

Response 200:
- Same as `GET /api/ngo-profile`

Errors:
- 401 UNAUTHORIZED
- 404 PROFILE_NOT_FOUND
- 422 VALIDATION_ERROR
- 500 INTERNAL_SERVER_ERROR

### 4) GET /api/ngo-profile/completeness
Purpose: provide completeness status and missing required fields for gating Fit Scans and showing the completeness bar.

Auth: REQUIRED (Bearer access token)

Response 200:

{
"status": "MISSING | DRAFT | COMPLETE",
"percent_complete": 0,
"required_fields": [
"organization_name",
"country_of_registration",
"mission_statement",
"focus_sectors",
"geographic_areas_of_work",
"target_groups",
"past_projects"
],
"missing_fields": ["string"],
"updated_at": "ISO-8601 timestamp or null"
}


Rules:
- If no profile exists: `status="MISSING"`, `percent_complete=0`, `missing_fields` MUST include all `required_fields`.
- If profile exists but required fields missing: `status="DRAFT"`, `missing_fields` contains the remaining required keys.
- If complete: `status="COMPLETE"`, `missing_fields=[]`, `percent_complete=100`.
- `past_projects` is considered missing if array is empty OR no item has a non-empty `project_title`.

Errors:
- 401 UNAUTHORIZED
- 500 INTERNAL_SERVER_ERROR

Fit Scan Endpoints (MVP — Locked)
7) POST /api/fit-scans

Purpose
Run a Fit Scan for a given funding opportunity using the authenticated user’s NGO profile.
This endpoint enforces plan quotas and persists the Fit Scan result.

Authentication
Required (Bearer access token).

Request

{
  "funding_opportunity_id": "uuid"
}


Response 200

{
  "fit_scan": {
    "id": "uuid",
    "funding_opportunity_id": "uuid",
    "overall_recommendation": "RECOMMENDED | APPLY_WITH_CAVEATS | NOT_RECOMMENDED",
    "model_rating": "STRONG | MODERATE | WEAK",
    "subscores": {
      "eligibility": 0,
      "alignment": 0,
      "readiness": 0
    },
    "primary_rationale": "string",
    "risk_flags": [
      {
        "risk_type": "string",
        "severity": "LOW | MEDIUM | HIGH",
        "description": "string"
      }
    ],
    "created_at": "ISO-8601 timestamp"
  }
}


Errors

401 UNAUTHORIZED

403 FORBIDDEN

404 OPPORTUNITY_NOT_FOUND

409 PROFILE_INCOMPLETE

details.missing_fields[] MUST be provided (keys align with /api/ngo-profile/completeness missing_fields)

429 QUOTA_EXCEEDED

500 FIT_SCAN_FAILED

8) GET /api/fit-scans/{id}

Purpose
Retrieve a previously generated Fit Scan. Results are read-only.

Authentication
Required.

Response 200
Same payload as POST /api/fit-scans.

Errors

401 UNAUTHORIZED

403 FORBIDDEN (attempt to access another user’s Fit Scan)

404 FIT_SCAN_NOT_FOUND

Notes

Fit Scan quota MUST be checked before execution.

Quota MUST be decremented only after successful persistence.

Failed, degraded, or invalid AI responses MUST NOT consume quota.

Model-level ratings are mapped to product recommendations as defined in FIT_SCAN_CRITERIA_MATRIX.md.

### 7) Proposal Endpoints section
POST /api/proposals (create)
GET /api/proposals/{id} (retrieve)
POST /api/proposals/{id}/regenerate (regenerate)
POST /api/proposals/{id}/export (DOCX export)

`POST /api/proposals` Response 200:
{
  "id": "uuid",
  "funding_opportunity_id": "uuid",
  "status": "string",
  "created_at": "ISO-8601 timestamp",
  "generation_summary": "object or null"
}

Notes:
- `id` is top-level and is the canonical proposal id for redirect to `/proposal/{id}`.
- Opportunity title is not currently returned by proposal or fit-scan endpoints. Frontend may optionally display `opportunity_title` from query params when provided, otherwise use a fallback label plus opportunity id context.

`POST /api/proposals` degraded behavior:
- If `requirements_json` is missing/invalid, return a degraded proposal payload (not 422)
- Degraded payload must use safe placeholders only (no hallucinated requirements)
- Sections that cannot be generated must be marked `MANUAL_REQUIRED` (or equivalent)
- Degraded/failed responses MUST NOT consume quota

`GET /api/proposals/{id}`:
- Returns persisted proposal content (including per-section statuses)

### 8) Document Export
  
  **POST /api/proposals/{id}/export**
  Request:
  { "format": "DOCX" }

  Quota semantics:
  - First export of a proposal version consumes proposal quota
  - Re-download of same proposal version does not re-consume quota (idempotent by `user_id + proposal_id + version`)
  
  Response 200:
  - Returns DOCX file as a binary stream.
  - `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `Content-Disposition: attachment; filename="proposal-{id}.docx"`
  
  Errors:
  - 404 PROPOSAL_NOT_FOUND
  - 403 FORBIDDEN
  - 422 UNSUPPORTED_FORMAT (if format != "DOCX")
