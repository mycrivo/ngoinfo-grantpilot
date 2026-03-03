# GrantPilot Onboarding Pipeline — Full Audit Report

**Date:** 2026-03-03
**Branch:** `claude/audit-onboarding-pipeline-ImpDv`
**Mode:** Read-Only + Fix Recommendations
**Scope:** Backend (FastAPI/SQLAlchemy). Frontend (Next.js) is a separate repository and **not available for audit** — frontend investigation items are flagged as NOT AUDITABLE.

---

## Investigation 1: NGO Profile Save

---

## I1.1: Route prefix — `/api/ngo-profile` vs `/ngo-profile`

**Status:** FIXED
**File:** `app/api/routes/ngo_profile.py:19`
**Finding:** The Feb 4 audit flagged the router was mounted without the `/api` prefix. The current code correctly uses `prefix="/api/ngo-profile"`. All four endpoints — `POST`, `GET`, `PUT /api/ngo-profile` and `GET /api/ngo-profile/completeness` — are reachable at the expected URLs.
**Fix required:** None.

---

## I1.2: SQLAlchemy model vs migration column names (all columns)

**Status:** FIXED
**Files:** `app/models/ngo_profile.py`, `alembic/versions/0003_ngo_profiles.py`
**Finding:** The Feb audit identified `organization_country_of_registration` (model) vs `country_of_registration` (migration) as a P0 crash. The current model uses `country_of_registration` as the attribute name with no explicit `mapped_column()` alias, so SQLAlchemy maps it directly to the DB column of the same name. Full column-by-column comparison:

| DB column (migration 0003) | Model attribute | Match? |
|---|---|---|
| `id` | `id` | ✅ |
| `user_id` | `user_id` | ✅ |
| `organization_name` | `organization_name` | ✅ |
| `country_of_registration` | `country_of_registration` | ✅ (was BROKEN in Feb) |
| `mission_statement` | `mission_statement` | ✅ |
| `focus_sectors` | `focus_sectors` | ✅ |
| `geographic_areas_of_work` | `geographic_areas_of_work` | ✅ |
| `target_groups` | `target_groups` | ✅ |
| `past_projects` | `past_projects` | ✅ |
| `profile_status` | `profile_status` | ✅ |
| `completeness_score` | `completeness_score` | ✅ |
| `missing_fields` | `missing_fields` | ✅ |
| `created_at` | `created_at` | ✅ |
| `updated_at` | `updated_at` | ✅ |
| `last_completed_at` | `last_completed_at` | ✅ |
| `year_of_establishment` | `year_of_establishment` | ✅ |
| `contact_person_name` | `contact_person_name` | ✅ |
| `contact_email` | `contact_email` | ✅ |
| `website` | `website` | ✅ |
| `full_time_staff` | `full_time_staff` | ✅ |
| `annual_budget_amount` | `annual_budget_amount` | ✅ |
| `annual_budget_currency` | `annual_budget_currency` | ✅ |
| `monitoring_and_evaluation_practices` | `monitoring_and_evaluation_practices` | ✅ |
| `funders_worked_with_before` | `funders_worked_with_before` | ✅ |

All 24 columns match. No mismatches.
**Fix required:** None.

---

## I1.3a: PastProject sub-object field names — frontend API contract mismatch

**Status:** BROKEN
**File:** `app/schemas/ngo_profile.py:4–9`
**Finding:** The `PastProject` Pydantic model uses:

```python
class PastProject(BaseModel):
    title: str | None = None
    donor: str | None = None
    ...
```

The API contract brief specifies the expected JSON shape as:

```
{ "project_title": "...", "donor_funder": "...", "duration": "...", "location": "...", "summary": "..." }
```

The field names `title`/`donor` in the schema do not match `project_title`/`donor_funder` from the spec. If the frontend sends `project_title` and `donor_funder`, Pydantic's strict parsing will silently set `title` and `donor` to `None` on those objects. The data will be saved as empty projects, which then fail the completeness check (`valid_project` requires `title` to be truthy), causing the profile to remain in DRAFT status even after the user has entered past project data. This is a likely contributor to the reported "profile not saved" bug.

**Fix required:** Rename `PastProject.title` → `project_title` and `PastProject.donor` → `donor_funder` in `app/schemas/ngo_profile.py`, then update all references in `profile_service.py` (the `_normalize_projects` call uses `project.get("title")` in `_compute_completeness` at line 63).

---

## I1.3b: `me_practices` vs `monitoring_and_evaluation_practices`

**Status:** BROKEN
**File:** `app/schemas/ngo_profile.py:31`
**Finding:** The Pydantic schema exposes `monitoring_and_evaluation_practices` (long name). If the frontend API client was built to a spec using the short alias `me_practices`, those fields are silently dropped by Pydantic and never saved. The profile will save without M&E data every time.
**Fix required:** Add a Pydantic field alias so the schema accepts either `me_practices` OR `monitoring_and_evaluation_practices` as input (use `Field(alias="me_practices")`), or confirm with the frontend team which name the client sends and align accordingly.

---

## I1.3c: `previous_funders` vs `funders_worked_with_before`

**Status:** BROKEN
**File:** `app/schemas/ngo_profile.py:32`
**Finding:** Same pattern. The schema field is `funders_worked_with_before`. If the frontend sends `previous_funders`, the value is silently dropped and the field defaults to an empty list.
**Fix required:** Same approach — add a Pydantic field alias for `previous_funders`, or confirm the frontend field name.

---

## I1.4: POST vs PUT logic (profile creation vs update)

**Status:** FIXED
**File:** `app/api/routes/ngo_profile.py`, `app/services/profile_service.py`
**Finding:**
- `POST /api/ngo-profile`: calls `create_profile()`, raises `409 PROFILE_ALREADY_EXISTS` if a profile already exists. Correct.
- `PUT /api/ngo-profile`: calls `update_profile()` → `get_profile()`, raises `404 PROFILE_NOT_FOUND` if no profile exists yet. Correct.
- `GET /api/ngo-profile`: raises `404 PROFILE_NOT_FOUND` if no profile. Frontend should use 404 response to decide whether to POST or PUT.
- `GET /api/ngo-profile/completeness`: raises `404` when no profile exists. Frontend must treat 404 as MISSING profile status.
Both endpoints exist, work, and the logic is correct.
**Fix required:** None.

---

## I1.5–I1.7: Frontend form handler, beforeunload, auth header

**Status:** NOT AUDITABLE
**Finding:** The frontend (Next.js app at `grantpilot.ngoinfo.org`) is not present in this repository. The `FRONTEND_ARCHITECTURE_SPEC.md` defines the expected frontend behaviour but no implementation files are available. Backend is consistent with what the frontend needs:
- The `/api/ngo-profile` prefix is correct.
- The auth dependency (`get_current_user`) validates Bearer tokens from the `Authorization` header.
- Any 401 from an expired token would be legitimate — the frontend must handle it via token refresh before logout.

**Root cause of the reported bug cannot be fully confirmed from the backend alone**, but the most likely backend-side contributor is I1.3a (silent data drop on `PastProject` fields), which would make the profile appear as DRAFT after save.
**Fix required:** Audit the frontend profile form component once the Next.js repo is accessible.

---

## Investigation 2: Auth Session Stability

---

## I2.1: Token refresh mechanism

**Status:** FIXED
**File:** `app/api/routes/auth.py:570–624`
**Finding:** `POST /api/auth/refresh` exists and implements full token rotation:
1. Validates the incoming refresh token (not revoked, not expired).
2. Revokes all active refresh tokens for the user.
3. Issues a new refresh token and a new access token.
4. Returns the new pair.

The `issue_access_token` call now reads the user's plan from the `user_plans` table via `resolve_user_plan()` (auth_service.py:90–94). The Feb audit P0 of hardcoded `plan="FREE"` is **FIXED**.

No backend race condition exists in the token refresh itself — it uses a single DB session. However, if the frontend makes multiple simultaneous 401-triggered refresh calls, they could result in multiple valid refresh tokens briefly. The `_revoke_active_refresh_tokens` call in each refresh handler mitigates this.
**Fix required:** None on the backend. Frontend should serialize token refresh calls (deduplicate concurrent refresh attempts using a promise/mutex pattern).

---

## I2.2: Token storage

**Status:** NOT AUDITABLE
**Finding:** Token storage (memory vs localStorage) is a frontend concern. The `FRONTEND_ARCHITECTURE_SPEC.md` specifies tokens must be stored in React context (in-memory), NOT in localStorage. Cannot verify without frontend code.
**Fix required:** Verify in the Next.js repo.

---

## I2.3: Post-save redirect race

**Status:** NOT AUDITABLE
**Finding:** Whether the profile form redirects before the API response arrives is a frontend concern. The backend correctly returns the full `NGOProfileRead` response on POST and PUT — there is no async delay.
**Fix required:** Verify in the Next.js repo. The save handler must `await` the API call before triggering any navigation.

---

## Investigation 3: Full Onboarding Pipeline Integrity

---

## I3.1–I3.3: `/start` page (WordPress handoff, auth, sessionStorage)

**Status:** NOT AUDITABLE
**Finding:** The `/start` page is a Next.js frontend component. The backend supports the required flow: Google OAuth produces a redirect to `AUTH_POST_LOGIN_REDIRECT_URL?code={code}`, which the frontend `/auth/callback` page exchanges via `POST /api/auth/exchange`. The backend stores the opportunity context via sessionStorage is entirely a frontend concern.
**Fix required:** Verify in the Next.js repo that `opportunity_id` is stored in sessionStorage before auth redirect, and restored after `/auth/callback`.

---

## I3.4: `/start` → Profile gate (completeness check)

**Status:** BROKEN
**Files:** `app/api/routes/ngo_profile.py:135–146`, `app/schemas/ngo_profile.py:58–61`
**Finding:** `GET /api/ngo-profile/completeness` exists and is correctly mounted. However, the **response shape does not match what the frontend spec requires.**

The endpoint currently returns:
```json
{
  "profile_status": "DRAFT",
  "completeness_score": 45,
  "missing_fields": ["focus_sectors", "past_projects"]
}
```

The audit brief (and implied API contract for this endpoint) specifies:
```json
{
  "status": "DRAFT",
  "percent_complete": 45,
  "required_fields": [...],
  "missing_fields": ["focus_sectors", "past_projects"],
  "updated_at": "2026-01-23T12:00:00Z"
}
```

**Mismatches:**
| Spec field | Actual field | Issue |
|---|---|---|
| `status` | `profile_status` | Different key name — frontend gets `undefined` if checking `response.status` |
| `percent_complete` | `completeness_score` | Different key name — frontend gets `undefined` if checking `response.percent_complete` |
| `required_fields` | *(missing)* | Never returned — frontend cannot display which fields are mandatory |
| `updated_at` | *(missing)* | Never returned |

Additionally, when no profile exists, the endpoint raises `404 PROFILE_NOT_FOUND` instead of returning `{ "status": "MISSING", ... }`. The frontend `/start` page should treat a 404 from this endpoint as status `"MISSING"` and redirect to `/profile`.

**Fix required:**
1. Rename `profile_status` → `status` and `completeness_score` → `percent_complete` in `NGOProfileCompletenessResponse`.
2. Add `required_fields: list[str]` (the static list of required fields) and `updated_at: str | None` to the response.
3. Update the route handler to populate these fields from the profile's `updated_at` timestamp.

---

## I3.5: `/start` → Fit Scan initiation

**Status:** FIXED
**Files:** `app/api/routes/fit_scans.py`, `app/services/fit_scan_service.py`, `app/api/routes/entitlements.py`
**Finding:**
- `GET /api/me/entitlements` — FIXED (see I4.1). No longer infinite recursion.
- `POST /api/fit-scans` — exists, enforces quota, checks profile completeness, runs AI, persists result, returns `FitScanResponseEnvelope`. Correctly returns `409 PROFILE_INCOMPLETE` with `missing_fields` if profile is incomplete.
- `GET /api/fit-scans/{id}` — exists, enforces ownership.
- Quota is checked before the AI call and usage is recorded after successful persistence. Failed AI calls do not consume quota. ✅
**Fix required:** None (backend only).

---

## Investigation 4: Known Backend P0s from Feb Audit

---

## I4.1: Entitlements infinite recursion

**Status:** FIXED
**File:** `app/api/routes/entitlements.py`
**Finding:** The Feb audit found the route handler named `get_entitlements` shadowed the imported `get_entitlements` from `quota_service`, causing a `RecursionError`. The current code aliases the import:

```python
from app.services.quota_service import get_entitlements as fetch_entitlements

def get_user_entitlements(...):
    return fetch_entitlements(db, current_user.id)
```

The handler is now named `get_user_entitlements`. No recursion.
**Fix required:** None.

---

## I4.2: Usage ledger phantom columns (`period_start`, `period_end`)

**Status:** FIXED
**File:** `app/services/quota_service.py:244–251`
**Finding:** The Feb audit found `quota_service.py` setting `period_start` and `period_end` on `UsageLedger` — columns that don't exist in the model or migration. The current `record_usage()` creates `UsageLedger` with only valid columns:

```python
ledger = UsageLedger(
    user_id=user_id,
    event_type=event_type,
    occurred_at=datetime.now(timezone.utc),
    idempotency_key=idempotency_key,
)
```

No phantom columns set.
**Fix required:** None.

---

## I4.3: Auth plan hardcoding

**Status:** FIXED
**Files:** `app/services/auth_service.py:90–100`, `app/core/security.py:27–43`
**Finding:** The Feb audit found all auth endpoints hardcoding `plan="FREE"` in the JWT payload. The current `issue_access_token()` calls `resolve_user_plan(db, user.id)` which queries the `user_plans` table:

```python
def resolve_user_plan(db: Session, user_id: uuid.UUID) -> str:
    plan = db.execute(
        select(UserPlan.plan_name).where(UserPlan.user_id == user_id)
    ).scalar_one_or_none()
    return plan or PLAN_FREE
```

The correct plan (FREE/GROWTH/IMPACT) is now embedded in every issued token.
**Fix required:** None.

---

## Additional Findings (not in original brief)

---

## X1: `user_plans` column name mismatch (Feb audit A1)

**Status:** FIXED
**Files:** `app/models/user_plan.py`, `alembic/versions/0005_commercial_spine.py`, `alembic/versions/0007_schema_alignment.py`
**Finding:** The Feb audit found the model used `current_period_start`/`current_period_end` but the migration created `billing_period_start`/`billing_period_end`. The current model uses the correct names matching the migration. Additionally, `plan_activated_at` was added to both the model and the DB via migration `0007_schema_alignment`. `quota_service.py` correctly references `plan.billing_period_start`, `plan.billing_period_end`, and `plan.plan_activated_at` — all of which now exist.
**Fix required:** None.

---

## X2: CORS middleware missing (Feb audit A5)

**Status:** FIXED
**File:** `app/main.py:26–32`
**Finding:** `CORSMiddleware` is imported and applied using `CORS_ALLOWED_ORIGINS` from config. Frontend is no longer blocked by the browser same-origin policy.
**Fix required:** None.

---

## X3: `idempotency_key` nullable mismatch — latent crash

**Status:** BROKEN
**File:** `app/services/quota_service.py:193–252`, `app/models/usage_ledger.py:44`
**Finding:** `record_usage()` accepts `idempotency_key: str | None = None`. If called without an idempotency key, `UsageLedger` is constructed with `idempotency_key=None`. The DB column `idempotency_key` is `NOT NULL` (both in the migration and model). The DB will reject the INSERT with a NOT NULL violation.

Currently, `fit_scan_service.py` always passes `str(uuid.uuid4())` so this path is not triggered in production. However, any future caller that omits `idempotency_key` will get a DB crash (not a clean domain error). The model type annotation `Mapped[str]` (not `Mapped[str | None]`) is also misleading.

**Fix required:** Either make `idempotency_key` required in `record_usage()` (remove the default `None`), or auto-generate a UUID when `None` is passed. Add a guard before constructing `UsageLedger`:
```python
idempotency_key = idempotency_key or str(uuid.uuid4())
```

---

## X4: Completeness calculation reads stale stored data

**Status:** PARTIALLY FIXED
**File:** `app/services/profile_service.py:187–189`
**Finding:** `get_completeness()` returns `profile.profile_status`, `profile.completeness_score`, and `profile.missing_fields` — values stored in the DB at last save. These are always recalculated on `create_profile()` and `update_profile()`, so the stored data is fresh immediately after a save. However, if a profile row was manually modified at the DB level (e.g., admin operation), the completeness would be stale until the next profile save. For the onboarding pipeline, this is not a practical risk.
**Fix required:** None for MVP; note for operational runbook.

---

## X5: No OpenAPI documentation for NGO profile endpoints in `API_CONTRACT.md`

**Status:** NOT IMPLEMENTED
**File:** `docs/artefacts/API_CONTRACT.md`
**Finding:** `API_CONTRACT.md` covers auth, billing, fit scans, and proposals but contains no documented request/response schema for the NGO Profile endpoints (`/api/ngo-profile`, `/api/ngo-profile/completeness`). This is the root cause of the field-name ambiguity in I1.3a–c and I3.4: the frontend team had no canonical spec to build against.
**Fix required:** Add the NGO Profile section to `API_CONTRACT.md` specifying all field names, types, and the completeness response shape. This locks the contract before further frontend development.

---

## Prioritised Fix List

### P0 — Blocks all users completing onboarding

| # | Issue | File(s) | Impact |
|---|---|---|---|
| P0-1 | **`PastProject` field names**: schema uses `title`/`donor` but spec requires `project_title`/`donor_funder`. Past project data is silently dropped; profile stays DRAFT; fit scans blocked. | `app/schemas/ngo_profile.py:4–9`, `app/services/profile_service.py:63` | Profile always DRAFT; fit scan blocked |
| P0-2 | **Completeness response shape mismatch**: returns `profile_status`/`completeness_score` but frontend spec reads `status`/`percent_complete`; `required_fields` and `updated_at` are absent. Frontend `/start` gate logic fails silently. | `app/schemas/ngo_profile.py:58–61`, `app/api/routes/ngo_profile.py:135–146` | `/start` profile gate always broken |
| P0-3 | **`me_practices` field alias missing**: `monitoring_and_evaluation_practices` data silently dropped if frontend sends `me_practices`. | `app/schemas/ngo_profile.py:31` | M&E data never saved |
| P0-4 | **`previous_funders` field alias missing**: `funders_worked_with_before` silently dropped if frontend sends `previous_funders`. | `app/schemas/ngo_profile.py:32` | Funders data never saved |

> **Note:** P0-1 is the most likely cause of the reported "profile not saved" bug. When the frontend sends past project objects with `project_title`, the backend receives them with `title=None`. The completeness check (`valid_project = any(... str(project.get("title", "")).strip() ...)`) fails → profile stays DRAFT → the save appears to succeed (200 response) but subsequent reads show DRAFT status with `past_projects` in `missing_fields`. The user sees no error but their data is gone.

### P1 — Breaks flow, workaround exists

| # | Issue | File(s) | Impact |
|---|---|---|---|
| P1-1 | **`idempotency_key` nullable gap**: `record_usage()` can pass `None` to a NOT NULL DB column; will crash if any future caller omits the key. | `app/services/quota_service.py:244` | Latent crash in usage recording |
| P1-2 | **NGO Profile API not in `API_CONTRACT.md`**: no canonical spec → frontend/backend field name divergence. | `docs/artefacts/API_CONTRACT.md` | Ongoing integration ambiguity |
| P1-3 | **Frontend profile form/beforeunload/auth** cannot be audited — repo not present. | Next.js repo (not available) | Unknown — must audit separately |

### P2 — Polish, does not block launch

| # | Issue | File(s) | Impact |
|---|---|---|---|
| P2-1 | Completeness endpoint returns 404 (not `{ status: "MISSING" }`) when no profile exists. Frontend must handle 404 as MISSING explicitly. | `app/api/routes/ngo_profile.py:135` | Minor UX — frontend must code around 404 |
| P2-2 | `get_completeness()` returns stale stored values rather than recalculating live. Safe for MVP but fragile. | `app/services/profile_service.py:187` | Non-issue unless DB is manually modified |

---

## Feb 2026 Audit P0 Status Summary

| Feb Audit Issue | Description | Current Status |
|---|---|---|
| A1 | `user_plans` column name mismatch (`current_period_*` vs `billing_period_*`) | ✅ FIXED |
| A2 | `NGOProfile` model attribute mismatch (`organization_country_of_registration`) | ✅ FIXED |
| A3 | `UsageLedger` phantom columns `period_start`/`period_end` in `quota_service` | ✅ FIXED |
| A4 | Entitlements endpoint infinite recursion | ✅ FIXED |
| A5 | CORS middleware missing | ✅ FIXED |
| A6 | OpenAI errors not caught by domain handler | ✅ FIXED (generic `Exception` handler in `main.py`) |
| F5 | Auth hardcoding `plan="FREE"` | ✅ FIXED |

All 7 P0 issues from the February audit are resolved. The remaining blockers are a new class of **API contract mismatches** between the Pydantic schemas and the field names the frontend was likely built against, plus a completeness endpoint response shape that does not match the spec.
