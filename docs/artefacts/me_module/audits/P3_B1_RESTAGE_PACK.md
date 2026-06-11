# P3 Phase B — B1 re-stage pack (M1–M4)

**Date:** 2026-06-11  
**Status:** B1 re-staged per owner decision of record; **`GO MUTATION` withheld** — prior staging (`P3_B1_MUTATION_STAGING.md` @ `300b430`) superseded  
**Role:** Facts and verbatim extracts only

---

## M1 — Discrepancy explanation

### What `TEMPLATE_INSTANCE_FCDO.json` actually contains

| Metric | Value |
|--------|-------|
| Section count | **8** |
| Section keys | `summary_and_overview`, `performance_and_conclusions`, `detailed_output_scoring`, `evidence_and_evaluation`, `risk_and_safeguarding`, `value_for_money`, `programme_management_delivery_commercial_financial`, `recommendations_and_actions` |
| Total requirements (indicators + tables) | 47 (39 indicators, 8 tables) |
| v1.2.0 tag coverage (items with `indicator_requirements` / `table_requirements` entry carrying `owner` and/or `requirement_type`) | **17 / 47** (36%) |
| Kill-list sections still present | `detailed_output_scoring`, `value_for_money` |
| Kill-list refs still present in JSONB | 12 refs incl. `review_summary_sheet`, `output_scores`, `vfm_measures`, … |

**Per-section tag coverage (repo instance):**

| Section | Indicators | Tables | Tagged req's |
|---------|------------|--------|--------------|
| `summary_and_overview` | 4 | 1 | 1 (`review_summary_sheet` table) |
| `performance_and_conclusions` | 4 | 1 | 1 (`outcome_assessment` → narrative) |
| `detailed_output_scoring` | 6 | 1 | 6 (owner/type on section + indicators) |
| `value_for_money` | 7 | 1 | 8 |
| `programme_management_delivery_commercial_financial` | 6 | 1 | 1 |
| Other NGO sections | 13 | 3 | 0 |

**Finding:** The repo file is **tagged but not cleaned** — it retains all 8 sections and all kill-list template rows. It is the **source** named in `P2_FUNDER_ROW_DELETION_PROPOSAL.md`, not a pre-built post-deletion artefact.

### Where the cleaned + tagged instance lives

**No committed file** contains the decided post-state (6 sections, kill-list absent, full tag pass).

Derived artefacts generated in this re-stage (not yet applied to prod):

| Artefact | Operation |
|----------|-----------|
| [`snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json) | **One-op:** `TEMPLATE_INSTANCE_FCDO.json` + kill-list removal |
| [`snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json) | **Two-step A:** prod structure + repo v1.2.0 tags merged |

Build script: `scripts/audit/b1_template_analysis.py`.

### Why prior staging diverged

| Factor | Fact |
|--------|------|
| Wrong source interpretation | Prior B1 (`b1_prod_snapshot.py` / `P3_B1_MUTATION_STAGING.md`) diffed prod vs **`TEMPLATE_INSTANCE_FCDO.json` verbatim** and treated the UPDATE as tag-metadata patch |
| Structural outcome stated | "8 field deltas; section keys unchanged" — **contradicts** proposal §Production DB (full replace with funder rows **removed**) |
| Root cause | **Wrong operational model:** applied "tag overlay on 8-section prod" instead of "kill-list deletion + tag carry-forward on 6-section payload" |
| Deliberate conservatism? | **No explicit owner decision** to defer deletion; conservatism was **not surfaced** — conflict with proposal/session pack should have been recorded before staging |
| In-flight strand risk | Likely implicit motivator; never documented as trade-off |

**Additional finding (one-op derived payload):** After kill-list removal, surviving 6 sections carry **1 / 30** tagged requirements (`outcome_assessment` narrative only). Repo tags were concentrated on funder sections/tables slated for deletion. Full NGO indicator `indicator_requirements` coverage is **not** present in any committed file — typed matcher will rely on fallbacks for most NGO items until a follow-up tag pass.

**Typed matcher schema version:** No `schema_version` field in template JSONB. Runtime contract: `app/reports/gap/requirement_metadata.py` header **"schema v1.2.0"**; canonical spec `FUNDER_TEMPLATE_SCHEMA.md` header v1.2.0. Intended payloads inherit repo tag blocks where sections survive.

---

## M2 — Re-staged decided operation

### Pre-mutation snapshot (unchanged)

| Field | Value |
|-------|-------|
| Path | [`snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json`](snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json) |
| SHA256 | `aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0` |
| Prod sections | 8 keys; **0** v1.2.0 tagged requirements |
| Alembic prod | `0018_usage_ledger_uq` (B2 verify-only) |

### Variant A — One-op (owner decision of record)

**Intended JSONB:** [`snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json)  
**SHA256:** `1c94a88aeb6b1c22a475b436b8ba42c3d8c591584ec9c1bb8f06e6164663fa9e`

| Structural post-state | Value |
|----------------------|-------|
| Section count | **6** |
| Section keys **removed** vs prod | `detailed_output_scoring`, `value_for_money` |
| Section keys **retained** | `summary_and_overview`, `performance_and_conclusions`, `evidence_and_evaluation`, `risk_and_safeguarding`, `programme_management_delivery_commercial_financial`, `recommendations_and_actions` |
| Kill-list refs remaining | **0** (incl. `review_summary_sheet` table row removed from section A) |
| Tag coverage (surviving requirements) | 1 / 30 tagged (`outcome_assessment` → `requirement_type: narrative`) |
| `outcome_assessment` table | **Retained** (not on kill list; narrative typing preserved) |

**Refs removed vs prod (17):** `review_summary_sheet`, `output_score_table`, `vfm_measures`, `output_scores`, `impact_weightings`, `risk_ratings`, `economy`, `efficiency`, `effectiveness`, `equity`, `commercial_improvement_where_relevant`, `FCDO_management_actions`, `output_indicators`, `logframe_milestones`, `actual_results`, `cost_drivers`, `forecast_vs_actual_costs`

**Exact UPDATE (single row, transactional):**

```sql
BEGIN;

UPDATE funder_report_templates
SET
  report_sections_json = :report_sections_json::jsonb,
  format_rules_json = :format_rules_json::jsonb,
  terminology_map_json = :terminology_map_json::jsonb,
  version = version + 1,
  updated_at = now()
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';

-- Assert ROW_COUNT = 1
-- Read back; canonical JSON compare against bind params from fcdo_55f891ac_intended_post_mutation_2026-06-11.json
-- COMMIT only on exact match; else ROLLBACK
COMMIT;
```

Bind from [`fcdo_55f891ac_intended_post_mutation_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json) keys `report_sections_json`, `format_rules_json`, `terminology_map_json`.

**Note:** `format_rules_json.extensions` still references `requires_output_scoring`, `requires_value_for_money_assessment`, and `value_for_money` block — **unchanged from repo instance**; extension drift vs 6-section shape is a post-replace follow-up (not in kill-list scope).

### Variant B — Two-step (staging evidence only)

**Step A JSONB:** [`snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json)  
**SHA256:** `099dbf1abf92b81e66286492716ebc4025b58938295f9d0d9fc675de4f67c58f`

| Post-state | Value |
|------------|-------|
| Section count | **8** (unchanged) |
| Tag coverage | **17 / 47** (repo tags merged onto prod structure) |
| Kill-list refs | **Still present** (12 refs, 2 funder sections) |

Same UPDATE shape; bind from tags-only artefact. Step B (deletion) would bind one-op payload after named trigger.

### Rollback — executable (not stub)

| Component | Path |
|-----------|------|
| Snapshot source | `fcdo_55f891ac_pre_phase3_exit_2026-06-11.json` |
| Executor | `scripts/audit/b1_rollback_execute.py --proof` (parameterized UPDATE from snapshot) |
| CI proof step | `.github/workflows/p3-offline-replay.yml` → job `alembic-upgrade` → `B1 rollback proof (scratch Postgres)` |

**Proof protocol:** Seed scratch row with intended post-mutation JSONB → run rollback executor → assert canonical JSON byte-equality with snapshot (`aa6c9926…`).

**Local proof:** Docker unavailable on agent host; proof runs in CI scratch Postgres (see M4 for run ID after push).

---

## M3 — Strand-risk dossier

**Scope:** 16 non-terminal FCDO-template reports (`report_jobs.status NOT IN ('done','failed')`).  
**Probe:** `scripts/audit/m3_inflight_dossier.py` (read-only prod, 2026-06-11).

### Full in-flight table (R5)

| # | Report ID | Created (UTC) | Account | Email | Report status | Job stage | Open gaps | Kill-list refs in stored `gap_analysis_json` | Kill-list sections in gaps | Kill-list sections in `content_json` |
|---|-----------|---------------|---------|-------|---------------|-----------|-----------|---------------------------------------------|----------------------------|--------------------------------------|
| 1 | `2c78550a-ed6b-4bb1-b6c4-058efd0a65f7` | 2026-05-31 20:24:47 | audit-mint | `stage-e-smoke-1780259087@grantpilot-test.org` | DRAFT | synthesise | 44 | 13 refs | C, D | — |
| 2 | `fe6bf98b-70b7-46f2-9bc2-a1306546af18` | 2026-05-31 22:11:31 | audit-mint | `stage-e-smoke-1780265491@grantpilot-test.org` | DRAFT | critique | 44 | 13 refs | C, D | C, D |
| 3 | `cabb8796-195b-4089-afab-94d6fe841d50` | 2026-06-01 13:06:32 | audit-mint | `fcdo-d4-f1-1780319191@grantpilot-test.org` | DRAFT | critique | 41 | 13 refs | C, D | C, D |
| 4 | `5026ab66-9e30-413b-a823-7931c16fe435` | 2026-06-01 15:31:06 | audit-mint | `fcdo-planted-1780327863@grantpilot-test.org` | DRAFT | export | 41 | 13 refs | C, D | C, D |
| 5 | `fda69a23-7e31-4ff9-afaf-0b5486eac54b` | 2026-06-01 16:54:27 | audit-mint | `fcdo-postf1-1780332863@grantpilot-test.org` | DRAFT | export | 41 | 13 refs | C, D | C, D |
| 6 | `4702aecb-f27c-4748-ad59-c9b1dc8b54c5` | 2026-06-01 17:07:25 | audit-mint | `fcdo-postf1-1780333644@grantpilot-test.org` | DRAFT | gap | 0 | — | — | — |
| 7 | `6643d922-150d-4000-b878-4025e7c9145a` | 2026-06-01 18:30:27 | audit-mint | `fcdo-postf1-1780338625@grantpilot-test.org` | COMPLETE | critique | 41 | 13 refs | C, D | C, D |
| 8 | `b91ae3e0-92fb-430d-9feb-1dcd9b878b70` | 2026-06-01 21:46:15 | audit-mint | `fcdo-postf1-1780350374@grantpilot-test.org` | DRAFT | export | 41 | 13 refs | C, D | C, D |
| 9 | `3182a86f-81c4-4c25-bf74-1500a892f390` | 2026-06-07 09:00:48 | **real-user** | `pranabksingh@gmail.com` | DRAFT | gap | 0 | — | — | — |
| 10 | `230290ce-d28a-4138-ae08-901cf1ad69c0` | 2026-06-08 13:30:07 | **real-user** | `pranabksingh@gmail.com` | DEGRADED | critique | 43 | 12 refs | C, D | C, D |
| 11 | `fcd8131c-eb7a-446d-8741-2368218ebdff` | 2026-06-09 05:52:33 | audit-mint | `audit-p0_degraded_pdf-1780984351@grantpilot-test.org` | DEGRADED | gap | 0 | — | — | — |
| 12 | `9606f25a-4b34-4fb6-8261-67d220d968fb` | 2026-06-09 05:58:01 | audit-mint | `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` | DEGRADED | synthesise | 46 | 13 refs | C, D | — |
| 13 | `982834f6-4032-4ed6-b6a4-f5f75080536b` | 2026-06-09 08:07:21 | audit-mint | `audit-p0_degraded_pdf-1780992440@grantpilot-test.org` | DEGRADED | gap | 0 | — | — | — |
| 14 | `c1e33557-eb88-4826-bf11-80f72042d0c6` | 2026-06-09 08:50:22 | audit-mint | `audit-p0_degraded_pdf-1780995021@grantpilot-test.org` | DEGRADED | gap | 0 | — | — | — |
| 15 | `1f617f76-ab03-453b-9731-8c148b7d4a95` | 2026-06-09 11:57:50 | audit-mint | `audit-p0_degraded_pdf-1781006269@grantpilot-test.org` | DEGRADED | gap | 0 | — | — | — |
| 16 | `f162ae64-2be2-4f7a-a8b5-de979b582bd0` | 2026-06-09 12:50:40 | audit-mint | `audit-p0_degraded_pdf-1781009439@grantpilot-test.org` | DEGRADED | gap | 0 | — | — | — |

*C = `detailed_output_scoring`, D = `value_for_money`*

### Under TRUE deletion (one-op) — per-class effects

| Class | Count | Post-replace experience (facts) |
|-------|-------|----------------------------------|
| **A** — Past gap stage; stored `gap_analysis_json` contains kill-list refs (13–12 refs) | **10** | Gap UI / resume reads **frozen** gap list with refs whose template rows no longer exist; re-gap not automatic on template FK change alone |
| **B** — `content_json` contains synthesized kill-list sections | **8** | In-app / stored prose for C+D sections **unchanged** (report row not mutated); Stage H re-export would **omit** C+D headings if re-run against new template |
| **C** — At gap stage; 0 stored gaps | **6** | Next engine read uses 6-section template; gap enumeration **drops** C+D items; lower orphan risk than class A |
| **D** — Real-user rows | **2** | `3182a86f…` class C; `230290ce…` class A+B (critique stage, 43 stale gaps, content has C+D) |

**Proposal reconciliation (job-state-scoped):** `P2_FUNDER_ROW_DELETION_PROPOSAL.md` scopes to **template row only** — no automatic report-row cleanup. P8-style job-state reconciliation applies to **quota ledger**, not gap JSON. In-flight reports are **not** terminal; proposal does not prescribe per-row gap rewrite.

### Recommendation (owner decides)

**Two-step (tags-only → deletion on trigger)** reduces immediate orphan-gap surface for class A (10 rows): Step A re-tags prod without removing sections, so stored gap refs still match template keys; typed matcher begins excluding funder-owned items from **new** gap runs. Step B (one-op deletion) after in-flight drain or explicit accept of stale gap lists.

**One-op now** matches owner decision of record and unblocks B3 validation on 6-section prod shape immediately; accept that **10 rows** carry stale kill-list entries in `gap_analysis_json` until abandoned or manually re-run through gap.

**Lean:** If B3 uses **fresh mint** reports only (`audit-p0_fcdo_pdf_full-1780984679@…`), strand risk on legacy 15 audit rows is **contained**; one-op is operationally cleaner. If real-user `230290ce…` must resume, two-step or explicit re-gap after mutation is lower risk.

---

## M4 — Reporting debt closure

### CI run conclusions (verbatim `gh run view` JSON fields)

| Run ID | Workflow | headSha | status | conclusion |
|--------|----------|---------|--------|------------|
| [27348215767](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215767) | Smoke Test | `e29c89e` | completed | success |
| [27348215676](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215676) | P3 Offline Replay | `e29c89e` | completed | success |
| [27350651156](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651156) | Smoke Test | `300b430` | completed | success |
| [27350651106](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651106) | P3 Offline Replay | `300b430` | completed | success |

**27350651106 jobs:** `alembic-upgrade` completed success; `offline-replay` completed success (includes NLCF pin replay step @ `300b430`; rollback proof step added in re-stage commit — run ID TBD after push).

### R2 — Offline replay committed paths (fresh checkout)

| Entry point | Reads (repo-relative) |
|-------------|----------------------|
| `python scripts/audit/offline_replay.py --fixture` | `tests/fixtures/synthesis/clean_faithfulness_fixture.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`; synthetic 2-ref gap inline in `replay_clean_fixture()` |
| `python scripts/audit/offline_replay.py --nlcf-pin` | `tests/fixtures/gap/keys/nlcf_regression_pin_e7fa9bee.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` |
| `offline_replay.py <path>` (walk mode) | Caller-supplied path only — **no** default read of `dynamic_run/` |
| `scripts/audit/distill_fcdo_complete_gap_fixture.py` | Default: `tests/fixtures/gap/fcdo_complete_3347590c_knowledge_bank.json`; optional `--walk` |

### R4 — `outcome_indicators` / `progress_against_expected_results` provenance

| Ref | Owner-adjudicated class (P2_GAP_SET_ADJUDICATION §Owner-confirmed) | In literal-forbidden list? | Evidence |
|-----|-------------------------------------------------------------------|---------------------------|----------|
| `outcome_indicators` | **Not listed** in owner-confirmed table | Yes (`FCDO_LITERAL_FORBIDDEN_GAP_REFS`) | Walk `3347590c` emitted as `performance_and_conclusions:indicator:outcome_indicators` in pre-complete gap wall; **complete-docset probe** (`fcdo_complete_3347590c_expected_gaps.json`) emits **zero** gaps for this ref (exact set `{logframe_row:op2_3, logframe_row:op4_2}` only). Template: indicator in `performance_and_conclusions` without `indicator_requirements` override → default data/ngo. **Classification:** typing-or-mapping miss **not owner-adjudicated**; retained in literal-forbidden as **walk-namespace regression pin** (must not reappear on complete KB). **Not reclassified out** per R4 rule (no adjudicated (a)/(b) verdict). |
| `progress_against_expected_results` | **Not listed** in owner-confirmed table | Yes | Same pattern as `outcome_indicators`; walk namespace ref exact string; absent from complete-docset probe; `fcdo_incomplete_answer_key.json` lists as expected on **incomplete** docset only. Regression pin retained. |

**Contrast (adjudicated refs in same walk namespace):**

| Ref | Adjudicated class | Evidence pointer |
|-----|-------------------|------------------|
| `review_summary_sheet` | (a) funder-owned | `P2_GAP_SET_ADJUDICATION.md` §1 |
| `outcome_assessment` | (b) narrative | `P2_GAP_SET_ADJUDICATION.md` §2 |

### R1 residue disposition

| Path | SHA256 / status | Disposition |
|------|-----------------|-------------|
| `docs/artefacts/me_module/audits/dynamic_run/walk_fcdo_full_3347590c.json` | `a254b42e198480cbb6b5983794f695f36bc65e910932cb9f14f641e9e66081d5` | **Laptop-archive** (gitignored); committed functional slice: `tests/fixtures/gap/fcdo_complete_3347590c_knowledge_bank.json` + `fcdo_complete_3347590c_expected_gaps.json` |
| `docs/artefacts/me_module/audits/dynamic_run/export_3347590c.docx` | **Absent** on agent disk at re-stage | **Laptop-archive entry** — not present locally; no committed vendored copy |
| `docs/artefacts/me_module/audits/P2_CORRECTIONS_FINDINGS.md` | untracked | **Recommend commit** (audit-artefact) |
| `scripts/audit/faithfulness_check.py` | untracked | **Recommend delete or merge** — duplicate of `app/reports/eval/faithfulness_check.py`; not imported by CI |
| `M_E_Module/Sample_docs/FCDO_Test_Set/02_FCDO_BridgeLight_Award_Letter.pdf` | `b56a1edb402ea6f5ed9d003df01acd5c0885d23e4563b31f2290d1fa737aa56d` | **Recommend commit** to sample docset path (docset parity for walks) |

### R6 — B3 NLCF docset note (session pack)

Recorded in [`P3_PHASE_EXIT_OWNER_SESSION_PACK.md`](P3_PHASE_EXIT_OWNER_SESSION_PACK.md) §8: NLCF regression pin basis = **default docset (proposal + award + monitoring)**; status `matches_observed_e7fa9bee`; B3 designated account `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org`. **B3 NLCF walk must use same default docset** — not complete-docset-relative.

---

## STOP

**`GO MUTATION` withheld.** Owner chooses:

- **`GO MUTATION` (one-op)** — bind [`fcdo_55f891ac_intended_post_mutation_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json), or  
- **Amended decision** — e.g. two-step tags-only first ([`fcdo_55f891ac_intended_tags_only_2026-06-11.json`](snapshots/fcdo_55f891ac_intended_tags_only_2026-06-11.json)), or require committed 6-section golden before prod touch.

**Supersedes:** [`P3_B1_MUTATION_STAGING.md`](P3_B1_MUTATION_STAGING.md) (@ `300b430`).
