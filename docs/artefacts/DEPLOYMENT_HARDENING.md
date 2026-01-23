DEPLOYMENT_HARDENING.md
Purpose

Define a stable, repeatable deployment approach for the GrantPilot backend on Railway that avoids prior deployment failures (version drift, environment misconfig, DB mismatch, broken CORS, missing runtime deps) and preserves a Plan B fallback.

This file acts as deployment guardrails for Cursor.

High-Level Deployment Strategy
Plan B Preservation (non-negotiable)

The existing ngoinfo-copilot Railway service remains deployed and unchanged.

No environment variables, DB schema, or deployment settings of Plan B are modified during Plan A build.

Plan B is a fallback for launch continuity.

Plan A Deployment (new service)

Create a new Railway service for ngoinfo-grantpilot.

Attach a new Postgres instance to Plan A.

Do not share databases between Plan A and Plan B.

Rationale: database sharing causes schema drift and rollback confusion and is a leading source of “it’s buggy and we don’t know why.”

Runtime and Dependency Hardening
Python + framework version discipline

Pin Python runtime version (explicitly; no floating).

Pin core dependencies (FastAPI, Pydantic, SQLAlchemy, Alembic, http clients, Stripe SDK, OAuth libs).

Avoid “latest” dependency ranges for MVP.

Start command discipline

Use a single, explicit production start method compatible with Railway.

Bind to Railway-provided port and host rules.

No dev server settings in production.

Avoid OS-level dependency surprises

Prefer pure-Python dependencies for MVP.

If any dependency requires OS packages, document explicitly and decide whether Docker is necessary.

Database and Migrations
Source of truth

DB schema is owned by the backend repo.

Migrations must be applied in a controlled manner as part of deployment.

Migration policy

No “manual edits” in production DB.

Every schema change:

has a migration

is applied in deployment pipeline

is backwards-compatible when feasible

Data integrity

Quota ledger writes must be atomic and consistent.

Proposal and fit scan outputs must be persistable and retrievable.

Environment Variables: Required Categories

Cursor must treat env vars as part of the product contract.

Core

Environment identifier (prod/staging/dev)

Database connection URL

Token signing secrets and token expiry settings

Allowed origins for CORS (include Vercel domain(s) explicitly)

Auth

Google OAuth client ID/secret

OAuth redirect URIs (explicitly enumerated for prod/staging)

Email verification token secret + TTL

Password reset token secret + TTL

Email provider credentials (or explicit stub mode for MVP if email sending deferred)

AI

OpenAI API key

Model and generation settings policy (model name(s), temperature, max tokens, safety boundaries)

Prompt version identifier (used in metadata persisted with outputs)

Stripe

Stripe secret key (test/prod separated)

Webhook signing secret

Plan → Price mapping identifiers

Success/cancel URLs (frontend endpoints)

Logging/Monitoring (minimum)

Error capture DSN (if used)

Log level

Request correlation id toggle

CORS and Security Hardening
CORS policy

Allow only known frontend origins (Vercel preview domains can be handled intentionally if needed).

Do not use wildcard CORS in production.

Auth enforcement

All protected endpoints validate access tokens.

Admin/debug endpoints must be protected or disabled in production.

Secrets handling

No secrets committed to repo.

No Stripe secrets or webhook logic in frontend.

Webhook Hardening (Stripe)
Requirements

Signature verification enabled

Idempotency enforced:

The same Stripe event cannot mutate state twice

Webhook handler is resilient:

logs event_id + outcome

fails safely without corrupting plan state

Deployment Flow
Standard deployment sequence (Plan A)

Configure Railway service from ngoinfo-grantpilot repo

Set env vars (copy baseline patterns from Plan B, but adjust values)

Attach new Postgres

Run migrations

Run smoke tests (from TESTING_STRATEGY.md)

Promote to “release candidate”

Only then connect frontend to Plan A base URL

Rollback sequence

If Plan A fails: revert frontend to Plan B base URL (or keep Plan A disconnected).

Plan B must remain deployable and stable without changes.

Build Hygiene: Repo Constraints for Cursor

Cursor must not:

Introduce Supabase dependencies

Add frontend storage as state source of truth

Embed Stripe secrets outside backend

Change existing artefact semantics (MVP scope, pricing, API contract) without updating the corresponding MD files

“No Surprises” Checklist (Pre-Launch)

Before going live:

Env vars validated (no missing required keys)

CORS validated against actual deployed frontend domain

DB migrations applied cleanly on a fresh DB

Stripe webhook verified end-to-end in test mode

Auth flows verified: Google OAuth, password reset, email verification

Smoke tests pass on deployed environment

Logs show correlation IDs and no unhandled exceptions

Plan B is still reachable and functional

Definition of Done (Deployment)

Deployment is “Done” only when:

Plan A service deploys reliably on Railway

Migrations are repeatable

All smoke flows pass on deployed Plan A

Stripe + auth flows work without manual intervention

Plan B remains untouched and operational