# API_CONTRACT.md (Canonical — Single Source of Truth)

**Status:** Canonical — LOCKED FOR BUILD
**Last updated:** 2026-03-09
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
    }
  }
}
```

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

```json
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
    "created_at": "ISO-8601 timestamp",
    "updated_at": "ISO-8601 timestamp"
  }
}
```

**Notes:** Arrays may be empty. `past_projects` may be empty; completeness rules define when it counts as "missing".

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND`
- 500 `INTERNAL_SERVER_ERROR`

---

### 6.2 POST /api/ngo-profile

Purpose: create authenticated user's NGO profile.

Auth: REQUIRED

Request: same shape as `ngo_profile` above, excluding `id` / `created_at` / `updated_at` and excluding `past_projects[].id`.

Response 200: same as `GET /api/ngo-profile`

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

Response 200: same as `GET /api/ngo-profile`

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

```json
{
  "profile_status": "DRAFT | COMPLETE",
  "completeness_score": 0,
  "missing_fields": ["string"]
}
```

**Rules:**

- If no profile exists: returns **404** `PROFILE_NOT_FOUND` (not a 200 with status "MISSING").
- If profile exists but required fields missing: `profile_status="DRAFT"`, `missing_fields` contains remaining required keys.
- If complete: `profile_status="COMPLETE"`, `missing_fields=[]`, `completeness_score=100`.
- `past_projects` is considered missing if array is empty OR no item has non-empty `title`.
- Backend does NOT return the previously documented required-field list or `updated_at` in this response.

Errors:

- 401 `UNAUTHORIZED`
- 404 `PROFILE_NOT_FOUND` (no profile exists for this user)
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
| `DRAFT` | Proposal persisted, generation complete (default terminal state for successful generation) |
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
        "generation_status": "GENERATED | FAILED | MANUAL_REQUIRED",
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
    "entitlement": "fit_scans | proposals | proposal_regenerations | docx_exports",
    "limit": 0,
    "used": 0,
    "remaining": 0,
    "period": "LIFETIME | BILLING_CYCLE",
    "reset_at": "ISO-8601 timestamp or null"
  }
}
```

---

## 11) OpenAPI Conformance Requirements (for backend)

These requirements ensure OpenAPI spec stays in sync with this contract. They are instructions for backend implementation, NOT consumed by the frontend directly.

1. **Bearer auth declaration:** OpenAPI MUST declare `components.securitySchemes` with HTTP bearer scheme, and all protected endpoints MUST have `security` applied.
2. **Typed response models:** All endpoint response schemas MUST use explicit Pydantic models — no `{}` empty schemas in OpenAPI for any 200 response.
3. **Standard error envelope:** All 4xx/5xx responses MUST reference a `StandardErrorResponse` model matching Section 1 — not FastAPI's default `HTTPValidationError` (except 422 where it may coexist).
4. **Google callback semantics:** `/api/auth/google/callback` MUST be represented as 302 redirect in OpenAPI, not JSON 200.
5. **NGO profile path:** Backend routes MUST use `/api/ngo-profile*` (with `/api` prefix) — not bare `/ngo-profile*`.

---

**END OF CONTRACT**
