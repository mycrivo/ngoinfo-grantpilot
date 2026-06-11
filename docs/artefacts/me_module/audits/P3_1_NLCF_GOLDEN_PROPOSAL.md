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
