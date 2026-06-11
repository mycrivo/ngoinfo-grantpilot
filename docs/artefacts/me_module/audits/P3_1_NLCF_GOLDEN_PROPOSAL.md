# P3-1 NLCF golden proposal (CP-2)

**Status:** Proposal only — NLCF eval gates wait for owner ratification; FCDO gates activate immediately on `main`.  
**Source walk:** `walk_nlcf_gen_e7fa9bee.json` (run `nlcf_gen`, report `e7fa9bee-4b05-4e5b-bdd4-17dfedaaa0a5`, verdict `stopped_at_gate2`).  
**Plan reference:** Phase 3 Plan v2 · CP-2.

---

## Proposed NLCF golden artefacts

| Artefact | Purpose | Ratification needed |
|----------|---------|---------------------|
| `tests/fixtures/gap/nlcf_complete_e7fa9bee_knowledge_bank.json` | Distilled Gate-1 KB snapshot from walk reconcile stage | Yes |
| `tests/fixtures/gap/keys/nlcf_complete_answer_key.json` | Expected gap identities + forbidden set (extend existing NLCF keys) | Yes |
| `tests/fixtures/synthesis/nlcf_faithfulness_fixture.json` | Post-synthesis content-keyed faithfulness baseline | Yes — requires export-complete walk |
| `tests/fixtures/eval/walk_nlcf_gen_e7fa9bee_distilled.json` | Trimmed offline replay input (content + gaps only; no tokens/costs) | Optional |

---

## Proposed NLCF gate set (mirrors FCDO; content-keyed)

| Gate | Proposed assertion |
|------|-------------------|
| G-degrade-leak | `degraded_pass_through == 0` on CLEAN NLCF docset |
| G-faithfulness | `unmatched_numbers == 0` on NLCF golden fixture |
| G-nlcf-gap-exact | TBD from owner gap adjudication (walk stopped at gate2 — gap list in `after_gap` snapshot) |
| G-forbidden | Zero funder-owned NGO data gaps; zero narrative misclassified as data |
| G-section-count | NLCF visible NGO section count unchanged vs template |
| G-charge-once | Same idempotency contract as FCDO |
| G-honest-exit | Non-zero on infrastructure / non-passing verdicts |

---

## Walk evidence summary (e7fa9bee)

- **Template:** NLCF Southbank  
- **Docset:** proposal + award letter + monitoring/spend table (default NLCF docset)  
- **Verdict:** `stopped_at_gate2` — synthesis/export not captured in this walk  
- **Gap stage:** Completed; gap checklist available in `snapshots.after_gap`  
- **Cost block present in walk JSON:** ignored by P3-1 harness (content-keyed only)

---

## Owner actions to ratify

1. Adjudicate NLCF gap exact set from `after_gap` snapshot (same process as P2 FCDO adjudication).  
2. Approve or edit proposed answer key under `tests/fixtures/gap/keys/`.  
3. Re-run export-complete NLCF walk (owner session / workflow_dispatch) to mint faithfulness golden.  
4. Signal ratification in decision log; agent may then wire NLCF named gates in smoke + offline replay.

---

## Non-blocking for P3-1 close

FCDO gates ship on `main` without NLCF ratification. This document satisfies CP-2 proposal deliverable.

---

## NLCF gap classification table (walk e7fa9bee — read-only ratification input)

**Walk:** `walk_nlcf_gen_e7fa9bee.json` · report `e7fa9bee-4b05-4e5b-bdd4-17dfedaaa0a5` · verdict `stopped_at_gate2`  
**Docset basis:** **Not complete-docset-relative.** Default NLCF docset only: proposal + award letter + monitoring/spend table (per walk metadata). Unlike FCDO golden (`walk_fcdo_full_3347590c`), this walk did **not** include a full committed docset parity set — gaps are relative to that partial upload set.  
**Template tags:** `TEMPLATE_INSTANCE_NLCF.json` carries **no v1.2.0 owner tags** (`indicator_requirements` / `table_requirements` metadata absent). All classifications below are **template-inferred** from `required_indicators` / `required_tables` keys in section JSON, not template-evidenced owner tags.  
**Visible NGO sections (annual context):** 6 (`project_story`, `community_involvement`, `difference_made`, `learning`, `changes_and_next_steps`, `spend_summary`; `final_update_only` conditional off).

| # | `required_item_ref` | Section | `required_item_type` (walk) | Recommended classification | Evidence basis |
|---|---------------------|---------|----------------------------|---------------------------|----------------|
| 1 | `community_participation_examples` | `community_involvement` | indicator | TRUE gap (default docset) | template-inferred: listed in `required_indicators`; KB has no matching fact |
| 2 | `partner_or_local_collaboration_examples` | `community_involvement` | indicator | TRUE gap (default docset) | template-inferred |
| 3 | `beneficiary_numbers` | `difference_made` | indicator | TRUE gap (default docset) | template-inferred |
| 4 | `community_feedback` | `difference_made` | indicator | TRUE gap (default docset) | template-inferred |
| 5 | `staff_or_volunteer_feedback` | `difference_made` | indicator | TRUE gap (default docset) | template-inferred |
| 6 | `outcome_indicators_where_available` | `difference_made` | indicator | TRUE gap (default docset) | template-inferred; NLCF-specific ref name (not FCDO `outcome_indicators`) |
| 7 | `what_worked` | `learning` | indicator | TRUE gap (default docset) | template-inferred |
| 8 | `what_did_not_work` | `learning` | indicator | TRUE gap (default docset) | template-inferred |
| 9 | `unexpected_findings` | `learning` | indicator | TRUE gap (default docset) | template-inferred |
| 10 | `learning_useful_to_others` | `learning` | indicator | TRUE gap (default docset) | template-inferred |
| 11 | `changes_made` | `changes_and_next_steps` | indicator | TRUE gap (default docset) | template-inferred |
| 12 | `planned_changes` | `changes_and_next_steps` | indicator | TRUE gap (default docset) | template-inferred |
| 13 | `support_needed` | `changes_and_next_steps` | indicator | TRUE gap (default docset) | template-inferred |
| 14 | `budgeted_total` | `spend_summary` | indicator | TRUE gap (default docset) | template-inferred |
| 15 | `actual_spend_total` | `spend_summary` | indicator | TRUE gap (default docset) | template-inferred |
| 16 | `revenue_cost_variance` | `spend_summary` | indicator | TRUE gap (default docset) | template-inferred |
| 17 | `capital_cost_variance` | `spend_summary` | indicator | TRUE gap (default docset) | template-inferred |
| 18 | `budget_vs_actual` | `spend_summary` | table | TRUE gap (default docset) / typing-or-mapping note | template-inferred table ref; walk emits `required_item_type: table`; min_rows=1 in template |

**Absent from walk gap list (facts):** zero funder-owned gaps; zero narrative misclassified as data gaps; zero refs matching FCDO forbidden set (`review_summary_sheet`, `outcome_assessment`, etc.) — NLCF template does not define those refs.

**Owner ratification options:** golden pin (18-ref exact set on default docset), regression pin (subset), or defer NLCF gates until export-complete walk + owner tags added to template instance.
