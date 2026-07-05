# M&E Module — KB Starvation / Section-Visibility Diagnosis (read-only)

**Date:** 2026-06-14 · **Mode:** read-only diagnosis, no code/prod/walk changes · **Status:** findings only, STOP for owner.

**Evidence anchor (single walk):**
`docs/artefacts/me_module/audits/snapshots/pkg2_nlcf_rewalk_703f0dcf.json` (verdict `completed`) and its export `pkg2_nlcf_rewalk_export_703f0dcf.docx`. All three uploads read cleanly — `extraction_outcome = complete`, no degrade on any document (proposal 17/17 fields, award 10/10, monitoring 16/16 rows); reconcile produced **47 facts**, `reconciliation_outcome` non-degraded, `conflicts: 0`, `gap_answers: {}` (all 12 Gate-2 items skipped). **Nothing in this walk was lost to a degrade/timeout/parse failure.** Every loss below happened on a clean full read.

---

## PLAIN VERDICT

This is a **cluster of four independent fault classes, not one root.** Extraction starvation is real but it is **not** the primary or sole cause — and the most damaging fault is not starvation at all.

1. **Section-scoped visibility** (the worst): facts that ARE in the KB and citable are invisible to the section that should narrate them, so honest synthesis declares them "not available." This produces **false** "not available" statements — the report asserts something untrue about its own evidence — and is the direct cause of the self-contradiction (budget "not available" on one page, full budget table on another). Logged-deliberate mechanism (Package C.1), known follow-up (C.2 candidate); this walk is new evidence of its severity.
2. **Extraction-coverage gaps**: the extractor schemas have **no field** for named partners, consultation narrative, or the monitoring table's evidence/notes/change-note columns, so that content is never pulled even on a clean read.
3. **Reconciliation drop**: demographic disaggregation **was extracted** (age bands, rows 3–7) but the reconciler never promoted it into a KB fact.
4. **Render-label provenance leak + tripwire blind spot** (two findings): the reconciler's `semantic_label` carries raw spreadsheet provenance (`— budget (Table2!C12)`) into table identity cells, and the Package 1 leak tripwire has no pattern for spreadsheet A1-notation or the em-dash facet suffix, so it stayed silent.

The distinct fixes implied therefore fall in **four different layers** — synthesis-input visibility (builder), extractor schemas, reconciler fact-promotion, and render-label/tripwire — not a single extractor change. **None of this is a synthesis-strictness problem; the moat is behaving correctly given a starved or wrongly-scoped fact view.**

---

## THE CONTRAST CASE (why some data survived — the heart of it)

| Survived | KB fact keys | Why visible to its section |
|---|---|---|
| 5 difference indicators (148/120, 61/55, 14/18, 58%/65%, 27/24) | `indicators.ind1…ind6.actual/.target` | `difference_made.required_indicators` includes `outcome_indicators_where_available` → token **`indicators`** → matches every `indicators.*` key in `subset_facts_for_section` |
| 6 spend lines + total | `financials.lines.11…17.budget/.actual` | `spend_summary` declares a `required_tables` with `data_source="financials"` → grants the **`financials.`** prefix in `_fact_prefixes_for_section` |

**Structural difference between survived and lost data:** data survived when **both** held — (a) it was a cleanly-shaped numeric row that the reconciler filed under a recognised namespace (`indicators.*` / `financials.*`), **and** (b) it landed in a section whose archetype, declared table, or indicator tokens grant visibility to that namespace. Data was lost when **any** of: it had no extractor schema slot (never a fact); it was extracted but not promoted to a fact; or it became a fact under `indicators.*` but the section that should narrate it (project_story, learning, changes, community_involvement) has **no** visibility to `indicators.*`. The survivors are exactly the two namespaces that the NLCF template happens to wire through to a section; everything else is dark.

**Root mechanism of the visibility half** — `app/reports/services/report_inputs_builder.py`:
- `_SHARED_FACT_PREFIXES = ("grant.", "reporting.", "objectives.")` — the only namespaces every section sees.
- `_ARCHETYPE_FACT_PREFIXES` grants `indicators.`/`financials.` to **eight FCDO archetypes only**. **None of the seven NLCF archetypes** (`ARCH_PROGRESS_NARRATIVE`, `ARCH_PARTICIPATION_AND_COMMUNITY_VOICE`, `ARCH_OUTCOMES_WITH_STORIES_AND_NUMBERS`, `ARCH_LEARNING_REFLECTION`, `ARCH_ADAPTATION_AND_NEXT_STEPS`, `ARCH_BUDGET_VARIANCE_SUMMARY`, `ARCH_END_OF_GRANT_REFLECTION`) is in the map.
- So each NLCF section sees `indicators.*`/`financials.*` **only** if it declares a matching table (`spend_summary` → financials) or its `required_indicators` happen to contain a ≥4-char token that appears in the fact key (`difference_made` → `indicators` token). Every other NLCF section is restricted to `grant./reporting./objectives.` — i.e. blind to all indicator and financial facts.

---

## PER-LOSS FINDINGS

Tags: **extraction-coverage / reconciliation / section-visibility / render-label / tripwire-coverage.** Severity at fix time: **AMBER** (moat-adjacent — truthfulness or factual-surface risk) / **GREEN** (additive, no invention risk).

### Loss 1 — Named partner/collaboration examples (school, food pantry, GP link worker, tenants group, local mosque)
- **In KB?** No. **Extracted?** No — strings `food pantry`, `mosque`, `link worker`, `tenants` are **absent from the entire walk JSON**.
- **Stage of loss:** **EXTRACTION-COVERAGE.** `proposal_extractor` structured schema = `summary / activities / indicators / objectives` only. It captured 7 activities and the objectives, but has **no field** for named partners/collaborators. The content is never pulled, so it cannot become a fact.
- **Output behaviour:** `community_involvement` honestly says "did not include named examples of local partners or collaboration activity" — a **correct** refusal (the data genuinely isn't in the KB).
- **COVERED-BY-V2-BRIEF?** **No.** The brief treats extractors as reading "their supported formats correctly" and scopes only latency/reliability/`.docx` indicator-table reading; it does not anticipate clean-read **schema coverage gaps** for qualitative proposal content.
- **Tag:** extraction-coverage · **GREEN** (capture real content; no moat/invention risk).

### Loss 2 — Qualitative learning ("Food-first format worked best" / "Formal wellbeing survey had low response")
- **In KB?** **YES.** `indicators.monitoring_row9.actual = "Food-first format worked best"`, `indicators.monitoring_row10.actual = "Formal wellbeing survey had low response"` — both citable (`confirmed=False, coverage=single_source`, post-Gate-1). **Extracted?** Yes (monitoring rows 9/10).
- **Stage of loss:** **SECTION-VISIBILITY.** The `learning` section (`ARCH_LEARNING_REFLECTION`) has prefixes `{grant., reporting., objectives.}` and tokens `{what, worked, work, unexpected, findings, learning, useful, others}`. The fact key `indicators.monitoring_row9.actual` starts with none of the prefixes and contains none of the tokens, so `subset_facts_for_section` **excludes it**. `learning`'s synthesis saw zero learning facts and honestly wrote "the submitted records did not include enough completed learning evidence … what worked best, what did not work." **That statement is false at the document level** — the learning notes are in the KB.
- **Secondary contributor:** the reconciler filed two free-text *learning notes* under the `indicators.*` namespace (`monitoring_row9/row10.actual`). That namespacing choice is what puts them out of `learning`'s reach; the decisive loss point is visibility (the fact exists and is citable, the section simply cannot see it).
- **COVERED-BY-V2-BRIEF?** **No** — visibility is a synthesis-input concern, entirely outside the extractor brief.
- **Tag:** section-visibility · **AMBER** (false "not available" = truthfulness defect).

### Loss 3 — Session-delivery counts (88 of 96 sessions) + the "boiler repair" change note
- **Counts — In KB? YES.** `indicators.monitoring_row2.actual = 88`, `.target = 96` (indicator name "Number of hub sessions delivered"). **Extracted?** Yes.
  - **Stage of loss:** **SECTION-VISIBILITY.** Row2 is visible only to `difference_made` (via the `indicators` token), but the section that would naturally narrate delivery volume — `project_story` (`ARCH_PROGRESS_NARRATIVE`, prefixes `{grant,reporting,objectives}`, **no** indicator tokens) or `changes_and_next_steps` — cannot see `indicators.*` at all. `difference_made` had it in view but used the five outcome indicators, not the delivery count. Net: the count never surfaces.
- **Change note ("Tuesday sessions paused during boiler repair") — In KB? No. Extracted? No** — `boiler` is absent from the entire walk JSON.
  - **Stage of loss:** **EXTRACTION-COVERAGE.** The monitoring row schema fields are `indicator_name, indicator_ref, target, actual, unit, disaggregation, multi_value, source_locator, row_id`. The source row spans `A2:M2` (columns A–M) but only B/C/D + disaggregation are pulled; there is **no notes/evidence field**, so an evidence/change column is dropped at extraction.
- **COVERED-BY-V2-BRIEF?** **No** for both halves (visibility out of scope; the evidence-column schema gap is a coverage gap the brief does not anticipate).
- **Tag:** section-visibility (counts) + extraction-coverage (change note) · **AMBER** (counts: data present, unsurfaced) / **GREEN** (note: capture real content).

### Loss 4 — Demographic disaggregation (age/gender/vulnerability breakdown)
- **In KB?** No. **Extracted?** **YES** — `indicators[*].disaggregation` is populated for rows 3–7 (e.g. row 3 breakdown `Children 8-11 = 42`, with per-cell `source_locator`). The data was read.
- **Stage of loss:** **RECONCILIATION.** Reconcile completed and emitted 47 facts, but **none** is a disaggregation/breakdown fact — every `indicators.indN.*` fact is only `.actual`/`.target`. The reconciler consumed the indicator rows but **did not promote the `disaggregation` array into KB facts**, so the breakdowns vanished between a clean extraction and a clean reconcile.
- **Output behaviour:** `project_story` lists "demographic breakdowns were not available" — false; they were extracted, just never reconciled into facts.
- **COVERED-BY-V2-BRIEF?** **No.** Brief §7 covers reconciler JSON **malformation/degrade**; here reconcile succeeded and silently dropped a populated field — a different fault than the one the brief instruments.
- **Tag:** reconciliation · **GREEN** (promote a real extracted, source-located field; traceable, no invention) — borderline AMBER only because it currently feeds a false "not available."

### Loss 5 — Delivery-change notes ("coordinator started three weeks late", "extra cover needed during school holidays")
- **In KB?** No. **Extracted?** No — `three weeks late`, `school holidays` absent from the entire walk JSON.
- **Stage of loss:** **EXTRACTION-COVERAGE.** Same root as Loss 3's change-note half: the monitoring row schema has no evidence/notes field, and the proposal schema has no narrative-change field. The columns carrying these notes (E–M of the monitoring table) are not in the extractor schema.
- **Output behaviour:** `changes_and_next_steps` honestly says it "did not include enough confirmed evidence to describe specific changes." Correct refusal given an empty KB for these items.
- **COVERED-BY-V2-BRIEF?** **No** (clean-read schema coverage gap).
- **Tag:** extraction-coverage · **GREEN**.

### Loss 6 — Community-consultation narrative (26 parents, 14 young people, 7 older residents consulted Jan 2025; feedback cards; monthly volunteer catch-ups)
- **In KB?** No (no consultation counts/dates fact). **Extracted?** **Partial.** The *activity* "Participant feedback collection via short cards" and "Parent and carer drop-in sessions" were captured as `activities[]`, and `indicators.ind5_parent_feedback_examples.target = 20` came through — but the **consultation counts/dates/narrative** (`26 parents`, `14 young people`, `7 older` — all absent from the walk JSON) were not.
- **Stage of loss:** **EXTRACTION-COVERAGE.** The proposal schema (`activities/indicators/objectives`) has no consultation/engagement-narrative field; activities are captured as labels only (no embedded counts), so the specific consultation figures have no slot.
- **Output behaviour:** `community_involvement` did surface the ind5 feedback **target** (20) via the `examples` token, then honestly said it lacked examples of how the community shaped decisions — correct for the un-extracted specifics.
- **COVERED-BY-V2-BRIEF?** **No.**
- **Tag:** extraction-coverage · **GREEN**.

---

## THE SELF-CONTRADICTION (distinct fault — confirmed section-scoped visibility)

- **Symptom:** `project_story` body: *"the submitted records did not include a budget compared with actual spend summary for this section"* and assumption *"The budget compared with actual spend was not available in the submitted records"* — while `spend_summary` renders the full budget-vs-actual table (£78,500 / £78,460 and all six lines) from the **same** KB.
- **Mechanism (confirmed):** `project_story` is `ARCH_PROGRESS_NARRATIVE` → `_fact_prefixes_for_section` returns `{grant., reporting., objectives.}` only (archetype not in `_ARCHETYPE_FACT_PREFIXES`; no financials table; `required_indicators: []` → no tokens). `subset_facts_for_section` therefore hands `project_story` **zero** `financials.*` and **zero** `indicators.*` facts. Its synthesis honestly reported "not available" **within its scoped view**, which is **false at the document level**. `spend_summary` sees financials because its `budget_vs_actual` table declares `data_source="financials"`.
- **Same defect, broader:** `project_story`'s other assumptions — "Beneficiary numbers were not available," "attendance figures … not available" — are also **false**; `indicators.ind1.actual = 148` (people attending) etc. are in the KB and rendered by `difference_made`. `project_story` simply cannot see `indicators.*`.
- **Statement for the record:** **section-scoped visibility is producing FALSE "not available" claims for data that IS in the KB (and in some cases rendered elsewhere in the same document).** This is a coherence/truthfulness defect distinct from extraction starvation. It is **not** a moat-strictness issue: the moat correctly refuses what the section's fact view lacks; the fault is that the fact view is wrongly narrow.
- **Logged-deliberate?** The mechanism is from **Package C.1 (2026-06-13)** (`build_knowledge_bank_inputs_for_section` / `subset_facts_for_section`), and the C.1 re-walk note already flagged the shared-prefix scoping as a **C.2 candidate** follow-up ("if programme-level `objectives.*` must not alone unlock narrative sections"). So the mechanism is logged and the over-restriction is a known open item — **not** a surprise regression. This walk supplies the missing severity evidence: the scoping yields false negatives, not merely sparse sections.
- **Tag:** section-visibility · **AMBER**.

---

## THE PROVENANCE LEAK (two findings)

### (a) Label source — reconciler `semantic_label`
- **Evidence:** KB fact `financials.lines.12.budget` has `semantic_label = "Sessional youth workers — budget (Table2!C12)"` (`coverage=agreed`); lines 13–17 (all `coverage=agreed`) carry the same `— <facet> (Table2!Cxx)` shape; line 11 (`coverage=single_source`) is **clean**: `"Part-time project coordinator — budget"` (no cell ref). The export renderer uses `semantic_label` as the table identity cell, so the provenance lands in the funder-facing table.
- **Where it enters:** the **reconciler** model output. The `indicator_data_extractor` provides per-cell `source_locator: {sheet:"Table2", cell_range:"C12"}`; the reconciler folds the sheet/cell into the human label and appends the facet word (`— budget` / `— actual spend`). `knowledge_bank_reconciler.py` passes the model's `semantic_label` through verbatim (`semantic_label=fact.semantic_label`). The cell-ref appears specifically on **`coverage=agreed`** (cross-source-merged) facts and not on the lone `single_source` line — i.e. the reconciler adds the locator when reconciling/merging.
- **Tag:** render-label (origin: reconciler `semantic_label`) · **AMBER** (raw internal provenance on a funder-facing factual cell).

### (b) Tripwire blind spot — why `scan_identifier_leaks` returned `[]`
- The six `_LEAK_PATTERNS` (`app/reports/eval/docx_export_assertions.py`) match: colon item-keys (`word(:word){2,}`), dotted schema paths (`(financials|indicators|…)(\.x){2,}`), `[fact:]`/`[gap:]` brackets, `ARCH_…`, the enums `cannot_provide`/`not_applicable`, and the literal "the required template items."
- The leaked strings are **`Table2!C12`** (spreadsheet **A1 notation** — `Sheet!ColRow`, no colon, no dotted namespace) and **`— budget`** (em-dash + a plain word). Neither matches any pattern: A1-notation has no colon and `Table2` is not one of the namespace keywords with following dots; the em-dash suffix is ordinary text. So the scan finds nothing → `[]`, even though provenance is visibly in the cells.
- **Two uncovered shapes:** (1) spreadsheet **A1 cell-reference notation** (`<Sheet>!<Cell>` / `<Sheet>!<Range>`), and (2) the **em-dash facet suffix** (`— budget` / `— actual spend`) on entity labels.
- **Tag:** tripwire-coverage · **AMBER** (the moat's leak tripwire failed to fire on a real funder-facing leak).

---

## ROOT SUMMARY & PACKAGE BOUNDARIES

| # | Loss | In KB | Extracted | Stage of loss | Tag | Tier | V2-brief |
|---|------|:----:|:----:|---|---|:--:|:--:|
| 1 | Named partners | no | no | extraction schema (proposal: no partner field) | extraction-coverage | GREEN | no |
| 2 | Qualitative learning notes | **yes** | yes | section-visibility (learning blind to `indicators.*`) | section-visibility | AMBER | no |
| 3a | Session counts 88/96 | **yes** | yes | section-visibility (narrating section blind to `indicators.*`) | section-visibility | AMBER | no |
| 3b | "boiler repair" change note | no | no | extraction schema (no notes/evidence field) | extraction-coverage | GREEN | no |
| 4 | Demographic disaggregation | no | **yes** | reconciliation (extracted, not promoted to fact) | reconciliation | GREEN | no |
| 5 | Delivery-change notes | no | no | extraction schema (no notes/evidence field) | extraction-coverage | GREEN | no |
| 6 | Consultation narrative | no | partial | extraction schema (no consultation-narrative field) | extraction-coverage | GREEN | no |
| SC | Budget/beneficiary "not available" on project_story | **yes** | yes | section-visibility (false "not available") | section-visibility | AMBER | no |
| PL-a | `— budget (Table2!C12)` in table cell | n/a | n/a | render-label / reconciler semantic_label | render-label | AMBER | no |
| PL-b | tripwire silent on the leak | n/a | n/a | tripwire pattern coverage gap | tripwire-coverage | AMBER | no |

**Single root, or cluster?** A **cluster of four fault classes**, falling on four distinct package boundaries:

- **A. Section-scoped visibility** (losses 2, 3a, self-contradiction) — `report_inputs_builder.subset_facts_for_section` / `_ARCHETYPE_FACT_PREFIXES`. The single highest-severity class (it generates **false** "not available"). Logged-deliberate mechanism (C.1), pre-flagged C.2 candidate. **AMBER.**
- **B. Extraction coverage** (losses 1, 3b, 5, 6) — the extractor schemas (`proposal_extractor`, `indicator_data_extractor` row schema) have no fields for qualitative/semi-structured content (partners, consultation narrative, monitoring evidence/notes columns). All on clean full reads. **GREEN.**
- **C. Reconciliation promotion** (loss 4) — `disaggregation` extracted but never turned into KB facts. **GREEN.**
- **D. Render-label + tripwire** (PL-a, PL-b) — reconciler `semantic_label` carries spreadsheet provenance into table cells, and the Package 1 tripwire lacks patterns for A1-notation / em-dash facet suffix. **AMBER.**

**Reconciliation against the V2 Extractor Quality Brief:** the brief's entire model is **"full clean read vs degrade"** (latency, runtime, JSON reliability, `.xlsx` degrade rate, a `.docx` indicator-table *reader* capability). **Every loss in this walk occurred on a clean full read with a clean reconcile** — so the brief's trigger (degrade rate) would not fire here, and **none of the ten findings is covered by it.** The brief explicitly assumes "the extractors … read their supported formats correctly"; this diagnosis shows the gap is **schema coverage, fact promotion, and section visibility**, which are orthogonal axes the brief does not address. Class B (extraction coverage) is the nearest neighbour to the brief but is still a *new* item — the brief's §6 is about reading a logframe that arrives as a Word table, whereas here the monitoring table **was** read and its evidence columns were simply not in the schema.

---

## SCOPE NOTES (per contract)
- No fix, recommendation to loosen synthesis/moat, code, prod write, or live walk was produced. Every finding is framed as a pipeline data-loss point.
- Temporary read-only analysis scripts used to parse the committed walk JSON were deleted; no engine/extractor/reconciler/template files were modified.
- Single-walk evidence (NLCF `703f0dcf`). The FCDO walk (`5cb5c9b4`) did not export, so FCDO-side confirmation of these classes is not available from this evidence set.

**STOP — findings only. Owner adjudicates and sets package boundaries.**
