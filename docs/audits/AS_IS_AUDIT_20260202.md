# AS-IS Audit 20260202

Scope: backend repo inspection only. DB schema verification via live Postgres was not performed in this audit; no live `psql` output was collected. DB tables/columns are assessed against migrations and models only. Evidence references are provided for every claim.

## 1) Repo Inventory (Modules Present)

Component | Exists? | Location | Notes
---|---|---|---
Route module: auth | Yes | `app/api/routes/auth.py` | Endpoints: `GET /api/auth/google/start`, `GET /api/auth/google/callback`, `POST /api/auth/magic-link/request`, `POST /api/auth/magic-link/consume`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `POST /api/auth/test-mode/mint` (`app/api/routes/auth.py:L141-L559`)
Route module: entitlements | Yes | `app/api/routes/entitlements.py` | Endpoint: `GET /api/me/entitlements` (`app/api/routes/entitlements.py:L9-L17`)
Route module: fit_scans | Yes | `app/api/routes/fit_scans.py` | Endpoints: `POST /api/fit-scans`, `GET /api/fit-scans/{fit_scan_id}` (`app/api/routes/fit_scans.py:L15-L39`)
Route module: health | Yes | `app/api/routes/health.py` | Endpoint: `GET /health` (`app/api/routes/health.py:L6-L16`)
Route module: ngo_profile | Yes | `app/api/routes/ngo_profile.py` | Endpoints: `POST /ngo-profile`, `GET /ngo-profile`, `PUT /ngo-profile`, `GET /ngo-profile/completeness` (note: no `/api` prefix) (`app/api/routes/ngo_profile.py:L19-L146`)
Service module: fit_scan_prompt_inputs | Yes | `app/services/fit_scan_prompt_inputs.py` | Builds `prompt_inputs_json` payload and derived fields (`app/services/fit_scan_prompt_inputs.py:L11-L162`)
Service module: fit_scan_service | Yes | `app/services/fit_scan_service.py` | Fit Scan execution, quota enforcement, persistence, ownership checks (`app/services/fit_scan_service.py:L36-L123`)
Service module: profile_service | Yes | `app/services/profile_service.py` | NGO profile CRUD + completeness computation (`app/services/profile_service.py:L46-L189`)
Service module: quota_service | Yes | `app/services/quota_service.py` | Plan entitlements, quota enforcement, usage ledger writes (`app/services/quota_service.py:L22-L194`)
Models (SQLAlchemy) | Yes | `app/models/` | `User`, `UserPlan`, `UsageLedger`, `AuthRefreshToken`, `AuthMagicLinkToken`, `FundingOpportunity`, `NGOProfile`, `FitScan` (`app/models/__init__.py:L1-L18`)
Schemas (Pydantic) | Yes | `app/schemas/` | `entitlements`, `fit_scans`, `ngo_profile` (`app/schemas/entitlements.py:L1-L20`; `app/schemas/fit_scans.py:L1-L35`; `app/schemas/ngo_profile.py:L1-L61`)
Scripts | Yes | `scripts/` | `smoke_test.py`, `e2e_auth_profile_test.py`, `start.sh` (`scripts/smoke_test.py:L1-L129`; `scripts/e2e_auth_profile_test.py:L1-L173`; `scripts/start.sh:L1-L8`)
Test-mode endpoint | Yes | `app/api/routes/auth.py` | `POST /api/auth/test-mode/mint` gated by `TEST_MODE` and `x-test-mode-secret` header (`app/api/routes/auth.py:L504-L559`; `app/core/config.py:L51-L52`)
Test-mode script | Yes | `scripts/e2e_auth_profile_test.py` | Uses `/api/auth/test-mode/mint` and `TEST_MODE_SECRET` (`scripts/e2e_auth_profile_test.py:L59-L83`)

## 2) Endpoint-to-Contract Coverage (API_CONTRACT.md)

Endpoint | Implemented (Y/N) | Contract Match (Y/N/Partial) | Gaps | Evidence (file:line)
---|---|---|---|---
GET `/api/auth/google/start` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L29-L42`; Impl: `app/api/routes/auth.py:L141-L172`
GET `/api/auth/google/callback` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L43-L71`; Impl: `app/api/routes/auth.py:L175-L290`
POST `/api/auth/magic-link/request` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L73-L87`; Impl: `app/api/routes/auth.py:L293-L353`
POST `/api/auth/magic-link/consume` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L89-L102`; Impl: `app/api/routes/auth.py:L356-L421`
POST `/api/auth/refresh` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L103-L123`; Impl: `app/api/routes/auth.py:L424-L477`
POST `/api/auth/logout` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L125-L138`; Impl: `app/api/routes/auth.py:L480-L501`
POST `/api/fit-scans` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L139-L196`; Impl: `app/api/routes/fit_scans.py:L18-L28`
GET `/api/fit-scans/{id}` | Y | Y | None observed | Contract: `docs/artefacts/API_CONTRACT.md:L198-L216`; Impl: `app/api/routes/fit_scans.py:L31-L39`
POST `/api/proposals` | N | N | No proposals routes registered in app | Contract: `docs/artefacts/API_CONTRACT.md:L227-L231`; Router list: `app/main.py:L5-L20`
GET `/api/proposals/{id}` | N | N | No proposals routes registered in app | Contract: `docs/artefacts/API_CONTRACT.md:L227-L231`; Router list: `app/main.py:L5-L20`
POST `/api/proposals/{id}/regenerate` | N | N | No proposals routes registered in app | Contract: `docs/artefacts/API_CONTRACT.md:L227-L231`; Router list: `app/main.py:L5-L20`
POST `/api/proposals/{id}/export` | N | N | No proposals export route registered in app | Contract: `docs/artefacts/API_CONTRACT.md:L233-L249`; Router list: `app/main.py:L5-L20`

## 3) Database Schema Audit (Contracts vs. Repo)

DB connection not available in this audit environment; no live `psql` output could be collected. The table below reflects migration/model expectations only.

Table | Contract Match (Y/N/Partial) | Missing/Extra Columns | Enum Issues | Index Issues | Evidence (psql output snippet)
---|---|---|---|---|---
funding_opportunities | Partial | None vs contract | Enums defined with `create_type=False` | Check constraint present | Migrations: `alembic/versions/0001_initial.py:L60-L102`; Model: `app/models/funding_opportunity.py:L36-L118`
users | Partial | Missing `stripe_customer_id` | None | Unique on email/google_sub present | Contract: `docs/artefacts/DB_FIELD_CONTRACT_USERS.md:L24-L38`; Migration: `alembic/versions/0002_auth_tables.py:L24-L57`; Model: `app/models/user.py:L14-L42`
ngo_profiles | Partial | None vs contract | None | Unique `user_id` present | Migration: `alembic/versions/0003_ngo_profiles.py:L20-L115`; Model: `app/models/ngo_profile.py:L10-L79`
user_plans | Partial | Model has `plan_activated_at/current_period_start/end`; migration has `stripe_subscription_id/billing_period_start/end` | None | Indexes on user_id and stripe_subscription_id present | Migration: `alembic/versions/0005_commercial_spine.py:L51-L148`; Model: `app/models/user_plan.py:L10-L45`
usage_ledger | Partial | Service writes `period_start/period_end` but model/migration lack those columns | None | Indexes on user_id/action_type/idempotency present | Migration: `alembic/versions/0005_commercial_spine.py:L150-L224`; Model: `app/models/usage_ledger.py:L20-L48`; Service: `app/services/quota_service.py:L185-L191`
auth_refresh_tokens | Partial | None vs contract | None | Indexes on user_id/expires_at present | Contract: `docs/artefacts/DB_FIELD_CONTRACT_AUTH_REFRESH_TOKENS.md:L6-L21`; Migration: `alembic/versions/0002_auth_tables.py:L60-L91`; Model: `app/models/auth_refresh_token.py:L10-L37`
auth_magic_link_tokens | Partial | None vs contract | None | Indexes on email/expires_at present | Contract: `docs/artefacts/DB_FIELD_CONTRACT_MAGIC_LINK_TOKENS.md:L6-L22`; Migration: `alembic/versions/0002_auth_tables.py:L93-L118`; Model: `app/models/auth_magic_link_token.py:L10-L30`
fit_scans | Partial | None vs contract | None | Indexes on user_id/created_at, opportunity, user+opportunity present | Contract: `docs/artefacts/DB_FIELD_CONTRACT_FIT_SCANS.md:L24-L104`; Migration: `alembic/versions/0006_fit_scans.py:L37-L85`; Model: `app/models/fit_scan.py:L10-L36`
proposals | N | Table not present in migrations/models | N/A | N/A | Models list excludes proposals: `app/models/__init__.py:L1-L18`
exports | N | Table not present in migrations/models | N/A | N/A | Models list excludes exports: `app/models/__init__.py:L1-L18`

## 4) AI Wiring Audit (Prompt Library + Input Mapping)

- PASS: Model hardcoded to `gpt-5.2` in Fit Scan executor (`app/ai/fit_scan_executor.py:L9-L10`).
- PASS: `response_format={"type":"json_object"}` used for the AI call (`app/ai/fit_scan_executor.py:L197-L205`).
- PASS: AI call receives a single `prompt_inputs_json` object in the prompt (`app/ai/fit_scan_executor.py:L183-L195`; `app/services/fit_scan_prompt_inputs.py:L11-L29`).
- PASS: Prompt version persisted for Fit Scans (`app/ai/fit_scan_executor.py:L9`; `app/services/fit_scan_service.py:L84-L93`).
- FAIL: Degraded modes for missing/invalid requirements are not handled; executor requires `fit_summary` and errors on any other payload shape (`app/services/fit_scan_prompt_inputs.py:L115-L118`; `app/ai/fit_scan_executor.py:L227-L247`). Must support `DEGRADED_*` payloads per prompt library and avoid returning 500 on degraded outputs.

## 5) Quota + Entitlements Audit (Commercial Spine)

Area | PASS/FAIL | Evidence (file:line) | Risk
---|---|---|---
Fit Scan quota guard applied | PASS | `app/services/fit_scan_service.py:L60-L61` | Low
Proposal quota guard applied | FAIL | No proposal routes registered (`app/main.py:L5-L20`) | High (quota rules not enforced because feature missing)
Atomic quota decrement after success (Fit Scan) | PASS | `app/services/fit_scan_service.py:L62-L98` | Low
Quota exhaustion maps to 429 | PASS | Error handler remaps QUOTA_EXCEEDED to 429 (`app/main.py:L48-L50`); raise site (`app/services/quota_service.py:L139-L149`) | Low
Free plan lifetime limits enforced | PARTIAL | Free quotas defined as lifetime (`app/services/quota_service.py:L29-L33`); proposal usage not implemented | Medium
Growth/Impact monthly quotas enforced | FAIL | Period logic uses `plan_activated_at/current_period_start/end` (`app/services/quota_service.py:L47-L58`), but migration defines `billing_period_start/end` and no `plan_activated_at` (`alembic/versions/0005_commercial_spine.py:L61-L69`) | High (period boundaries may not persist)

## 6) Stripe + Billing Audit (Spec Adherence)

- FAIL: No checkout creation endpoint found in registered routers (`app/main.py:L5-L20`).
- FAIL: No Stripe webhook handler found in registered routers (`app/main.py:L5-L20`).
- FAIL: No webhook signature verification or idempotency handling present in codebase (`app/main.py:L5-L20`).

## 7) Email Audit (Resend + Transactional Events)

- PASS: Resend integration is present for magic link request (`app/api/routes/auth.py:L330-L338`).
- FAIL: Magic link email sends a raw token rather than a login link (`app/api/routes/auth.py:L333-L338`).
- FAIL: Other transactional triggers (Fit Scan ready, proposal ready, billing events) are not implemented (`app/main.py:L5-L20`).
- FAIL: Non-prod suppression logic is not implemented (no `EMAIL_SUPPRESS_SENDING` handling) (`app/core/config.py:L35-L38`).

## 8) Deployment + Hardening Audit

- PASS: Runtime and dependencies are pinned (`runtime.txt:L1`; `requirements.txt:L1-L10`).
- PASS: Start command runs migrations then uvicorn (`Procfile:L1-L2`; `scripts/start.sh:L1-L8`).
- FAIL: CORS middleware not configured in app startup (`app/main.py:L15-L20`), despite required `CORS_ALLOWED_ORIGINS` in config (`app/core/config.py:L18-L19`).
- PASS: Smoke tests exist (`scripts/smoke_test.py:L1-L129`; `scripts/e2e_auth_profile_test.py:L1-L173`).
- FAIL: Test-mode mint endpoint exists in codebase (must be removed or hard-disabled in prod) (`app/api/routes/auth.py:L504-L559`; `app/core/config.py:L51-L52`).

## Final Output

### A) What is COMPLETE

- Foundations: Core auth endpoints (Google OAuth + Magic Link + refresh/logout) are implemented (`app/api/routes/auth.py:L141-L501`).
- Foundations: Health endpoint present (`app/api/routes/health.py:L6-L16`).
- Commercial spine: Entitlements endpoint available (`app/api/routes/entitlements.py:L9-L17`).
- Core product: Fit Scan POST/GET endpoints implemented (`app/api/routes/fit_scans.py:L18-L39`).

### B) What is PARTIAL / IN PROGRESS

- Commercial spine: User plans schema/logic mismatch (model vs migration columns) (`app/models/user_plan.py:L10-L45`; `alembic/versions/0005_commercial_spine.py:L51-L104`).
- Commercial spine: Usage ledger period fields referenced in service but absent in model/migration (`app/services/quota_service.py:L185-L191`; `app/models/usage_ledger.py:L20-L48`).
- Core product: Fit Scan degraded-mode handling not implemented (`app/services/fit_scan_prompt_inputs.py:L115-L118`; `app/ai/fit_scan_executor.py:L227-L247`).

### C) What is MISSING (per MVP checklist)

- P0: Proposal endpoints (create/get/regenerate/export) not implemented (`docs/artefacts/API_CONTRACT.md:L227-L249`; `app/main.py:L5-L20`).
- P0: Stripe checkout + webhook handling not implemented (`docs/artefacts/STRIPE_INTEGRATION_SPEC.md:L1-L33`; `app/main.py:L5-L20`).
- P1: Proposal persistence tables not present (no models/migrations for proposals/exports) (`docs/artefacts/API_CONTRACT.md:L227-L249`; `app/models/__init__.py:L1-L18`).
- P1: Transactional email events beyond magic link not implemented (`docs/artefacts/TRANSACTIONAL_EMAILS_SPEC.md:L33-L96`; `app/main.py:L5-L20`).
- P2: WordPress context-preserving start flow not implemented in backend routes (`docs/artefacts/WORDPRESS_TO_GRANTPILOT_INTEGRATION.md:L23-L37`; `app/main.py:L5-L20`).

### D) Top 10 Risks

1) **Proposal feature missing entirely**  
Impact: Blocks MVP core workflow after Fit Scan.  
Likelihood: High (no routes/models).  
Mitigation: Implement proposal endpoints + persistence per contract.  
Evidence: `docs/artefacts/API_CONTRACT.md:L227-L249`; `app/main.py:L5-L20`

2) **Stripe billing not implemented**  
Impact: Paid plans cannot be activated or enforced.  
Likelihood: High (no stripe routes).  
Mitigation: Add checkout + webhook handling with signature verification and idempotency.  
Evidence: `docs/artefacts/STRIPE_INTEGRATION_SPEC.md:L1-L33`; `app/main.py:L5-L20`

3) **User plan period mismatch (model vs migration)**  
Impact: Monthly quota resets may fail or compute incorrectly.  
Likelihood: High (schema mismatch).  
Mitigation: Align `user_plans` model and migrations to a single period field scheme.  
Evidence: `app/models/user_plan.py:L10-L45`; `alembic/versions/0005_commercial_spine.py:L61-L69`

4) **Usage ledger period fields missing**  
Impact: Usage recording may raise errors or skip period fields.  
Likelihood: High (service passes unknown args).  
Mitigation: Add columns or remove period_start/period_end usage.  
Evidence: `app/services/quota_service.py:L185-L191`; `app/models/usage_ledger.py:L20-L48`

5) **Degraded AI response handling missing**  
Impact: Fit Scan failures return 500 instead of degraded response; may confuse users and hide missing requirements.  
Likelihood: Medium.  
Mitigation: Handle `DEGRADED_*` payloads and avoid quota consumption.  
Evidence: `app/services/fit_scan_prompt_inputs.py:L115-L118`; `app/ai/fit_scan_executor.py:L227-L247`

6) **Missing Stripe-driven plan updates**  
Impact: Entitlements may not align with billing cycles.  
Likelihood: High (no webhook code).  
Mitigation: Implement webhook-driven plan updates.  
Evidence: `docs/artefacts/STRIPE_INTEGRATION_SPEC.md:L9-L33`; `app/main.py:L5-L20`

7) **No CORS middleware configured**  
Impact: Frontend may be blocked in browsers or CORS defaults misapplied.  
Likelihood: Medium.  
Mitigation: Add explicit CORS allowlist middleware using configured origins.  
Evidence: `app/main.py:L15-L20`; `app/core/config.py:L18-L19`

8) **Test-mode mint endpoint present**  
Impact: If misconfigured, could allow token minting in production.  
Likelihood: Medium.  
Mitigation: Remove endpoint or hard-disable in prod builds.  
Evidence: `app/api/routes/auth.py:L504-L559`; `docs/artefacts/DEPLOYMENT_HARDENING.md:L230-L233`

9) **Magic link email content not per spec**  
Impact: Users receive token text instead of link; UX/security issues.  
Likelihood: Medium.  
Mitigation: Send login link with expiry and base URL.  
Evidence: `app/api/routes/auth.py:L333-L338`; `docs/artefacts/TRANSACTIONAL_EMAILS_SPEC.md:L37-L40`

10) **Users table missing `stripe_customer_id`**  
Impact: Billing linkage may fail or require workarounds.  
Likelihood: Medium.  
Mitigation: Add `stripe_customer_id` per DB contract.  
Evidence: `docs/artefacts/DB_FIELD_CONTRACT_USERS.md:L24-L38`; `alembic/versions/0002_auth_tables.py:L24-L57`

### E) Proposed Next Build Prompt (single highest-leverage vertical slice)

"Implement the proposal feature vertical slice per `API_CONTRACT.md` and `PRICING_AND_ENTITLEMENTS.md`: add proposal persistence tables/models, `/api/proposals` create/get/regenerate and `/api/proposals/{id}/export` (DOCX-only), enforce proposal quotas with `usage_ledger`, and return the standard error envelope. Do not expand scope beyond proposal generation/export and quota enforcement."
