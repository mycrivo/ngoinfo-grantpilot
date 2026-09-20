# Bugbot rules — GrantPilot backend

Report only issues that would matter in production. Skip style, formatting and naming unless a rule below says otherwise.

## Always check
- **Ownership.** Every route under `/api/reports`, `/api/grants` and `/api/report-templates` resolves the resource and checks it belongs to `current_user` before any read or write. Flag any handler that loads a resource by id without the ownership helper.
- **Entitlement.** Every M&E route is behind the IMPACT plan check. Flag a new M&E route that bypasses it.
- **Quota integrity.** Quota checks and decrements are transactional and idempotent; a failed or degraded job never consumes report quota. Flag any new charge path or any change to `REPORT_CREATE` / `REPORT_EXPORT` semantics.
- **Secrets and privacy.** No secret value, token, `DATABASE_URL`, source-document text, knowledge-bank content or report body in a log line, exception message, error `details` or test fixture committed to the repo. Flag `print`/`logger` calls that interpolate request bodies or JSONB payloads.
- **FK direction.** No core table (`users`, `proposals`, `ngo_profiles`, `funding_opportunities`, `usage_ledger`, …) gains a foreign key to an M&E table. M&E tables FK inward only.
- **Migrations.** Additive; nullable or defaulted; reversible; enum values added, never removed or renamed; CHECK constraints widened, never narrowed. Flag a migration without a working `downgrade`.
- **Contract drift.** A response schema field or enum value that is not in `docs/API_CONTRACT_ME_V2.md`, `docs/artefacts/API_CONTRACT.md` or `docs/artefacts/ENUM_REGISTRY.md`. A returned enum without its `_label` sibling.
- **Tests as ruler.** Any change to a file under `tests/contract/` in a PR that also changes non-test code. Any assertion loosened to match behaviour (a changed expected value, a removed assert, a broadened `pytest.raises`).
- **Kill switch.** Any change that makes M&E code run when `ME_MODULE_ENABLED` is off, or that lets core import from `app/reports`.
- **Concurrency and idempotency.** Job stages must remain resumable; a stage that re-runs must not duplicate facts, charges or exports.

## Never
- Do not flag date or number formatting in prose fixtures.
- Do not request comments, docstrings or type hints.
