# P3-6 package report — Reliability tidy

**Package:** P3-6  
**Status:** Shipped (pending CI run ID after push)  
**Plan:** Phase 3 Plan v2 · F-26, F-6, F-5

## Shipped

| Item | Change |
|------|--------|
| F-26 R2 delete ordering | `delete_document` — DB row delete + commit **before** storage delete; `DocumentStorageError` fail-loud → `DOCUMENT_STORAGE_DELETE_FAILED` |
| Export orphan cleanup | `export_and_persist` — delete prior `content_json.export.storage_ref` after successful upload; fail loud on cleanup error |
| F-6 ledger index | Migration `0017_usage_ledger_idempotency_unique` — unique `(user_id, action_type, idempotency_key)` |
| F-5 synthesis lock | `pg_advisory_xact_lock` on `donor_report_id` at `synthesise_and_persist` entry (PostgreSQL only; no-op on SQLite tests) |
| Tests | `tests/test_p3_6_reliability.py` — delete ordering, storage fail-loud, lock content-unchanged proof |

## Fence judgments

- Advisory lock is transaction-scoped; SQLite test path unchanged
- DB-first delete may leave orphan R2 object on storage failure (acceptable vs dangling DB ref)

## Exit checkpoint

- Local: `pytest tests/test_p3_6_reliability.py tests/test_report_lifecycle_routes.py -k delete_document tests/test_report_synthesis_service.py::test_synthesis_persists_all_fcdo_sections -q`
- CI run ID: _(pending push)_
