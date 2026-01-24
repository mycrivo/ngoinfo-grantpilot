TESTING_STRATEGY.md
Purpose

Define the minimum, non-negotiable testing methodology to ship GrantPilot MVP confidently within 72 hours, without repeating prior failure modes (late testing, integration drift, silent regressions, quota bypass, brittle deployments).

This file is a release gate. If these tests are not passing, the build is not considered shippable.

Scope and Principles
In Scope (MVP release gates)

Auth: Google OAuth + Email Magic Link + refresh tokens

Profile CRUD + completeness status

Fit Scan generation + persisted results

Proposal generation + persisted results

Usage / quota enforcement (server-side)

Stripe checkout + webhook processing + plan activation

End-to-end integration: Railway thin client → Railway API → Postgres

Out of Scope (explicitly not required for MVP)

Advanced analytics dashboards

Admin consoles beyond minimal debug endpoints

Multi-org/team accounts

Opportunity ingestion automation (manual/CSV seed acceptable)


Testing principles

Backend is source of truth: quotas, entitlements, persistence, Stripe state, auth validation.

No “it works on my machine”: tests must run against a deployed environment.

Prefer fewer tests with higher signal: focus on flows that caused bugs previously.

Tests must be runnable repeatedly: deterministic, not flaky, minimal external dependencies.

Environments and Release Gates
Environments


Plan A: New ngoinfo-grantpilot Railway service + new Postgres.

Frontend: may be rebuilt; for MVP, frontend can be basic but must be a thin client.

Release gates (must pass to ship)

A release candidate is shippable only if:

All Contract Tests pass

All Smoke E2E Flows pass

Quota bypass checks pass (server-side enforcement)

Stripe webhook signature validation and idempotency checks pass

“Golden Path” works on a clean account end-to-end in production-like environment

Test Layers

---

## TEST_MODE Minting (Temporary, Pre-Launch Only)

Because there is no staging environment yet, a gated test-only endpoint exists to mint tokens for smoke tests.

Hard gates (all required):
- `TEST_MODE=true`
- Caller must provide `X-Test-Mode-Secret` header matching `TEST_MODE_SECRET`
- Strict rate limiting
- Audit logs include timestamp, request_id (if available), caller IP, and outcome

Safety:
- If any gate fails, return 404 (preferred) with standard error schema.
- Endpoint must be removed post-launch or replaced by staging.

---

## Smoke Test Runner (Railway Environment)

Single-command runner against `SMOKE_BASE_URL` executes:

1) `GET /health` → 200
2) `POST /api/auth/test-mode/mint` → tokens
3) `GET /ngo-profile` → 200 or 404
4) If 404: `POST /ngo-profile` → 200
5) `PUT /ngo-profile` → 200
6) `GET /ngo-profile/completeness` → 200 with `profile_status`, `completeness_score`, `missing_fields`
7) `POST /api/auth/refresh` → 200
8) `POST /api/auth/logout` → 200
9) Protected endpoint without auth → 401
10) Invalid payload to profile endpoint → 422 with validation details

Release gate:
- Any smoke failure blocks release.
Layer 1: Contract Tests (API correctness)

Goal: Prevent FE/BE mismatches and silent breaking changes.

What to validate

Request/response JSON shapes match API_CONTRACT.md

Required fields present and correctly typed

Status codes align with contract (200/201/400/401/403/404/409/422)

Error payload structure is consistent (machine-readable codes + human message)

Must-have contract coverage

Auth endpoints:

Google OAuth callback/exchange (as defined in AUTH_AND_SSO_STRATEGY.md)

Magic Link request + consume

Refresh token

Logout / token revocation (if implemented)

NGO Profile:

Create/update profile

Get profile

Completeness status calculation

Fit Scan:

Create/run fit scan against a funding opportunity

Retrieve past fit scans

Persisted scoring fields consistent with FIT_SCAN_* artefacts

Proposal:

Generate proposal

Retrieve proposal

Proposal metadata + sections structure stable

Usage/Quota:

Retrieve quota usage

Enforced decrements on successful generation only

No decrement on failed generation

Billing:

Create Stripe checkout session

Webhook receipt updates plan/entitlements

Plan reflected in /me or usage endpoint

Contract test acceptance criteria

Any breaking change requires updating API_CONTRACT.md + tests in the same PR.

No endpoint returns raw stack traces in non-dev environments.

Layer 2: Smoke E2E Flows (the unbreakable journeys)

Goal: Catch integration + state bugs early (the primary prior pain point).

Smoke Flow 1 — Signup/Login (OAuth + Magic Link)

User signs up or logs in via Google OAuth or Email Magic Link

Receives valid access + refresh token

Protected endpoints work with access token

Refresh rotates/renews access without breaking session

Smoke Flow 2 — Plan selection + Stripe checkout + entitlements

User selects plan (Growth/Impact), completes Stripe checkout, webhook activates entitlements, quotas reflect plan

Smoke Flow 3 — Profile setup

User submits profile fields defined in the product artefacts

Backend returns completeness status

Data persists and can be retrieved consistently

Smoke Flow 4 — Fit Scan run

User selects/inputs a funding opportunity record

Fit Scan runs and persists results

Fit rating methodology is applied consistently (per artefacts)

Re-fetch returns identical stored results (no re-generation on refresh)

Smoke Flow 5 — Proposal generation + export

User generates proposal successfully

Proposal stored and retrievable

Sections are present (Executive Summary, Problem, Approach, M&E, Budget narrative assumptions, etc. per your proposal spec direction)

Regeneration creates a new proposal record (or explicitly overwrites per contract)

DOCX export succeeds (PDF export not supported)

Layer 3: Quota and Abuse Controls (must be server-side)

Goal: Prevent the exact class of “frontend bypass” bugs.

Checks

Quota cannot be bypassed by:

Direct API calls from Postman/browser

Modified frontend requests

Replaying old requests

Usage decrement occurs only when:

Output successfully generated AND persisted

Concurrent requests do not double-spend quota:

Enforce atomic ledger logic at DB level

Acceptance criteria

A user on Free plan cannot exceed Fit Scan / Proposal limits defined in PRICING_AND_ENTITLEMENTS.md.

When quota exhausted, API returns a clear error code used by FE to show upgrade CTA.

Layer 4: Stripe Webhook Reliability

Goal: Avoid billing drift and broken entitlements.

Non-negotiables

Webhook signature verification enabled

Webhook processing is idempotent:

Duplicate deliveries do not create duplicate plan updates

Webhook updates plan entitlements deterministically

Failed webhook processing is logged with correlation ID and retry-safe

Acceptance criteria

A paid user’s plan reflects correctly within a bounded time after checkout (near real-time).

Cancelled/expired subscriptions are reflected correctly.

Test Data Strategy
Test accounts

Maintain:

One Free plan test user

One Paid plan test user (Stripe test mode)

One “Quota exhausted” test user

Funding opportunity fixtures

Maintain at least 3 fixture opportunities:

Strong fit, clear alignment

Moderate fit, partial alignment, missing data

Weak fit, misaligned focus/geography

These should map to DB_FIELD_CONTRACT_FUNDING_OPPORTUNITY.md.

Deterministic AI generation constraints

Generation prompts and settings must be stable between runs for the same inputs when possible.

Store the exact prompt version and model settings metadata alongside outputs.

If non-determinism is unavoidable, ensure output schema consistency is deterministic.

Observability Requirements for Testing

Every smoke run must emit:

Correlation ID across FE → BE → DB writes

Structured logs for:

Auth events

Fit Scan run + score

Proposal generation + persisted proposal_id

Stripe webhook event_id + processing outcome

Error capture in a central tool (minimal setup acceptable)

Definition of Done (MVP)

MVP is “Done” only when:

All 5 Smoke Flows pass on deployed Plan A environment

Contract tests pass for all endpoints used by FE

Quota cannot be bypassed via direct API usage

Stripe checkout + webhook activates paid plan correctly

Outputs are persisted and retrievable without re-generation
