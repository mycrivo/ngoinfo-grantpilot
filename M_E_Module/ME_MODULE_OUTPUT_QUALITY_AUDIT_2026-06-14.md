# M&E Engine — Output-Quality & Integrity Audit

| | |
|---|---|
| **What this is** | Independent, read-only static audit of the M&E (Donor Report Writer) engine, scoped strictly to **funder-trust and output integrity** — can an NGO submit the generated report without embarrassment, and is every number/statement traceable to real evidence? |
| **Audited against** | Tree at commit `9531d2fbd11d2f19e7c4031bb334c5d9ac722035` (`9531d2f` — "Record Package C.1 close in decision log with re-walk evidence pointers"), branch `claude/eager-planck-vt2d49`. This is the commit that records the C.1 owner-confirming re-walk evidence the audit is anchored to. |
| **Date** | 2026-06-14 |
| **Status** | **READ-ONLY FINDINGS. No fixes proposed, no code changed, no effort estimated.** This document is a prioritized findings record only. |
| **Primary evidence** | `docs/artefacts/me_module/audits/snapshots/c1_nlcf_rewalk_d8e7518b.json` (full walk: KB facts, per-section content, claims, bind status, caveats) · `…/c1_nlcf_rewalk_export_d8e7518b.docx` (the rendered NGO-facing document) · `…/p3_b3_export_nlcf_df7450dc.docx`, `…/p3_b3_export_fcdo_7cdcc3a8.docx`, `…/p3_7_fcdo_export_1beb588b.docx` (cross-funder exports) · `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` (authoritative LOCKED decisions) · `TEMPLATE_INSTANCE_NLCF.json`, `TEMPLATE_INSTANCE_FCDO.json` (funder templates). |
| **Walk conditions** | The committed `d8e7518b` walk is a deliberate **worst case**: the thin 3-file NLCF docset with **all 13 gaps skipped** at Gate-2. Findings distinguish (a) defects that occur on **any** input from (b) behaviours that are a **consequence of the skip-all worst case**. The latter are tagged `INPUT-DEPENDENT? Yes` and are not treated as code defects unless the engine could avoid them without inventing data. |

> **The one question every finding ladders up to:** *"Would an NGO submit this report to a funder without embarrassment, and can we trust every number and statement on the page as traceable to real evidence?"* Anything not bearing on funder-trust or output integrity is out of scope (code style, performance, test-coverage, architecture preference).

**Tag legend**
- **SEVERITY:** `moat-breach-risk` (violates the core promise that no unverified/degraded data becomes a stated fact, and that internal refs never surface) · `funder-trust` · `quality-polish`.
- **LAUNCH-IMPACT:** `blocks-launch` · `should-fix-pre-launch` · `post-launch-ok`.
- **SURFACE:** file/function, and which NGO-facing output it reaches.
- **ROOT:** single shared cause vs isolated (tells us the package boundary of a fix).
- **INPUT-DEPENDENT?:** `yes`/`no`, per the worst-case framing above.

---

## VERDICT

**Not submittable today.** The committed worst-case walk produces prose that is honest in *meaning* and clean in its *numbers* — every stated figure (14 volunteers, target 18, target 20) binds to a real fact, and the engine correctly refuses to invent the feedback actual it lacks. That core moat (no invented numbers) is holding. But two things an NGO would be embarrassed by, and one that breaks the moat's "internal refs must NEVER surface" promise, are live in the *committed* export:

1. **Machine refs leak into the NGO-facing "Assumptions & Caveats" page** — `spend_summary:table:budget_vs_actual`, `difference_made:indicator:beneficiary_numbers`, `changes_and_next_steps:indicator:support_needed`, etc., printed verbatim. This is a moat breach, not cosmetics, and it shipped in the owner-confirming walk.
2. **Funder-required tables never render** — 0 Word tables across NLCF *and* FCDO, despite headings and data present. NLCF budget figures are dumped as prose under a "Budget compared with actual spend" heading; FCDO ships 5 table headings with nothing beneath them.
3. **No central scrubber** — the assumptions surface has zero sanitization, and the body scrubber only catches bracketed `[fact:/gap:]` markers, so the leak class can recur on any input and on any NGO-facing surface.

**Top 3 between us and "yes":** (A1) scrub/abolish raw refs in the caveats path; (D1) make funder-required tables render the data already in the KB; (A2/E2) install one identifier-redaction chokepoint covering every NGO-facing surface + an export assertion that fails the build on a leak.

---

## Summary table (sorted: SEVERITY, then LAUNCH-IMPACT)

| ID | Severity | Launch-impact | NGO-facing surface | Root | Input-dep? |
|----|----------|---------------|--------------------|------|-----------|
| [A1](#a1--raw-gaprequirement-keys-leak-into-the-assumptions--caveats-appendix) | moat-breach | blocks-launch | Assumptions & Caveats appendix | shared (no assumption scrub) | No |
| [D1](#d1--funder-required-tables-never-render-0-tables-nlcf--fcdo) | funder-trust | blocks-launch | every funder table section (0 tables) | shared (renderer handles 2 of N) | No |
| [A2](#a2--body-prose-scrubber-cannot-catch-bare-refs-only-bracketed-markers--arch_) | moat-breach (latent) | should-fix-pre-launch | section body prose | shared (scrubber too narrow) | Yes |
| [A3](#a3--insufficiency-path-colon-delimited-refs-survive-and-a-generic-placeholder-is-emitted) | funder-trust + moat | should-fix-pre-launch | insufficiency section prose | isolated, same class | Yes |
| [D2](#d2--renderer-limitation-rationalized-as-an-evidence-gap-misleading-honesty) | funder-trust | should-fix-pre-launch | model caveat (outcomes table) | couples D1b | No |
| [B1](#b1--meaning-integrity-is-clean-the-ref-leak-breaks-the-legibility-of-the-honesty-itself) | funder-trust | should-fix-pre-launch | caveats (legibility) | couples A1 | No |
| [E2](#e2--the-export-machine-check-gate-has-no-leak-assertion-why-a1-shipped) | funder-trust (guardrail) | should-fix-pre-launch | export gate (tripwire missing) | isolated | No |
| [E1](#e1--terminology-substitution-produces-an-awkward-lowercase-mid-sentence-heading) | quality-polish | should-fix-pre-launch | table/section headings | isolated | No |
| [C2](#c2--residual-qualitative-claims-bind-on-ref-existence-alone-no-content-check) | funder-trust (bounded) | post-launch-ok | qualitative claim binding | isolated | Yes |
| [C1](#c1--number-binding-is-clean-in-the-committed-walk) | — clean — | — | number binding | — | n/a |
| [B (meaning)](#b--honesty-legibility) | — clean — | — | refusal phrasing | — | n/a |
| [E3](#e3--sparse-sections-restating-objectives-is-input-dependent-not-a-defect) | — input-dependent, not a defect — | — | sparse-section prose | — | Yes |

**Single shared root for the two blockers:** A1 and D1 are each one cause with many surfaces — (A1) no identifier-redaction chokepoint covering the assumptions/prose/insufficiency surfaces; (D1) a table renderer that recognizes only two hardcoded key shapes while every funder template declares more. Both are contained, package-sized boundaries.

---

## A — Machine-legibility leaks

> **Class definition:** every path where an internal identifier — schema key, requirement ref, enum value, `fact_key`, `section_key`, gap `item_key` — can reach NGO-facing text (section prose, caveats, insufficiency statements, table labels, headings, export). The moat states internal requirement refs and funder-owned fields must **NEVER** surface to the NGO.

### A1 — Raw gap/requirement keys leak into the "Assumptions & Caveats" appendix
**`[CONFIRMED IN COMMITTED EXPORT]`**

| Tag | Value |
|---|---|
| **SEVERITY** | moat-breach-risk |
| **LAUNCH-IMPACT** | blocks-launch |
| **SURFACE** | Synthesis model output → `content.assumptions` → `app/reports/export/docx_renderer.py:236-237,245` (`collected_assumptions.extend(...)` → `add_assumptions_appendix`) → `app/core/docx_presentation.py:204-212` (`add_assumptions_appendix`) → the funder-facing **"Assumptions & Caveats"** page of the `.docx`. |
| **ROOT** | **Shared.** Assumptions are sanitized **nowhere**. |
| **INPUT-DEPENDENT?** | **No** — fires whenever model synthesis runs and notes a skipped/missing item. This is the live path: `d8e7518b` is the owner-confirming *completed* walk. |

**What's wrong.** `app/reports/services/synthesis_output_hygiene.py::sanitize_generated_content` processes only the section `text` and `evidence_used` list — the `assumptions[]` array is passed through untouched (synthesis service → DB `content_json` → export). The body-prose scrubber `_strip_internal_tokens` (see A2) is never applied to the appendix at all. So whatever the model writes into `assumptions[]` reaches the NGO-facing page verbatim.

**Contributing cause (why the model emits the keys).** The synthesis prompt `app/reports/ai/prompts/synthesis.py` dumps the **full knowledge bank into the model context** — including the colon-delimited gap `item_key`s — and explicitly instructs the model to "note the gap in `assumptions[]`":
- L43: "`source_refs[]`: exact `fact:` or `gap:` keys from `report_inputs.knowledge_bank`"
- L53: "Text drawn from a gap answer → `gap:{item_key}`"
- L143-144: "If insufficient evidence for a required indicator or table row, **note the gap in `assumptions[]`** and write around it without fabricating numbers."

The model does exactly that and echoes the raw keys. Nothing in the prompt or downstream says assumptions must be plain English with no identifiers.

**Evidence — verbatim strings in `c1_nlcf_rewalk_export_d8e7518b.docx`, "Assumptions & Caveats" section** (also present in `c1_nlcf_rewalk_d8e7518b.json` under the per-section `content.assumptions`):
- "No budget versus actual spend summary was available from gap answer **`spend_summary:table:budget_vs_actual`**."
- "A full budget versus actual comparison was not available because **`spend_summary:table:budget_vs_actual`** was marked cannot_provide…"
- "No beneficiary numbers were available from gap answer **`difference_made:indicator:beneficiary_numbers`**."
- "No gap answer content was provided for **`changes_and_next_steps:indicator:changes_made`**." (and `:planned_changes`, `:support_needed`)

This is the seed-defect class reproduced in the latest committed walk.

**Decision-log check (is this a blessed behaviour? No).** `ME_MODULE_DECISION_LOG.md` D-045 (2026-06-04) states "stored `content_json` prose was always clean; defect was export-only" — but that fix addressed only **body-prose markers** at the render layer (`canonical_to_funder` labels-only, whole-marker citation removal). It never covered the **assumptions appendix**, which is where this leak lives. This is a genuine divergence, not a logged decision.

---

### A2 — Body-prose scrubber cannot catch bare refs (only bracketed markers + `ARCH_`)

| Tag | Value |
|---|---|
| **SEVERITY** | moat-breach-risk (latent) |
| **LAUNCH-IMPACT** | should-fix-pre-launch |
| **SURFACE** | `app/reports/export/docx_renderer.py:29-30,62-68` (`_CITATION_MARKER_RE` = `\s*\[(?:fact\|gap):[^\]]+\]\s*`, `_ARCHETYPE_RE` = `\bARCH_[A-Z0-9_]+\b`, applied in `_strip_internal_tokens`) → section body prose in the `.docx`. |
| **ROOT** | **Shared** with A1 — same missing comprehensive identifier redaction. |
| **INPUT-DEPENDENT?** | **Yes** — no body leak was observed in committed exports; the model placed refs in `assumptions[]`, not body prose. The risk is that the body surface is structurally unprotected. |

**What's wrong.** `_strip_internal_tokens` only removes square-bracketed `[fact:…]` / `[gap:…]` citation markers and `ARCH_*` archetype tokens. A **bare** identifier in body prose — e.g. `section:indicator:item`, `financials.lines.part_time_coordinator.budget`, or a raw `gap:`-less key — would render verbatim. The body is not protected against the same identifier class that A1 leaks through the (entirely unscrubbed) assumptions path.

---

### A3 — Insufficiency path: colon-delimited refs survive, and a generic placeholder is emitted
**`[SEED DEFECT 2 — the "the required template items" class]`**

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust (placeholder) + moat-breach-risk (colon survival) |
| **LAUNCH-IMPACT** | should-fix-pre-launch |
| **SURFACE** | `app/reports/services/section_prose.py:51-77` (`_humanize_requirement_refs`, `build_insufficiency_statement`) → NGO-facing section prose, used when a section has zero citable inputs (the Package C.1 honest-insufficiency path). |
| **ROOT** | **Isolated** assembly point, same class as A1/A2 (no shared scrubber). |
| **INPUT-DEPENDENT?** | **Yes** — fires only when a section routes to `insufficient_data`. It did **not** fire in `d8e7518b` (all 6 sections bound). It is the intended path for genuinely empty sections per the Package C.1 decision (`ME_MODULE_DECISION_LOG.md`, 2026-06-13), and the earlier P3-8 NLCF freeze (`588c3e7d`) exercised it. |

**What's wrong.** `_humanize_requirement_refs(refs)` does only `ref.replace("_", " ")`. If a ref is a full path such as `changes_and_next_steps:indicator:changes_made`, the underscores become spaces but the `:` separators **survive** into NGO-facing prose. And when `refs` is empty it returns the literal string **"the required template items"** — the confirmed seed-defect-2 generic placeholder — instead of named, human requirements. Both branches reach the funder-facing insufficiency statement built by `build_insufficiency_statement`.

---

### A4 — Root summary: no single humaniser/redaction chokepoint

NGO-facing text is assembled at **≥5 independent surfaces**, with **no single scrubber** all of them pass through:

1. Section **body prose** — sanitized by `sanitize_prose` (control chars) + `_strip_internal_tokens` (bracketed markers + `ARCH_` only).
2. **Assumptions / caveats appendix** — **no sanitization at any stage** (A1).
3. Deterministic **insufficiency prose** — `_humanize_requirement_refs` strips underscores only; emits a generic placeholder (A3).
4. **Table cells** — `app/reports/export/kb_table_renderer.py`.
5. **Headings** — section labels + table labels, via terminology substitution (E1).

A1–A3 are the same root cause manifesting wherever a surface lacks coverage. The fix boundary is one package: a single identifier-redaction pass every NGO-facing surface must clear.

---

## B — Honesty-legibility

> **Class definition:** where the engine correctly refuses to invent, is the refusal stated in plain funder-readable language that preserves the exact "we did not have this" meaning, without drifting into overstatement (implying data existed/matched when it did not)?

### B1 — Meaning-integrity is clean; the ref-leak breaks the legibility of the honesty itself

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust |
| **LAUNCH-IMPACT** | should-fix-pre-launch (couples to A1) |
| **SURFACE** | Refusal phrasing in section prose + the caveats appendix. |
| **ROOT** | Couples to A1. |
| **INPUT-DEPENDENT?** | No |

**Assessment — substantively CLEAN.** The engine's refusals read in plain, exact English with **no overstatement drift**. Examples from `d8e7518b`:
- "the submitted records available for this section did not include the actual number collected, so we have not stated an achievement figure where evidence was missing."
- "we have described the project story in line with the confirmed objectives and outcomes, but we have not added unsupported numbers or detail."

It consistently says "not available / not provided in submitted records" without ever implying data existed or matched. **The "we did not have this" meaning is preserved end-to-end — state this plainly.**

**The only damage is A1.** A caveat such as "No gap answer content was provided for `changes_and_next_steps:indicator:support_needed`" simultaneously (a) preserves the honest meaning *and* (b) exposes machine internals — so the honest disclosure itself looks machine-generated, eroding the trust it exists to build.

---

## C — Numeric & claim integrity

> **Class definition:** can any stated number, date, or specific be surfaced WITHOUT a binding to a real fact? In the committed walk, broad programme-objective facts bind to claims in sections needing specific evidence — is that safely confined to honest framing, or could a branch let it read as an unsupported assertion?

### C1 — Number-binding is CLEAN in the committed walk
**`[PATH IS CLEAN — stated plainly]`**

| Tag | Value |
|---|---|
| **SEVERITY** | — clean — |
| **LAUNCH-IMPACT** | — |
| **SURFACE** | `app/reports/services/synthesis_claim_binding.py` (`bind_structured_claims`) → all stated numbers in section prose. |
| **INPUT-DEPENDENT?** | n/a |

**Assessment.** Every specific in the `difference_made` section binds correctly (from `c1_nlcf_rewalk_d8e7518b.json`, per-section `content.claims`):
- "14 community volunteers" → `fact:indicator.op_volunteers_recruited.actual` (value_token `14`), `bind_status=bound`.
- "target of 18" → `fact:indicator.op_volunteers_recruited.target` (value_token `18`), `bound`.
- "target… was 20 short comments" → `fact:indicator.op_parent_feedback.target` (value_token `20`), `bound`.
- The feedback **actual** is correctly omitted — only the target was evidenced — and the prose says so.
- Broad `objectives.*` facts bind only to "aimed to" / "intended differences" framing.

`bind_structured_claims` (`synthesis_claim_binding.py:266-288`) replaces any unbound numeric token with the honest-omission phrase, so **no number reaches the page without a real fact binding.** The moat's central promise is intact here.

---

### C2 — Residual: qualitative claims bind on ref-existence alone (no content check)

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust (bounded; critic-mitigated) |
| **LAUNCH-IMPACT** | post-launch-ok |
| **SURFACE** | `app/reports/services/synthesis_claim_binding.py:289-290` (empty `value_tokens` → `bind_status="bound"` purely if a citable ref exists); `_value_in_source:148-149` returns `True` for an empty normalized token → qualitative claims in any narrative section. |
| **ROOT** | Isolated. |
| **INPUT-DEPENDENT?** | **Yes** — did not trigger in `d8e7518b`; the prose stayed honest. |

**What's wrong (bounded).** A qualitative clause (empty `value_tokens`) is marked `bound` by attaching any citable ref, with **no verification that the clause is actually supported by that fact's content.** A model could pair a broad `objectives.*` fact with an overstated qualitative sentence and it would bind `bound`; the **fact-safety critic is the only backstop**.

**Why this is logged, not a fresh defect.** `ME_MODULE_DECISION_LOG.md` (2026-06-13, Package C.1 re-walk note for `d8e7518b`) explicitly records that the reconciler emitted two `objectives.*` facts and the shared-prefix scoped-facts fallback routed sparse sections to synthesis (rather than the `insufficient_data` path) — "documented for follow-up (**C.2 candidate**), not a rollback." So this is logged, expected behaviour to monitor, not an unflagged risk.

---

## D — Structured-output gaps

> **Class definition:** where templates require tables (budget vs actual, logframe/outcomes) but the renderer emits prose or nothing. The committed export has **0 Word tables** despite a "Budget compared with actual spend" heading and spend figures present as prose.

### D1 — Funder-required tables never render (0 tables, NLCF + FCDO)
**`[CONFIRMED ACROSS 4 COMMITTED EXPORTS]`**

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust (NLCF budget figures dumped as prose ≈ moat-adjacent) |
| **LAUNCH-IMPACT** | blocks-launch |
| **SURFACE** | `app/reports/export/kb_table_renderer.py:179-201` (`table_rows_for_definition`) → `app/reports/export/docx_renderer.py:212-227` → every funder table section in the `.docx`. |
| **ROOT** | **Shared.** `table_rows_for_definition` handles exactly two hardcoded `(table_key, data_source)` pairs and returns `None` for all others. |
| **INPUT-DEPENDENT?** | **No** |

**Confirmed empties.** Word `<w:tbl>` count is **0** in all four committed exports: `c1_nlcf_rewalk_export_d8e7518b.docx`, `p3_b3_export_nlcf_df7450dc.docx`, `p3_b3_export_fcdo_7cdcc3a8.docx`, `p3_7_fcdo_export_1beb588b.docx`. Table **headings** still render (proving `required_tables` reach the renderer via `report_sections_json`, passed at `report_export_service.py:105`), then no table body follows.

**Against stated intent.** `ME_MODULE_DECISION_LOG.md` S3 (line ~219) declares deterministic NLCF `budget_vs_actual` and logframe `output_score_table` rendering "**from KB facts; wired in `docx_renderer` + export service (no LLM)**." So 0 tables is a **defect against declared-complete intent**, not a deferral. (Line ~199 separately flags `budget_vs_actual` typing parity as a queued follow-up.)

#### D1a — NLCF `budget_vs_actual`: data-key mismatch (`INPUT-DEPENDENT? No`)
`build_budget_vs_actual_rows` (`kb_table_renderer.py:99-117`) requires fact keys matching:
```
^financials\.lines\.(OP\d+\.\d+)\.(y1_actual|y1_budget|actual|budget)$
```
The actual NLCF facts in `c1_nlcf_rewalk_d8e7518b.json` are:
```
financials.lines.part_time_coordinator.budget / .actual
financials.lines.sessional_youth_workers.budget
financials.lines.row_13.budget / .actual   (also row_14, row_15, row_16, row_17, row_12)
```
**None** match the required `OP\d+\.\d+` line-identifier shape (that shape is FCDO logframe style). Zero regex matches → `[]` → `table_rows_for_definition` returns `None` → no table. The data is fully present and is rendered in **prose** instead: "We spent £29,950 on the part-time project coordinator against a budget of £31,200… Our total spend was £78,460 against a budget of £78,500." The funder asked for a "Budget compared with actual spend" table; the engine has every number and emits prose.

#### D1b — `data_source="manual"` tables have no renderer branch at all (`INPUT-DEPENDENT? No`)
`table_rows_for_definition` has no handler for `data_source="manual"` → always `None`. Affected required tables:
- **NLCF:** `outcomes_summary` (label "Outcomes, evidence and examples").
- **FCDO:** `review_summary_sheet`, `evidence_quality_matrix`, `risk_register_update`, `recommendations_action_plan`.

Confirmed in `p3_b3_export_fcdo_7cdcc3a8.docx`: **5 dangling H2 table headings** render with **zero tables** beneath any — "Annual Outcome Assessment", "Evidence quality and gaps", "Risk rating / assumptions / controls update", "Delivery, commercial and financial performance", "Recommendations and action points".

#### D1c — Other indicators/financials FCDO tables don't match the two handled keys (`INPUT-DEPENDENT? No`)
FCDO `outcome_assessment`, `vfm_measures` (`data_source="indicators"`) and `delivery_financial_performance` (`data_source="financials"`) do not match the only handled `table_key`s (`output_score_table`, `budget_vs_actual`) → `None`. Of FCDO's **8** declared required tables, the renderer can satisfy at most **one** (`output_score_table`).

#### D1d — Even the one handled FCDO table produced 0 tables in committed exports
`output_score_table` (`indicators`, gated on `format_rules_json.logframe.enabled`) is the single path with a renderer branch, yet committed FCDO exports show **0** tables — i.e. the logframe wiring / OP-keyed-fact dependency is not landing in practice either. Noted.

**Net:** of NLCF's 2 required tables, 0 render; of FCDO's 8 required tables, 0 render. Every funder-required structured output currently renders as nothing (or as prose for NLCF spend).

---

### D2 — Renderer limitation rationalized as an evidence gap (misleading honesty)

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust |
| **LAUNCH-IMPACT** | should-fix-pre-launch |
| **SURFACE** | Model-emitted caveat in `d8e7518b`, "Assumptions & Caveats". |
| **ROOT** | Couples to D1b. |
| **INPUT-DEPENDENT?** | No |

**What's wrong.** The committed caveat reads: "A required outcomes table was not populated **because the output schema did not include a table field** and the submitted records did not provide enough verified row-level detail…" The schema **does** define the `outcomes_summary` table (`TEMPLATE_INSTANCE_NLCF.json`, `difference_made.required_tables`); the renderer simply cannot fill `manual` tables (D1b). Presenting an **engine** limitation to the funder as a **data** limitation misattributes the engine's gap to the NGO's evidence — a trust risk.

---

## E — Other funder-trust / integrity findings

### E1 — Terminology substitution produces an awkward lowercase mid-sentence heading

| Tag | Value |
|---|---|
| **SEVERITY** | quality-polish |
| **LAUNCH-IMPACT** | should-fix-pre-launch |
| **SURFACE** | `app/reports/export/docx_renderer.py:210,217` (`_apply_terminology` applied to section/table labels) → headings in the `.docx`. |
| **ROOT** | Isolated. |
| **INPUT-DEPENDENT?** | No |

**What's wrong.** In `c1_nlcf_rewalk_export_d8e7518b.docx`, the NLCF table label "Outcomes, evidence and examples" is rendered as the heading **"differences you are making, evidence and examples"** — the `canonical_to_funder` mapping ("Outcomes" → "differences you are making") was applied inside a label, producing a broken sentence-fragment heading with a lowercase start. It also heads a table that never renders (couples with D1b), compounding the oddness.

---

### E2 — The export machine-check gate has no leak assertion (why A1 shipped)

| Tag | Value |
|---|---|
| **SEVERITY** | funder-trust (guardrail gap) |
| **LAUNCH-IMPACT** | should-fix-pre-launch |
| **SURFACE** | `app/reports/eval/docx_export_assertions.py` (the "Docx machine-check", decision-log S4). |
| **ROOT** | Isolated. |
| **INPUT-DEPENDENT?** | No |

**What's wrong.** The export assertion module contains **no** check against identifier-leak patterns (`:indicator:`, `:table:`, `financials.lines.*`, bare `section:item` refs) or against assumptions content. This is precisely why the A1 moat-breach reached a committed, owner-confirmed export undetected. The output defect is A1; this is the missing tripwire that let it through.

---

### E3 — Sparse sections restating objectives is INPUT-DEPENDENT, not a defect
**`[noted, per worst-case framing]`**

| Tag | Value |
|---|---|
| **SEVERITY** | — (input-dependent, not a code defect) |
| **LAUNCH-IMPACT** | — |
| **SURFACE** | Section prose in the worst-case walk. |
| **INPUT-DEPENDENT?** | **Yes** |

**Assessment.** The repeated restating of objectives across sections is a direct consequence of the skip-all 3-file worst case (no specifics supplied) — not a code defect. The engine stayed honest throughout ("we have described the project story in line with the confirmed objectives… but we have not added unsupported numbers"). The only engine-avoidable angle is C2: the scoped-facts fallback let sparse sections **synthesize** rather than route to the cleaner deterministic insufficiency prose — already logged as the C.2 follow-up. **Not flagged as a code defect.**

---

## Appendix — Methodology & traceability

- **Read-only.** No code, prod, or live walk was touched. Findings are anchored to committed artefacts and source at `9531d2f`.
- **Export inspection.** Word table counts and leaked-string checks were taken directly from the committed `.docx` files' `word/document.xml` (`<w:tbl>` count; verbatim text of the "Assumptions & Caveats" section).
- **KB / claim inspection.** Per-section `content.assumptions`, `content.claims` (with `bind_status`, `source_refs`, `value_tokens`), and the financial `fact_key`s were read from `c1_nlcf_rewalk_d8e7518b.json`.
- **Template shapes.** `required_tables` (`table_key`, `data_source`, `columns`, `label`) and `logframe.enabled` were read from `TEMPLATE_INSTANCE_NLCF.json` and `TEMPLATE_INSTANCE_FCDO.json`.
- **Locked-decision check.** Every finding was checked against `ME_MODULE_DECISION_LOG.md` so logged deliberate behaviours (e.g. the C.2 broad-objective binding follow-up) are tagged as such and not mis-filed as defects.

**END OF FINDINGS — read-only, no fixes proposed.**
