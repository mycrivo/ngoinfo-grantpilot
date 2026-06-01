# F1 citation-resolution BLOCK decomposition — report 6643d922

**Report ID:** `6643d922-150d-4000-b878-4025e7c9145a`  
**Deploy:** `9b430a1` (post C1+C2 hygiene + E3 logframe)  
**Walk artifact:** `FCDO_PLANTED_CONFLICT_POST_F1_WALK_6643d922.json`  
**Analysis date:** 2026-06-01  
**Method:** Read-only — walk artifact + prod DB snapshot (`facts{}`, `gap_answers{}`, persisted `content_json`). No walk re-run, no critic re-invocation, no source documents consulted.

## Headline bucket counts

| Bucket | Count | Meaning |
|--------|------:|---------|
| **A** — Mechanical drop (safe noise) | **2** | Malformed F1 key dropped; canonical KB entry exists |
| **B** — Genuine catch (keep) | **3** | Claim not supported by `facts{}` or `gap_answers{}` |
| **C** — Backfill miss (logic gap) | **16** | KB entry exists; not bound in `evidence_used[]`; C1/C2 did not repair |
| **Total** | **21** | A + B + C = 21 |

---

## Method

**Admissible sources (contract lock):** Only `knowledge_bank_json.facts{}` and `knowledge_bank_json.gap_answers{}` per `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md`. No raw uploads or extractor re-runs.

**BLOCK inventory:** All 21 entries from `f1_hygiene_audit.citation_resolution_flags` in the walk artifact (citation-coverage BLOCKs only; `total_critic_blocks` also equals 21 on this report).

**F1 citation fields:** Per-section `evidence_used[]`, `dropped_citations[]`, `remapped_citations[]`, `auto_citations[]` from persisted `content_json` (prod DB read-only).

**Classification rules:**

- **A:** Canonical key exists in KB; F1 emitted a malformed/wrong-shape citation listed in `dropped_citations`; C1 correctly refused to guess; critic BLOCK is fallout from missing valid cite.
- **B:** No matching value/text in `facts{}` or `gap_answers{}` for the flagged specific (including derived aggregates and wrong dates).
- **C:** Matching KB entry exists; claim appears in section prose; final `evidence_used[]` lacks the canonical `fact:`/`gap:` ref and neither `remapped_citations` nor `auto_citations` added it.

---

## Summary by bucket

### A — Mechanical drop (2)

- **B04** — `0.68` hardship follow-up: whitespace-malformed `fact: indicators.op3_3…y1_actual` dropped in `performance_and_conclusions`.
- **B10** — Annual review end date: wrong-index `fact:reporting.annual_review_period_0.end` dropped; canonical `.annual_review_period_1.end` exists.

### B — Genuine catch (3)

- **B01** — Report-form window `2025-04-01`–`2026-03-31` not in KB (KB carries award/grant dates instead).
- **B02** — Aggregate spend `694,860` / `653,000` not stored in KB (derived from line items).
- **B15** — Overrun `40,420` not in KB (derived from cited actual minus uncited budget).

### C — Backfill miss (16)

- **B03, B05–B09, B11–B14, B16–B21** — KB fact or gap answer supports the claim (or the spend/date sub-claim) but the binding `fact:`/`gap:` key is absent from that section’s final `evidence_used[]`.

---

## Per-BLOCK classification (21 rows)

| ID | Section | Claim (abbrev) | F1 emitted citation(s) | KB key checked (value) or absence | Drop / flag reason | Bucket | Rationale |
|----|---------|----------------|--------------------------|-------------------------------------|--------------------|--------|-----------|
| B01 | summary_and_overview | reporting period 2025-04-01 to 2026-03-31 | Prose only; `fact:reporting.obligation.*` cited (generic) | **Absent** for this window. KB: `reporting.annual_review_period_1.start` = 2024-10-15, `.end` = 2025-10-14; `grant.period.start/end` = 2024-10-15 / 2026-10-14 | no KB match | **B** | Model used report-creation window; not an admissible KB value. Critic correctly flags. |
| B02 | summary_and_overview | GBP 694,860 vs 653,000 aggregate spend | `fact:financials.lines.op*` (many line keys in eu) | **Absent** for 694860 and 653000 in facts{} and gap_answers{} | no KB match | **B** | Aggregates are synthesis-derived; line facts exist but these totals are not KB-stored. |
| B03 | summary_and_overview | 16 deduplicated caregiver records | None in section; 0 dropped | `gap:risk_and_safeguarding:indicator:funds_not_used_as_intended_risk` — answer_text contains “deduplicated 16 caregiver records” | recoverable-but-unrepaired | **C** | Admissible gap answer; summary `evidence_used[]` has 0 `gap:` refs. C2 did not backfill. |
| B04 | performance_and_conclusions | hardship follow-up proportion 0.68 | **`fact: indicators.op3_3_hardship_households_followup.y1_actual`** (dropped) | `indicators.op3_3_hardship_households_followup.y1_actual` = **0.68** | malformed key | **A** | Space after `fact:`; canonical fact exists; drop prevented cite → critic BLOCK on 0.68. |
| B05 | evidence_and_evaluation | review period 01-Oct-24 to 30-Sep-25 | None; `gap:data_quality_limitations` **not** in EE eu | `gap:evidence_and_evaluation:indicator:data_quality_limitations` — answer_text contains “01-Oct-24 to 30-Sep-25” | recoverable-but-unrepaired | **C** | Exact dates in gap_answers; EE section did not cite that gap key. |
| B06 | evidence_and_evaluation | Four schools late attendance registers | None; `gap:data_quality_limitations` **not** in EE eu | Same gap key — “Four schools submitted attendance registers late” | recoverable-but-unrepaired | **C** | Same gap answer; not bound in EE `evidence_used[]`. |
| B07 | risk_and_safeguarding | three schools lacking female focal teacher | None; `gap:realised_assumptions` **not** in RS eu | `gap:risk_and_safeguarding:indicator:realised_assumptions` — “three schools lacked a female focal teacher” | recoverable-but-unrepaired | **C** | Exact count in gap_answers; RS cites other gaps but not this one. |
| B08 | risk_and_safeguarding | 16 duplicate records removed | None; `gap:funds_not_used_as_intended_risk` **not** in RS eu | `gap:risk_and_safeguarding:indicator:funds_not_used_as_intended_risk` — “deduplicated 16 caregiver records” | recoverable-but-unrepaired | **C** | Admissible gap text; not cited in RS section. |
| B09 | risk_and_safeguarding | partner review period 01-Oct-24 to 30-Sep-25 | None in RS eu (PM cites `gap:data_quality_limitations`; RS does not) | `gap:evidence_and_evaluation:indicator:data_quality_limitations` — date range in answer_text | recoverable-but-unrepaired | **C** | Gap answer admissible; RS section missing cite. |
| B10 | risk_and_safeguarding | AR period end 14 October 2025 | **`fact:reporting.annual_review_period_0.end`** (dropped); `fact:reporting.annual_review_period_1.start` kept | `reporting.annual_review_period_1.end` = **2025-10-14** | malformed key | **A** | Wrong index (`period_0`); canonical `.period_1.end` in facts{}; end not in eu → critic BLOCK. |
| B11 | risk_and_safeguarding | four schools late attendance | None in RS eu | `gap:evidence_and_evaluation:indicator:data_quality_limitations` and `gap:programme_management_delivery_commercial_financial:indicator:partner_performance` — both mention four schools / late registers | recoverable-but-unrepaired | **C** | Admissible gap text exists; RS did not cite either gap key. |
| B12 | risk_and_safeguarding | 472 vs target 500 (op1_2 attendance) | `fact:indicators.op1_2_girls_attending_80pct.y1_target` in eu; **y1_actual omitted** | `indicators.op1_2_girls_attending_80pct.y1_actual` = **472** | recoverable-but-unrepaired | **C** | Actual in facts{}; critic names missing y1_actual cite (target only). C2 backfill miss. |
| B13 | risk_and_safeguarding | three remaining schools OP2.2 | None in RS eu | `gap:recommendations_and_actions:indicator:recommendations_from_current_review` — “three remaining schools” menstrual health | recoverable-but-unrepaired | **C** | Gap answer admissible; not in RS `evidence_used[]`. |
| B14 | programme_management | GBP 920,420 vs 880,000 Y1 budget | `fact:financials.y1_actual.total` in eu; **y1_budget.total omitted** | `financials.y1_actual.total` = 920420; `financials.y1_budget.total` = **880000** | recoverable-but-unrepaired | **C** | Both totals in facts{}; budget total never bound. |
| B15 | programme_management | GBP 40,420 overrun | Derived in prose | **Absent** — 40420 not in facts{} or gap_answers{} (components 920420 and 880000 exist separately) | no KB match | **B** | Derived delta; critic correctly flags unsupported derived figure. |
| B16 | programme_management | overspends OP1.1–OP4.3 | `fact:indicators.op1_1/op1_2/op2_1/op4_1*` in eu; **financials.lines** for those OPs absent | e.g. `financials.lines.op1_1.y1_actual` = 174850, `.y1_budget` = 162000; similar for op1_2, op2_1, op3_1, op3_2, op4_3 | recoverable-but-unrepaired | **C** | GBP line facts exist; critic asks for line-level spend cites, not indicator counts alone. |
| B17 | programme_management | underspends OP1.3, OP2.2, OP3.3, OP4.1 | `fact:financials.lines.op3_3.*`, `op1_3.y1_budget` only | `financials.lines.op1_3/op2_2/op4_1` actual+budget in facts{} | recoverable-but-unrepaired | **C** | Partial line binding; missing lines for underspend sub-claims. |
| B18 | programme_management | OP2.1 GBP 148,900 vs 121,000 | `fact:indicators.op2_1_*` only | `financials.lines.op2_1.y1_actual` = 148900; `.y1_budget` = 121000 | recoverable-but-unrepaired | **C** | Spend amounts in facts{}; indicator cites do not satisfy GBP line claim. |
| B19 | programme_management | OP1.1 GBP 174,850 vs 162,000 | `fact:indicators.op1_1_*` only | `financials.lines.op1_1.y1_actual` = 174850; `.y1_budget` = 162000 | recoverable-but-unrepaired | **C** | Same indicator-vs-financial line gap. |
| B20 | programme_management | OP4.1 GBP 32,700 vs 39,000 | `fact:indicators.op4_1_*` only | `financials.lines.op4_1.y1_actual` = 32700; `.y1_budget` = 39000 | recoverable-but-unrepaired | **C** | Same pattern. |
| B21 | programme_management | AR period 15 Oct 2024–14 Oct 2025; deadline 21 Nov 2025 | `fact:reporting.obligation.annual_review` only (generic) | `reporting.annual_review_period_1.start` = 2024-10-15; `.end` = 2025-10-14; `reporting.annual_review_pack_deadline` = **2025-11-21** | recoverable-but-unrepaired | **C** | Specific dates/deadline in facts{}; only generic obligation cited. |

---

## Hygiene audit appendix

From walk artifact `f1_hygiene_audit` + persisted `content_json`:

| Metric | Value |
|--------|------:|
| Citation-resolution BLOCKs | 21 |
| Total critic BLOCKs (this report) | 21 |
| Prior walk citation-resolution BLOCKs (~) | 55 |
| `evidence_used` refs (all sections) | 182 |
| `dropped_citations` (artifact aggregate) | 40 |
| Unicode digit keys in eu | 0 |

**Per-section F1 hygiene (content_json):**

| Section | dropped | remapped | auto | gap: in eu |
|---------|--------:|---------:|-----:|-----------:|
| summary_and_overview | 0 | 1 | 26 | 0 |
| performance_and_conclusions | 19 | 13 | 23 | 8 |
| evidence_and_evaluation | 8 | 1 | 22 | 7 |
| risk_and_safeguarding | 2 | 0 | 20 | 4 |
| programme_management_delivery_commercial_financial | 11 | 2 | 18 | 10 |
| recommendations_and_actions | 0 | 0 | 3 | — |
| detailed_output_scoring / value_for_money | 0 | 0 | 0 | — |

**Notable dropped-key cluster:** `performance_and_conclusions` — 19 drops, predominantly whitespace-malformed `fact: indicators.opN_N…` keys (canonical keys without space exist in `facts{}`). Only **B04** among the 21 BLOCKs maps directly to one of these drops; the cluster explains missing indicator cites that contribute to **C**-type BLOCKs elsewhere (e.g. financial line vs indicator binding in `programme_management`).

**Remapped / auto (totals):** 17 remapped, 112 auto_citations across sections — C1/C2 ran extensively but did not resolve the 16 **C** bucket BLOCKs.

---

## Decision input

**Further citation hygiene work:** **Warranted, but narrow in scope.** Only **2/21 (A)** and **3/21 (B)** are expected or correct critic behaviour at Gate 3; **16/21 (C)** indicate residual binding gaps where admissible `facts{}` or `gap_answers{}` entries were not attached to the critic’s `evidence_used[]` allowlist. The dominant **C** themes are: (1) gap-answer text not cited in the section that prose repeats it, (2) `financials.lines.op*` spend facts not bound when synthesis cites indicator keys instead, and (3) specific reporting dates/deadlines in `facts{}` not cited alongside generic obligation keys.

**Not a goal:** Driving BLOCKs to zero — the **3 B** bucket items (wrong report window, invented aggregates, derived overrun) are the critic working as intended and should remain visible at Gate 3.

**A-only follow-up (optional, low priority):** **2** mechanical drops (B04, B10) may yield marginal BLOCK reduction if F1 emission stops emitting space-prefixed and wrong-index keys; they are safe noise, not compliance failures.

---

*Read-only analysis. Single deliverable: this file. No code, schema, test, or walk changes.*
