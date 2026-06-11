# P3 — FCDO empty-render diagnosis (read-only)

**Reports:** FCDO `7cdcc3a8-e15e-449b-991c-b79d99c918ec` (template v2 post-replace) · NLCF control `df7450dc-5d63-4461-98fc-9f09dea44a70`  
**Artefacts:** `dynamic_run/walk_p3_b3_fcdo_7cdcc3a8.json`, `dynamic_run/walk_p3_b3_nlcf_df7450dc.json`, committed exports under `snapshots/p3_b3_export_*.docx`  
**Date:** 2026-06-11 · **No prod writes, no fixes, no new walks.**

---

## Executive summary

The FCDO export shows headings only because **`content_json.sections[*].content.text` is empty for all six sections at synthesis time**, while **`content.claims[]` is populated and bound**. The export renderer (`docx_renderer.render_donor_report_docx`) emits body prose **only from `content.text`**; it never reads `content.claims`. The knowledge bank was populated (79 facts, 10 logframe actual rows). The **inputs-builder fact subset for v1 vs v2 is identical** for narrative and logframe-bearing sections — the prime hypothesis (v2 template starves `report_inputs_builder`) is **not supported** by the decisive offline experiment.

**Named break point:** **(d)** content persisted with empty `text` and export reads the wrong field for structured synthesis output; **(b)** contributes — the synthesis model returned claims without companion prose and the bind path accepts that shape.

---

## D1 · Where the chain broke — FCDO `7cdcc3a8`

### knowledge_bank_json (after export snapshot)

| Metric | Value |
|--------|------:|
| Total facts | 79 |
| Indicator-namespace facts | 36 |
| `logframe_ar1_actual` keys | 10 |
| Gap answers (Gate 2 skipped) | 2 |
| Conflicts surfaced | 10 |
| Conflicts resolved at Gate 1 | 10 |
| Gate 1 confirmed | `2026-06-11T16:02:01.965339+00:00` |
| Gate 2 confirmed | `2026-06-11T16:02:14.766691+00:00` |

**Logframe actual keys present (10):**  
`indicators.OP1.1` … `OP4.3` with suffix `.logframe_ar1_actual` — all except `OP2.3` and `OP4.2` (the two adjudicated gap refs). Proposal targets exist for OP2.3 and OP4.2.

Gap stage (Gate 2 boundary) emitted exactly `{logframe_row:op2_3, logframe_row:op4_2}` — see `snapshots/p3_b3_gap_stage_7cdcc3a8.json`.

### content_json (after synthesis → after export)

| section_key | generation_status (synth → export) | `text` len | claims total | claims `bound` | `structured_bind_status` |
|-------------|-----------------------------------|----------:|-------------:|-----------------:|---------------------------|
| summary_and_overview | GENERATED → ACCEPTED | 0 | 8 | 5 | bound |
| performance_and_conclusions | GENERATED → ACCEPTED | 0 | 21 | 6 | bound |
| evidence_and_evaluation | GENERATED → ACCEPTED | 0 | 6 | 5 | bound |
| risk_and_safeguarding | GENERATED → ACCEPTED | 0 | 16 | 4 | bound |
| programme_management_delivery_commercial_financial | GENERATED → ACCEPTED | 0 | 6 | 4 | bound |
| recommendations_and_actions | GENERATED → ACCEPTED | 0 | 6 | 5 | bound |

**Totals:** 63 claims, 29 bound, **0 characters prose across all sections**, `assumptions[]` empty on every section.

Example bound claim (summary section) with empty prose container:

```json
{
  "text": "The programme objective was that adolescent girls complete basic education in safer, more supportive environments.",
  "bind_status": "bound",
  "source_refs": ["fact:objectives.impact_girls_complete_basic_education"]
}
```

Parent section: `"content": { "text": "", "claims": […], "citation_mode": "structured" }`.

### Synthesis stage trace

| Field | Value |
|-------|-------|
| `agent_trace_json.stages.synthesise.action` | `synthesise_completed` |
| `generated` | 6 |
| `failed` | 0 |
| `section_count` | 6 |
| Per-section token fields in trace | **absent** (pipeline trace does not record OpenAI input/output tokens) |
| Walk `cost.openai_*_tokens` | 0 (accounting reads `stages.synthesise.openai_*`, not populated) |

**Classification (a/b/c/d):**

| Code | Applicable? | Evidence |
|------|-------------|----------|
| **(a) No LLM call** | No | Six sections `GENERATED`; 63 structured claims persisted; `synthesise_completed` |
| **(b) Call with starved inputs / claims-only output** | **Partial** | Inputs not fact-starved (see D2); model output shape is **claims populated, `generated_content.text` empty** on all sections |
| **(c) Produced but not persisted** | No | `after_synthesis` snapshot matches export snapshot for text/claims |
| **(d) Persisted but export reads wrong keys** | **Yes — primary render break** | `docx_renderer` line 218–223: renders body only when `content.text.strip()` non-empty; **`claims` never consulted** |

Binding note: `resolve_structured_synthesis` / `bind_structured_claims` set `structured_bind_status: bound` when ≥1 claim binds; **`BoundSectionContent.text` remains empty** when the model omits prose (`working_text` starts from model `text` field only — `synthesis_claim_binding.py`).

### Export renderer behaviour

**Source read per section:** `content_json.sections[]` matched by `section_key`; body from `section.content.text` only.

**Code path:** `app/reports/export/docx_renderer.py`

```218:226:app/reports/export/docx_renderer.py
        text = str(content.get("text") or "")
        ...
        if status in ("GENERATED", "AWAITING_REVIEW", "ACCEPTED") and text.strip():
            _render_section_body(document, text)
        elif status == "FAILED":
            pass
        # Empty / missing content: heading only — no internal placeholder paragraphs.
```

**Template table headings:** For each `required_tables[]` entry, renderer adds a level-2 heading from template label only (`docx_renderer.py` 205–210). **No rows** are built from KB, `format_rules_json.logframe`, or `content.claims`.

**Committed export inspection (`snapshots/p3_b3_export_fcdo_7cdcc3a8.docx`):**

| Metric | Value |
|--------|------:|
| Non-empty paragraphs | 16 |
| Word tables | 0 |
| Body content | Title block + six section H1 headings + five table H2 headings (e.g. “Annual Outcome Assessment”, “Evidence quality and gaps”) — **no narrative paragraphs** |

`format_rules_json.logframe.enabled` is `true` on template v2, but **`render_donor_report_docx` does not consume `format_rules_json.logframe`** — logframe table cannot emit via current renderer regardless of KB content.

---

## D2 · Two-consumer template diff (v1 `aa6c9926…` vs v2 `c151a434…`)

### Fields read by `report_inputs_builder.py`

| Field / source | Read how | Present v1? | Present v2? | Identical shape? |
|----------------|----------|-------------|-------------|------------------|
| `section.archetype` | `_fact_prefixes_for_section` | Yes | Yes | Yes (surviving sections) |
| `section.required_indicators[]` | `_indicator_match_tokens` | Yes | Yes | Yes |
| `section.required_tables[].data_source` | `_fact_prefixes_for_section` | Yes | Yes | Yes (per surviving section) |
| Full `section` object | Passed in `report_inputs["section"]` → synthesis prompt | Yes | Yes | **Differs** — v2 adds v1.2.0 tag blocks |
| `section.required_tables[]` (summary) | Synthesis + export headings | **Includes `review_summary_sheet`** | **Empty `[]`** (kill-list removal) | **No** |
| `section.indicator_requirements` | Not read by builder; in prompt JSON | Absent | Present | N/A |
| `section.table_requirements` | Not read by builder; in prompt JSON | Absent on most | Present | N/A |
| `template.format_rules_json` | `_narrative_constraints`, export | Yes | Yes | **Identical** |
| `template.terminology_map_json` | `_terminology_resolved` | Yes | Yes | **Identical** |
| `template.funder_name` / `template_name` | Envelope | Yes | Yes | Yes |
| P3-4 `derived.linked_proposal_summary` | `_linked_proposal_summary(db)` | null (no linked proposal) | null | Yes |

**Surviving section count:** v1 8 → v2 6 (removed `detailed_output_scoring`, `value_for_money`).

### Decisive experiment — fact subset offline (same KB as walk)

KB: `walk_p3_b3_fcdo_7cdcc3a8.json` → `after_export.report.knowledge_bank_json`  
Method: replicate `subset_facts_for_section` + `filter_citable_facts` (same logic as `report_inputs_builder.py`).

| Section | v1 subset fact count | v2 subset fact count | Delta | Keys only in v1 | Keys only in v2 |
|---------|---------------------:|---------------------:|------:|----------------:|----------------:|
| `summary_and_overview` | 62 | 62 | **0** | 0 | 0 |
| `performance_and_conclusions` | 39 | 39 | **0** | 0 | 0 |

**Conclusion:** For the narrative and logframe-bearing sections, **v2 does not reduce synthesis-facing fact inputs**. The gap engine contract and the inputs-builder trim path receive the same citable fact keys under v1 and v2 for this KB.

Prompt JSON size differs only by added tag metadata on the embedded `section` object (v1.2.0 tags); fact payloads in `knowledge_bank.facts` within each section call are unchanged.

---

## D3 · NLCF control — `df7450dc`

### content_json per section (after export)

| section_key | status | `text` len | claims total | claims bound |
|-------------|--------|----------:|-------------:|-------------:|
| project_story | ACCEPTED | **1180** | 7 | 6 |
| community_involvement | ACCEPTED | 0 | 0 | 0 (generation FAILED at synth) |
| difference_made | ACCEPTED | 0 | 18 | 6 |
| learning | ACCEPTED | 0 | 5 | 5 |
| changes_and_next_steps | ACCEPTED | 0 | 8 | 6 |
| spend_summary | ACCEPTED | 0 | 7 | 6 |

**Pattern:** One section (`project_story`) drafted with KB-backed prose; five sections have **claims but zero `text`** (same structured-bind shape as FCDO). `community_involvement` has neither claims nor text (synthesis `FAILED`).

**Export (`snapshots/p3_b3_export_nlcf_df7450dc.docx`):** 23 non-empty paragraphs — title block + **`project_story` body paragraphs** + heading-only sections for the rest; **0 Word tables**. Four assumptions appended (from `project_story` only).

**NLCF vs FCDO difference observed in exports:** NLCF is not “fully drafted with caveats throughout” — it is **one drafted section + five heading-only sections** under the same export rules. FCDO has **zero drafted sections** because **all six** returned empty `text` (despite bound claims).

---

## D4 · Gate 3 record — harness auto-confirm over empty FCDO content

### FCDO walk sequence (from `p3_b3_fcdo_walk.log` + snapshots)

| Step | Timestamp / status | Notes |
|------|-------------------|-------|
| Gate 2 submit | `GATE2 gaps=2 answered=0 skipped=2` → 200 | Gaps skipped, synthesis unlocked |
| Synthesis complete | `2026-06-11T16:06:05.752277+00:00` | 6 generated, 0 failed |
| Resume critique | 200 | Critic trace: `skipped: 6`, `flagged: 0` |
| Accept all | 200 | Sets every section `generation_status: ACCEPTED` — **no text check** |
| Gate 3 confirm | 200 | `kb.gate3_confirmed_at: 2026-06-11T16:06:29.396048+00:00` |
| Export | done | `template_version: 2`, 37828 bytes |

**Gate 3 preconditions exercised (`gate3_confirmation_service.confirm_gate3`):**

- Requires `content_json.sections` non-empty — **passes with empty-text sections**
- Requires critique `action == critique_completed` — passes (6 skipped, 0 blocks)
- Requires all sections `ACCEPTED` — passes after harness `accept-all`
- **Does not inspect** `content.text` length, claim count, or `structured_bind_status`

**Harness source:** `scripts/audit/full_walk.py` → `accept_all_sections` + `confirm_gate3` API calls (audit tooling, not owner UI).

---

## Findings register (facts only — no remediation)

| ID | Finding | P3-7 disposition |
|----|---------|------------------|
| F-1 | FCDO KB at export: **79 facts**, **10** `logframe_ar1_actual` indicator rows, **2** gap answers; Gate 1/2 confirmed. | Unchanged fact; KB path intact for renderer. |
| F-2 | Gap stage emitted the adjudicated **2-ref set**; intake/reconcile loop closed before synthesis. | Unchanged; phase2 validator now grades at Gate-2 boundary snapshot. |
| F-3 | All six FCDO sections: **`content.text` length 0** after synthesis; **63 claims** (29 bound) persisted. | **Addressed (branch i):** binder assembles prose from bound claims; synthesis fails if still empty. |
| F-4 | Synthesis trace reports **`synthesise_completed` / generated=6**; per-section OpenAI token counts **not captured** in `agent_trace_json`. | **Addressed:** `openai_input_tokens` / `openai_output_tokens` on synthesise stage trace. |
| F-5 | **Primary render break:** `docx_renderer` reads **`content.text` only**; ignores **`content.claims`** — headings-only export is expected given F-2/F-3. | **Addressed upstream:** prose populated at synthesis; renderer still text-first (by design). |
| F-6 | **No logframe/table body path** in renderer — `format_rules_json.logframe` unused; template `required_tables` emit **headings only**. Export had **0 tables**. | **Addressed:** `kb_table_renderer` + docx table emission from KB. |
| F-7 | **Template inputs-builder starvation hypothesis rejected** — v1 vs v2 **identical fact subset counts** (62 and 39) for summary and performance sections on this KB. | Confirmed exonerated; no inputs-builder change. |
| F-8 | v2 template diff vs v1 on surviving sections: adds **v1.2.0 tag metadata**; removes **summary `review_summary_sheet` table** from template definition; **`format_rules_json` identical**. | Out of scope (template fence); renderer no longer heading-only for logframe. |
| F-9 | Structured bind accepts **claims-only** output: `structured_bind_status: bound` with **empty prose** does not fail synthesis. | **Addressed:** `EMPTY_SECTION_PROSE` fail-closed + claim assembly. |
| F-10 | NLCF control: **same export/text/claims split** on 5/6 sections; only **`project_story`** has non-zero `text` (1180 chars). | Same contract fix applies; owner re-walk pending. |
| F-11 | Gate 3 harness **auto-confirmed** FCDO with **all sections ACCEPTED and empty prose** — no content-quality gate at confirm time. | **Addressed:** accept API + Gate 3 prose/bind preconditions. |
| F-12 | Walk cost summary **`openai_*_tokens: 0`** is an **artefact accounting gap**, not proof that synthesis did not run (claims contradict zero-call). | **Addressed:** synthesise trace token fields populated. |

---

## STOP (diagnosis — superseded for remediation by P3-7)

Diagnosis complete. Owner decides correction package. Expected shape on confirmation (not authorized here): template field repair or inputs-builder contract fix; synthesis-facing assertion in template post-state check; rubric pointed at live exports; Gate 3 no-rubber-stamp rule.

**P3-7 correction package built** — see `ME_MODULE_DECISION_LOG.md` P3-7 entry. Owner-triggered re-walk remains.

**Artefact paths for owner reading:**

- FCDO export: `docs/artefacts/me_module/audits/snapshots/p3_b3_export_fcdo_7cdcc3a8.docx`
- NLCF export: `docs/artefacts/me_module/audits/snapshots/p3_b3_export_nlcf_df7450dc.docx`
- Gap-stage JSON: `docs/artefacts/me_module/audits/snapshots/p3_b3_gap_stage_7cdcc3a8.json`
