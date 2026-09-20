---
name: grantpilot-package
description: How to run, test, migrate, guard and score a GrantPilot backend change. Use whenever a task needs the test suite, a migration, the funder-string guard, or the M&E harness.
---

# GrantPilot package workflow

## Environment
- Python venv at `.venv` (created by worktree setup). Activate before any command.
- `DATABASE_URL` points at a disposable Postgres database for this checkout (worktree setup names it after the worktree). Never point tests at a shared or production database.
- No model keys in this environment. Tests that would call a model must stub the model boundary.

## Run
| Step | Command |
|---|---|
| Install | `pip install -r requirements.txt` |
| Migrate up | `alembic upgrade head` |
| Prove down | `alembic downgrade -1` then `alembic upgrade head` (required in any PR that adds a migration) |
| Contract tests for a package | `pytest tests/contract/<ID>/ -q` |
| Whole suite | `pytest tests/ -q` |
| Guard (tree-wide) | `python scripts/governance/tree_audit.py` |
| Guard (staged) | `python scripts/governance/run_guards.py --staged --layer pre-commit --allow-env-override` |
| Harness export (CI-tier constructed) | `pytest tests/test_p0_bundle_export_scorecard.py -q` |
| Harness score (local bundle file only) | `python scripts/audit/scorecard_emit.py --bundle <path>` |

## Order of work for a package
1. Read `docs/packages/<ID>.md` and the contracts it names.
2. `pytest tests/contract/<ID>/ -q` — see what the ruler expects.
3. Implement inside the fence.
4. `pytest tests/ -q`; guard; migration up/down if applicable.
5. PR from the template. Say what was not done.

## Migration checklist
- Additive only; nullable or defaulted columns; CHECK constraints extended, never narrowed.
- Enum additions through `ENUM_REGISTRY.md` first.
- Backfill is a separate, idempotent, reversible step in the same revision.
- Runs from a clean DB and from the current production schema.

## Things that end a task early (stop and report)
- The spec conflicts with a contract.
- A needed change is outside the fence.
- A test under `tests/contract/` looks wrong.
- Verification needs a model, Railway, Stripe, storage or a production database.
