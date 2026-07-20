# DELTA RE-AUDIT #2 — Package 1 backend (PR #10, `9316716` → head `340cc7f`)

**Date:** 2026-07-19
**Auditor role:** Independent read-only auditor (Layer 2 merge gate). Findings only; no fixes, no product commits.
**Scope:** `mycrivo/ngoinfo-grantpilot` PR #10 (`feat/gate1-conflict-integrity`), commits after `9316716` through head `340cc7f`:

| Commit | Subject | Content |
|--------|---------|---------|
| `655ea3c` | *(malformed: bare `Co-authored-by:`)* | DF-1/DF-2 fix + governance records |
| `63661e7` | fix(me): Package 1 fix round 2 CI evidence for async gate tests | Verbose CI proof step + completion-doc evidence |
| `340cc7f` | docs(me): quote fix round 2 CI PASSED lines | Docs only |

**Method:** every commit in the range read in full; the final head's actual CI job logs pulled and inspected directly (not the builder's quotes); ERROR-not-skip behavior, the None-key fail-closed path, and the moat probes verified empirically in a scratch worktree; byte-identity checks on all invariant surfaces and all resurrected tests. Scratch worktrees removed; nothing modified or committed to the PR branch.

---

## VERDICT: **APPROVE** (this delta round)

DF-1 and DF-2 are verified closed with direct evidence from the final head's own CI run; commit `655ea3c` carries nothing beyond the DF-1/DF-2 fix and its governance records; no invariant regressed. Two non-blocking notes below.

---

## DF-1 — CLOSED in the gate that matters

The final head `340cc7f` has exactly one check run — job `88213240664` on run `29694668632`, conclusion **success**, started 2026-07-19T16:20:40Z immediately after the head was pushed. The auditor pulled that run's own logs and confirmed all three required facts **in that run** (not only in the intermediate runs the completion doc quotes):

1. **Full smoke selection: `294 passed, 2 warnings in 37.16s` — zero skipped.** The two warnings are the pre-existing fastapi testclient deprecation and a pre-existing never-awaited-coroutine `RuntimeWarning` inside a mock — warnings, not skips. (Baseline on `9316716`: 269 passed / 25 skipped.) The install step shows `Successfully installed … pytest-asyncio-0.21.1`.
2. **Both named tests visibly executed and passed on that head**, in the new verbose proof step, which reports `plugins: … asyncio-0.21.1 …` and `asyncio: mode=Mode.AUTO`, then:

   ```text
   tests/test_conflict_integrity.py::test_reconcile_and_persist_normalizes_orphan_at_seam PASSED [ 50%]
   tests/test_gap_compliance_agent.py::test_fcdo_complete_distilled_gap_set_exact PASSED [100%]
   ```

   The hard_red gates (2 passed) and offline replay (all gates passed, including `G-fcdo-gap-exact`) also ran green in the same job.
3. **The configuration genuinely makes unhandled async tests error rather than skip.** Empirical check at `340cc7f`: running the seam test with the asyncio plugin disabled (`-p no:asyncio`) produces **FAILED**, not SKIPPED — `pytest.ini`'s `filterwarnings = error::pytest.PytestUnhandledCoroutineWarning` converts the old silent skip into a red gate. The blind-spot failure mode cannot silently recur.

Auditor's local run of the identical smoke selection at `340cc7f`: 294 passed / 0 skipped — matches CI.

## DF-2 — CLOSED

Both loops in `ensure_conflicts_materializable` now share the merged condition `raw_key is None or not isinstance(raw_key, str) or not raw_key.strip()` → `ValueError` (`app/reports/knowledge/conflict_integrity.py`, repair loop and post-condition). Auditor probes: a literal-`None` key raises fail-closed in the repair loop and in a mixed KB (one valid conflict + one None-key conflict); empty-string and whitespace keys still raise. `test_blank_conflict_fact_key_fails_closed` now includes `None` alongside `""` and `"   "` and runs inside the CI smoke selection (all 8 tests in the file pass at head).

## Diff purity and commit `655ea3c`

- **tests/ across the whole range:** exactly one change — the blank-key test's docstring and the addition of `None` to its parameter tuple (4 lines). Nothing else.
- **The 25 resurrected tests are byte-unmodified:** explicit diff over `test_classify_isolation.py`, `test_proposal_extractor_agent.py`, `test_gap_compliance_agent.py`, and every other Package 1 test file is empty. They pass unmodified now that they run.
- **`655ea3c` tree isolation confirmed:** its changes are precisely the DF-1/DF-2 fix and its governance records — `requirements.txt` (+`pytest-asyncio==0.21.1`), `pytest.ini` (+`asyncio_mode = auto`, +unhandled-coroutine→error), `conflict_integrity.py` (None-key merge), the one test change, the decision-log narrative, and the completion doc. Nothing else rides in it.
- `63661e7` adds only the additive, blocking verbose proof step (two named node ids, `-v`, no secrets, runs in PR context) plus completion-doc evidence; `340cc7f` is docs-only.

## No invariant regressed

- `git diff 9316716..340cc7f` over `app/reports/services/knowledge_bank_patch_service.py`, `scripts/audit/`, `app/reports/knowledge/confirmed_kb.py`, `app/reports/export/docx_renderer.py`, and `app/reports/schemas/` is **zero lines**.
- The patch service is zero-diff all the way back to `46157ab`, so the `KB_PATCH_VALIDATION_FAILED` missing-fact guard remains byte-identical to the version certified in the original audit.
- The repair script is untouched this round — `prepare_repair`'s invented-value/`resolved_value` STOPs stand, and `test_prepare_repair_never_writes_resolved_value` executes in the CI selection. Repair still cannot write values.
- Sibling-marking probes at the final head produce identical results to prior rounds: source-mismatch → NOT marked; ambiguous double-match → NOT marked; normalized-representation variant → marked (per the owner-accepted F4 disposition); whitespace/empty/None keys → `ValueError`.

## Governance

The gate-integrity narrative is appended to `ME_MODULE_DECISION_LOG.md` (no new D-number): discovery with the audited 269/25 numbers, cause (`requirements.txt` never contained an async plugin), history — naming `fcf35e5` and `bd72572`, both of which exist and match their described roles — and the restoration, ending in a STOP. DF-3's accepted disposition is recorded in `PACKAGE1_FIX_ROUND2_COMPLETION_2026-07-19.md`. The completion doc's CI-evidence quotes cover the two intermediate runs (`29694314799`, `29694530257`); the auditor did not independently pull those, but the final-head run pulled directly supersedes them and satisfies the acceptance criteria on its own.

## Non-blocking notes

1. **`655ea3c` has a malformed commit subject** (bare `Co-authored-by:` — a trailer hook ate the intended message). Cosmetic; documented by the builder in the completion doc, and pushed history was correctly not rewritten. The tree content is exactly the fix.
2. **`asyncio_mode = auto` resurrects async tests suite-wide, beyond the gate selection.** Supplementary full-suite sweep at `340cc7f`: 651 passed (up from 565 at `46157ab` in the same environment — roughly 86 resurrected), with one new local-only failure (`test_indicator_data_extractor_agent.py::test_unparseable_docx_from_path_returns_degraded_no_raise`) caused solely by docling being absent from the auditor's slim venv (`ModuleNotFoundError`); CI installs docling and the file is outside the gate selection. The known pre-existing flaky worker test behaved as before. No regression attributable to this round.

---

## Disposition

- **Backend PR #10 delta round 2: APPROVE.** DF-1 and DF-2 closed with head-run CI evidence; diff purity and invariants verified.
- Standing reminder from the original audit, outside this brief's scope: **frontend PR #3 remains unaudited and ungated** — it still needs its own audit session before the package merges as a pair.

**STOP.** Findings only; nothing modified or committed on the PR branch.
