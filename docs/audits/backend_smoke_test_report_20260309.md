# GrantPilot Backend Smoke Test Report

**Date:** 2026-03-09 (UTC)
**Backend URL:** `https://ngoinfo-grantpilot-production.up.railway.app`
**Method:** Static source code analysis (live curl tests blocked by sandbox egress proxy)

---

## Execution Note

All tests were planned to run via `curl` against the live Railway URL, but the sandbox environment's egress proxy blocks `*.up.railway.app` (HTTP 403 `host_not_allowed`). This report is based on complete source code analysis, which is the definitive source of truth for schema field names and API behavior. Prior pre-launch smoke results (2026-02-24) are referenced where applicable.

---

## PHASE 0: Schema Discovery (from source code)

### PastProject schema (`app/schemas/ngo_profile.py:4-9`)

| Field | Type | Required |
|-------|------|----------|
| `title` | str \| None | No |
| `donor` | str \| None | No |
| `duration` | str \| None | No |
| `location` | str \| None | No |
| `summary` | str \| None | No |

### NGOProfileCreate / NGOProfileUpdate schema (`app/schemas/ngo_profile.py:35-44`)

| Field | Type | Required |
|-------|------|----------|
| `organization_name` | str | **Yes** |
| `country_of_registration` | str | **Yes** |
| `mission_statement` | str | **Yes** |
| `focus_sectors` | list[str] | No (default: []) |
| `geographic_areas_of_work` | list[str] | No (default: []) |
| `target_groups` | list[str] | No (default: []) |
| `past_projects` | list[PastProject] | No (default: []) |
| `year_of_establishment` | int \| None | No |
| `contact_person_name` | str \| None | No |
| `contact_email` | str \| None | No |
| `website` | str \| None | No |
| `full_time_staff` | int \| None | No |
| `annual_budget_amount` | float \| None | No |
| `annual_budget_currency` | str \| None | No |
| `monitoring_and_evaluation_practices` | str \| None | No |
| `funders_worked_with_before` | list[str] | No (default: []) |

### NGOProfileRead schema (`app/schemas/ngo_profile.py:47-55`)

All fields from Create/Update plus:

| Field | Type |
|-------|------|
| `id` | str |
| `user_id` | str |
| `profile_status` | str ("DRAFT" \| "COMPLETE") |
| `completeness_score` | int (0-100) |
| `missing_fields` | list[str] |
| `created_at` | str (ISO-8601) |
| `updated_at` | str (ISO-8601) |
| `last_completed_at` | str \| None |

### NGOProfileCompletenessResponse (`app/schemas/ngo_profile.py:58-61`)

| Field | Type |
|-------|------|
| `profile_status` | str |
| `completeness_score` | int |
| `missing_fields` | list[str] |

### FitScanCreateRequest (`app/schemas/fit_scans.py`)

| Field | Type | Required |
|-------|------|----------|
| `funding_opportunity_id` | UUID | **Yes** |

---

## Summary Table

| Test | Expected Status | Assessment | Issue |
|------|--------|------------|-------|
| 0.1 Health | 200 | PASS (per smoke report) | None |
| 0.2 OpenAPI | 200 | PASS (per smoke report) | None |
| 1.1 Mint tokens | 200 | PASS (per smoke report) | None |
| 1.2 Entitlements | 200 | PASS (per smoke report) | None |
| 2.1 Get profile | 200 or 404 | PASS (per smoke report) | None |
| 2.2 Completeness (before) | 200 | PASS (per smoke report) | None |
| 2.3a Create with `project_title`/`donor_funder` | 200 but data loss | **FAIL** | Fields silently ignored; profile stores null titles |
| 2.3b Create with `title`/`donor` | 200 | PASS | Correct field names |
| 2.4 Read back profile | 200 | **FAIL** (if 2.3a used) | past_projects have null titles |
| 2.5 Completeness (after) | 200 | **FAIL** (if 2.3a used) | DRAFT; missing `past_projects` |
| 2.6 Update (PUT) | 200 | PASS (per smoke report) | None |
| 2.7 POST when exists | 409 | PASS | Returns PROFILE_ALREADY_EXISTS |
| 3.1 Funding opportunities | N/A | **NO LIST ENDPOINT** | Only GET by ID |
| 4.1 Create fit scan | 200 or 409 | CONDITIONAL | Requires COMPLETE profile + valid opportunity |
| 4.2 Get fit scan | 200 | CONDITIONAL | Requires fit scan to exist |
| 5.1 Token refresh | 200 | PASS (per smoke report) | None |
| 5.2 Old token after refresh | 200 | PASS | JWTs are stateless, valid until expiry |
| 5.3 New token | 200 | PASS (per smoke report) | None |
| 5.4 No auth | 401 | PASS (per smoke report) | None |

---

## Critical Findings

### 1. PastProject field names: `title` and `donor`

The backend accepts `title` and `donor`. NOT `project_title` / `donor_funder`.

**Source:** `app/schemas/ngo_profile.py:4-9`

Pydantic silently discards unknown fields, so sending `project_title` stores `title: null` with no error. The existing e2e test (`scripts/e2e_auth_profile_test.py:134`) sends `project_title`, which was a mis-correction during the pre-launch audit.

### 2. M&E field name: `monitoring_and_evaluation_practices`

NOT `me_practices`.

**Source:** `app/schemas/ngo_profile.py:31`

### 3. Funders field name: `funders_worked_with_before`

NOT `previous_funders`.

**Source:** `app/schemas/ngo_profile.py:32`

### 4. Completeness response shape

```json
{
  "profile_status": "DRAFT" | "COMPLETE",
  "completeness_score": 0-100,
  "missing_fields": ["field_name_1", ...]
}
```

Uses `profile_status` (NOT `status`), `completeness_score` (NOT `percent_complete`). Does NOT include `required_fields` or `updated_at`.

### 5. COMPLETE status requires past_project with non-empty `title`

The completeness logic (`profile_service.py:62-64`) checks `project.get("title")`. If the frontend sends `project_title` instead, the profile stays DRAFT permanently despite appearing to have complete data.

### 6. PUT (update) works after POST (create)

Confirmed by both source code and smoke report.

### 7. No seeded funding opportunities

No seed script exists. The pre-launch smoke report shows opportunity lookup returned 404 and extended journey tests were skipped.

### 8. Fit scan requires COMPLETE profile + valid opportunity

Both conditions must be met. Since opportunities appear unseeded and the `project_title` bug prevents COMPLETE status, the full pipeline is blocked.

---

## Recommended Fix Sequence

### Priority 1: Fix e2e test field names (CRITICAL)

`scripts/e2e_auth_profile_test.py` lines 134 and 153 use `project_title` instead of `title`. This was a backwards "correction" during the pre-launch audit.

**Fix:** `{"project_title": "Pilot Project"}` → `{"title": "Pilot Project"}`

### Priority 2: Frontend field name alignment

| What | Correct name | Wrong alternatives |
|------|--------------|--------------------|
| Past project name | `title` | `project_title`, `name` |
| Past project funder | `donor` | `donor_funder`, `funder` |
| M&E practices | `monitoring_and_evaluation_practices` | `me_practices` |
| Previous funders | `funders_worked_with_before` | `previous_funders` |
| Completeness status | `profile_status` | `status` |
| Completeness score | `completeness_score` | `percent_complete` |

### Priority 3: Seed funding opportunities in production

Without seeded opportunities, the fit scan and proposal pipeline cannot be tested or used.

### Priority 4: Add `extra="forbid"` to Pydantic models

Adding `model_config = ConfigDict(extra="forbid")` to PastProject and profile schemas would return 422 on unknown fields instead of silently discarding them, preventing the root cause of this bug class.

### Priority 5: Add funding opportunities list endpoint

Currently only `GET /api/funding-opportunities/{id}` exists. A list endpoint is needed for the frontend to browse available opportunities.
