# R0 — KB consumer seam audit (blast radius for canonical fact/gap key names)

**Scope:** Every consumer of `donor_reports.knowledge_bank_json` (`facts{}` / `gap_answers{}`) in the M&E module.
**Question answered:** What breaks, and where, if fact/gap key **NAMES** become canonical and stable — values and the KB envelope shape unchanged?
**Deploy:** `633e05e` (current `HEAD`, branch `claude/zen-sagan-HppBG`).
**Date:** 2026-06-02
**Method:** Read-only static trace. No walk, no agent/model invocation, no edits. Builds on `F1_CITATION_BINDING_DIAGNOSIS_b91ae3e0.md`.

> **Reference note.** Of the four canonical references, `ME_MODULE_MASTER_MEMORY.md`, `FUNDER_TEMPLATE_SCHEMA.md`, and `F1_CITATION_BINDING_DIAGNOSIS_b91ae3e0.md` are present and were read. `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` **does not exist** in the repo, git history, or filesystem (same as recorded in the prior diagnosis) — the provenance/source contract was instead taken from the live code (`report_fact_safety_service`, `synthesis_output_hygiene`) and `FUNDER_TEMPLATE_SCHEMA.md §2.1b evidence_rules`.

---

## Headline

| | Count |
|---|------:|
| **NAME-SENSITIVE consumers** (behaviour depends on literal fact/gap key strings) | **5** — 4 wired + 1 latent/unwired |
| **VALUE-ONLY consumers** (read values/structure; do not depend on key strings) | **8** |
| **Total KB consumers inventoried** | **13** |

**Locked-stage go/no-go: GO to canonicalise, with ONE guardrail.**

- **Gate 1 confirm (E2): SAFE.** Confirmation is a whole-KB snapshot overwrite + `gate1_confirmed_at` stamp; validation checks per-fact *value-side* fields and uses `fact_key` only in error strings. Nothing binds to a specific key name, and there is no cross-run name comparison. Canonical names cannot mis-bind it.
- **F2 critic resolver: SAFE — improves.** Exact `dict.get`; benefits from stable names, breaks on nothing when names are canonical and consistent within a run (this is the seam the prior diagnosis already flagged as wanting stable names).
- **E3 gap agent: SAFE *iff* one invariant holds.** The LLM path is semantic/value-driven (robust). The **deterministic logframe path** (`derive_missing_logframe_actuals`) is NAME-SENSITIVE: it extracts an `opN_N` indicator id and a facet token (`.target`/`.actual`/`ar1_*`/`_actual`/`.milestone`) from the fact-key **string** (with fallback to `semantic_label` and provenance). Canonicalisation is safe **only if the canonical scheme preserves an extractable `opN_N` id and a recognised facet token in the key or label**; otherwise it mis-computes the missing-actual set → wrong Gate-2 questions / readiness — a **silent** regression. This is the single thing R2 must not break.

The only "no-go" risk in the whole module is therefore confined to one deterministic E3 helper, and it is a *guardrail on the canonical scheme's shape*, not a blocker.

---

## 1. Consumer inventory

Legend — **NS** = name-sensitive, **VO** = value-only. "Within-run" = produced and consumed inside one report's pipeline pass (no cross-run name comparison). Stages: E1 reconcile · E2 Gate1 · E3 gap · Gate2 · F1 synth · F2 critic · Gate3.

| # | File / function | Reads | NS / VO | What it does | What breaks if fact/gap NAMES canonicalise | Loud / silent |
|---|-----------------|-------|:------:|--------------|---------------------------------------------|---------------|
| 1 | `synthesis_citation_emission.emit_claim_granular_evidence` | facts + gaps | **NS** | F1 emission: prefix/facet logic (`financials.lines.`, `reporting.`, `.y1_*`, wrong-index regex, `_extract_indicator_id`) to (re)bind `evidence_used` | Nothing *new* breaks — already mismatched today (per F1 diagnosis). Canonicalising **fixes** it *iff* emission's hardcoded shapes are aligned to the same scheme. Within-run; no persisted cross-run dependence. | silent (today) |
| 2 | `synthesis_output_hygiene.sanitize_evidence_used` + `enrich_evidence_from_kb` | facts + gaps | **NS** | Binds/drops citations via exact→NFKC→signature lookup; `_extract_indicator_id`, facet tokens, aggregate markers (`total`, `programme_budget`, …), `financials`/`reporting` prefixes | Drops/keeps depend on key strings. With a stable canonical scheme it works *better* (exact-match hits more). Breaks only if its hardcoded prefixes/markers/facets disagree with the chosen scheme. Within-run. | silent |
| 3 | `fact_safety_critic.resolve_cited_sources` | facts + gaps (via persisted `evidence_used`) | **NS** | Exact `facts.get(key)` / `gap_answers.get(key)` to build `cited_sources` for the critic | Nothing — it resolves whatever canonical key the run emitted. Improves with stable names. Reads `content_json.evidence_used` written *in the same run* (consistent). | n/a (improves) |
| 4 | `gap/logframe_completeness.derive_missing_logframe_actuals` (+ `has_indicator_data_actual_for_id`, `_is_*_facet`) — wired into E3 via `run_gap_compliance` | facts | **NS** | Deterministically finds proposal targets without indicator-data actuals; matches `opN_N` from key/label + facet token from key + data-source from provenance | If canonical scheme drops `opN_N` from the key **and** the label, the indicator is skipped → its missing actual is **not** surfaced. If facet token (`.target`/`.actual`/…) changes shape, target/actual classification flips. Wrong gap set at Gate 2. | **silent (LOCKED-STAGE risk)** |
| 5 | `gap/satisfaction.is_requirement_satisfied` / `unsatisfied_requirements` | facts + gaps | **NS** | Token-substring match of template `required_item_ref` against fact-key string + `semantic_label`; gap via `item_key` | Same class of risk as #4 (token-substring on key + label). **But has no live caller** outside its own module (grep: not wired into `run_gap_compliance` or any service). Latent — matters only if re-wired. | silent (if re-wired) |
| 6 | `report_inputs_builder.build_knowledge_bank_inputs` / `_answered_gap_answers` | facts + gaps | **VO** | Serialises whole `facts{}` + answered `gap_answers{}` into the F1 prompt; gap filter keys on `disposition` (value field) | Nothing in the builder — it passes the dict whole. (Name-sensitivity is downstream in the F1 *model* + #1/#2.) | n/a |
| 7 | `gap_compliance_agent.build_gap_compliance_prompt` / `run_gap_compliance` (LLM path) | facts | **VO** | Passes raw `facts{}` to the gap LLM; output constrained to **template** `allowed_item_keys` | Nothing in code — the LLM reads values/labels; emitted gaps are keyed to template item_keys, not fact names. | n/a |
| 8 | `donor_report_lifecycle_service.get_knowledge_bank` | facts + conflicts | **VO** | Gate-1 view: returns all facts/conflicts to the API verbatim | Nothing — renders whatever keys exist (display only). | n/a |
| 9 | `gate1_confirmation_service.confirm_gate1` + `validate_gate1_confirm_payload` / `validate_gate1_knowledge_bank` | facts + conflicts | **VO** | Overwrites KB with human snapshot + stamps `gate1_confirmed_at`; validates per-fact `source_document_id`/`provenance.excerpt`; `fact_key` only in error strings | Nothing — no expected-name set, no name comparison. | n/a |
| 10 | `gate2_gap_answer_service.submit_gate2_gap_responses` | gap_answers | **VO**\* | Writes `gap_answers[item_key]`; validates responses against surfaced **template** item_keys; provenance carries no fact-key name | Nothing w.r.t. *reconciler fact* names. \*Keyed by **template** `item_key` (`section:type:ref`) — stable and **R2-independent**. | n/a |
| 11 | `gate3_confirmation_service.confirm_gate3` | (KB stamp only) | **VO** | Requires all `content_json` sections ACCEPTED (by `section_key`), stamps `gate3_confirmed_at` | Nothing — no fact/gap key binding. | n/a |
| 12 | `orchestration/pipeline.py` (all stage steps) | KB envelope | **VO** | Reads `gate1/2/3_confirmed_at`; passes whole KB to E3/F1/F2 | Nothing — gate stamps are envelope keys, not fact keys. | n/a |
| 13 | `schemas/knowledge_bank_reconciliation_v1.structured_payload_from_persisted` + `validate_e1/gate1_knowledge_bank` | KB envelope + per-fact fields | **VO** | Extracts envelope-level keys (`facts`, `gap_answers`, …); per-fact value-field validation | Nothing — operates on the *envelope* keys (KB contract shape, which is unchanged) and per-fact fields, not fact-key names. | n/a |

**Producers (context, not consumers — relevant to migration/feasibility):** `knowledge_bank_reconciler` (LLM, invents `fact_key` — the nondeterminism source); `reconciliation/degrade_resilience.pass_through_facts_from_candidates` (degraded path keys facts as `degraded_pass_through:{candidate_id}` — a *fourth* key scheme); Gate1/Gate2/Gate3 services (write snapshots/stamps/gap answers).

---

## 2. Locked-stage findings (explicit)

### 2.1 Gate 1 confirm (E2) — **SAFE, not name-bound**
`confirm_gate1` (`gate1_confirmation_service.py:50-99`) takes the human-edited `knowledge_bank_json`, drops/sets `gate1_confirmed_at`, and **overwrites the whole object**. It does not diff against a prior snapshot, does not look up specific keys, and does not persist any separate name index. Confirmation is keyed to the **whole-KB snapshot + a timestamp**, never to individual `fact_key` names or to values/IDs per key. `validate_gate1_confirm_payload` (`knowledge_bank_reconciliation_v1.py:150-165`) checks `schema_version`, `reconciler_agent`, the envelope structure, and per-fact `source_document_id` + `provenance.excerpt`; `fact_key` appears **only inside error message f-strings** (`…:130-147`). Whatever names the reconciler emits are what Gate 1 confirms and what every later stage reads — there is no point at which a name could change "between the confirmed snapshot and a later read" within a run. **No mis-bind. GO.**

### 2.2 E3 gap agent — **SAFE iff `opN_N` + facet tokens survive canonicalisation**
`run_gap_compliance` (`gap_compliance_agent.py:363-430`) has two detection paths:
- **LLM path** — `build_gap_compliance_prompt` ships raw `facts{}` + the template checklist; the model judges coverage from values/labels; its output gaps are validated against **template** `allowed_item_keys`. Robust to fact-key naming (semantic), and structurally incapable of emitting a reconciler-fact-keyed gap.
- **Deterministic logframe path** — `derive_missing_logframe_actuals` (`logframe_completeness.py:117-175`) is the **name-sensitive** part actually wired in. It (a) derives `opN_N` via `normalize_indicator_id` from the fact-key string **or** the `semantic_label`; (b) classifies target vs actual via substring facet tokens on the key (`_is_target_facet`/`_is_actual_facet`: `.target`, `.proposal_target`, `ar1_target`, `.milestone`; `.actual`, `ar1_actual`, `_actual`); (c) decides "indicator-data source" via provenance `cell_ref`/source label (value-side). It then emits missing-actual gaps merged into the E3 output.

Would canonical names change which gaps it finds? **Yes, if the scheme drops those tokens.** Concretely against today's reconciler output: keys like `indicators.op1_1_girls_reenrolled.actual` work (`op1_1` + `.actual` both present); `indicators.ocm1_attendance_80pct.*` are **already** invisible to this path (no `opN_N`, label has none either). So canonicalisation is safe **only** if the canonical scheme keeps `opN_N` (for OP-class indicators) and a recognised facet token. If R2 chose, say, opaque numeric ids or a facet like `.y1_target` (note: `_is_target_facet` does **not** match `.y1_target` because it looks for the substring `.target`), the deterministic deriver would silently stop surfacing missing actuals. **Conditional GO — guardrail required.**

### 2.3 F2 critic resolver — **verified VALUE-/name-agnostic beyond exact match**
`resolve_cited_sources` (`fact_safety_critic.py:132-153`) is exact `dict.get` after a `fact:`/`gap:` prefix strip, no normalisation. `report_fact_safety_service.py:113-143` feeds it `facts = kb.get("facts")` and `gap_answers = _answered_gap_answers(...)` plus the persisted `content_json.evidence_used` (written by F1 in the same run). It resolves any key that exists and only those; it breaks on nothing when names are canonical and run-consistent, and stable names strictly help it. **GO (improves).** (Confirmation only — not re-derived here.)

---

## 3. Persisted-reference findings (every site key NAMES outlive a single run)

There are **no live users**, so this is about in-flight/parked jobs and **test fixtures**, not production rows. Sites where fact/gap key **names** are persisted:

| Site | Field | Key scheme persisted | Read back by | Migration concern |
|------|-------|----------------------|--------------|-------------------|
| P1 | `knowledge_bank_json.facts{}` | reconciler-invented **fact_key** (dict keys) | E2/E3/F1/F2 — all within the same report's lifecycle | A parked report keeps its run's scheme; internally consistent. Breaks only if R2 *also* re-points a name-sensitive consumer (#1,#2,#4) to canonical while a parked report still has old keys. |
| P2 | `knowledge_bank_json.conflicts[].fact_key` | reconciler **fact_key** name | Gate-1 view / human conflict resolution | Same as P1; conflict refers to a fact key name. |
| P3 | `content_json.sections[].content.evidence_used[]`, `dropped_citations[]`, `remapped_citations[].from/.to`, `auto_citations[]` | `fact:`/`gap:` **key-name strings** (`content_json_v1.py:8-47`) | F2 critic, Gate-3 review, future export | Written by F1; if a report is re-reconciled (new scheme) **without** re-running F1, these become stale refs. In normal flow F1 runs after reconcile, so consistent. |
| P4 | `knowledge_bank_json.gap_answers{}` | **template** `item_key` (`section:type:ref`) — *not* a reconciler fact key | F1/F2/Gate2 | **R2-independent** (template-derived). Listed for completeness; canonicalising *fact* names does not touch it. |
| P5 | `gap_analysis_json.gaps[].item_key` / `required_item_ref` | **template** item_key / `logframe_row:opN_N` | Gate 2 (`surfaced_keys`) | R2-independent (template-derived). `logframe_row:opN_N` embeds an indicator id — stable as long as template indicator refs are stable. |
| P6 | degraded path facts | `degraded_pass_through:{doc_id}:{field_path}` | downstream as ordinary facts | A 4th scheme; a canonical-key effort must decide whether degraded facts are canonicalised or remain opaque. |

**Test-fixture dimension (the real "parked state" today):** key schemes are hardcoded in fixtures and unit tests — e.g. `tests/.../fcdo_bridgelight_recorded_knowledge_bank.json` (`indicators.{slug}.target/.actual`, `reporting_period.annual_review_1.*`, `financials.total_programme_budget.actual_spend`) and `tests/test_synthesis_citation_emission.py` `BRIDGELIGHT_FINANCIALS` (`.y1_actual`, `financials.lines.opN_N.y1_*`, `reporting.annual_review_period_1.*`). These two **already disagree** with each other (the second encodes the fictional namespace from `F1_CITATION_BINDING_DIAGNOSIS_b91ae3e0.md`). Any canonical scheme will require re-recording these fixtures, and the emission tests will need to stop asserting the fictional scheme. **Recorded as a migration cost, not fixed.**

---

## 4. Schema-source feasibility (read-only assessment)

**Can a canonical key schema be derived deterministically from funder-template + extractor-output contracts? Largely yes — for the anchored majority; the reconciler's semantic/aggregation layer is the hard part.**

Deterministic anchors already exist:
- **`reconciliation/input_builder.py`** builds candidate `field_path`s deterministically from extractor output: `indicators.{indicator_key|row_id}.{target|actual}` (`:203,:253`), `financials.lines.{line_key}.{budget|actual}` (`:281`), `financials.currency`, `award_budget.{amount|currency}`, `grant_period.{start|end}`, `reporting_period.{start|end}`, `reporting_deadlines[idx]`, `reporting_obligations[idx]`, `funder`, `grant_reference`, `objectives.{objective_key}`.
- **Extractor slugs** are the natural identity source: proposal extractor emits `indicator_key` / `objective_key` (`proposal_extractor.py:159,:141`); indicator-data extractor emits `row_id` (`indicator_data_extractor.py:156`); grant-terms extractor emits the fixed scalar fields above.
- **Template side** supplies the consumer-expected refs: `required_indicators[]`, `required_tables[].data_source ∈ {indicators, financials, knowledge_bank, manual}`, and `format_rules_json.logframe.columns` (`FUNDER_TEMPLATE_SCHEMA.md §2.1/§3.3`).

So `canonical_key = f(classification, field_path, facet)` is generable for indicators, financial lines, grant scalars, and objectives — i.e. every fact that flows through `input_builder` as a typed candidate.

**Hard cases (no natural template/extractor anchor — the R2 risk surface):**
1. **Reconciler semantic renaming/aggregation.** Today the LLM maps `reporting_period.start` → `reporting_period.annual_review_1.start`, `reporting_deadlines[0]` → `reporting_deadline.annual_review_pack`, `reporting_obligations[0]` → `reporting_obligations.annual_review_narrative`, and aggregates line items → `financials.total_programme_budget.actual_spend`. The *semantic identity* (which period is "AR1", which deadline is "the pack", which lines roll into a total) is LLM-assigned and has no deterministic source in the candidate stream.
2. **Indexed multi-value candidates** (`reporting_deadlines[idx]`, `reporting_obligations[idx]`) — the array index is not a stable identity across runs/documents.
3. **Conflict fact_keys** (e.g. `financials.total_programme_budget.budget`) — LLM-named; must align to whatever the canonical scheme calls the same quantity.
4. **Non-`opN_N` indicators** (`ocm1_…`, `equity_support_reach_qualitative`) — anchored by the proposal `indicator_key`, but they lack the `opN_N` token the deterministic logframe deriver (#4) keys on, so they sit outside that path regardless of canonicalisation.
5. **Degraded pass-through facts** (`degraded_pass_through:{candidate_id}`) — opaque by construction; no semantic anchor.

**Net:** the structured/extractor-anchored facts (the bulk of indicators, financial lines, grant scalars, objectives) can be assigned canonical keys deterministically; the funder template + extractor contracts are complete enough for them. The facts with **no natural anchor** are precisely those the reconciler currently *synthesises by renaming/aggregating* — semantically-named reporting periods/deadlines/obligations, rolled-up financial totals, conflict keys, and degraded pass-throughs. Those are the cases R2 must handle explicitly.

---

## 5. Bugs / sharp edges recorded (not fixed)

- **B-1 (latent dead path).** `gap/satisfaction.py` (`unsatisfied_requirements`, `is_requirement_satisfied`) is name-sensitive (token-substring on key + label) but has **no live caller** in `app/` — it is not wired into `run_gap_compliance` or any gate service. If a future change re-wires it, it inherits the same silent-mis-detection risk as the logframe deriver. (Confirm before relying on it as a safety net.)
- **B-2 (facet-token inconsistency across modules).** Facet detection differs by consumer: `logframe_completeness` matches `.target`/`.actual`/`ar1_*`/`_actual`/`.milestone`; `synthesis_output_hygiene._map_facet_token` matches `actual`/`target`/`budget`/`spend`/`ar1*`; `synthesis_citation_emission` hardcodes `.y1_target`/`.y1_actual`. A single canonical facet convention would need to satisfy all three, or they continue to disagree. (This is the same root as the F1 diagnosis namespace break, surfaced here as a multi-consumer constraint.)
- **B-3 (third/fourth key schemes).** Beyond the reconciler's per-run naming, the degraded path emits `degraded_pass_through:{candidate_id}` and `input_builder` emits `field_path`-style candidates — any canonicalisation effort must enumerate all production sites, not just the happy-path reconciler.

---

## Headline restated + STOP

- **NAME-SENSITIVE consumers: 5** (4 wired — `emit_claim_granular_evidence`, `sanitize_evidence_used`/`enrich_evidence_from_kb`, `resolve_cited_sources`, `derive_missing_logframe_actuals`; 1 latent — `gap/satisfaction`).
- **VALUE-ONLY consumers: 8.**
- **Locked-stage go/no-go: GO.** Gate 1 confirm is value/snapshot-bound (safe); the F2 critic resolver is exact-match and only benefits from stable names (safe); the E3 gap agent is safe **provided** the canonical scheme preserves an extractable `opN_N` indicator id and a recognised facet token (`.target`/`.actual`/…) in the key or `semantic_label` — otherwise `derive_missing_logframe_actuals` silently mis-detects missing actuals. Gate 2 gap-answer keying is on template `item_key`s and is independent of reconciler fact names.

**STOP.** This is a map, not a plan — no R1/R2 change proposed, scoped, or begun. Read-only: no code, schema, test, prompt, or fixture modified. Single deliverable: this file.
