# API_CONTRACT.md (Canonical — Single Source of Truth)

**Status:** Canonical — LOCKED FOR BUILD
**Last updated:** 2026-04-01
**Scope:** GrantPilot API contract for backend + frontend integration

This file supersedes any duplicate copies. If multiple copies exist in different repos, they MUST be kept identical to this canonical version. Cursor MUST use this file as the authoritative source for all API call shapes, error codes, and response contracts. If any other document conflicts with this file, this file wins.

---

## 0) Standards

**Base path:** all API routes are under `/api/*` (except `/health`).

- RESTful endpoints.
- JSON for all endpoints except proposal export, which returns DOCX binary.
- All timestamps: ISO-8601 (UTC), e.g. `"2026-02-23T12:34:56Z"`.
- Auth for protected endpoints: `Authorization: Bearer <access_token>`.
- Content-Type for JSON requests: `Content-Type: application/json`.
- MVP list endpoints support `limit` only — no offset/cursor pagination.

---

## 1) Standard Error Model (All Endpoints)

HTTP status codes used: 400 / 401 / 403 / 404 / 409 / 422 / 429 / 500

Error JSON:

```json
{
  "error_code": "string",
  "message": "string",
  "details": {},
  "request_id": "string"
}
```

**Rules:**

- `details` is optional unless explicitly required by an endpoint (e.g., `PROFILE_INCOMPLETE`).
- `request_id` is optional if available.
- 429 is used for either rate limiting (`error_code=RATE_LIMITED`) or quota (`error_code=QUOTA_EXCEEDED`).
- For proposal export, all non-200 responses MUST be JSON using this error model.
- All protected endpoints MUST return this envelope for 401/403/404/429/500 — **not** FastAPI's default `HTTPValidationError`. The only acceptable use of 422 `HTTPValidationError` is for request body validation failures, and even then the response SHOULD use this envelope where possible.

---

## 2) Health

### GET /health

Purpose: deployment liveness.

Auth: NONE

Response 200:

```json
{ "status": "ok" }
```

Errors: 500 `INTERNAL_SERVER_ERROR`

---

## 3) Auth Endpoints (Locked)

### 3.1 GET /api/auth/google/start

Purpose: returns Google authorization URL; frontend navigates.

Auth: NONE

Response 200:

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "opaque_state_string"
}
```

Errors: 500 `OAUTH_CONFIG_ERROR`

---

### 3.2 GET /api/auth/google/callback

Purpose: completes OAuth, issues one-time exchange code, redirects user agent.

Auth: NONE

**Behavior:**

- ALWAYS redirect user agent (HTTP 302) to `AUTH_POST_LOGIN_REDIRECT_URL`.
- Redirect query params: `code` (short-lived one-time exchange code), `state` (optional, as provided).
- Callback NEVER returns tokens or JSON payloads.

**OpenAPI note:** This endpoint MUST be represented as a 302 redirect with `Location` header — NOT as a JSON 200.

Errors (as redirect with `?error=...` OR handled internally; API must log safely):

- 400 `OAUTH_STATE_INVALID`
- 400 `OAUTH_CODE_MISSING`
- 401 `OAUTH_EXCHANGE_FAILED`
- 500 `OAUTH_INTERNAL_ERROR`

---

### 3.3 POST /api/auth/exchange

Purpose: exchange short-lived OAuth redirect code for tokens.

Auth: NONE

Code semantics: DB-backed store, single-use, short-lived (60 seconds).

Request:

```json
{ "code": "opaque_one_time_code" }
```

Response 200 (TokenResponse):

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "email": "user@example.org",
    "full_name": "Optional Name",
    "plan": "FREE | GROWTH | IMPACT"
  }
}
```

**Note:** `plan` MUST reflect the user's actual current plan (not hardcoded to `FREE`).

Errors:

- 400 `OAUTH_CODE_MISSING`
- 401 `OAUTH_EXCHANGE_FAILED` (expired / already used / not found — all code-related failures use this single error code)
- 429 `RATE_LIMITED`
- 500 `OAUTH_INTERNAL_ERROR`

---

### 3.4 POST /api/auth/magic-link/request

Purpose: send magic link email.

Auth: NONE

Request:

```json
{ "email": "user@example.org" }
```

Response 200:

```json
{ "status": "sent" }
```

Errors:

- 422 `VALIDATION_ERROR`
- 429 `RATE_LIMITED`
- 500 `EMAIL_PROVIDER_ERROR`

---

### 3.5 POST /api/auth/magic-link/consume

Purpose: consume magic link token, issue tokens.

Auth: NONE

Request:

```json
{ "token": "opaque_token_from_email" }
```

Response 200: same as `/api/auth/exchange` Response 200 (TokenResponse).

Errors:

- 400 `MAGIC_TOKEN_INVALID`
- 400 `MAGIC_TOKEN_EXPIRED`
- 409 `MAGIC_TOKEN_ALREADY_USED`
- 429 `RATE_LIMITED`
- 500 `AUTH_INTERNAL_ERROR`

---

### 3.6 POST /api/auth/refresh

Purpose: rotate refresh token, issue new access token.

Auth: NONE

Request:

```json
{ "refresh_token": "opaque" }
```

Response 200:

```json
{
  "access_token": "jwt",
  "refresh_token": "new_opaque",
  "token_type": "Bearer",
  "expires_in": 900
}
```

Errors:

- 401 `REFRESH_TOKEN_INVALID`
- 401 `REFRESH_TOKEN_EXPIRED`
- 401 `REFRESH_TOKEN_REVOKED`
- 429 `RATE_LIMITED`
- 500 `AUTH_INTERNAL_ERROR`

---

### 3.7 POST /api/auth/logout

Purpose: revoke refresh token.

Auth: NONE

Request:

```json
{ "refresh_token": "opaque" }
```

Response 200:

```json
{ "status": "logged_out" }
```

Errors:

- 401 `REFRESH_TOKEN_INVALID`
- 500 `AUTH_INTERNAL_ERROR`

---

### 3.8 POST /api/auth/test-mode/mint (Pre-launch only)

Purpose: test-only token minting for smoke tests. Must be disabled/removed pre-launch.

Auth: NONE (gated by `TEST_MODE=true` AND correct `TEST_MODE_SECRET`)

Request:

```json
{
  "secret": "TEST_MODE_SECRET",
  "email": "test@example.org",
  "full_name": "Optional Name",
  "plan": "FREE | GROWTH | IMPACT"
}
```

Response 200: same as `/api/auth/exchange` Response 200 (TokenResponse).

Errors:

- 403 `TEST_MODE_DISABLED`
- 401 `TEST_MODE_UNAUTHORIZED`
- 422 `VALIDATION_ERROR`
- 500 `AUTH_INTERNAL_ERROR`

---

## 4) Me / Entitlements (MVP — Locked)

### GET /api/me/entitlements

Purpose: current plan + quota counters for gating CTAs and `/start` preflight.

Auth: REQUIRED (Bearer access token)

Response 200:

```json
{
  "plan": "FREE | GROWTH | IMPACT",
  "entitlements": {
    "fit_scans": {
      "limit": 0,
      "used": 0,
      "remaining": 0,
      "period": "LIFETIME | BILLING_CYCLE",
      "reset_at": "ISO-8601 timestamp or null"
    },
    "proposals": {
      "limit": 0,
      "used": 0,
      "remaining": 0,
      "period": "LIFETIME | BILLING_CYCLE",
      "reset_at": "ISO-8601 timestamp or null"
    },
    "proposal_regenerations": {
      "limit_per_proposal": 0
    },
    "reports": {
      "limit": 0,
      "used": 0,
      "remaining": 0,
      "period": "BILLING_CYCLE",
      "reset_at": "ISO-8601 timestamp or null"
    },
    "report_exports": {
      "limit": 0,
      "used": 0,
      "remaining": 0,
      "period": "BILLING_CYCLE",
      "reset_at": "ISO-8601 timestamp or null"
    }
  }
}
```

**M&E entitlement limits (Stage J):**
- **FREE / GROWTH:** `reports.limit` = 0 (M&E not available; entry points return `403 UPGRADE_REQUIRED`).
- **IMPACT:** `reports.limit` = 2 per billing cycle; `report_exports` idempotent per report version (mirrors proposal `DOCX_EXPORT` pattern).

Errors:

- 401 `UNAUTHORIZED`
- 500 `INTERNAL_SERVER_ERROR`

---

## 5) Billing API (Stripe)

### 5.1 POST /api/billing/checkout

Purpose: create Stripe Checkout session.

Auth: REQUIRED (Bearer access token)

Request:

```json
{ "plan": "GROWTH" | "IMPACT" }
```

Response 200:

```json
{ "checkout_url": "https://checkout.stripe.com/..." }
```

Errors:

- 400 `BAD_REQUEST` (invalid or missing plan)
- 401 `UNAUTHORIZED`
- 409 `CONFLICT` (already has active paid subscription)
- 500 `INTERNAL_SERVER_ERROR`

---

### 5.2 GET /api/billing/portal

Purpose: create Stripe Customer Portal session.

Auth: REQUIRED (Bearer access token)

Response 200:

```json
{ "portal_url": "https://billing.stripe.com/..." }
```

Errors:

- 400 `BAD_REQUEST` (no Stripe customer / no billing account)
- 401 `UNAUTHORIZED`
- 500 `INTERNAL_SERVER_ERROR`

---

### 5.3 POST /api/billing/webhook

Purpose: receive Stripe webhook events.

Auth: NONE (Stripe-signed request)

Request: raw Stripe payload

Response 200: acknowledged

Errors:

- 400 `BAD_REQUEST` (signature verification failed / invalid payload)
- 500 `INTERNAL_SERVER_ERROR`

**Note:** Stripe is the billing source of truth; subscription state is synchronized via webhooks; DB stores a cache/projection for entitlements.

---

## 6) NGO Profile Endpoints (MVP — Locked, Contract Aligned 2026-03-09)

### 6.1 GET /api/ngo-profile

Purpose: return authenticated user's NGO profile.

Auth: REQUIRED

Response 200:

json
{
  "id": "uuid",
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
      "id": "uuid",
      "title": "string",
      "donor": "string or null",
      "duration": "string or null",
      "location": "string or null",
      "summary": "string or null"
    }
  ],
  "full_time_staff": 0,
  "annual_budget_amount": 0,
  "annual_budget_currency": "USD | GBP | EUR | INR | KES | string or null",
  "monitoring_and_evaluation_practices": "string or null",
  "funders_worked_with_before": ["string"],
  "knowledge_bank": {},
  "profile_status": "DRAFT | COMPLETE",
  "completeness_score": 0,
  "missing_fields": ["string"],
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}


**Response shape:** Top-level profile object. No envelope wrapper.

**Notes:**
- Arrays may be empty. `past_projects` may be empty; completeness rules define when it counts as "missing".
- `profile_status`, `completeness_score`, and `missing_fields` are computed server-side on every create/update and returned with the profile for convenience.

**Field name mapping (canonical):**
| Field | Notes |
|-------|-------|
| `past_projects[].title` | NOT `project_title` |
| `past_projects[].donor` | NOT `donor_funder` |
| `monitoring_and_evaluation_practices` | NOT `me_practices` |
| `funders_worked_with_before` | NOT `previous_funders` |

Backend enforces `extra="forbid"` on Pydantic schemas. Sending legacy field names (`project_title`, `donor_funder`, `me_practices`, `previous_funders`) will return 422 `VALIDATION_ERROR`.

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND`
- 500 `INTERNAL_SERVER_ERROR`

---

### 6.2 POST /api/ngo-profile

### 6.2 POST /api/ngo-profile

Purpose: create authenticated user's NGO profile.

Auth: REQUIRED

Request: same field names as GET response above, excluding read-only fields (`id`, `profile_status`, `completeness_score`, `missing_fields`, `created_at`, `updated_at`) and excluding `past_projects[].id`.

Response 200: same shape as `GET /api/ngo-profile` (top-level profile object, no envelope).

Errors:

- 401 `UNAUTHORIZED`
- 409 `PROFILE_ALREADY_EXISTS`
- 422 `VALIDATION_ERROR`
- 500 `INTERNAL_SERVER_ERROR`

---

### 6.3 PUT /api/ngo-profile

Purpose: update authenticated user's NGO profile.

Auth: REQUIRED

Request: same as POST.

Response 200: same shape as `GET /api/ngo-profile` (top-level profile object, no envelope).

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND`
- 422 `VALIDATION_ERROR`
- 500 `INTERNAL_SERVER_ERROR`

---

### 6.4 GET /api/ngo-profile/completeness

Purpose: completeness status + missing required fields (gating fit scan and proposal creation).

Auth: REQUIRED

Response 200:

\`\`\`json
{
  "profile_status": "DRAFT | COMPLETE",
  "completeness_score": 0,
  "missing_fields": ["string"]
}
\`\`\`

**Rules:**

- If no profile exists: endpoint returns `404 PROFILE_NOT_FOUND` (not a JSON body with status "MISSING").
- If profile exists but required fields missing: `profile_status="DRAFT"`, `missing_fields` contains remaining required keys.
- If complete: `profile_status="COMPLETE"`, `missing_fields=[]`, `completeness_score=100`.
- `past_projects` is considered missing if array is empty OR no item has non-empty `title`.

**Completeness scoring (informational, 0–100):**
- Organization name + country: 20
- Mission statement: 15
- Focus sectors (≥1): 15
- Geographic areas (≥1): 15
- Target groups (≥1): 15
- At least 1 past project with non-empty `title`: 20

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND` (no profile exists for this user)
- 500 `INTERNAL_SERVER_ERROR`

---

### 6.5 PUT /api/ngo-profile/knowledge-bank

Purpose: save user-provided data to NGO profile knowledge bank for reuse across proposals.

Auth: REQUIRED

Request:

```json
{
  "entries": [
    {
      "key": "string",
      "text": "string",
      "opportunity_id": "string or null"
    }
  ]
}
```

Response 200:

```json
{
  "knowledge_bank": {
    "key_name": {
      "text": "string",
      "source": "user_input",
      "opportunity_id": "string or null",
      "updated_at": "ISO-8601"
    }
  }
}
```

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND`
- 422 `VALIDATION_ERROR` (empty `key` or `text`)
- 500 `INTERNAL_SERVER_ERROR`

---

## 7) Funding Opportunities (Read-only for MVP)

### 7.1 GET /api/funding-opportunities/{id}

Purpose: fetch opportunity summary for `/start`, `/fit-scan/*`, and `/proposal/*` headers.

Auth: REQUIRED (MVP), unless explicitly opened later.

Response 200:

```json
{
  "funding_opportunity": {
    "id": "uuid",
    "title": "string",
    "donor_organization": "string",
    "funding_type": "string",
    "applicant_type": "string",
    "location_text": "string",
    "focus_areas": ["string"],
    "deadline_type": "FIXED | ROLLING | VARIES",
    "application_deadline": "YYYY-MM-DD or null",
    "short_summary": "string",
    "source_url": "string",
    "application_url": "string",
    "status": "string",
    "is_active": true,
    "last_verified": "YYYY-MM-DD or null"
  }
}
```

**Notes:**

- DB stores `focus_areas` as CSV; API returns an array of strings.
- Fields intentionally excluded from MVP response: `amount_min`, `amount_max`, `total_funding_available`, `currency`, `requirements_json`, `overview_text`, `eligibility_criteria`, `application_process`, and all operational/internal fields. These are backend-only or post-MVP.

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `OPPORTUNITY_NOT_FOUND`
- 500 `INTERNAL_SERVER_ERROR`

---

## 8) Fit Scan Endpoints (MVP — Locked)

### 8.1 POST /api/fit-scans

Purpose: run Fit Scan for a funding opportunity using the authenticated user's NGO profile; enforces quota and persists.

Auth: REQUIRED

Request:

```json
{ "funding_opportunity_id": "uuid" }
```

Response 200:

```json
{
  "fit_scan": {
    "id": "uuid",
    "funding_opportunity_id": "uuid",
    "opportunity_title": "string or null",
    "overall_recommendation": "RECOMMENDED | APPLY_WITH_CAVEATS | NOT_RECOMMENDED",
    "model_rating": "STRONG | MODERATE | WEAK",
    "subscores": { "eligibility": 0, "alignment": 0, "readiness": 0 },
    "primary_rationale": "string",
    "risk_flags": [
      { "risk_type": "string", "severity": "LOW | MEDIUM | HIGH", "description": "string" }
    ],
    "created_at": "ISO-8601 timestamp"
  }
}
```

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `OPPORTUNITY_NOT_FOUND`
- 409 `PROFILE_INCOMPLETE` (`details.missing_fields[]` REQUIRED; keys align with `/api/ngo-profile/completeness.missing_fields`)
- 429 `QUOTA_EXCEEDED`
- 500 `FIT_SCAN_FAILED`

**Rules:**

- Quota MUST be decremented only after successful persistence.
- Failed/degraded/invalid AI output MUST NOT consume quota.
- Rating mapping governed by `FIT_SCAN_CRITERIA_MATRIX.md`.

---

### 8.2 GET /api/fit-scans/{id}

Purpose: retrieve a previously generated Fit Scan (read-only).

Auth: REQUIRED

Response 200: same payload as `POST /api/fit-scans`.

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN` (attempt to access another user's Fit Scan)
- 404 `FIT_SCAN_NOT_FOUND`
- 500 `INTERNAL_SERVER_ERROR`

---

### 8.3 GET /api/fit-scans

Purpose: list user's Fit Scans (newest first). Used by Dashboard.

Auth: REQUIRED

Query params: `limit` (optional, default 5, max 50)

**MVP note:** No offset or cursor pagination. Returns most recent `limit` items only. Pagination is post-MVP.

Response 200:

```json
{
  "fit_scans": [
    {
      "id": "uuid",
      "funding_opportunity_id": "uuid",
      "opportunity_title": "string or null",
      "overall_recommendation": "RECOMMENDED | APPLY_WITH_CAVEATS | NOT_RECOMMENDED",
      "model_rating": "STRONG | MODERATE | WEAK",
      "subscores": { "eligibility": 0, "alignment": 0, "readiness": 0 },
      "created_at": "ISO-8601 timestamp"
    }
  ]
}
```

**Note:** This is a summary view. `primary_rationale` and `risk_flags` are omitted from list items — they are only returned by the detail endpoint (`GET /api/fit-scans/{id}`).

Errors:

- 401 `UNAUTHORIZED`
- 500 `INTERNAL_SERVER_ERROR`

---

## 9) Proposal Endpoints (MVP — Locked)

### Proposal status values (enum-like text field)

Valid values for the `status` field on all proposal responses:

| Status | Meaning |
|--------|---------|
| `DRAFT` | Proposal persisted and usable; includes fully generated proposals and proposals with `NEEDS_USER_INPUT` sections (as long as there are no `FAILED` sections) |
| `DEGRADED` | Generated with degraded inputs (e.g., missing `requirements_json`); safe placeholders used |
| `FAILED` | All sections failed to generate; proposal was NOT persisted (only visible in error responses, never in GET) |

**Note:** `GENERATING` is NOT a persisted status. Generation is synchronous from the frontend's perspective — the POST call blocks until complete or failed. The frontend shows a loading screen during this time.

---

### 9.1 POST /api/proposals

Purpose: create proposal draft from opportunity + profile; enforces quota; persists if ≥1 section generated.

Auth: REQUIRED

Request (ProposalCreateRequest):

```json
{
  "funding_opportunity_id": "uuid",
  "fit_scan_id": "uuid or null",
  "selected_variant_id": "string or null",
  "user_overrides": "object or null"
}
```

**Note:** `selected_variant_id` and `user_overrides` are accepted but optional for MVP. If `selected_variant_id` is null and the opportunity has multiple variants, the backend selects the first variant. `user_overrides` is reserved for future use and ignored in MVP.

Response 200 (ProposalResponse):

```json
{
  "id": "uuid",
  "funding_opportunity_id": "uuid",
  "fit_scan_id": "uuid or null",
  "opportunity_title": "string or null",
  "status": "DRAFT | DEGRADED",
  "version": 1,
  "created_at": "ISO-8601 timestamp",
  "generation_summary": {
    "total_items": 0,
    "generated": 0,
    "failed": 0,
    "manual_required": 0,
    "warnings": ["string"]
  }
}
```

**Degraded behavior:**

- If `requirements_json` is missing/invalid on the opportunity, return a degraded response payload (NOT 422) with `status: "DEGRADED"`, safe placeholders only, and NO quota consumption.

**Partial failure behavior:**

- If ≥1 section generated → persist + consume proposal quota.
- If ALL sections fail → do NOT persist, do NOT consume quota, return 500 with `error_code=PROPOSAL_GENERATION_FAILED`.

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `OPPORTUNITY_NOT_FOUND`
- 409 `PROFILE_INCOMPLETE` (`details.missing_fields[]` REQUIRED)
- 429 `QUOTA_EXCEEDED`
- 500 `PROPOSAL_GENERATION_FAILED` / `INTERNAL_SERVER_ERROR`

---

### 9.1A POST /api/proposals/pre-flight

Purpose: run pre-generation gap check against NGO profile for a specific funding opportunity. No OpenAI calls. No quota consumption.

Auth: REQUIRED

Request:

```json
{
  "funding_opportunity_id": "uuid",
  "selected_variant_id": "string or null"
}
```

Response 200:

```json
{
  "opportunity_title": "string",
  "variant_id": "string",
  "ready_to_generate": true,
  "readiness_percent": 67,
  "sections": [
    {
      "submission_item_id": "string",
      "label": "string",
      "status": "READY | NEEDS_INPUT | MANUAL_REQUIRED",
      "missing_fields": ["string"],
      "prompt_for_user": "string or null",
      "generation_allowed": true
    }
  ],
  "summary": {
    "total_sections": 6,
    "ready": 3,
    "needs_input": 2,
    "manual_required": 1
  }
}
```

Readiness calculation:
- `readiness_percent = (READY sections / generatable sections) * 100` (rounded to nearest integer)
- `MANUAL_REQUIRED` sections are excluded from the denominator
- `ready_to_generate = true` only when `readiness_percent == 100`

Errors:
- 401 `UNAUTHORIZED`
- 404 `OPPORTUNITY_NOT_FOUND`
- 409 `PROFILE_INCOMPLETE`
- 500 `INTERNAL_SERVER_ERROR`

---

### 9.2 GET /api/proposals/{id}

Purpose: retrieve proposal with full `content_json` including per-section statuses.

Auth: REQUIRED

Response 200 (ProposalDetailResponse):

```json
{
  "id": "uuid",
  "funding_opportunity_id": "uuid",
  "fit_scan_id": "uuid or null",
  "opportunity_title": "string or null",
  "status": "DRAFT | DEGRADED",
  "version": 1,
  "regeneration_count": 0,
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "content_json": {
    "sections": [
      {
        "submission_item_id": "string",
        "label": "string",
        "generation_status": "GENERATED | FAILED | MANUAL_REQUIRED | NEEDS_USER_INPUT",
        "missing_inputs": ["string"],
        "archetype": "string or null",
        "content": {
          "text": "string",
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
      "total_items": 0,
      "generated": 0,
      "failed": 0,
      "manual_required": 0,
      "needs_user_input": 0,
      "warnings": ["string"]
    }
  }
}
```

**Frontend rendering guidance for `content_json.sections[]`:**

| `generation_status` | UI treatment |
|---------------------|-------------|
| `GENERATED` | Show content normally with section heading |
| `FAILED` | Show "This section could not be generated." + retry option (regenerate) |
| `MANUAL_REQUIRED` | Show "This section requires manual input. AI generation is not available for this item." — no retry button |
| `NEEDS_USER_INPUT` | Show missing data prompts + input field + "Save & Regenerate" button |

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN` (attempt to access another user's proposal)
- 404 `PROPOSAL_NOT_FOUND`
- 500 `INTERNAL_SERVER_ERROR`

---

### 9.3 GET /api/proposals

Purpose: list user's proposals (newest first). Used by Dashboard.

Auth: REQUIRED

Query params: `limit` (optional, default 5, max 50)

**MVP note:** No offset or cursor pagination. Returns most recent `limit` items only. Pagination is post-MVP.

Response 200:

```json
{
  "proposals": [
    {
      "id": "uuid",
      "funding_opportunity_id": "uuid",
      "fit_scan_id": "uuid or null",
      "opportunity_title": "string or null",
      "status": "DRAFT | DEGRADED",
      "version": 1,
      "created_at": "ISO-8601 timestamp",
      "updated_at": "ISO-8601 timestamp",
      "generation_summary": {
        "total_items": 0,
        "generated": 0,
        "failed": 0,
        "manual_required": 0,
        "warnings": ["string"]
      }
    }
  ]
}
```

**Note:** This is a summary view. `content_json` is NOT included in list items — it is only returned by the detail endpoint (`GET /api/proposals/{id}`).

Errors:

- 401 `UNAUTHORIZED`
- 500 `INTERNAL_SERVER_ERROR`

---

### 9.4 POST /api/proposals/{id}/regenerate

Purpose: regenerate proposal sections in-place, incrementing proposal version; plan-gated.

Auth: REQUIRED

Request:

```json
{ "mode": "FULL" }
```

**MVP regeneration semantics:**

- `FULL` regeneration re-runs ALL previously `GENERATED` and `FAILED` sections.
- `MANUAL_REQUIRED` sections stay as-is.
- Per-section regeneration is NOT supported in MVP. The `{ "mode": "FULL" }` request body is the only valid payload. Do not send `{ "section": "..." }` — the backend will ignore it.
- Free plan: regeneration not allowed (403).

Response 200: same shape as `GET /api/proposals/{id}` (ProposalDetailResponse).

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN` (Free plan OR cross-user access)
- 404 `PROPOSAL_NOT_FOUND`
- 429 `QUOTA_EXCEEDED` (used as "regeneration limit reached" as well; `details` SHOULD explain)
- 500 `PROPOSAL_REGEN_FAILED` / `INTERNAL_SERVER_ERROR`

**Rules:**

- Growth/Impact: max 3 regenerations per proposal (tracked by `regeneration_count`).
- On successful regen: update `content_json`, increment `version` and `regeneration_count`.
- If a regen attempt results in ALL sections failing, it MUST NOT increment `regeneration_count`.

---

### 9.5 POST /api/proposals/{id}/export

Purpose: export proposal to DOCX (direct streaming). Only format supported: DOCX.

Auth: REQUIRED

Request:

```json
{ "format": "DOCX" }
```

Response 200:

- Binary stream.
- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment; filename="proposal-{id}.docx"`

**Quota semantics:**

- First export of a given proposal version consumes quota once (idempotent by `user_id + proposal_id + version`).
- Re-download of same version does NOT re-consume quota.

Errors (JSON error envelope):

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `PROPOSAL_NOT_FOUND`
- 422 `UNSUPPORTED_FORMAT` (if format != "DOCX")
- 429 `QUOTA_EXCEEDED`
- 500 `INTERNAL_SERVER_ERROR`

---

## 10) Cross-cutting Required Error Details

### 10.1 409 PROFILE_INCOMPLETE

When returned by any endpoint, `details.missing_fields[]` MUST be provided:

```json
{
  "error_code": "PROFILE_INCOMPLETE",
  "message": "NGO profile is incomplete.",
  "details": { "missing_fields": ["organization_name", "mission_statement"] }
}
```

### 10.2 429 QUOTA_EXCEEDED

`details` SHOULD include the entitlement snapshot:

```json
{
  "error_code": "QUOTA_EXCEEDED",
  "message": "Quota exceeded.",
  "details": {
    "entitlement": "fit_scans | proposals | proposal_regenerations | docx_exports | reports | report_exports",
    "limit": 0,
    "used": 0,
    "remaining": 0,
    "period": "LIFETIME | BILLING_CYCLE",
    "reset_at": "ISO-8601 timestamp or null"
  }
}
```

### 10.3 403 UPGRADE_REQUIRED (M&E — Free/Growth)

Returned when a Free or Growth user hits any M&E entry point or `/api/reports*` endpoint (Stage J).

```json
{
  "error_code": "UPGRADE_REQUIRED",
  "message": "M&E reporting is available on the Impact plan.",
  "details": {
    "required_plan": "IMPACT",
    "feature": "me_reports"
  }
}
```

**Distinct from** `429 QUOTA_EXCEEDED`, which Impact users receive when the bundled 2-reports/month quota is exhausted.

---

## 11) OpenAPI Conformance Requirements (for backend)

These requirements ensure OpenAPI spec stays in sync with this contract. They are instructions for backend implementation, NOT consumed by the frontend directly.

1. **Bearer auth declaration:** OpenAPI MUST declare `components.securitySchemes` with HTTP bearer scheme, and all protected endpoints MUST have `security` applied.
2. **Typed response models:** All endpoint response schemas MUST use explicit Pydantic models — no `{}` empty schemas in OpenAPI for any 200 response.
3. **Standard error envelope:** All 4xx/5xx responses MUST reference a `StandardErrorResponse` model matching Section 1 — not FastAPI's default `HTTPValidationError` (except 422 where it may coexist).
4. **Google callback semantics:** `/api/auth/google/callback` MUST be represented as 302 redirect in OpenAPI, not JSON 200.
5. **NGO profile path:** Backend routes MUST use `/api/ngo-profile*` (with `/api` prefix) — not bare `/ngo-profile*`.


## 12) M&E Module — Donor Report Writer (Stage B — Locked)

**Status:** Stage B structure lock · **Implementation:** Stage C onward  
**Scope:** All `/api/reports*` and `/api/report-templates*` endpoints  
**Entitlement:** `IMPACT` plan required for all endpoints in this section (Stage J enforcement). Free/Growth receive `403 UPGRADE_REQUIRED` (§10.3).  
**Feature flag:** Backend `ME_MODULE_ENABLED`; frontend `NEXT_PUBLIC_ME_MODULE_ENABLED` (separate repo)

**Canonical path prefix:** All M&E routes use `/api/reports/{id}/...` — no `donor-reports` path segment. (Code path alignment: A-03.)

### 12.0 M&E Response Envelope Conventions (LOCKED)

These rules apply **only** to §12 endpoints. Existing §1–§11 envelopes are unchanged.

| Pattern | Rule | Rationale |
|---------|------|-----------|
| Single-resource success | **Top-level object** — no `{ "report": {...} }` wrapper | Aligns with `GET /api/proposals/{id}` and post-audit NGO profile (§6.1) |
| List endpoints | Named array wrapper: `{ "reports": [...] }`, `{ "report_templates": [...] }` | Aligns with `GET /api/proposals` |
| Sub-resource reads | **Top-level object** with descriptive fields (`readiness_score`, `stage`, etc.) | Avoids `ngo_profile`-style wrapper drift noted in audit_1603 |
| Errors | Standard error model (§1) | Unchanged |
| Timestamps | ISO-8601 UTC | Unchanged |
| UUIDs | String | Unchanged |

**Explicit non-wrapper decision:** `GET /api/reports/{id}` returns the report fields at the top level — same pattern as `ProposalDetailResponse`.

**Independence:** M&E report creation does **not** require `funding_opportunity_id`. `linked_proposal_id` is optional only.

**Job model (canonical):** Pipeline execution uses `POST /api/reports/{id}/job` (enqueue) + `GET /api/reports/{id}/job` (poll). There is no synchronous `POST .../generate` endpoint.

---

### 12.1 GET /api/report-templates

Purpose: list active funder report templates for template picker.

Auth: REQUIRED · Entitlement: IMPACT (Stage J)

Query params: `region` (optional filter)

Response 200:

```json
{
  "report_templates": [
    {
      "id": "uuid",
      "funder_name": "string",
      "template_name": "string",
      "region": "string",
      "reporting_frequency": "end_of_grant | annual | quarterly | interim | final",
      "version": 1
    }
  ]
}
```

Errors: 401 `UNAUTHORIZED` · 403 `FORBIDDEN` · 500 `INTERNAL_SERVER_ERROR`

---

### 12.2 POST /api/reports

Purpose: create a donor report in `DRAFT` status.

Auth: REQUIRED · Entitlement: IMPACT + report quota (Stage J)

Request:

```json
{
  "funder_report_template_id": "uuid",
  "linked_proposal_id": "uuid or null",
  "reporting_period_start": "YYYY-MM-DD",
  "reporting_period_end": "YYYY-MM-DD"
}
```

Response 200 (top-level ReportSummaryResponse):

```json
{
  "id": "uuid",
  "funder_report_template_id": "uuid",
  "funder_name": "string",
  "template_name": "string",
  "linked_proposal_id": "uuid or null",
  "reporting_period_start": "YYYY-MM-DD",
  "reporting_period_end": "YYYY-MM-DD",
  "status": "DRAFT",
  "version": 1,
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `TEMPLATE_NOT_FOUND`
- 404 `PROPOSAL_NOT_FOUND` (when linked_proposal_id invalid)
- 409 `PROFILE_INCOMPLETE` (same semantics as proposals — NGO profile required)
- 429 `QUOTA_EXCEEDED` (`details.entitlement`: `reports`)
- 422 `VALIDATION_ERROR`
- 500 `INTERNAL_SERVER_ERROR`

---

### 12.3 POST /api/reports/{id}/documents

Purpose: upload one document; triggers classification + extraction job.

Auth: REQUIRED · Owner only

Content-Type: `multipart/form-data`

Form fields:

| Field | Type | Required |
|-------|------|----------|
| `file` | binary | YES |

Response 200 (top-level UploadedDocumentResponse):

```json
{
  "id": "uuid",
  "donor_report_id": "uuid",
  "original_filename": "string",
  "mime_type": "string",
  "size_bytes": 0,
  "classification": "proposal | grant_letter | mou | indicator_data | photo | deck | other | null",
  "extraction_status": "PENDING | PROCESSING | COMPLETE | FAILED",
  "created_at": "ISO-8601 timestamp",
  "job_id": "uuid"
}
```

**Notes:**
- `storage_ref` is NEVER returned to clients.
- `job_id` references `report_jobs` for watch-UI polling (§12.12).
- Multiple uploads = multiple POST calls (batch upload post-MVP).

Errors:

- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN`
- 404 `REPORT_NOT_FOUND`
- 413 `FILE_TOO_LARGE` (limit in ENV_VARS — Stage C)
- 415 `UNSUPPORTED_MEDIA_TYPE`
- 422 `VALIDATION_ERROR`
- 500 `INTERNAL_SERVER_ERROR`

---

### 12.4 GET /api/reports/{id}/knowledge-bank

Purpose: Gate 1 — reconciled picture + conflicts.

Auth: REQUIRED · Owner only

Response 200 (top-level — no wrapper):

```json
{
  "donor_report_id": "uuid",
  "facts": {},
  "conflicts": [],
  "gate1_confirmed_at": "ISO-8601 or null",
  "ready_for_gate1": true
}
```

Shape of `facts` / `conflicts`: `DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.6.

Errors: 401 · 403 · 404 `REPORT_NOT_FOUND` · 500

---

### 12.5 PATCH /api/reports/{id}/knowledge-bank

**PROVISIONAL — confirm against Plan 1 (Track B) gate UI design before building.**

Purpose: Gate 1 — human confirmations, conflict resolutions (alternate to POST §12.5a).

Auth: REQUIRED · Owner only

Request:

```json
{
  "facts": {
    "<fact_key>": {
      "value": "any",
      "confirmed": true
    }
  },
  "conflict_resolutions": [
    {
      "fact_key": "string",
      "resolved_value": "any"
    }
  ],
  "confirm_gate1": true
}
```

Response 200: same shape as GET §12.4.

**Rules:**
- When `confirm_gate1: true`, server sets `gate1_confirmed_at` and advances pipeline if valid.
- Pipeline MUST NOT advance without `confirm_gate1: true` recorded.
- 409 `GATE_NOT_SATISFIED` if unresolved conflicts remain.

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.5a POST /api/reports/{id}/knowledge-bank/gate1/confirm (canonical — implemented)

Purpose: Gate 1 — human confirmation of reconciled knowledge bank.

Auth: REQUIRED · Owner only

Request: knowledge bank payload with confirmed facts (shape per Gate 1 service contract).

Response 200: includes `gate1_confirmed_at` when confirmed.

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.6 GET /api/reports/{id}/gap-check

**PROVISIONAL — confirm against Plan 1 (Track B) gate UI design before building.**

Purpose: Gate 2 — readiness score + funder-aware missing items.

Auth: REQUIRED · Owner only

Response 200 (top-level):

```json
{
  "donor_report_id": "uuid",
  "readiness_score": 0,
  "ready_for_gate2": false,
  "missing_items": [
    {
      "item_key": "string",
      "label": "string",
      "prompt": "string",
      "severity": "required | recommended",
      "section_key": "string or null"
    }
  ],
  "gate2_confirmed_at": "ISO-8601 or null"
}
```

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` (Gate 1 not complete) · 500

---

### 12.7 PATCH /api/reports/{id}/gap-answers

**PROVISIONAL — confirm against Plan 1 (Track B) gate UI design before building.**

Purpose: Gate 2 — free-text answers for genuinely missing items (alternate to POST §12.7a).

Auth: REQUIRED · Owner only

Request:

```json
{
  "gap_answers": {
    "<item_key>": {
      "answer_text": "string"
    }
  },
  "confirm_gate2": true
}
```

Response 200: same shape as GET §12.6 (with updated `gate2_confirmed_at` when confirmed).

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.7a POST /api/reports/{id}/knowledge-bank/gate2/gap-responses (canonical — implemented)

Purpose: Gate 2 — submit gap answers (answer-or-skip); sets `gate2_confirmed_at` when complete.

Auth: REQUIRED · Owner only

Request: gap response payload per Gate 2 service contract.

Response 200: remaining gaps + `gate2_confirmed_at` when confirmed.

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.8 POST /api/reports/{id}/job

Purpose: enqueue async report pipeline (classify → extract → reconcile → gap → synthesise → critique → export stage).

Auth: REQUIRED · Owner only · Report quota enforced on successful pipeline completion (Stage J)

Response 200:

```json
{
  "job_id": "uuid",
  "donor_report_id": "uuid",
  "stage": "classify | extract | reconcile | gap | synthesise | critique | export",
  "status": "queued | running | awaiting_human | failed | done"
}
```

**Rules:**
- Poll status via `GET /api/reports/{id}/job` (§12.12).
- Requires prior gate preconditions per pipeline stage (Gate 1 before gap advance, etc.).
- `REPORT_CREATE` quota decremented on successful report generation completion (exact trigger at implementation).
- Reclaim of failed jobs at gate stages: implementation-defined (A-03).

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 409 `JOB_ALREADY_ACTIVE` · 429 `QUOTA_EXCEEDED` · 500

---

### 12.8a POST /api/reports/{id}/knowledge-bank/gate3/confirm (canonical — implemented)

Purpose: Gate 3 — human confirmation after critic review; marks sections accepted for export.

Auth: REQUIRED · Owner only

Response 200: includes `gate3_confirmed_at` when confirmed.

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.9 GET /api/reports/{id}

Purpose: full report state — Gate 3 review surface.

Auth: REQUIRED · Owner only

Response 200 (top-level ReportDetailResponse):

```json
{
  "id": "uuid",
  "funder_report_template_id": "uuid",
  "funder_name": "string",
  "template_name": "string",
  "linked_proposal_id": "uuid or null",
  "reporting_period_start": "YYYY-MM-DD",
  "reporting_period_end": "YYYY-MM-DD",
  "status": "DRAFT | EXTRACTING | AWAITING_REVIEW | GENERATING | DEGRADED | COMPLETE",
  "version": 1,
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "content_json": {
    "sections": [
      {
        "section_key": "string",
        "label": "string",
        "generation_status": "GENERATED | FAILED | AWAITING_REVIEW | ACCEPTED",
        "content": {
          "text": "string",
          "assumptions": ["string"],
          "evidence_used": ["string"]
        },
        "critic_flags": [
          {
            "claim_text": "string",
            "severity": "BLOCK | WARN",
            "reason": "string",
            "accepted": false
          }
        ],
        "failure_reason": "string or null",
        "constraints_applied": {
          "word_limit": 0,
          "word_limit_respected": true
        },
        "human_edited": false,
        "last_edited_at": "ISO-8601 or null"
      }
    ],
    "generation_summary": {
      "total_sections": 0,
      "generated": 0,
      "failed": 0,
      "awaiting_review": 0,
      "accepted": 0,
      "critic_blocks": 0,
      "warnings": ["string"]
    }
  },
  "knowledge_bank_json": {},
  "gap_analysis_json": {
    "schema_version": "1.0.0",
    "readiness_score": 0,
    "ready_for_gate2": false,
    "gaps": [
      {
        "item_key": "string",
        "section_key": "string",
        "section_label": "string",
        "required_item_type": "indicator | table | section",
        "required_item_ref": "string",
        "severity": "required | recommended",
        "question": "string",
        "rationale": "string"
      }
    ],
    "gap_agent": "gap_compliance_agent",
    "analyzed_at": "ISO-8601 or null",
    "report_context": {
      "report_type": "annual"
    },
    "agent_trace": {},
    "error": "string or null"
  },
  "indicator_actuals_json": {},
  "current_gate": "none | gate1 | gate2 | gate3",
  "gate3_confirmed_at": "ISO-8601 or null"
}
```

**Note:** Full JSONB payloads included on detail endpoint only — not on list (§12.10). `gap_analysis_json` shape matches `DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.9 (flattened E3 persist from `envelope_to_gap_analysis_json`).

Errors: 401 · 403 · 404 · 500

---

### 12.10 GET /api/reports

Purpose: list user's reports (dashboard).

Auth: REQUIRED

Query: `limit` (optional, default 10, max 50)

Response 200:

```json
{
  "reports": [
    {
      "id": "uuid",
      "funder_name": "string",
      "template_name": "string",
      "status": "DRAFT | EXTRACTING | AWAITING_REVIEW | GENERATING | DEGRADED | COMPLETE",
      "reporting_period_start": "YYYY-MM-DD",
      "reporting_period_end": "YYYY-MM-DD",
      "current_gate": "none | gate1 | gate2 | gate3",
      "latest_job_status": "queued | running | awaiting_human | failed | done | null",
      "latest_job_stage": "classify | extract | reconcile | gap | synthesise | critique | export | null",
      "created_at": "ISO-8601 timestamp",
      "updated_at": "ISO-8601 timestamp"
    }
  ]
}
```

Errors: 401 · 500

---

### 12.11 PATCH /api/reports/{id}/sections/{key}

**PROVISIONAL — confirm against Plan 1 (Track B) gate UI design before building.**

Purpose: Gate 3 — human edit or accept critic flags for one section (alternate to POST §12.8a + detail GET).

Auth: REQUIRED · Owner only

Request:

```json
{
  "content_text": "string or null",
  "accept_critic_flags": ["claim_text"],
  "accept_section": true
}
```

Response 200: same shape as GET §12.9 (full detail).

**Rules:**
- `accept_section: true` marks section `generation_status: ACCEPTED`.
- Export requires all required sections `ACCEPTED` and no unaccepted `BLOCK` critic flags.
- Setting `confirm_gate3` equivalent: when all sections accepted, server sets `gate3_confirmed_at` on knowledge bank and `status: COMPLETE`.

Errors: 401 · 403 · 404 · 404 `SECTION_NOT_FOUND` · 409 `GATE_NOT_SATISFIED` · 422 · 500

---

### 12.12 GET /api/reports/{id}/job

Purpose: async pipeline status ("watch the agents work" UI).

Auth: REQUIRED · Owner only

Query: `job_id` (optional — latest active job if omitted)

Response 200 (top-level):

```json
{
  "job_id": "uuid",
  "donor_report_id": "uuid",
  "stage": "classify | extract | reconcile | gap | synthesise | critique | export",
  "status": "queued | running | awaiting_human | failed | done",
  "agent_trace_json": {
    "runs": [],
    "total_estimated_cost_usd": 0.0
  },
  "error": "string or null",
  "started_at": "ISO-8601 or null",
  "finished_at": "ISO-8601 or null",
  "current_gate": "none | gate1 | gate2 | gate3"
}
```

Errors: 401 · 403 · 404 · 404 `JOB_NOT_FOUND` · 500

---

### 12.13 POST /api/reports/{id}/export

Purpose: render funder-formatted DOCX (idempotent).

Auth: REQUIRED · Owner only

Request:

```json
{
  "export_format": "DOCX"
}
```

Response 200: binary DOCX stream

Headers:

- `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `Content-Disposition: attachment; filename="report-{id}.docx"`

**Rules:**
- Idempotent re-download does not consume quota.
- First successful export per report version consumes `REPORT_EXPORT` quota (Stage J).
- Requires Gate 3 complete / `status: COMPLETE` or `DEGRADED` with all accepted sections.
- Non-200 responses: JSON error envelope (§1).

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` · 409 `EXPORT_NOT_READY` · 422 `UNSUPPORTED_FORMAT` · 429 `QUOTA_EXCEEDED` · 500

---

### 12.14 M&E Error Codes (additive)

| error_code | HTTP | When |
|------------|------|------|
| `REPORT_NOT_FOUND` | 404 | Report id invalid or not owned |
| `TEMPLATE_NOT_FOUND` | 404 | Template id invalid or inactive |
| `JOB_NOT_FOUND` | 404 | Job id invalid |
| `SECTION_NOT_FOUND` | 404 | section_key not in template |
| `GATE_NOT_SATISFIED` | 409 | Human gate prerequisite missing |
| `EXPORT_NOT_READY` | 409 | Gate 3 incomplete or critic blocks remain |
| `FILE_TOO_LARGE` | 413 | Upload exceeds limit |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | MIME not allowed |
| `UPGRADE_REQUIRED` | 403 | Free/Growth M&E entry (§10.3) |

Quota errors use existing `QUOTA_EXCEEDED` with `details.entitlement`: `reports` | `report_exports`.

---

## Changelog

### 2026-05-24 — M&E Module Stage B contract lock

**Decision:** Stage B structure lock for Donor Report Writer module. No existing §1–§11 endpoint shapes altered.

**Adds:**
1. **Section 12:** Full M&E API surface (13 endpoints) with locked envelope conventions.
2. Explicit top-level response objects for single-resource endpoints (no `report` wrapper).
3. Named list wrappers for collection endpoints.
4. Stage J entitlements on **IMPACT** (2 reports/month bundled) and §4 `reports` / `report_exports` blocks (§12.0).

**Governance:** Field contracts in `docs/artefacts/me_module/DB_FIELD_CONTRACT_*.md`; enums in `ENUM_REGISTRY.md` §5.

---

### 2026-03-16 — Contract alignment to live backend (Phase 1)

**Decision:** Backend is source of truth. Contract updated to match deployed Railway backend behavior, verified by runtime audit (audit_1603.md).

**Changes:**
1. **Section 6.1–6.3:** Removed `ngo_profile` response envelope. All profile endpoints (GET/POST/PUT) return top-level profile objects.
2. **Section 6.1:** Updated `past_projects` field names from `project_title`/`donor_funder` to `title`/`donor` (matches DB schema and Pydantic model).
3. **Section 6.1:** Updated `me_practices` → `monitoring_and_evaluation_practices`, `previous_funders` → `funders_worked_with_before`.
4. **Section 6.1:** Added `profile_status`, `completeness_score`, `missing_fields` to profile response (backend includes these computed fields in profile responses).
5. **Section 6.4:** Updated completeness field names from `status`/`percent_complete`/`required_fields`/`updated_at` to `profile_status`/`completeness_score`/`missing_fields`.
6. **Section 6.4:** Documented that 404 is returned when no profile exists (not a JSON body with `status: "MISSING"`).
7. **Section 6.4:** Added completeness scoring breakdown for reference.
8. **Section 6.2:** Clarified read-only fields excluded from request body.

**Governance note:** This is a deliberate alignment decision, not a convenience edit. The backend Pydantic schemas enforce `extra="forbid"` — sending legacy field names returns 422. All three layers (backend, contract, frontend) must now converge on these canonical shapes.

```

---

**END OF CONTRACT**
