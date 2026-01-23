## Local setup

1) Create and activate a virtual environment.
2) Install dependencies:
   - `python -m pip install -r requirements.txt`
3) Set required environment variables per `docs/artefacts/ENV_VARS_REFERENCE.md`.
4) Set `PORT` (Railway compatibility for local runs).

## Run the app locally

PowerShell example:
- `$env:PORT = "8000"`
- `python -m uvicorn app.main:app --host 0.0.0.0 --port $env:PORT`

## Call /health

- `GET http://localhost:8000/health`

Expected JSON fields:
- `status`, `service`, `version`, `time_utc`

## Validate config failure behavior

1) Unset any required env var (e.g., `AUTH_JWT_SIGNING_KEY`).
2) Start the app with uvicorn.
3) Confirm startup exits with a non-zero status and logs a `CONFIG_ERROR` line.

## Database migrations (Alembic)

1) Ensure `DATABASE_URL` is set.
2) Run migrations:
   - `alembic upgrade head`

## DB readiness check (manual)

- `python -c "from app.db.session import check_db_connection; raise SystemExit(check_db_connection() or 0)"`
