# E1 conflict surfacing — read-only diagnosis

**Walk:** `5026ab66-9e30-413b-a823-7931c16fe435` (FCDO planted-conflict prod walk; pre–F1-hygiene deploy `1e1b124`)  
**Upload set:** proposal `.docx` + award letter `.docx` + indicator `.xlsx` (logframe `.docx` omitted)  
**Date:** 2026-06-01  
**Scope:** Diagnosis only — no code, pipeline, or model runs.

---

## Verdict (3 lines)

1. **Dominant cause:** `conflicts_pre_gate1: []` is **not** primarily an E1 LLM failure to compare values — **seven of nine** answer-key planted issues never reach E1 as **paired, same-semantics candidates** because extraction/candidate-building supplies **at most one side** (or none).
2. **Owning component:** **Extraction + candidate-building** (D2 proposal, D3 grant-terms, D4 indicator) owns the fix for cross-document numeric/date/budget conflicts; **E1 logic** owns at most **one** intra-document award-letter case where both values were extracted but filed as separate facts instead of a conflict.
3. **Fix class:** Expand extractors to emit the missing sides (narrative actuals, proposal budget, sheet totals/disaggregation, review-window notes) and/or emit explicit **absent** markers for missing rows; optionally tighten E1 rules for **intra-doc multi-value grant-terms** fields — not a generic “reconciler is blind” bug.

---

## Oracle — answer key planted conflicts (9)

Source: `M_E_Module/Sample_docs/FCDO_Test_Set/04_FCDO_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx` (table rows from para index 7, groups of 5).

| # | Issue type | Planted problem (summary) | Documents | True / intended | Expected catch layer |
|---|------------|---------------------------|-----------|-----------------|----------------------|
| 1 | Output actual mismatch | OP1.1 actual **612** (proposal narrative) vs **684** (spreadsheet) | Doc 1 vs Doc 3 | **684** final AR1 actual | Reconciler |
| 2 | Missing indicator row | OP2.3 in proposal; **no OP2.3 row** in spreadsheet | Doc 1 vs Doc 3 | Indicator required; data missing | **Gap agent** |
| 3 | Missing indicator row | OP4.2 in proposal; **no OP4.2 row** in spreadsheet | Doc 1 vs Doc 3 | Indicator required; data missing | **Gap agent** |
| 4 | Budget mismatch | Proposal/sheet **£1,184,000** vs award **£1,240,000** | Doc 1+3 vs Doc 2 | **£1,240,000** official | Reconciler / downstream |
| 5 | Date mismatch | Proposal **1 Oct 2024–30 Sep 2026** / AR1 Oct–Sep vs award **15 Oct 2024–14 Oct 2025/2026**; sheet note **1 Oct–30 Sep** | Doc 1+3 vs Doc 2 | Award dates authoritative | Reconciler / Gate 1 |
| 6 | Forecast-vs-actual scope | Sheet AR1 **£880,000 / £920,420** vs proposal **£1,184,000** vs award **£1,240,000** | All three | Keep grant **£1,240,000**; compare AR1 forecast/actual only | VfM / reconciler semantics |
| 7 | Disaggregation arithmetic | OP1.1 actual **684** vs female disagg sum **681** (58+590+33) | Doc 3 internal | **684**; disagg wrong | Disaggregation checker / reconciler |
| 8 | Disaggregation category | OP3.1 caregivers **392** but disagg under wrong age/sex bands | Doc 3 internal | **392** actual; fix disagg | Engine / gap |
| 9 | Awkward formatting | Buried reporting period; proposal **£1.184m / £1,184,000** vs award **£1,240,000** | All three | **£1,240,000**; AR1 **15 Oct 2024–14 Oct 2025** | Extractors |

**Walk artifact:** `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json` → `reconcile.conflicts_pre_gate1: []`, `reconciliation_outcome: complete`, **71 KB facts**, **0 conflicts**.

**Note:** No post–F1-hygiene (`cd15e37`) re-run exists for this walk. E1 runs before F1; `5026ab66` is the correct artifact for reconcile diagnosis.

---

## Per-conflict trace

### 1. OP1.1 actual mismatch (612 vs 684)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | **One side only.** Spreadsheet `extracted_json`: `OP1.1.actual.normalized = "684"`. Proposal `extracted_json`: **`612` absent** (`contains_612: false`). D2 emits **targets only** (`indicators.op1_1_girls_reenrolled_retained.target` = 1200), not narrative progress actuals. |
| **Candidates (`input_builder`)** | `indicators.OP1.1.actual` → 684 (xlsx). **No candidate** with value 612. |
| **KB facts** | `indicators.op1_1.ar1_actual` = **684** (xlsx only). **No fact** containing 612. |
| **E1 behaviour** | `conflicts: []`. Cannot VALUE_MISMATCH — second party missing (E1 rule: *“Single-source silence is NOT a conflict”*). |
| **Class** | **(a) Not extracted** — **D2 proposal extractor** (narrative actuals out of scope). |

---

### 2. OP2.3 missing spreadsheet row

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | Proposal: `op2_3_schools_safeguarding_pathway` target **40** extracted. Spreadsheet `indicator_row_ids`: **OP1.1 … OP4.3 — no OP2.3**. |
| **Candidates** | `indicators.op2_3_schools_safeguarding_pathway.target` = 40 (proposal). **No** `indicators.OP2.3.*` candidate. |
| **KB facts** | `indicators.op2_3_schools_safeguarding_pathway.proposal_target` = 40. **No** sheet actual/target for OP2.3. |
| **E1 behaviour** | No conflict — absence only. Answer key assigns **Gap agent**, not reconciler. |
| **Class** | **(a) Not extracted** (missing row / no absent marker) — **D4 + gap path**; **not an E1 VALUE_MISMATCH** by contract. |

---

### 3. OP4.2 missing spreadsheet row

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | Proposal: `op4_2_learning_briefs` target **5**. Spreadsheet rows: **no OP4.2**. |
| **Candidates / KB** | `indicators.op4_2_learning_briefs.proposal_target` = 5 only. |
| **E1 behaviour** | `conflicts: []`. Answer key: **Gap agent**. |
| **Class** | **(a) Not extracted** — same as #2 (**D4 / gap**). |

---

### 4. Budget mismatch (£1,184,000 vs £1,240,000)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | Award letter: `award_budget.amount.normalized = "1240000"`. Proposal + spreadsheet: **`1184000` absent** in all three `extracted_json` blobs (`contains_1184000: false`). D2 does not extract programme budget amounts. |
| **Candidates** | Single budget candidate: `award_budget.amount` → 1240000 (grant letter). |
| **KB facts** | `award_budget.amount` = **1240000** only. |
| **E1 behaviour** | No second budget figure to compare. |
| **Class** | **(a) Not extracted** — **D2** (proposal budget) + possibly **D4** (sheet envelope if present only in prose/totals not structured). |

---

### 5. Date mismatch (cross-document periods)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | Award letter: `grant_period` / `reporting_period` → **2024-10-15** start, **2025-10-14** AR1 end. Proposal calendar dates (**2024-10-01**, **2025-09-30**) **not in any extract**. Spreadsheet review-window note (**01-Oct-24 / 30-Sep-25**) **not in D4 structured output** (no candidates with those normalized dates). |
| **Candidates** | Grant-letter date candidates only (`grant_period.start`, `reporting_period.start`, `reporting_period.end.stated_values[0]`). |
| **KB facts** | `grant_period.start/end`, `reporting_period.start`, `reporting_period.end.ar1` = award values. |
| **E1 behaviour** | Cross-doc mismatch **never materialized** — competing dates not extracted from proposal/sheet. |
| **Class** | **(a) Not extracted** — **D2** (proposal periods), **D4** (sheet review-window note). |

**Related intra-doc sub-case (award letter only):** D3 **did** extract `reporting_period.end` multi-value: `14 October 2025` + `October to September`. E1 wrote **`reporting_period.end.ar1` = 2025-10-14** and **`reporting_period.end.cycle_description` = October to September** as **two facts**, not a conflict → see #9 / partial **(c)**.

---

### 6. Forecast-vs-actual scope (£880k / £920,420 vs £1.184m / £1.24m)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | **`880000` and `920420` absent** from all `extracted_json` and from KB fact values as aggregate keys. D4 emits **line-level** `financials.lines.OPn.n.budget/actual` only (`financials_totals.budget/actual: null`). Line budgets **sum to 880,000** and line actuals **sum to 920,420** in KB, but **no total-level candidates** exist. Award **1240000** present; proposal **1184000** absent. |
| **Candidates** | Per-line financial candidates (41 from xlsx) + `award_budget.amount`; **no** `financials.totals.*` or proposal budget. |
| **KB facts** | e.g. `financials.lines.op3_1.ar1_budget` = 146000; `award_budget.amount` = 1240000. **No** key for AR1 forecast/actual totals. |
| **E1 behaviour** | E1 **disambiguated by design** (full grant vs line AR1 spend are different semantic quantities per E1 prompt). No comparable pair at same `fact_key`. |
| **Class** | **(a) Not extracted** as **explicit total facts** — **D4** (sheet totals) + **D2** (proposal budget). Minor **(b)** risk if totals were keyed differently from grant amount, but root gap is missing aggregate candidates. |

---

### 7. Disaggregation arithmetic (684 vs sum 681)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | OP1.1 actual **684** extracted. Disaggregation cells (**58, 590, 33, 681**) **not in D4 output** (`681` / disagg rows absent from `extracted_json` and candidates). |
| **Candidates / KB** | Only `indicators.op1_1.ar1_actual` = 684. |
| **E1 behaviour** | Nothing to compare. |
| **Class** | **(a) Not extracted** — **D4 indicator extractor** (disaggregation rows out of scope). |

---

### 8. Disaggregation category misalignment (OP3.1)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | OP3.1 actual **392** extracted. Wrong-band disaggregation **not extracted** as structured fields. |
| **KB** | `indicators.op3_1.ar1_actual` = 392 only. |
| **E1 behaviour** | N/A — category error never represented in candidates. Answer key: **Gap / checker**, not numeric reconciler. |
| **Class** | **(a) Not extracted** — **D4**; downstream gap/validation, not E1 VALUE_MISMATCH. |

---

### 9. Awkward formatting / buried facts (money formats + reporting period)

| Stage | Evidence |
|-------|----------|
| **Extraction presence** | Award **£1,240,000** extracted. Proposal **£1,184,000 / £1.184m** **not extracted**. D3 **did** surface buried reporting-period alternative: candidate `reporting_period.end.stated_values[1]` = `"October to September"` (normalized **null**). |
| **Candidates** | Both AR1 end date and cycle-description candidates reach E1 (same document). |
| **KB facts** | `reporting_period.end.ar1` = **2025-10-14**; `reporting_period.end.cycle_description` = **October to September** (both persisted — neither dropped). |
| **E1 behaviour** | **No conflict flagged.** E1 **split** intra-doc alternatives into **separate semantic fact_keys** (consistent with reconciler prompt: disambiguate different meanings, do not force VALUE_MISMATCH). Test fixture `fcdo_bridgelight_award_letter_answer_key.json` expects intra-doc reporting-period tension to remain visible — E1 chose **disambiguation over conflict**. |
| **Class** | **(c) Matching keys not used / E1 disambiguation policy** for intra-doc award letter; **(a)** for missing proposal money formats (**D2/D3**). |

---

## Summary tally

| Class | Count | Planted issues |
|-------|-------|----------------|
| **(a) Not extracted** (one side or both missing from candidates) | **8** | #1, #2, #3, #4, #5, #6, #7, #8 (+ proposal-money part of #9) |
| **(b) Non-matching keys** (both sides exist but different `field_path`/`fact_key`) | **0** as primary cause | Endline `*.proposal_target` vs AR1 `*.ar1_*` splits are **intentional E1 semantics**, not answer-key conflicts |
| **(c) E1 did not flag** (both sides reached E1 under related semantics) | **1** | #9 intra-doc award `reporting_period.end` (also overlaps #5) |
| **(d) Undetermined** | **0** | — |

**E1-relevant planted conflicts (answer key says “Reconciler”):** #1, #4, #5, #6, #7 → **all fail before E1 compare** except partial #5/#9 intra-doc award-letter case → **(c)**.

**Gap-agent issues (not E1 conflicts by design):** #2, #3, #8.

---

## Why `conflicts_pre_gate1: []` — chain summary

```
Answer-key conflict pairs
  → D2/D3/D4 extracted_json   ← MOST PAIRS DIE HERE (612, 1184000, totals, disagg, proposal dates)
  → input_builder candidates  ← field_paths split proposal vs sheet (OP1.1 vs op1_1_*); no 612 candidate
  → E1 reconciler LLM         ← receives ≤1 value per semantic quantity; disambiguates grant vs AR1 lines
  → knowledge_bank_json       ← 71 facts, conflicts: []
```

**Code anchors (read-only):**

- Proposal candidates: targets only — `_flatten_proposal` → `indicators.{indicator_key}.target` (`input_builder.py`).
- Sheet candidates: `indicators.{row_id}.actual|target` with dotted row IDs (`OP1.1`) (`input_builder.py`).
- E1 disambiguation rule: different semantic quantities → separate `fact_key`, not conflict (`knowledge_bank_reconciler.py` system prompt).
- E1 absence rule: single-source silence ≠ conflict (same prompt).

---

## Fix-class direction (no implementation)

| Owner | Direction |
|-------|-----------|
| **D2 proposal extractor** | Extract progress-narrative **actuals** (612), programme **budget** (£1,184,000 variants), and **project/AR1 period** statements as grant-term-like candidates. |
| **D4 indicator extractor** | Extract **disaggregation rows**, **sheet AR1 total forecast/actual**, **review-period notes**, and explicit **missing-row / absent** markers for OP2.3 / OP4.2. |
| **Candidate builder** | Optional canonical key map so proposal vs sheet indicators align for compare (without merging endline vs AR1 milestone semantics). |
| **E1 reconciler** | Only if product wants intra-doc **VALUE_MISMATCH** for grant-terms `multi_value` fields (e.g. `reporting_period.end` contractual date vs inception-call phrasing) instead of dual facts. |

---

## Evidence index

| Artifact | Use |
|----------|-----|
| `04_FCDO_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx` | Oracle (9 rows) |
| `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json` | `conflicts_pre_gate1: []`, upload set, scoring table |
| Prod DB `5026ab66` `uploaded_documents.extracted_json` | Per-doc extraction audit (2026-06-01) |
| Prod DB `5026ab66` `donor_reports.knowledge_bank_json` | 71 facts, 0 conflicts |
| `input_builder.py` | Candidate `field_path` rules |
| `knowledge_bank_reconciler.py` | E1 disambiguation / absence rules |

---

**STOP** — diagnosis complete; no fix implemented.
