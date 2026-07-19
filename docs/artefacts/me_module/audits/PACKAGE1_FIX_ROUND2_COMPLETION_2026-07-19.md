# Package 1 — Fix round 2 completion (DF-1 / DF-2)

**Date:** 2026-07-19  
**Scope:** Backend PR #10 branch `feat/gate1-conflict-integrity` only. Frontend untouched.  
**STOP:** Pushed for delta re-audit #2 before merge.

## Before / after CI smoke counts

| Head | P0 unit smoke (CI) | Notes |
|------|--------------------|--------|
| `9316716` (fix round 1) | **269 passed / 25 skipped** | Async tests silently skipped — no `pytest-asyncio` in `requirements.txt` |
| This head (fix round 2) | See linked run below | Target: **0 async-plugin skips**; seam + FCDO gap gate executed |

Local verification of the same smoke selection after this change: **294 passed, 0 skipped** (1 unrelated `RuntimeWarning`).

## R1 (DF-1) — async tests execute in CI

- Added `pytest-asyncio==0.21.1` to `requirements.txt` (pin matches the locally verified environment that ran 294/0).
- `pytest.ini`: `asyncio_mode = auto`; `filterwarnings = error::pytest.PytestUnhandledCoroutineWarning` so an unhandled `async def` test **fails** rather than skips.
- No mass test rewrites; resurrected tests pass unmodified.

## R2 (DF-2) — `None` fact_key fails closed

- Both the repair loop and post-condition in `ensure_conflicts_materializable` raise `ValueError` for `None` / blank / whitespace keys.
- `test_blank_conflict_fact_key_fails_closed` now includes `None` alongside `""` and `"   "`.

## Dispositions (record only)

- **DF-3 accepted:** field-level diff omits a conflicts section; full preimage/postimage are embedded in dry-run evidence; `prepare_repair` STOPs if `resolved_value` changes on the target key.
- **Gate-integrity narrative:** appended to `ME_MODULE_DECISION_LOG.md` (no new D-number) — silent skip discovery, cause, history (`fcf35e5` / `bd72572` vs never-present plugin), restoration.

## Files touched this round

| File | Reason |
|------|--------|
| `requirements.txt` | Add `pytest-asyncio==0.21.1` |
| `pytest.ini` | `asyncio_mode = auto` + unhandled-coroutine → error |
| `app/reports/knowledge/conflict_integrity.py` | DF-2: `None` key fails closed in both loops |
| `tests/test_conflict_integrity.py` | DF-2: add `None` to blank-key test only |
| `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` | Gate-integrity narrative |
| `docs/artefacts/me_module/audits/PACKAGE1_FIX_ROUND2_COMPLETION_2026-07-19.md` | This note |

## CI evidence (fill after push)

- **Run URL:** _(filled after CI completes)_
- **Log lines proving execution** (seam + FCDO gap gate): _(quoted after CI completes)_
