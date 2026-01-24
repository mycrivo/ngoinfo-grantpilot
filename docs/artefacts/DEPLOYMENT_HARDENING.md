DEPLOYMENT_HARDENING.md
Purpose

Define a stable, repeatable deployment approach for the GrantPilot backend on Railway that avoids prior deployment failures (version drift, environment misconfig, DB mismatch, broken CORS, missing runtime deps) and preserves a Plan B fallback.

This file acts as deployment guardrails for Cursor.

High-Level Deployment Strategy


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

Allowed origins for CORS 

Auth

Google OAuth client ID/secret

OAuth redirect URIs (explicitly enumerated for prod/staging)

Email Magic Link token secret + TTL

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

CORS policy

Allow only known frontend origins.

Primary production origin:
- https://grantpilot.ngoinfo.org

If staging exists:
- https://staging.grantpilot.ngoinfo.org (or explicit staging hostname)

Do not use wildcard CORS in production.

Cloudflare note:
- Cloudflare sits in front of the Railway frontend, but browser origin remains grantpilot.ngoinfo.org.
- CORS allowlist must match the browser origin, not the Railway service URL.


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

Cloudflare CDN hardening (frontend)

- Cache only safe, versioned static assets (e.g. /_next/static/*).
- Never cache:
  - /auth/*
  - /api/*
  - /dashboard/*
  - any route that renders user-specific content
- Ensure Cloudflare SSL mode is compatible with Railway TLS (avoid redirect loops).


Railway Frontend Service (Locked)

The GrantPilot frontend is deployed as a dedicated Railway service running a Next.js application using a Node runtime (not serverless, not edge-only). The service is responsible only for rendering UI and making authenticated API calls to the backend; it must not contain secrets, signing keys, or Stripe credentials. The frontend is exposed publicly via the canonical domain https://grantpilot.ngoinfo.org, with Cloudflare providing DNS, TLS, and caching strictly for static assets (e.g., /_next/static/*). All authenticated, user-specific, and API routes must bypass CDN caching. The frontend service does not perform business logic, entitlement checks, quota enforcement, or AI execution; the backend remains the single source of truth for all such concerns.


Rollback sequence


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

Auth flows verified: Google OAuth, Email Magic Link

Smoke tests pass on deployed environment

Logs show correlation IDs and no unhandled exceptions

Plan B is still reachable and functional

Definition of Done (Deployment)

Deployment is “Done” only when:

Service deploys reliably on Railway

Migrations are repeatable

All smoke flows pass on deployed build

Stripe + auth flows work without manual intervention

