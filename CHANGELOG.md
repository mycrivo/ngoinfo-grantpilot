Prompt 1 changes:
- Added FastAPI skeleton in `app/` (entrypoint, config validation, health route).
- Added dependency and runtime locks (`requirements.txt`, `runtime.txt`).
- Added guardrail docs (`BUILDLOG.md`, `CHANGELOG.md`, `RUNBOOK.md`, `DOC_GAP_REPORT.md`).
- Added repo hygiene file (`.gitignore`).

Prompt 2 changes:
- Added DB base/session modules and funding opportunity model.
- Added Alembic config, env wiring, and initial migration.
- Added DB dependencies to `requirements.txt`.
- Extended `RUNBOOK.md` with migration and DB check commands.

Prompt 3 changes:
- Added auth endpoints for Google OAuth, magic links, refresh, and logout.
- Added auth models and Alembic migration for users and tokens.
- Added JWT/token utilities, rate limiting, and validation error handling.
- Added auth dependencies to `requirements.txt`.
