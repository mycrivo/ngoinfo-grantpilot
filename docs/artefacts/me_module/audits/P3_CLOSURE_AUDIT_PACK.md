# P3 closure audit pack (Phase A — read-only)

**Date:** 2026-06-11  
**Authority:** Owner prompt supersedes pack wording on agent-as-hands; conflict rule satisfied by owner authority note.  
**HEAD (repo):** `ffbd86c8886cfb08463e518d268a250a7eec6c11`  
**Scope:** Facts and verbatim extracts only. No owner verdicts.

---

## NO-GO conditions (owner checklist vs repo/CI/prod facts)

| # | Condition | Hold? | Evidence |
|---|-----------|-------|----------|
| 1 | All seven locked positives present in gate list (incl. explicit forbidden refs `review_summary_sheet` + `outcome_assessment`, RSS/OA, funder/narrative zero, FCDO 6/6, NLCF unchanged, charge-once, honest exit) | **YES — hold** | Seven gate *names* present in `tests/test_p3_eval_harness.py`. `G-forbidden` asserts `forbidden_rss_oa == 0`, `funder_owned == 0`, `narrative_data == 0` only — does **not** name `review_summary_sheet` or `outcome_assessment` explicitly. `FCDO_FORBIDDEN_GAP_REFS` in `app/reports/eval/output_rubric.py` lists only `outcome_indicators`, `progress_against_expected_results`. `fcdo_incomplete_answer_key.json` lists `review_summary_sheet` and `outcome_assessment` under `forbidden_gaps` but harness does not import that key. |
| 2 | `hard_red` / harness in **blocking** CI path on `main` | **YES — hold** | `smoke-test.yml` includes `tests/test_p3_eval_harness.py` (blocking). `@pytest.mark.hard_red` tests live in `tests/test_p3_4_output_quality.py` only — **not** referenced in `smoke-test.yml` or `p3-offline-replay.yml`. |
| 3 | Missing alembic scratch-Postgres upgrade evidence | **NO — hold cleared** | Run [27343602374](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27343602374) job `alembic-upgrade` completed; log excerpt in A5. |
| 4 | Decision-log entry missing either supersession (reaper-D4 + D3 Route A) | **NO — hold cleared** | Verbatim entries in A6. |
| 5 | Gate3 fix touched app code without fence note | **YES — hold** | `app/services/quota_service.py` changed in `bd72572` (explicit `created_at`/`updated_at` on `UserPlan` insert). `P3_1_PACKAGE_REPORT.md` documents gate3/quota fixes but contains no dedicated fence note separating app-code vs test-seed changes. |
| 6 | Dirty working tree | **YES — hold** | `git status -sb` on 2026-06-11: `main...origin/main` with **no tracked modifications**; **32+ untracked paths** including `docs/artefacts/me_module/audits/dynamic_run/**`, `me_capture/`, throwaway scripts, sample PDF. |
| 7 | Prod running pre-P3 code with no upgrade path | **NO — hold cleared** | API deployment `ba60be38` logs show alembic upgrades through `0018_usage_ledger_uq`; prod DB probe (A8) confirms same revision. |

**Phase A stop:** Four holds active (rows 1, 2, 5, 6). Owner review required before `GO PHASE B`.

---

## A1 — Commit log `ab66dd9..bd72572` + package mapping

```
bd72572 Phase 3 P3-1..P3-6: eval harness, worker recovery, cost truth, quality, contract, reliability.
```

| Commit | Package(s) | Notes |
|--------|------------|-------|
| `ab66dd9` | P3-0 (baseline) | P2-CORRECTIONS closure — **range start, not included in log above** |
| `bd72572` | P3-1, P3-2, P3-3, P3-4, P3-5, P3-6 | Single combined commit (70 files) |

**Post-range commits on `main` (after `bd72572`):**

| Commit | Scope |
|--------|-------|
| `f608e32` | Docs: CI run IDs in phase exit pack |
| `ffbd86c` | Alembic revision ID shorten (`0018_usage_ledger_uq`) — **current HEAD** |

---

## A2 — CP-1 verbatim facts (from `P3_0_BASELINE_AUDIT.md` + gate3 delta)

### Baseline-green answer (clean `b20b27a`)

Verbatim from audit §2.1:

> **CI evidence:** Run [27333324256](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27333324256) — **success** on `headSha=b20b27a`, 2026-06-11T08:13:03Z (workflow_dispatch post-adjudication commit).
>
> **Local evidence (detached worktree at `b20b27a`):** … → **67 passed**, 1 warning
>
> **Conclusion:** **Yes** — clean `b20b27a` passes the smoke-test.yml graded suite.

P3-0 closure CI after land: run [27341189633](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27341189633) on push of `ab66dd9`.

### Per-delta disposition table (summary pointer)

Full 21-row content-modified table + 67-row untracked grouping: `docs/artefacts/me_module/audits/P3_0_BASELINE_AUDIT.md` §1.2–1.3. Disposition at CP-1: land gap moat + 21 content files in `ab66dd9`; do not commit `dynamic_run/` bulk, `me_capture/`, throwaway scripts.

### Flake identity (gate3)

Verbatim from audit §3.1 / §2.2:

> `test_gate3_resume_does_not_re_run_critic` fails **3/3** runs at baseline and current; … **Consistent fail, not flake locally**

Reclassified in Plan v2 P3-1 as fail-at-both; fixed in `bd72572` (now in blocking smoke path).

### Gate3 fix — app code vs test seeding

| File | Layer |
|------|-------|
| `app/services/quota_service.py` | **Application code** — `get_or_create_user_plan` sets explicit `created_at` / `updated_at` on insert |
| `tests/worker_validation_seed.py` | **Test seeding** — `seed_user_plan(PLAN_IMPACT)` in `seed_orchestrator_fixture`; `requeue_count=0` on job seeds |

No other application files changed solely for gate3 in `bd72572` diff for quota/gate3 path.

---

## A3 — Seven named gates: name + literal assertion line

Source: `tests/test_p3_eval_harness.py`

| Gate | Test | Literal assertion line(s) |
|------|------|----------------------------|
| G-degrade-leak | `test_g_degrade_leak_zero_on_clean` | `assert result.summary["degraded_pass_through"] == 0` |
| G-faithfulness | `test_g_faithfulness_zero_unmatched_on_clean` | `assert result.summary["faithfulness.unmatched_numbers"] == 0` |
| G-fcdo-gap-exact | `test_g_fcdo_gap_exact_two_ref` | `assert set(result.summary["gap_refs"]) == set(FCDO_COMPLETE_GAP_REFS)` where `FCDO_COMPLETE_GAP_REFS = frozenset({"logframe_row:op2_3", "logframe_row:op4_2"})` |
| G-forbidden | `test_g_forbidden_no_rss_oa_funder_narrative` | `assert result.summary["forbidden_rss_oa"] == 0`; `assert result.summary["funder_owned"] == 0`; `assert result.summary["narrative_data"] == 0` |
| G-section-count | `test_g_section_count_fcdo_six` / `test_g_section_count_nlcf_unchanged` | FCDO: `assert result.summary["generated_ngo_sections"] == FCDO_NGO_SECTION_COUNT` (6). NLCF: `assert result.passed` with `expected_count=len(visible)` |
| G-charge-once | `test_g_charge_once_export_idempotent` | `assert len(rows) == 1` on `UsageLedger` rows for `report_create_idempotency_key(report_id)` |
| G-honest-exit | `test_g_honest_exit_passing_verdicts` / `test_g_honest_exit_failing_verdicts` | Passing: `assert exit_code_for_verdict(verdict) == 0`. Failing: `assert exit_code_for_verdict(verdict) == 1` |

Supporting gate implementation constants: `app/reports/eval/gates.py` lines 19–20.

---

## A4 — Workflow proof

### `smoke-test.yml` diff (`ab66dd9` → `bd72572`) — harness in blocking path

```diff
-        run: pytest ... tests/test_full_walk_exit_codes.py -q
+        run: pytest ... tests/test_full_walk_exit_codes.py tests/test_p3_eval_harness.py tests/test_gap_compliance_agent.py::test_fcdo_complete_distilled_gap_set_exact tests/test_orchestrator_critique.py::test_gate3_resume_does_not_re_run_critic -q
+      - name: P3-1 offline replay (fixture)
+        run: python scripts/audit/offline_replay.py --fixture
```

Step `Run P0 M&E unit smoke` has no `continue-on-error: true` → **blocking**.

`hard_red`: **not** in this workflow (see NO-GO #2).

### `p3-offline-replay.yml` (added `bd72572`) — blocking jobs

- Job `alembic-upgrade`: `alembic upgrade head` on scratch Postgres 15 service — blocking.
- Job `offline-replay`: `pytest tests/test_p3_eval_harness.py -q`; offline replay CLI; honest exit probe — all blocking (no `continue-on-error`).

Triggers: `push` to `main`, `schedule` (`0 */6 * * *`), `workflow_dispatch`.

### `p0-audit-walk.yml` — live walk dispatch-only

Verbatim trigger block:

```yaml
on:
  workflow_dispatch:
```

`bd72572` added to first live walk step:

```diff
           python scripts/audit/full_walk.py | tee .../p1_clean_docset.log
+          test "${PIPESTATUS[0]}" -eq 0
```

---

## A5 — Migrations 0017 / 0018 scratch-Postgres evidence

**CI run:** [27343602374](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27343602374) (`ffbd86c`, workflow `P3 Offline Replay`, job `alembic-upgrade`, conclusion `completed`).

Verbatim log tail:

```
INFO  [alembic.runtime.migration] Running upgrade 0016_updated_at_trigger -> 0017_report_jobs_worker_recovery, P3-2 worker recovery columns on report_jobs.
INFO  [alembic.runtime.migration] Running upgrade 0017_report_jobs_worker_recovery -> 0018_usage_ledger_uq, Composite unique index on usage_ledger idempotency (F-6).
```

---

## A6 — Decision-log entry (verbatim)

From `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md`:

```
DECISION (2026-06-11) — P3-2 worker recovery (supersedes reaper D3 Route A + D4).
Context: Phase 3 Plan v2 · [`P3_2_DECISION_LOG.md`](audits/P3_2_DECISION_LOG.md); diagnosis [`P3_2_EXTRACT_HANG_DIAGNOSIS.md`](audits/P3_2_EXTRACT_HANG_DIAGNOSIS.md).

1. Migration 0017: `last_heartbeat_at`, `lease_owner`, `lease_expires_at`, `requeue_count` on `report_jobs`.
2. Heartbeat on claim, stage entry, per-document classify/extract, checkpoints; reaper prefers heartbeat over stage `completed_at`.
3. Requeue bound 1 (0→1) then terminal `orphan_reaped`; degraded jobs never requeued; stage-boundary restart only.
4. F-11 unified timeout via `job_timeout.py` (stage-aware budget + shared failure path).
5. Supersedes prior D3 Route A (no migration) and D4 (fail-only); does not change stage-D4 indicator extractor degrade.
```

Superseded prior entry (still in log, marked superseded):

```
DECISION (2026-06-08) — P3 orphan reaper (D3 Route A, D4).
...
3. Recovery via existing `mark_job_failed` with `failure.event = orphan_reaped` — same refund/UX as other failures; no requeue.
```

Extended narrative: `docs/artefacts/me_module/audits/P3_2_DECISION_LOG.md`.

---

## A7 — NLCF golden proposal (CP-2)

Source: `docs/artefacts/me_module/audits/P3_1_NLCF_GOLDEN_PROPOSAL.md` + walk `walk_nlcf_gen_e7fa9bee.json`.

| Field | Value |
|-------|-------|
| Walk run label | `nlcf_gen` |
| Report ID | `e7fa9bee-4b05-4e5b-bdd4-17dfedaaa0a5` |
| Verdict | `stopped_at_gate2` |
| Gap count (walk extra) | `"gaps": 18` |
| Proposed section count (template) | **6** visible NGO sections (`project_story`, `community_involvement`, `difference_made`, `learning`, `changes_and_next_steps`, `spend_summary`) |
| Proposed gap exact set | **TBD — owner ratification** (not adjudicated) |

**18 `required_item_ref` values from walk `after_gap.gap_analysis_json.gaps`:**

1. `community_participation_examples`  
2. `partner_or_local_collaboration_examples`  
3. `beneficiary_numbers`  
4. `community_feedback`  
5. `staff_or_volunteer_feedback`  
6. `outcome_indicators_where_available`  
7. `what_worked`  
8. `what_did_not_work`  
9. `unexpected_findings`  
10. `learning_useful_to_others`  
11. `changes_made`  
12. `planned_changes`  
13. `support_needed`  
14. `budgeted_total`  
15. `actual_spend_total`  
16. `revenue_cost_variance`  
17. `capital_cost_variance`  
18. `budget_vs_actual`  

Artefact path (untracked local): `docs/artefacts/me_module/audits/dynamic_run/walk_nlcf_gen_e7fa9bee.json`.

---

## A8 — Prod deploy state (read-only)

### Railway services (2026-06-11)

| Service | Status | Deployment ID | Repo |
|---------|--------|---------------|------|
| `ngoinfo-grantpilot` (API) | Online | `ba60be38-c540-4d1c-997e-bf17ecde5ed9` | `mycrivo/ngoinfo-grantpilot` |
| `exemplary-encouragement` (worker) | Online | `d884aaef-9f8c-4dce-85c6-655c39147127` | `mycrivo/ngoinfo-grantpilot` |
| `Postgres` | Online | `1045bb0d-0ade-4354-bd00-c116ec50ea49` | template image |

API URL: `https://ngoinfo-grantpilot-production.up.railway.app`  
Health probe response (2026-06-11T12:32:17Z):

```json
{"status":"ok","service":"grantpilot","version":"v1.0.0","time_utc":"2026-06-11T12:32:17.431634+00:00"}
```

### API container startup — alembic on deploy (`ba60be38`)

Verbatim:

```
INFO  [alembic.runtime.migration] Running upgrade 0016_updated_at_trigger -> 0017_report_jobs_worker_recovery, P3-2 worker recovery columns on report_jobs.
INFO  [alembic.runtime.migration] Running upgrade 0017_report_jobs_worker_recovery -> 0018_usage_ledger_uq, Composite unique index on usage_ledger idempotency (F-6).
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Prod database alembic + schema probe (read-only SQL)

```
alembic_version.version_num='0018_usage_ledger_uq'
report_jobs_p3_columns=['last_heartbeat_at', 'lease_expires_at', 'lease_owner', 'requeue_count']
usage_ledger_uq_index_present=True
```

**B2 implication:** Migrations 0017/0018 already applied on prod at audit time — B2 alembic step would be verify-only unless drift detected.

Failed deploys immediately prior (Railway): `b1bdcab2`, `493f45c7` (2026-06-11 ~11:58) — long revision ID crash per owner diagnosis; resolved by `ffbd86c`.

---

## A9 — In-flight exposure (FCDO template `55f891ac-bb8b-4137-bc42-6de8ff935064`)

Scope: non-terminal `report_jobs` (`status NOT IN ('done','failed')`) for reports bound to FCDO template row.

```
in_flight_non_terminal_by_status=[
  {"report_status": "DRAFT", "job_status": "awaiting_human", "n": 8},
  {"report_status": "DEGRADED", "job_status": "awaiting_human", "n": 7},
  {"report_status": "COMPLETE", "job_status": "awaiting_human", "n": 1}
]
in_flight_distinct_reports=16
in_flight_jobs=16
```

---

## A10 — Working tree vs `main`

```
## main...origin/main
```

No staged or modified **tracked** files at audit time.

Untracked paths present (partial list): `docs/artefacts/me_module/audits/dynamic_run/**`, `me_capture/**`, `scripts/_check_report_status.py`, `scripts/_poll_report_job.py`, `M_E_Module/Sample_docs/.../02_FCDO_BridgeLight_Award_Letter.pdf`, `docs/artefacts/me_module/audits/P2_CORRECTIONS_FINDINGS.md`.

**Tracked branch matches `origin/main` at `ffbd86c`; working tree is not clean due to untracked files.**

---

## Phase A stop

Owner review required. Reply with:

```
GO PHASE B
NLCF RATIFIED: <gap set / section count>
```

(or amendments to close NO-GO holds 1, 2, 5, 6 before mutation).

**No Phase B actions executed in this session.**
