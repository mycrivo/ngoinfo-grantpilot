Status: Canonical (LOCKED FOR BUILD)
Scope: Backend repo structure & engineering patterns for Cursor-guided development

============================================================
1) Goals
============================================================

- Predictable structure so Cursor does not invent new patterns per feature.
- Keep business logic out of route handlers.
- Ensure consistent DB session handling, auth, and error contracts.

============================================================
2) Recommended Folder Structure (FastAPI)
============================================================

app/
  main.py                  # app creation, middleware, exception handlers
  api/
    routes/                # route modules grouped by domain
    dependencies/          # auth dependencies, db session dependency, common guards
  core/
    config.py              # settings/env
    security.py            # JWT helpers, hashing utilities
    rate_limit.py          # rate limiting utilities
    errors.py              # domain error classes + mapping to API envelope
    logging.py             # request_id/correlation helpers
  db/
    session.py             # engine + session factory + request-scoped session dependency
    migrations/            # alembic (or top-level alembic/ if already used)
  models/
    user.py
    auth_refresh_token.py
    auth_magic_link_token.py
    ngo_profile.py
    ...                    # SQLAlchemy models only
  schemas/
    user.py                # Pydantic request/response schemas
    ngo_profile.py
    ...
  services/
    auth_service.py
    profile_service.py
    quota_service.py
    email_service.py
    ...
  repositories/            # optional; only if you want explicit DB access layer
  utils/                   # small shared utilities

Note:
- If your repo already has a slightly different structure, keep it—just enforce consistency.

============================================================
3) Service Layer Rules
============================================================

- Route handlers:
  - validate inputs (Pydantic)
  - call service functions
  - return API envelope responses
- Services:
  - enforce business rules (completeness, entitlements, quotas)
  - own transactions (commit/rollback)
  - raise domain errors (not HTTP exceptions)
- Models:
  - no business logic beyond simple computed helpers

============================================================
4) DB Session Lifecycle
============================================================

- Use a request-scoped session dependency everywhere.
- Do not create ad-hoc sessions inside services unless explicitly required.
- Transactions:
  - service layer should group changes into a single transaction per user action.
  - quota checks + decrements must be atomic and transactional.

============================================================
5) Authorization Pattern
============================================================

- Authentication dependency yields current_user (users row).
- Resource ownership checks must be centralized helpers:
  - e.g., require_profile_owner(current_user, profile.user_id)
- Plan/entitlement checks must go through a single service/hook (even if stubbed initially).

============================================================
6) Error Contract Pattern
============================================================

- All non-validation errors must map to API_CONTRACT.md envelope:
  - success=false
  - error.code (stable machine code)
  - error.message (human readable)
  - error.details (optional structured)
  - request_id (if available)

- Prefer domain errors:
  - ProfileIncompleteError
  - QuotaExceededError
  - ForbiddenResourceError
  - NotFoundError
  - ExternalServiceError (Stripe/Email provider)

============================================================
7) Naming & Conventions
============================================================

- snake_case for JSON fields unless frontend contract differs.
- Table names: plural snake_case (users, ngo_profiles, funding_opportunities)
- Columns: snake_case
- Avoid abbreviations that reduce clarity.

============================================================
8) “Do Not Do” List
============================================================

- Do not edit old Alembic migrations. Always create a new one.
- Do not introduce a second error envelope.
- Do not put business logic in route handlers.
- Do not bypass quota checks in services that consume quota.
