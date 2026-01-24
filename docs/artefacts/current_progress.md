# Current Progress (Audit Snapshot)

This file summarizes what has been implemented so far in the GrantPilot backend.
It is intended to help review artefacts for missing details or ambiguity.

## Runtime / App Structure

- FastAPI app in `app/main.py`
- Configuration validation in `app/core/config.py` (fail-fast on startup)
- JSON error envelope for validation + domain errors
- Logging configuration in `app/core/logging.py`
- Health endpoint in `app/api/routes/health.py`

## Database / Migrations

Alembic is used for all schema changes:
- `alembic/versions/0001_initial.py` — funding_opportunities + enum types (idempotent)
- `alembic/versions/0002_auth_tables.py` — users, auth_refresh_tokens, auth_magic_link_tokens
- `alembic/versions/0003_ngo_profiles.py` — ngo_profiles
- `alembic/versions/0004_funding_defaults.py` — DB defaults for funding_opportunities system fields
- `alembic/versions/0005_commercial_spine.py` — user_plans + usage_ledger

SQLAlchemy models (in `app/models/`):
- `User`
- `AuthRefreshToken`
- `AuthMagicLinkToken`
- `NGOProfile`
- `FundingOpportunity`
- `UserPlan`
- `UsageLedger`

## Authentication (Google OAuth + Magic Link)

Implemented in `app/api/routes/auth.py`:
- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `POST /api/auth/magic-link/request`
- `POST /api/auth/magic-link/consume`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/test-mode/mint` (gated by TEST_MODE; for smoke tests)

Auth support modules:
- JWT + token hashing in `app/core/security.py`
- Rate limiting in `app/core/rate_limit.py`
- Auth dependency in `app/api/dependencies/auth.py`

## NGO Profile Domain

Endpoints in `app/api/routes/ngo_profile.py`:
- `POST /ngo-profile`
- `GET /ngo-profile`
- `PUT /ngo-profile`
- `GET /ngo-profile/completeness`

Service logic in `app/services/profile_service.py`:
- Create/update, completeness computation, validation rules

Schemas in `app/schemas/ngo_profile.py`

## Funding Opportunities

Model: `app/models/funding_opportunity.py`
- Includes check constraint for FIXED deadline requires application_deadline
- JSONB defaults for list fields

DB defaults for CSV Mode B:
- `id` default `gen_random_uuid()`
- `created_at` default `now()`
- `updated_at` default `now()`

## Commercial Spine (Plans / Quotas / Usage)

Tables:
- `user_plans` (plan + billing period fields)
- `usage_ledger` (append-only usage events + idempotency key)

Service layer:
- `app/services/quota_service.py`
  - Plan quotas
  - Entitlements calculation
  - Quota enforcement (raises DomainError)
  - Usage recording

Endpoint:
- `GET /api/me/entitlements` (in `app/api/routes/entitlements.py`)

Guard/dependency:
- `app/api/dependencies/quota.py` (reusable quota guard)

## Testing / Scripts

Smoke tests:
- `scripts/smoke_test.py` (Track A — gating)
- `scripts/e2e_auth_profile_test.py` (Track B — optional)
- CI workflow: `.github/workflows/smoke-test.yml`

Unit tests:
- `tests/test_quota_service.py` (quota payload + exhausted quota case)

## Documentation Updates Made

- `CHANGELOG.md` updated per completed prompts
- `RUNBOOK.md` includes DB migration and readiness checks
- `DOC_GAP_REPORT.md` used to log ambiguities during earlier prompts

## Pending / Not Implemented Yet

- Fit Scan v1 (blocked pending artefact alignment)
- Proposal generation flows
- Stripe checkout + webhook processing
- Any frontend UI work (explicitly out of scope)

