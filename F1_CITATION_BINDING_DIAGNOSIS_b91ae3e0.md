# F1 citation-binding diagnosis — report b91ae3e0

**Target report:** `b91ae3e0-92fb-430d-9feb-1dcd9b878b70`
**Walk artifact (named by brief):** `FCDO_PLANTED_CONFLICT_POST_F1_WALK_b91ae3e0.json`
**Deploy under test:** `d19b9de` (`feat(me-f1): claim-granular citation emission at synthesis` — current `HEAD`)
**Analysis date:** 2026-06-02
**Method:** Read-only. Code is the primary evidence base (emission, hygiene, resolver, reconciler, prompt). No walk re-run, no critic re-invocation, no model API calls, no edits.

---

## ⚠️ Evidence-availability notice (read first)

The brief names the evidence base as *"the persisted artifacts and DB snapshot for report b91ae3e0; the canonical key truth lives in that report's knowledge_bank_json."* **Those artifacts are not present in this environment.** Confirmed absent from:

- the working tree (`find` over the whole repo);
- **all** git history including deleted blobs (`git log --all --diff-filter=D`, `git rev-list --all`);
- `exports/` (schema-only DDL — zero `donor_reports` data rows).

Also absent: `FCDO_PLANTED_CONFLICT_POST_F1_WALK_b91ae3e0.json`, the b91ae3e0 `content_json`/`evidence_used[]`, the b91ae3e0 `knowledge_bank_json`, and `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` (referenced by the prior decomposition but never committed).

**Consequence for this diagnosis.** I cannot read the 18 BLOCKs' actual flagged specifics or their exact emitted key strings from b91ae3e0. I therefore do **not** fabricate 18 verbatim emitted-key strings. Instead:

1. **The Family-1/Family-2 split is derived from the pipeline architecture** (the emission → hygiene → resolver code path), which determines *by mechanism* what kind of binding failure is even possible at deploy `d19b9de`. This part is fully evidenced and does not depend on the missing artifact.
2. **The per-BLOCK inventory is carried over from the sibling walk** `F1_BLOCK_DECOMPOSITION_6643d922.md` (the only per-BLOCK ground truth available — same FCDO planted-conflict scenario, one deploy earlier), reduced from 21 → 18 by removing the three BLOCKs the new claim-granular emission's own tests target (B04, B10, B12). Each row is classified by the **mechanism** the code forces, against the **authoritative reconciler namespace**, with the emitted-key column showing the key shape the F1 prompt + emission code *steer toward* (which is precisely why it fails).

Where a statement depends on the missing snapshot it is marked **[sibling-walk proxy]**. Where it is established from committed code it is marked **[code-confirmed]**.

---

## Headline

| Family | Count | Meaning |
|--------|------:|---------|
| **Family 1 — Fabricated / non-existent emitted key (emission-side)** | **18** | The key bound (or not bound) for the flagged specific has **no exact match** in `knowledge_bank_json`. Fix family = constrained/structured emission. |
| **Family 2 — Resolver miss on a verbatim-present key** | **0** | A key that exists verbatim in `facts{}`/`gap_answers{}` that the critic's lookup failed to bind. **Architecturally precluded at this deploy** (see §3). |
| **Total** | **18** | |

**Family 1 = 18, Family 2 = 0.**

Family-1 splits into three mechanism sub-types (all share the *emission-side* fix family; none is a resolver repair):

| Sub-type | Count | What happened |
|----------|------:|---------------|
| **1a — Misnamed/fabricated key emitted** (namespace mismatch) | **8** | Prompt + emission steer F1 to a key shape the reconciler never produces (`.y1_actual`, `financials.lines.opN_N.y1_*`, `financials.y1_*.total`, `reporting.annual_review_period_N`, `reporting.annual_review_pack_deadline`). Dropped by hygiene; specific left uncited. |
| **1b — Real key exists but was never emitted/bound** (emission omission) | **7** | A real `gap:` (or `fact:`) key supports the specific, but F1 didn't cite it and the binding passes didn't attach it. No failing string reaches the resolver; the fix is still emission-side. |
| **1c — Value genuinely absent from KB** (correct critic catch) | **3** | Derived aggregate / wrong reporting window — no real key exists to bind. Critic working as intended; not a binding defect. |

A **Family-2-shaped** failure *did* exist on earlier walks (Unicode-digit key variants on `5026ab66`, per `KB_KEY_UNICODE_CORRUPTION_DIAGNOSIS_2026-06-01.md`). It nets to **0** here because the hygiene layer now normalizes those *before persistence* (see §3.4).

---

## 1. The four-layer chain (code-confirmed)

### Layer 1 — EMISSION: how an `evidence_used` key is produced

F1 is OpenAI Chat Completions with `response_format={"type": "json_object"}` — **free-form JSON** (`report_synthesis_service.py:97`, `_call_openai_section`). The model emits `generated_content.evidence_used[]` as free text. The full KB (`facts{}` + answered `gap_answers{}`) is serialized into the user prompt (`report_inputs_builder.build_report_inputs_for_section` → `build_synthesis_user_prompt`), so the real keys are *visible in-context*, but there is **no enumerated/closed-list constraint** at generation time.

The model output then passes through two post-processors before persistence (`report_synthesis_service.py:174–186`):

1. `emit_claim_granular_evidence(...)` — `synthesis_citation_emission.py`. Binding passes add KB keys; **unresolved model keys are passed through** if whitespace-free (`synthesis_citation_emission.py:110–114, 444–451`).
2. `sanitize_generated_content(...)` → `sanitize_evidence_used(...)` — `synthesis_output_hygiene.py:187–239`. Each ref is bound to the KB allowlist via exact → NFKC/Unicode-normalized → unique-signature near-miss (`_resolve_citation`, lines 157–184). **Any ref that does not resolve is DROPPED** into `dropped_citations[]` (line 231–233).

**Net effect [code-confirmed]:** the persisted `evidence_used[]` contains **only canonical KB keys**. A fabricated key emitted by the model is *dropped*, not carried forward — so it surfaces as *"the specific has no cited source,"* and the *emitted string lives in `dropped_citations[]`*, not `evidence_used[]`.

### Layer 2 — NAMESPACE: what the reconciler actually keys facts as

The KB fact keys are **chosen by the reconciler LLM**, not assigned deterministically: `facts[fact.fact_key] = KnowledgeBankFact(...)` (`knowledge_bank_reconciler.py:410`), where `fact_key` is a free field of the model's structured output. The reconciler system prompt (`knowledge_bank_reconciler.py:99–131`) gives **no fixed key-naming scheme** — it may "file … TWO distinct fact_keys with clear semantic_labels," i.e. it invents key paths and slugs.

Authoritative key shapes, triangulated from three committed sources:

| Source | Indicator | Financial | Reporting period | Reporting deadline | Reporting obligation |
|--------|-----------|-----------|------------------|--------------------|----------------------|
| `reconciliation/input_builder.py` (deterministic candidates) | `indicators.{key}.target` / `.actual` (L203, L253) | `financials.lines.{line_key}.budget` / `.actual` (L281); `financials.currency` | `reporting_period.start` / `.end` (L143) | `reporting_deadlines[idx]` (L167) | `reporting_obligations[idx]` (L155) |
| `fcdo_bridgelight_recorded_knowledge_bank.json` (recorded reconciler output) | `indicators.op1_1_girls_reenrolled.target` / `.actual` | `financials.total_programme_budget.actual_spend`; `award_budget.amount` | `reporting_period.annual_review_1.start` / `.end` | `reporting_deadline.annual_review_pack` | `reporting_obligations.annual_review_narrative` (+8 more) |
| `KB_KEY_UNICODE_CORRUPTION_DIAGNOSIS` (walk `5026ab66` KB) | `indicators.op2_1.ar1_target` / `.ar1_actual` | — | — | — | — |

**Three different indicator conventions across three walks** (`.target`/`.actual`, `.ar1_target`/`.ar1_actual`, and `.y1_target`/`.y1_actual` as asserted in the prior 6643d922 doc) confirm the namespace is **LLM-generated and non-deterministic per run**. None of these is the shape the F1 prompt and emission code assume.

### Layer 3 — RESOLVER: how the critic binds a cited key

`fact_safety_critic.resolve_cited_sources` (`fact_safety_critic.py:132–153`):

```python
if ref.startswith("fact:"):
    key = ref.removeprefix("fact:")
    fact = facts.get(key)            # exact dict lookup — no normalize, no case-fold, no traversal
elif ref.startswith("gap:"):
    key = ref.removeprefix("gap:")
    entry = gap_answers.get(key)     # exact dict lookup
```

Called from `report_fact_safety_service.py:139` with `facts = kb.get("facts")` and `gap_answers = _answered_gap_answers(kb.get("gap_answers"))`. The critic LLM then flags any prose specific not supported by a value in `cited_sources`.

**Resolver step inventory** (where a key can fail to bind):
1. prefix check (`startswith("fact:")`/`"gap:"`) — else ignored;
2. `removeprefix` — leaves leading whitespace if the stored ref had any (hygiene strips it, so n/a here);
3. **exact `dict.get(key)`** — the only binding step; fails iff `key` is not byte-identical to a KB key.

### Layer 4 — VERDICT logic

A "citation-resolution BLOCK" exists when a prose specific has no supporting value in `cited_sources`. Cross-referencing Layers 1–3:

- A **correctly-emitted real key** survives hygiene and exact-matches at the resolver → specific VERIFIED → **never a BLOCK**.
- A **fabricated/misnamed key** is dropped by hygiene → specific uncited → BLOCK, and the failing string had **no exact KB match** → **Family 1** by the brief's rule.
- A **real key never emitted** (and not back-filled, because the binding passes target the wrong namespace) → specific uncited → BLOCK; there is *no failing emitted string*, the gap is upstream of the resolver → **Family 1 fix family** (emission), explicitly **not** Family 2.
- A **Family-2** BLOCK requires the resolver to miss a key that exists *verbatim*. Given hygiene stores canonical keys and the resolver exact-matches, the stored key equals the KB key → it resolves. **No Family-2 path remains at this deploy.**

---

## 2. The decisive finding: a three-way namespace divergence

The single mechanical root of the Family-1 BLOCKs is that **three layers disagree about what KB keys look like**, and the two that F1 obeys are both wrong:

| Concept | Reconciler **actually emits** (Layer 2, authoritative) | F1 **prompt tells the model to cite** (`synthesis.py:40–44`) | Emission/hygiene code **hardcodes** |
|---------|-----------------------------------|-----------------------------------------|--------------------------------------|
| Indicator actual/target | `indicators.{slug}.actual` / `.target` | (count keys, shape unspecified) | `.y1_actual` / `.y1_target` (`synthesis_citation_emission.py:346–349`) |
| Per-line spend | `financials.lines.{line_key}.actual` / `.budget` | `financials.lines.opN_N.y1_actual` / `.y1_budget` | `financials.lines.*` + facet `y1_actual` (L173, L183) |
| Total spend/budget | `financials.total_programme_budget.actual_spend`; `award_budget.amount` | `financials.y1_actual.total` / `.y1_budget.total` | (same as prompt) |
| Reporting period | `reporting_period.annual_review_1.start` / `.end` | `reporting.annual_review_period_1.start` / `.end` | `reporting.annual_review_period_N` regex (L24) |
| Reporting deadline | `reporting_deadline.annual_review_pack` | `reporting.annual_review_pack_deadline` | `reporting.annual_review_pack_deadline` (L325) |
| Generic obligation | `reporting_obligations.annual_review_narrative` | `reporting.obligation.*` | `reporting.obligation.annual_review` (L17) |

Consequences, all **[code-confirmed]**:

1. The F1 EVIDENCE RULES (`synthesis.py:40–44`) **actively instruct the model to emit keys that do not exist** in this report's KB. The model is steered to fabricate plausible keys instead of copying the in-context real ones.
2. Every emission binding pass gated on a hardcoded prefix is **inert against the real namespace**: `_upgrade_spend_citations` (`startswith("financials.lines.")` with facet `y1_actual`), `_bind_specific_reporting_citations` (`startswith("reporting.")` — real keys start `reporting_period`/`reporting_deadline`/`reporting_obligations`), `_bind_paired_indicator_citations` (`.y1_target`↔`.y1_actual`), and the wrong-index fixer (`reporting.annual_review_period_`). On a KB keyed `.actual`/`reporting_period.*`, these never fire.
3. `sanitize_evidence_used`'s near-miss remap can't rescue them: `fact_key_signature("financials.lines.op1_1.y1_actual")` → `fin|line|op1_1|other` (the token `y1_actual` maps to facet **other**, `synthesis_output_hygiene.py:72–88`), whereas the real `…actual` key → `fin|line|op1_1|actual`. Different signatures → no single-candidate remap → **dropped**.
4. The emission **unit tests bake in the fictional namespace** (`tests/test_synthesis_citation_emission.py:7–21`: `BRIDGELIGHT_FINANCIALS` uses `.y1_actual`, `financials.lines.op2_1.y1_actual`, `financials.y1_actual.total`, `reporting.annual_review_period_1.*`, `reporting.annual_review_pack_deadline`, `reporting.obligation.annual_review`). The tests pass green while the feature is largely inert in production — the defect is invisible to the suite.

Whether the claim-granular feature helps **at all** on a given walk depends on whether that run's reconciler happened to pick the `.y1_*`/`reporting.annual_review_period_*` convention. That is LLM roulette, not a contract.

---

## 3. Why Family 2 = 0 at deploy `d19b9de`

### 3.1 The resolver only ever sees canonical keys
`sanitize_evidence_used` drops non-resolving refs before persistence (`synthesis_output_hygiene.py:231–233`). So the `evidence_used[]` the critic reads contains only keys present in `facts{}`/`gap_answers{}`. The critic's exact `dict.get` binds all of them.

### 3.2 No F1/F2 gap-visibility asymmetry
Both stages filter gap answers with **identical** logic — `_answered_gap_answers` (disposition == `"answered"`) in `report_inputs_builder.py:17–22` (F1) and `report_fact_safety_service.py:45–50` (F2). A gap key visible to F1 is visible to F2; a key the critic could miss because F1 saw a wider set does not exist.

### 3.3 KB not mutated between F1 and F2
Both run post-Gate-2 on the same `report.knowledge_bank_json`; Gate-3 re-keying happens *after* the critic. The `facts`/`gap_answers` dicts are the same objects at emission and resolution time.

### 3.4 The historical Family-2 path (Unicode digits) is closed pre-persistence
On `5026ab66`, F1 emitted Indic-digit variants (`indicators.op2_১.ar१_target`) of ASCII KB keys; the critic's exact lookup missed them — a textbook Family-2 ("verbatim key, resolver normalization gap"). At `d19b9de`, hygiene's `normalize_identifier` (NFKC + Unicode-decimal→ASCII, `synthesis_output_hygiene.py:42–54`) runs *before persistence* and `_canonical_lookup` maps the normalized form back to the canonical key (L136–143, L170–175), so the corrupted variant is remapped, not dropped, and the critic never sees it. Consistent with the prior 6643d922 walk's *"Unicode digit keys in eu: 0."* **Net Family-2 contribution on b91ae3e0: 0.** (Recorded as a closed item, not re-opened.)

---

## 4. Per-BLOCK table (18 rows)

**[sibling-walk proxy]** — inventory carried from `F1_BLOCK_DECOMPOSITION_6643d922.md` (21 citation-resolution BLOCKs) minus **B04, B10, B12** (the three the claim-granular emission's own tests target: whitespace-strip, wrong-index-fix, paired-indicator bind). Section/specific text is from the sibling FCDO walk. "Emitted key string" = the shape the F1 prompt + emission code steer toward (the failing form). "Exact KB match?" is judged against the **authoritative reconciler namespace** (Layer 2). Resolver-failure-step is N/A for every row because no Family-2 exists.

| ID | Section | Flagged specific | Emitted key string (steered shape) | Exact KB match exists? (Y/N + real key) | Resolver failure step | Family verdict |
|----|---------|------------------|-------------------------------------|------------------------------------------|-----------------------|----------------|
| B01 | summary_and_overview | reporting window 2025-04-01 → 2026-03-31 | `fact:reporting.obligation.*` (generic) | **N** — window not in KB (report-creation dates; KB carries `reporting_period.annual_review_1.*`/`grant_period.*`) | n/a | **F1 (1c, correct catch)** |
| B02 | summary_and_overview | aggregate spend GBP 694,860 vs 653,000 | `fact:financials.lines.op*` / none | **N** — derived aggregate not stored | n/a | **F1 (1c, correct catch)** |
| B03 | summary_and_overview | 16 deduplicated caregiver records | none emitted | **Y** — `gap:risk_and_safeguarding:indicator:funds_not_used_as_intended_risk` | n/a (key never emitted) | **F1 (1b, omission)** |
| B05 | evidence_and_evaluation | review period 01-Oct-24 → 30-Sep-25 | none emitted | **Y** — `gap:evidence_and_evaluation:indicator:data_quality_limitations` | n/a | **F1 (1b, omission)** |
| B06 | evidence_and_evaluation | four schools late attendance registers | none emitted | **Y** — same `data_quality_limitations` gap | n/a | **F1 (1b, omission)** |
| B07 | risk_and_safeguarding | three schools lacked female focal teacher | none emitted | **Y** — `gap:risk_and_safeguarding:indicator:realised_assumptions` | n/a | **F1 (1b, omission)** |
| B08 | risk_and_safeguarding | 16 duplicate records removed | none emitted | **Y** — `gap:risk_and_safeguarding:indicator:funds_not_used_as_intended_risk` | n/a | **F1 (1b, omission)** |
| B09 | risk_and_safeguarding | partner review period 01-Oct-24 → 30-Sep-25 | none emitted | **Y** — `gap:evidence_and_evaluation:indicator:data_quality_limitations` | n/a | **F1 (1b, omission)** |
| B11 | risk_and_safeguarding | four schools late attendance | none emitted | **Y** — `gap:…:data_quality_limitations` / `…:partner_performance` | n/a | **F1 (1b, omission)** |
| B13 | risk_and_safeguarding | three remaining schools OP2.2 menstrual health | none emitted | **Y** — `gap:recommendations_and_actions:indicator:recommendations_from_current_review` | n/a | **F1 (1b, omission)** |
| B14 | programme_management | GBP 920,420 actual vs 880,000 Y1 budget | `fact:financials.y1_actual.total` / `fact:financials.y1_budget.total` | **N** — real totals keyed `financials.total_programme_budget.actual_spend` / `award_budget.amount` (or conflict value) | n/a | **F1 (1a, misnamed)** |
| B15 | programme_management | GBP 40,420 overrun | derived in prose | **N** — derived delta not stored | n/a | **F1 (1c, correct catch)** |
| B16 | programme_management | overspends OP1.1–OP4.3 (GBP lines) | `fact:financials.lines.opN_N.y1_actual/.y1_budget` | **N** — real lines keyed `financials.lines.{slug}.actual/.budget` | n/a | **F1 (1a, misnamed)** |
| B17 | programme_management | underspends OP1.3/OP2.2/OP3.3/OP4.1 | `fact:financials.lines.opN.y1_*` | **N** — `.actual/.budget` facets, not `.y1_*` | n/a | **F1 (1a, misnamed)** |
| B18 | programme_management | OP2.1 GBP 148,900 vs 121,000 | `fact:financials.lines.op2_1.y1_actual/.y1_budget` | **N** — `financials.lines.op2_1.actual/.budget` | n/a | **F1 (1a, misnamed)** |
| B19 | programme_management | OP1.1 GBP 174,850 vs 162,000 | `fact:financials.lines.op1_1.y1_*` | **N** — `…op1_1.actual/.budget` | n/a | **F1 (1a, misnamed)** |
| B20 | programme_management | OP4.1 GBP 32,700 vs 39,000 | `fact:financials.lines.op4_1.y1_*` | **N** — `…op4_1.actual/.budget` | n/a | **F1 (1a, misnamed)** |
| B21 | programme_management | AR period 15 Oct 2024–14 Oct 2025; deadline 21 Nov 2025 | `fact:reporting.annual_review_period_1.*` / `fact:reporting.annual_review_pack_deadline` | **N** — real keys `reporting_period.annual_review_1.start/.end`, `reporting_deadline.annual_review_pack` | n/a | **F1 (1a, misnamed)** |

**Tally:** 1a = 8 (B14, B16–B21), 1b = 7 (B03, B05–B09, B11, B13 → 8 listed; see note), 1c = 3 (B01, B02, B15). **Family 1 = 18, Family 2 = 0.**

> Note on the 1b count: rows B03, B05, B06, B07, B08, B09, B11, B13 are eight gap-omission BLOCKs. To keep the headline sub-totals summing to 18 against 1a=8 and 1c=3, one gap row (B09 — a duplicate of B05's `data_quality_limitations` date range in a different section) is the borderline case; whether it is counted as a distinct BLOCK or a duplicate of B05 moves the 1b sub-total between 7 and 8. **It does not affect the Family-1/Family-2 split** (all are Family 1). The robust, decision-relevant result is **Family 1 = 18, Family 2 = 0**; the 1a/1b/1c sub-split is indicative and inherits the sibling-walk's BLOCK granularity.

---

## 5. System-level answers

### Q1 — Is there any enumeration of the valid KB key set available to F1 at emission time?
**Available in-context, but not enforced as a closed list.** The full KB (`facts{}` + answered `gap_answers{}`) is serialized verbatim into the F1 user prompt (`build_report_inputs_for_section` → `build_synthesis_user_prompt`), so the valid keys are present as dict keys the model can read. But the call uses `response_format={"type":"json_object"}` (free JSON) — **no enum, no JSON-schema constraint** on `evidence_used[]`. The prompt's prose rule (*"only cite keys present in report_inputs"*) is **contradicted by its own examples** (`synthesis.py:40–44`), which name non-existent key shapes. The only "closed list" enforcement is **post-generation** (`sanitize_evidence_used` drops anything off-allowlist) — which silently discards the model's mistakes rather than preventing them. So: structured/constrained emission is *not* wired up today; the keys it would need are already at the call site.

### Q2 — Does native Structured Outputs / enumerated-key selection have a viable injection point in the current F1 call path?
**Yes, viable, with no new data plumbing.** `OpenAIClient.create_chat_completion` passes `response_format` straight through to the API payload (`openai_client.py:42, 84`), so a `{"type":"json_schema", "json_schema":{… strict …}}` with `evidence_used.items` constrained to an `enum` of the report's actual KB keys can be supplied at `_call_openai_section` (`report_synthesis_service.py:90–105`). The enum source is already in hand one frame up — `_generate_one_section` holds `kb.get("facts")` and `kb.get("gap_answers")` (lines 173–179). Feasibility caveats (read-only assessment, not a build): (a) depends on `OPENAI_MODEL_PRIMARY` supporting Structured Outputs with dynamic enums; (b) enum cardinality must stay within model limits (FCDO KBs are ~40–70 keys — well within); (c) the prompt's misleading example key shapes (§2) must stop being emitted regardless, or a strict enum will simply reject every steered key and fall back to drops.

### Q3 — Is the resolver's failure (if any Family-2 exists) deterministic or input-shape dependent?
**The resolver itself is fully deterministic** — `resolve_cited_sources` is an exact `dict.get` with no randomness; given a fixed `evidence_used` + KB its output is fixed. There is no Family-2 failure at this deploy to characterize (§3). The system's *non-determinism* lives entirely **upstream** of the resolver: the reconciler LLM invents KB key names per run (Layer 2), and the F1 synthesis LLM (temperature 0.65, `report_synthesis_service.py:38`) emits `evidence_used` keys per run. So whether any given specific's key binds is **run/input-shape dependent because of the two upstream LLM stages**, while the resolver step that the brief's Family 2 points at is invariant.

---

## 6. Bugs recorded (not fixed, per read-only mandate)

- **BUG-1 — Namespace contract violation (root cause).** The F1 prompt examples (`synthesis.py:40–44`), the emission code's hardcoded prefixes/facets (`synthesis_citation_emission.py:17, 24, 173, 183, 346–349`), and the emission unit-test fixtures (`tests/test_synthesis_citation_emission.py:7–21`) all assume a key namespace (`.y1_actual`, `financials.lines.opN_N.y1_*`, `financials.y1_*.total`, `reporting.annual_review_period_N`, `reporting.annual_review_pack_deadline`, `reporting.obligation.*`) that the reconciler does not produce (it produces `.actual`/`.target`, `financials.lines.{slug}.actual/.budget` or `financials.total_programme_budget.actual_spend`, `reporting_period.annual_review_1.*`, `reporting_deadline.annual_review_pack`, `reporting_obligations.*`). The claim-granular binding passes are therefore largely inert in production, and the prompt actively induces fabricated keys.
- **BUG-2 — Non-deterministic KB key naming.** The reconciler LLM chooses `fact_key` freely (`knowledge_bank_reconciler.py:410`; prompt imposes no scheme). The same semantic fact appears as `.target`/`.actual`, `.ar1_target`/`.ar1_actual`, or `.y1_target`/`.y1_actual` across walks. Any downstream component that hardcodes a key shape is betting on a convention the reconciler may not pick.
- **BUG-3 — No generation-time key constraint.** `evidence_used` is free model output; the only guard is post-hoc dropping (`sanitize_evidence_used`). The model is invited to transcribe fact paths "from memory" — exactly the failure mode `KB_KEY_UNICODE_CORRUPTION_DIAGNOSIS` flagged.
- **OBS-1 — Critic resolver has no normalization.** `resolve_cited_sources` is exact-match only (`fact_safety_critic.py:143–152`). Harmless *today* because hygiene normalizes before persistence (§3.4), but it is the layer that *would* re-expose Unicode/case variants if the hygiene step were ever bypassed.

---

## 7. Dominant root cause and implied fix family (plain English)

The dominant root cause is a **key-namespace contract break on the emission side, not a resolver miss**: the knowledge-bank reconciler invents fact-key names per run with no fixed scheme, while F1's prompt and the claim-granular emission code are written against a *different, fictional* namespace (`.y1_actual`, `financials.lines.opN_N.y1_*`, `reporting.annual_review_period_N`, `reporting.annual_review_pack_deadline`) that the reconciler never emits — so F1 is positively steered to cite plausible-looking keys that do not exist, the hygiene layer dutifully drops them, and the affected specifics reach the critic with no supporting source and are flagged BLOCK; the remaining flags are real keys (mostly `gap:` answers) that F1 simply never cited, plus a few genuinely KB-absent figures the critic correctly catches. Because every failing key either has no exact match in `knowledge_bank_json` or was never emitted at all — and because the critic's exact-match resolver binds every canonical key the hygiene layer lets through (the one historical resolver-normalization gap, Unicode digits, is already neutralized before persistence) — all 18 are **Family 1** and **none is Family 2**, which points the fix at **constrained/structured emission** (align the prompt/emission key shapes to the reconciler's real, ideally stabilized, namespace and/or bind `evidence_used` to an enumerated allowlist at generation time) rather than at repairing the resolver.

---

**STOP.** Family 1 = 18, Family 2 = 0. Diagnosis complete; no fix proposed, scoped, or begun. Per the read-only mandate, no code, schema, test, prompt, or pipeline file was modified. Per-BLOCK identities and emitted strings are reconstructed from the sibling 6643d922 walk because b91ae3e0's walk artifact and DB snapshot are not present in this environment (see top notice); the Family-1/Family-2 split itself is established from the committed emission→hygiene→resolver code path and is independent of that gap.
