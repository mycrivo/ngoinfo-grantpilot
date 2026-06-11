# P2-ADJUDICATION — Gap-set ground truth + failure provenance

**Date:** 2026-06-11  
**Baseline commit:** `07e941c` (pre–P2-CORRECTIONS; worktree `NGOInfo-Grantpilot-p2adj-baseline`)  
**Package under test:** Uncommitted P2-CORRECTIONS + P2-ADJUDICATION typing on current tree

---

## Owner-confirmed adjudicated CI set

After applying template typing (no matcher changes):

| `required_item_ref` | Verdict | In CI exact set? |
|---------------------|---------|------------------|
| `logframe_row:op2_3` | **(c) data** — genuine | Yes |
| `logframe_row:op4_2` | **(c) data** — genuine | Yes |
| `review_summary_sheet` | **(a) owner: funder** | No — kill list |
| `outcome_assessment` | **(b) narrative** | No — synthesis prose |

**Confirmed exact set:** `{logframe_row:op2_3, logframe_row:op4_2}` (2 items).  
Sidecar: `tests/fixtures/gap/fcdo_complete_3347590c_expected_gaps.json` (probed 2026-06-11).

---

## 1. `review_summary_sheet`

### Template definition (pre-adjudication)

Section `summary_and_overview` (`A. Summary and Overview`), table:

```json
{
  "table_key": "review_summary_sheet",
  "label": "Annual Review Summary Sheet",
  "min_rows": 1,
  "data_source": "manual",
  "columns": [
    "programme_title", "programme_code", "review_date", "review_period",
    "budget", "overall_score_or_rating", "risk_rating", "review_team"
  ]
}
```

- **No** `table_requirements` override before adjudication → `resolve_requirement_type()` defaulted to **`data`**, owner **`ngo`** (`requirement_metadata._fallback_requirement_type`).
- Section has no `owner` or `requirement_type_default`.

### Matcher rule that emitted the gap (4-ref set)

1. `enumerate_template_requirements()` included `summary_and_overview:table:review_summary_sheet` as NGO data checklist item.
2. `unsatisfied_requirements()` → `_table_satisfied()` — no citable fact key/label token contains `reviewsummarysheet`.
3. `build_deterministic_gap_compliance_output()` emitted gap (`requirement_type == "data"`, not narrative/funder).
4. **Note:** `DATA_BACKED_HINTS["review_summary_sheet"]` lists `programme_title`, `programme_code`, `review_date` but applies only in `_data_indicator_satisfied()` for **indicators**, not tables.

### Relevant distilled KB facts (`fcdo_complete_3347590c_knowledge_bank.json`)

- **Absent:** dedicated summary-sheet row; no facts keyed `programme_title`, `programme_code`, `review_date`.
- **Present (partial context only):** `reporting_period.*`, grant reference code, financial lines, reporting obligations — not funder scoring fields.
- **Absent:** `overall_score_or_rating`, `risk_rating`, `review_team` (FCDO review-team artefacts).

### FCDO guidance in repo

From `WORKSTREAM_T2_NLCF_FCDO_REFERENCE_TEMPLATES.md` §3.2 (sourced):

- Annual Reviews **score achievement against outputs** and **assess the outcome**; five-point output scoring; review against logframe.
- Source URLs: Programme Operating Framework PDF, HTN Reviewing/Scoring Projects PDF, DevTracker examples.

**Not in repo:** field-by-field instructions for who completes the Annual Review Summary Sheet row (listed under §5 P0 “Needs real grantee or programme material”).

### 3347590c audit cross-ref

`analysis_3347590c.json` categorized `review_summary_sheet` as `narrative_or_judgment`. **Superseded** for adjudication: column set includes funder scoring and review-team identity.

### Classification rule → owner verdict

**(a) owner: funder** — columns `overall_score_or_rating`, `risk_rating`, `review_team` are FCDO review scoring/identity; not NGO discrete data. Added to deletion kill list; typed `table_requirements.review_summary_sheet: { owner: funder, requirement_type: funder_supplied }`.

---

## 2. `outcome_assessment`

### Template definition (pre-adjudication)

Section `performance_and_conclusions`, table:

```json
{
  "table_key": "outcome_assessment",
  "label": "Annual Outcome Assessment",
  "min_rows": 1,
  "data_source": "indicators",
  "columns": [
    "outcome_statement", "progress_summary", "evidence", "issues", "assessment"
  ]
}
```

- Default typing: **`data`**, owner **`ngo`** (no `table_requirements` override).

### Matcher rule that emitted the gap (4-ref set)

Same path as above: `_table_satisfied()` found no matching table token in citable facts → deterministic data gap.

### Relevant distilled KB facts

- **Present:** `objectives.outcome_objective_1`, `objectives.impact_objective_1`; extensive `indicators.OP*.ar1_actual` / targets / milestones.
- **Absent:** structured `outcome_assessment` table fact or gap answer on this slice (`gap_answers: {}`).
- Prose source material exists; missing item is **narrative table content**, not discrete NGO-supplied values.

### FCDO guidance in repo

§3.2 sourced: Annual Reviews **assess the outcome**; review tests assumptions linking indicators, outputs, outcomes (not tick-box only).

**Not in repo:** explicit “implementing partner fills outcome assessment table vs FCDO reviewer” split at column level.

### 3347590c audit cross-ref

`analysis_3347590c.json`: `narrative_or_judgment` — “narrative content; should be synthesized or human-authored”. **Aligned** with owner verdict (b).

### Classification rule → owner verdict

**(b) requirement_type: narrative** — synthesis drafts from objectives + indicator actuals; never a Gate 2 data question on this KB. Typed `table_requirements.outcome_assessment: { requirement_type: narrative }`.

---

## 3. Genuine data holes (unchanged)

| Ref | Evidence |
|-----|----------|
| `logframe_row:op2_3` | No `indicators.OP2.3.ar1_actual` (or equivalent) in distilled KB; proposal target present |
| `logframe_row:op4_2` | No `indicators.OP4.2.ar1_actual`; proposal target present |

---

## 4. Failure provenance (14 tests)

Pre-package baseline: git worktree at `07e941c`. Current: uncommitted tree with P2-CORRECTIONS + adjudication typing.

| # | Test | Failing @ 07e941c | Failing @ current | Failure summary |
|---|------|-------------------|-------------------|-----------------|
| 1 | `test_auth_account_linking.py::test_google_then_magic_link_links_same_user` | yes | yes | `AttributeError: 'tuple' object has no attribute 'id'` |
| 2 | `test_auth_account_linking.py::test_magic_link_then_google_links_same_user` | yes | yes | Same tuple `.id` AttributeError |
| 3 | `test_extract_isolation.py::test_mixed_unparseable_indicator_reaches_gate1_with_unreadable_sources` | yes | yes | Extract/isolation assertion failure |
| 4 | `test_gate1_confirmation.py::test_gate1_confirm_endpoint_404_when_module_disabled` | **no** | **no** | — |
| 5 | `test_indicator_data_extractor_agent.py::test_unparseable_docx_from_path_returns_degraded_no_raise` | yes | yes | Docling `ConversionError: logframe_data.docx is not valid` |
| 6 | `test_me_module_worker.py::test_worker_startup_path_registers_mappers_before_claim` | yes | yes | Worker subprocess AssertionError / import failure |
| 7 | `test_orchestrator_critique.py::test_gate3_resume_does_not_re_run_critic` | yes | yes | `PendingRollbackError` / `user_plans.created_at` NOT NULL |
| 8 | `test_orchestrator_gate1.py::test_outcome_b_happy_path_halts_at_gate1` | yes | yes | `classification == 'other'` not `'proposal'` |
| 9 | `test_orchestrator_gate1.py::test_outcome_uniform_raised_failure_preserves_checkpoint` | yes | yes | Document classification assertion |
| 10 | `test_orchestrator_gate1.py::test_outcome_uniform_degraded_extract_continues` | yes | yes | `degraded_documents` empty |
| 11 | `test_orchestrator_gate1.py::test_outcome_uniform_degraded_proposal_extract_continues_to_gate1` | yes | yes | proposal doc id not in `degraded_documents` |
| 12 | `test_orchestrator_gate1.py::test_outcome_uniform_degraded_indicator_unparseable_mixed_stage_reaches_gate1` | yes | yes | logframe doc id not in `degraded_documents` |
| 13 | `test_orchestrator_gate1.py::test_outcome_degraded_reconcile_parse_failure_pass_through_reaches_gate1` | yes | yes | zero facts after degraded reconcile |
| 14 | `test_orchestrator_gate1.py::test_outcome_g_h_resume_after_gate2_full_confirm` | **no** | **yes** | `section_count` 6 vs 8 (funder sections excluded from synthesis post-P2) |

### Package-introduced regressions (fixed in Part 2)

| Test | Fix |
|------|-----|
| `test_outcome_g_h_resume_after_gate2_full_confirm` | Assert `section_count == 6` (NGO-synthesizable sections only; funder-owned C + D excluded) |

### P3-6 named debt (pre-existing at baseline — out of scope)

All other failing tests fail at **both** commits with substantially the same root cause. Not introduced by P2-CORRECTIONS or P2-ADJUDICATION.

**Fail-at-both (12):**

| Test | Failure summary |
|------|-----------------|
| `test_auth_account_linking.py::test_google_then_magic_link_links_same_user` | `AttributeError: 'tuple' object has no attribute 'id'` on account link |
| `test_auth_account_linking.py::test_magic_link_then_google_links_same_user` | Same tuple `.id` AttributeError on reverse link order |
| `test_extract_isolation.py::test_mixed_unparseable_indicator_reaches_gate1_with_unreadable_sources` | Extract/isolation assertion — unreadable indicator doc not degraded as expected |
| `test_indicator_data_extractor_agent.py::test_unparseable_docx_from_path_returns_degraded_no_raise` | Docling `ConversionError: logframe_data.docx is not valid` |
| `test_me_module_worker.py::test_worker_startup_path_registers_mappers_before_claim` | Worker subprocess AssertionError / mapper registration import failure |
| `test_orchestrator_gate1.py::test_outcome_b_happy_path_halts_at_gate1` | Document classification `other` not `proposal` |
| `test_orchestrator_gate1.py::test_outcome_uniform_raised_failure_preserves_checkpoint` | Document classification assertion on raised failure path |
| `test_orchestrator_gate1.py::test_outcome_uniform_degraded_extract_continues` | `degraded_documents` empty when extract degrade expected |
| `test_orchestrator_gate1.py::test_outcome_uniform_degraded_proposal_extract_continues_to_gate1` | Proposal doc id not listed in `degraded_documents` |
| `test_orchestrator_gate1.py::test_outcome_uniform_degraded_indicator_unparseable_mixed_stage_reaches_gate1` | Logframe doc id not listed in `degraded_documents` |
| `test_orchestrator_gate1.py::test_outcome_degraded_reconcile_parse_failure_pass_through_reaches_gate1` | Zero facts after degraded reconcile pass-through |
| `test_orchestrator_critique.py::test_gate3_resume_does_not_re_run_critic` | `PendingRollbackError` / `user_plans.created_at` NOT NULL on resume path |

**Flaky (1):**

| Test | Failure summary |
|------|-----------------|
| `test_orchestrator_critique.py::test_gate3_resume_does_not_re_run_critic` | Intermittent `PendingRollbackError` / `user_plans.created_at` NOT NULL on Gate 3 resume path |

---

## 5. Part 2 changes applied

- `TEMPLATE_INSTANCE_FCDO.json`: `table_requirements` for both refs (see above).
- `P2_FUNDER_ROW_DELETION_PROPOSAL.md`: kill list + full JSONB replace operation for prod `55f891ac`.
- Fixtures/validator: 2-ref exact set.
- No matcher logic changes.
