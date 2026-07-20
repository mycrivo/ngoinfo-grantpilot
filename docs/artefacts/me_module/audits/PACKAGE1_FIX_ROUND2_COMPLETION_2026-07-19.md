# Package 1 – Fix round 2 completion (DF-1 / DF-2)

**Date:** 2026-07-19  
**Scope:** Backend PR #10 branch `feat/gate1-conflict-integrity` only. Frontend untouched.  
**STOP:** Pushed for delta re-audit #2 before merge.

## Before / after CI smoke counts

| Head | P0 unit smoke (CI) | Notes |
|------|--------------------|--------|
| `9316716` (fix round 1) | **269 passed / 25 skipped** | Async tests silently skipped – no `pytest-asyncio` in `requirements.txt` |
| `655ea3c` (fix round 2 code) | **294 passed / 0 skipped** | Run https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/29694314799 – log line: `294 passed, 2 warnings in 36.57s` (no `skipped`) |
| `63661e7` (verbose proof step) | **294 passed / 0 skipped** | Run https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/29694530257 – P0: `294 passed, 2 warnings in 37.45s`; named async gate step quotes PASSED lines below |

Local verification of the same smoke selection after this change: **294 passed, 0 skipped**.

## R1 (DF-1) – async tests execute in CI

- Added `pytest-asyncio==0.21.1` to `requirements.txt` (pin matches the locally verified environment that ran 294/0).
- `pytest.ini`: `asyncio_mode = auto`; `filterwarnings = error::pytest.PytestUnhandledCoroutineWarning` so an unhandled `async def` test **fails** rather than skips.
- No mass test rewrites; resurrected tests pass unmodified.
- Workflow adds a short verbose step that re-runs the seam test and FCDO gap gate by node id so acceptance can quote PASSED lines (main selection remains `-q`).

## R2 (DF-2) – `None` fact_key fails closed

- Both the repair loop and post-condition in `ensure_conflicts_materializable` raise `ValueError` for `None` / blank / whitespace keys.
- `test_blank_conflict_fact_key_fails_closed` now includes `None` alongside `""` and `"   "`.

## Dispositions (record only)

- **DF-3 accepted:** field-level diff omits a conflicts section; full preimage/postimage are embedded in dry-run evidence; `prepare_repair` STOPs if `resolved_value` changes on the target key.
- **Gate-integrity narrative:** appended to `ME_MODULE_DECISION_LOG.md` (no new D-number) – silent skip discovery, cause, history (`fcf35e5` / `bd72572` vs never-present plugin), restoration.

## CI evidence – `655ea3c` / run 29694314799

Summary line (P0 unit smoke step):

```text
294 passed, 2 warnings in 36.57s
```

Zero `skipped` in that summary (was 25 on `9316716`). The main step uses `-q`, so per-test names are not printed there.

## CI evidence – `63661e7` / run 29694530257

P0 unit smoke summary:

```text
294 passed, 2 warnings in 37.45s
```

Prove async gate tests execute (verbose step):

```text
tests/test_conflict_integrity.py::test_reconcile_and_persist_normalizes_orphan_at_seam PASSED [ 50%]
tests/test_gap_compliance_agent.py::test_fcdo_complete_distilled_gap_set_exact PASSED [100%]
```

## Files touched this round

| File | Reason |
|------|--------|
| `requirements.txt` | Add `pytest-asyncio==0.21.1` |
| `pytest.ini` | `asyncio_mode = auto` + unhandled-coroutine → error |
| `app/reports/knowledge/conflict_integrity.py` | DF-2: `None` key fails closed in both loops |
| `tests/test_conflict_integrity.py` | DF-2: add `None` to blank-key test only |
| `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` | Gate-integrity narrative |
| `.github/workflows/smoke-test.yml` | Verbose proof step for named async gate tests |
| `docs/artefacts/me_module/audits/PACKAGE1_FIX_ROUND2_COMPLETION_2026-07-19.md` | This note |

## Note on commit `655ea3c` message

A Cursor/Git trailer hook emptied the subject of `655ea3c` to a bare `Co-authored-by:` line after push. The tree content of that commit is the DF-1/DF-2 product change; this follow-up commit carries the intended messaging and the verbose CI proof step. No force-push/amend.