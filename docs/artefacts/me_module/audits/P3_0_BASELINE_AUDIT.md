# P3-0 — Baseline audit (read-only)

**Date:** 2026-06-11  
**Baseline commit:** `b20b27a` — `P2-ADJUDICATION: cement 2-ref gap set, FCDO section count 6, P3-6 debt.`  
**HEAD:** `b20b27a` (same; uncommitted working-tree deltas only)  
**Scope:** Read-only inventory + local pytest observation. No dispositions executed.

---

## Executive summary

| Question | Answer |
|----------|--------|
| Is `b20b27a` green on smoke-test.yml suite? | **Yes** — CI run [27333324256](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27333324256) success; local worktree replay **67 passed** |
| Does local tree match `b20b27a` content? | **No** — 21 tracked files with real content delta + 67 untracked paths; 41 tracked files show `M` but **byte-identical to HEAD** (stat phantom) |
| Is P2 gap exact-set test green at `b20b27a` alone? | **No** — requires uncommitted gap-moat code |
| Is the registered “flaky” test actually flaky? | **No local evidence** — `test_gate3_resume_does_not_re_run_critic` fails **3/3** runs at baseline and current; `test_gate1_confirm_endpoint_404_when_module_disabled` passes consistently |
| May P3-1 start? | **No** — owner must review dispositions and reconcile tree first (C4) |

---

## 1. Inventory — working tree vs `b20b27a`

### 1.1 Stat-only phantom modifications (41 files)

Git `status` shows `M` but `git hash-object` == `HEAD:` blob (OneDrive/index stat noise). **No content delta.**

**Recommended disposition:** `git checkout -- <paths>` or `git update-index --refresh` to clear index noise before any closure commit. **Do not fold into P3 packages** — no substantive change.

<details>
<summary>Full list (41)</summary>

- `alembic/versions/0016_updated_at_trigger.py`
- `app/reports/api/routes/review.py`
- `app/reports/eval/__init__.py`
- `app/reports/eval/faithfulness_check.py`
- `app/reports/extraction/pdf_ocr_fallback.py`
- `app/reports/knowledge/__init__.py`
- `app/reports/knowledge/confirmed_kb.py`
- `app/reports/knowledge/qualitative_kb_scope.py`
- `app/reports/orchestration/classify_isolation.py`
- `app/reports/parsing/json_from_text.py`
- `app/reports/reconciliation/degrade_dedup.py`
- `app/reports/schemas/qualitative_critic_v1.py`
- `app/reports/schemas/report_review.py`
- `app/reports/services/critique_resume_service.py`
- `app/reports/services/numeric_fact_verifier.py`
- `app/reports/services/report_section_review_service.py`
- `app/reports/services/synthesis_claim_binding.py`
- `docs/artefacts/me_module/audits/P3-2_STALL_SIGHTINGS.md`
- `docs/artefacts/me_module/audits/gap_stage_230290ce_diagnosis.json`
- `nixpacks.toml`
- `scripts/audit/phase1_signoff_gate.py`
- `scripts/gap_stage_diagnosis.py`
- `scripts/refresh_degraded_knowledge_bank.py`
- `scripts/requeue_gap_job.py`
- `tests/critic_eval_helpers.py`
- `tests/fixtures/critic/dyn02_false_positive_slice.json`
- `tests/fixtures/reconciler/e1_reconciler_degraded_230290ce_kb.json`
- `tests/fixtures/synthesis/clean_faithfulness_fixture.json`
- `tests/test_classify_isolation.py`
- `tests/test_confirmed_kb.py`
- `tests/test_degrade_dedup.py`
- `tests/test_full_walk_exit_codes.py`
- `tests/test_json_from_text.py`
- `tests/test_p0_me_smoke.py`
- `tests/test_p1_claim_binding.py`
- `tests/test_p1_critic_adversarial.py`
- `tests/test_p1_faithfulness_eval.py`
- `tests/test_p1_fence_eval.py`
- `tests/test_p1_numeric_verifier.py`
- `tests/test_p1_phase1_faithfulness.py`
- `tests/test_review_routes.py`

</details>

---

### 1.2 Content-modified tracked files (21)

| File | Nature | P2 / assertion link | Recommended disposition |
|------|--------|---------------------|------------------------|
| `app/reports/gap/satisfaction.py` | Owner/narrative/funder gap filtering; satisfaction rewrite | P2 adjudication: RSS funder, OA narrative; 2-ref exact set | **Land as named P2-CORRECTIONS closure commit** (prerequisite for gap exact test) |
| `app/reports/gap/template_requirements.py` | `table_requirements`, owner tags | P2 template typing in `TEMPLATE_INSTANCE_FCDO.json` (committed) | Same closure commit |
| `app/reports/gap/deterministic_gaps.py` | Deterministic gap path updates | P2 gap wall / E3 | Same closure commit |
| `app/reports/gap/logframe_completeness.py` | Logframe row completeness | P2 `{logframe_row:op2_3, op4_2}` | Same closure commit |
| `app/reports/agents/gap_compliance_agent.py` | Agent wiring to new satisfaction | P2 gap set | Same closure commit |
| `app/reports/services/gap_check_service.py` | `open_items_count`, readiness | P2-2b gate-2 contract | Same closure commit |
| `app/reports/services/gap_compliance_service.py` | Service pass-through | P2 gap | Same closure commit |
| `app/reports/schemas/gap_check.py` | Schema fields | P2 readiness | Same closure commit |
| `app/reports/schemas/gap_compliance_v1.py` | Envelope fields | P2 gap | Same closure commit |
| `app/reports/agents/knowledge_bank_reconciler.py` | Reconciler tweaks | P2 corrections (cluster/promotion path) | Same closure commit or fold P3-1 if owner splits |
| `app/reports/schemas/knowledge_bank_reconciliation_v1.py` | Schema minor | P2 E1 | Same closure commit |
| `app/reports/orchestration/pipeline.py` | Pipeline / trace / open_items | P2 orchestration | Same closure commit |
| `app/reports/services/report_synthesis_service.py` | Section visibility / 6-section synthesis | P2 FCDO 6/6 target | Same closure commit — **AMBER: moat service** |
| `tests/gap_grading.py` | Grader updates | P2 gap eval | Same closure commit |
| `tests/test_gap_check_routes.py` | Route tests | P2 gap-check API | Same closure commit |
| `tests/test_gate2_gap_answers.py` | Gate-2 tests | P2 | Same closure commit |
| `tests/test_gate1_confirmation.py` | Large expansion (~519 lines touched) | P2 Gate-1 promote API / cluster batch | Same closure commit — **AMBER: auth/gate moat** |
| `tests/test_orchestrator_synthesis.py` | Section count 6 assertions | P2 FCDO 6/6 | Same closure commit |
| `tests/test_report_synthesis_service.py` | Synthesis section count | P2 FCDO 6/6 | Same closure commit |
| `docs/artefacts/API_CONTRACT.md` | Contract edits | P2 readiness / gap-check | **Fold into P3-5** if not landed in P2 closure |
| `docs/artefacts/me_module/DB_FIELD_CONTRACT_DONOR_REPORTS.md` | Field contract | P2 | P3-5 or P2 closure |

---

### 1.3 Untracked paths (67) — grouped

| Group | Paths (representative) | Nature | P2 link | Recommended disposition |
|-------|------------------------|--------|---------|------------------------|
| **Gap moat modules** | `app/reports/gap/section_visibility.py`, `requirement_metadata.py`, `requirement_satisfaction.py`, `post_draft_gaps.py` | New modules for owner/funder/narrative filtering | P2 adjudication + corrections | **Land in P2-CORRECTIONS closure commit** (required for exact gap test) |
| **Reconciliation** | `app/reports/reconciliation/chunked_reconcile.py`, `tests/test_reconciliation_chunking.py` | Chunked reconcile | P2 E1 scale | Closure commit or defer owner decision |
| **Test overlay** | `tests/fixtures/templates/fcdo_owner_tagged.json` | Template regression slice | P2 owner tags | Closure commit |
| **Findings doc** | `docs/artefacts/me_module/audits/P2_CORRECTIONS_FINDINGS.md` | As-built reference | P2 | **Land as docs-only commit** (owner) |
| **Audit artefacts** | `docs/artefacts/me_module/audits/dynamic_run/**` (walk JSON, logs, docx, CI download caches) | Live walk captures | P1/P2 evidence | **Do not commit** — gitignore or leave local; use committed subset only (`rubric_traces.json` already in `b20b27a`) |
| **Prod capture** | `me_capture/230290ce/*`, `me_capture/_extract.py` | Prod row snapshots | P2 rollback reference | **Do not commit** (prod data); keep local or separate secure store |
| **Throwaway scripts** | `scripts/_audit_out.txt`, `_check_report_status.py`, `_poll_report_job.py` | Operator diagnostics | — | **Revert / delete** before P3-1 |
| **Audit helper** | `scripts/audit/faithfulness_check.py` | CLI wrapper | P1 eval | Fold **P3-1** if kept |
| **Sample PDF** | `M_E_Module/Sample_docs/FCDO_Test_Set/02_FCDO_BridgeLight_Award_Letter.pdf` | Test doc | P0 walk | Commit if needed for offline replay; else LFS |

---

## 2. Baseline-green question

### 2.1 smoke-test.yml suite (P2 closure CI gate)

**CI evidence:** Run [27333324256](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27333324256) — **success** on `headSha=b20b27a`, 2026-06-11T08:13:03Z (workflow_dispatch post-adjudication commit).

**Local evidence (detached worktree at `b20b27a`):**

```
pytest tests/test_p0_me_smoke.py tests/test_classify_isolation.py tests/test_review_routes.py
  tests/test_confirmed_kb.py tests/test_p1_fence_eval.py tests/test_p1_claim_binding.py
  tests/test_p1_faithfulness_eval.py tests/test_p1_numeric_verifier.py
  tests/test_p1_critic_adversarial.py tests/test_p1_phase1_faithfulness.py
  tests/test_report_fact_safety_service.py tests/test_fact_safety_critic_agent.py
  tests/test_gate1_confirmation.py tests/test_full_walk_exit_codes.py -q
→ 67 passed, 1 warning
```

**Current working tree (with uncommitted changes):** same command → **67 passed, 1 warning**.

**Conclusion:** **Yes** — clean `b20b27a` passes the smoke-test.yml graded suite. Local tree does **not** regress that suite.

### 2.2 Tests that differ with vs without local changes

| Test | @ `b20b27a` worktree | @ current tree | Notes |
|------|----------------------|----------------|-------|
| `test_fcdo_complete_distilled_gap_set_exact` | **FAIL** (46 spurious gaps) | **PASS** | Requires uncommitted gap moat (`satisfaction.py`, untracked `section_visibility.py`, etc.) |
| `test_fcdo_complete_has_no_funder_side_gaps` | not re-run separately | **PASS** | Same dependency |
| `test_orchestrator_gate1.py` (6 outcome tests) | **FAIL** (12-debt subset) | **FAIL** | Identical failure class — not fixed by local delta |
| `test_gate3_resume_does_not_re_run_critic` | **FAIL** (3/3 runs) | **FAIL** (3/3 runs) | Consistent fail, not flake locally |
| `test_gate1_confirm_endpoint_404_when_module_disabled` | **PASS** | **PASS** | Pass-at-both per P2 adjudication |
| Smoke suite (67 tests) | **PASS** | **PASS** | No difference |

**Conclusion:** Uncommitted changes are **necessary** for P2 adjudicated gap exact-set test but **not** for smoke CI. Tree reconciliation must land gap moat code before P3-1 can assert the 2-ref set.

---

## 3. Flake identification

### 3.1 Candidates named in P2 adjudication

| Test | Registered as | Local evidence (2026-06-11) |
|------|---------------|----------------------------|
| `test_orchestrator_critique.py::test_gate3_resume_does_not_re_run_critic` | fail-at-both **and** flaky | **Fails 3/3** at baseline and current; `PendingRollbackError` / SAWarning every run — **consistent failure, not intermittent locally** |
| `test_gate1_confirmation.py::test_gate1_confirm_endpoint_404_when_module_disabled` | pass-at-both | **Passes** every run — **not flaky** |

### 3.2 CI run history

Recent `smoke-test.yml` runs on `main` (20 fetched): **all success** including scheduled [27334781736](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27334781736). Debt-register tests are **not** in smoke CI — no CI flake signal for gate3.

### 3.3 Register currency

**12 fail-at-both:** Confirmed **still current** — all 12 fail locally at `b20b27a` worktree (same command as P2 adjudication table).

**1 flaky:** **Not supported by evidence.** `test_gate3_resume_does_not_re_run_critic` behaves as **deterministic fail-at-both** locally. Recommend owner **reclassify**: remove duplicate flaky row; treat gate3 as fail-at-both only until CI shows intermittent pass. **Quarantine/fix still belongs in P3-1** (C1a) regardless — consistent failures also block a trustworthy gate.

---

## 4. CI state

### 4.1 smoke-test.yml @ `main` HEAD (`b20b27a`)

| Property | Value |
|----------|-------|
| Status | **Green** (latest scheduled + dispatch runs success) |
| Triggers | `push` to `main`, cron `*/30`, `workflow_dispatch` |
| Unit gate | 14 pytest modules (~67 tests) — see [`smoke-test.yml`](../../../.github/workflows/smoke-test.yml) line 23 |
| **Not gated** | `test_gap_compliance_agent.py`, `test_orchestrator_gate1.py`, `test_orchestrator_critique.py`, `test_auth_account_linking.py`, debt register subset, offline walk replay, P3 eval metrics |

### 4.2 p0-audit-walk.yml

| Property | Value |
|----------|-------|
| Trigger | **`workflow_dispatch` only** — no schedule (C3 compliant) |
| Live jobs | FCDO CLEAN, degraded PDF, FCDO PDF full + phase1 signoff |
| Deferred | Owner end-of-phase session per revised plan C3 |

---

## 5. AMBER flags — moat, quota, auth, schema

| Area | Working-tree touch | Risk |
|------|-------------------|------|
| **Gap moat** | `satisfaction.py`, untracked `section_visibility.py`, `requirement_satisfaction.py`, `post_draft_gaps.py`, `gap_compliance_agent.py` | **High** — defines 2-ref CI set; uncommitted |
| **Synthesis moat** | `report_synthesis_service.py` (6-section visibility) | **High** — FCDO 6/6 target |
| **Gate-1 API** | `test_gate1_confirmation.py` expansion | **High** — promote/cluster contract |
| **Pipeline** | `pipeline.py` | **Medium** — orchestration trace / open_items |
| **Quota** | No content delta in working tree vs `b20b27a` | None locally |
| **Auth** | No content delta; auth linking failures are test-only tuple bug | Test debt only |
| **Schema / migration** | Stat-only phantom on `alembic/0016` — no content change | None |
| **Contract** | `API_CONTRACT.md` content delta | **Medium** — reconcile in P3-5 or P2 closure |

---

## 6. Recommended owner actions (dispositions — not executed)

1. **Clear 41 stat-only phantom `M` files** before any commit (`git checkout --` or refresh index).
2. **Land P2-CORRECTIONS closure commit** from 21 content files + 4 untracked gap moat modules + `fcdo_owner_tagged.json` — single scoped commit on top of `b20b27a` so gap exact-set test passes without dirty tree.
3. **Commit `P2_CORRECTIONS_FINDINGS.md`** separately (docs-only) if owner chooses.
4. **Do not commit** `dynamic_run/` bulk artefacts or `me_capture/` prod snapshots.
5. **Delete or gitignore** throwaway scripts (`scripts/_*.py`, `_audit_out.txt`).
6. **Reclassify flake register** — gate3 is fail-at-both (consistent), not flaky per local/CI evidence.
7. **Ratify P3-1 assertion manifest** before activating blocking gates on `main`.

---

## 7. Audit method notes

- Local pytest: Python 3.11, `PYTHONPATH=.`, Windows host.
- Baseline replay used git worktree at `NGOInfo-Grantpilot-p30-baseline` @ `b20b27a` (read-only test harness; worktree can be removed with `git worktree remove`).
- No commits, no fixture edits, no live walks performed during this audit.

---

**STOP.** Owner reviews §6 dispositions. P3-1 brief follows separately after reconciliation.
