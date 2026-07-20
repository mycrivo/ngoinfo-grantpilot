# Package 1 — Fix round completion (audit F1/F2/F3/F5/F9)

**Date:** 2026-07-19  
**Scope:** Backend PR #10 branch `feat/gate1-conflict-integrity` only. Frontend untouched.  
**STOP:** Pushed for delta re-audit before merge.

## Zero CI checks on `46157ab` (R5 / F9)

**Cause:** `.github/workflows/smoke-test.yml` triggered only on `push` to `main`, `workflow_dispatch`, and a cron schedule — **no `pull_request` trigger**. PR head commits never started the Smoke Test workflow, so `get_status` reported 0 checks.

**Remediation:** Added `pull_request: branches: [main]`. Live HTTP smoke + Track B + Slack alert remain gated to non-PR events (secrets / production probe). PR CI runs unit Smoke P0 + hard_red + offline replay.

## R3 red-run witness (seam wiring)

1. Temporarily assigned `report.knowledge_bank_json = kb` without `ensure_conflicts_materializable` in `knowledge_bank_reconciliation_service.reconcile_and_persist`.
2. Ran `pytest tests/test_conflict_integrity.py::test_reconcile_and_persist_normalizes_orphan_at_seam -q --tb=line`
3. **Result (RED):** `FAILED` — `KeyError: 'reporting_period.end'` at the stub assertion (line ~267).
4. Immediately restored the normalizer call; re-ran the same test — **PASSED**.
5. No detached seam left in the tree.

## Owner dispositions (record only — no new decision-log IDs)

- **F4 accepted:** normalized equality is the intended meaning of “same value” for sibling marking; conservative failure direction remains binding.
- **F6 accepted:** WARNING log is the operative frequency signal; trace in `knowledge_bank_json.agent_trace.conflict_integrity_repairs` matches committed decision text. **Note for inspection tooling:** these events are not written to `report_jobs.agent_trace_json`.
- **F7 accepted:** Phase A→B ordering is procedural (owner authorization); blast radius bounded by constant report id.
- **F8 accepted:** synthetic `source_document_id` token is internal-only; user-facing field is `source_label`.
- **Environment note accepted:** flaky `test_outcome_1_concurrent_claim_only_one_wins` is pre-existing, outside smoke, untouched — queued for housekeeping package.

## Files touched this round

| File | Reason |
|------|--------|
| `scripts/audit/gate1_orphan_repair_cb090edb.py` | R1 full postimage + field-level diff; R2 `--approved-preimage-sha256` apply anchor |
| `app/reports/knowledge/conflict_integrity.py` | R4 blank `fact_key` fails closed |
| `tests/test_conflict_integrity.py` | R3 seam test; R4 blank-key test |
| `tests/test_gate1_orphan_repair_evidence.py` | R1/R2 helper coverage (diff + prepare never resolves) |
| `.github/workflows/smoke-test.yml` | R5 `pull_request` trigger; skip live smoke on PR; include new evidence tests |
| `docs/artefacts/me_module/audits/PACKAGE1_FIX_ROUND_COMPLETION_2026-07-19.md` | This completion note |

## Tests touched / added

| Test | Reason |
|------|--------|
| `test_reconcile_and_persist_normalizes_orphan_at_seam` | **Added** — R3 seam wiring regression |
| `test_blank_conflict_fact_key_fails_closed` | **Added** — R4 empty/whitespace keys |
| `test_field_level_diff_includes_stub_and_provenance_markers` | **Added** — R1 evidence shape |
| `test_prepare_repair_never_writes_resolved_value` | **Added** — repair path invents neither value nor resolution |
| All prior Package 1 tests | **Unchanged** — no deletions, skips, or weakened assertions |

## Verification

- Smoke P0 (workflow selection + new evidence file): **294 passed** locally.
- R3 red-run recorded above; seam restored.
- Invariants preserved: no reconciler/grader/migration/auth changes; missing-fact guard untouched; repair cannot write `resolved_value`.
