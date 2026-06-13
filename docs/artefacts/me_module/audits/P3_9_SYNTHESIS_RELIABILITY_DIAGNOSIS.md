# P3-9 — Synthesis reliability diagnosis (read-only)

**Authority:** Owner-triggered characterize-before-build pass.  
**Scope:** Clusters A–D from P3-8 re-walk evidence (§8) plus P3-7 re-walk snapshots and code-path trace.  
**Constraints:** No code changes, no prod writes, no new walks. Findings only.

**Evidence base:**

| Walk | Report ID | Verdict | Gate-3 refusing `section_key` |
|------|-----------|---------|-------------------------------|
| P3-7 FCDO re-walk | `1beb588b-68e1-4ad9-a43e-a6695aa15dd6` | **completed** (exit 0) | — |
| P3-7 NLCF re-walk | `6c756017-d510-46b0-a765-bdd82605a7a1` | `accept_all_failed` | `changes_and_next_steps` |
| P3-8 FCDO re-walk | `d838c419-8ac3-44c4-a22e-d713e491bcc6` | `accept_all_failed` | `evidence_and_evaluation` |
| P3-8 NLCF re-walk | `588c3e7d-d16b-49b2-b4f4-9c2a695c1c2c` | `accept_all_failed` | `community_involvement` (422); also `changes_and_next_steps` FAILED |

**Note on “P3-7 FCDO summary”:** Committed P3-7 FCDO re-walk **did not freeze**; `summary_and_overview` reached ACCEPTED with 433 chars ([`P3_7_REWALK_EVIDENCE.md`](P3_7_REWALK_EVIDENCE.md) §4). The three **frozen** live walks are P3-7 NLCF + both P3-8 walks. Closest historical “summary” analogue is P3-B3 FCDO (`7cdcc3a8`), where `summary_and_overview` was GENERATED/ACCEPTED with **0 chars text** but populated claims ([`P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md`](P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md)) — a different failure class (empty prose / export field), not Gate-3 FAILED.

---

## Executive summary

| Cluster | One-line characterization | Root cause (where established) |
|---------|---------------------------|--------------------------------|
| **A** Synthesis failures | **Several failure modes** under one pipeline, not one bug | Stochastic single-shot JSON synthesis with **no parse retry**; two distinct post-call paths (`json.loads` exception vs model `INSUFFICIENT_INPUT`) |
| **B** Logframe KB keys | Spreadsheet **was read**; actuals **are in KB** under wrong suffix | **Key-naming mismatch:** pipeline writes `indicators.{OP}.actual`; table renderer reads `indicators.{OP}.logframe_ar1_actual` |
| **C** Insufficiency routing | Preflight predicate disagrees with model path for skipped-gap docsets | **Skipped gap answers count as “satisfied”** for `section_has_synthesizable_inputs`; narrative indicators auto-satisfied; live prose uses empty `required_indicators` on `project_story` |
| **D** gap-check 500 | Deterministic server bug on every gap-check with remaining items | **`NameError`:** `GapCheckMissingItemResponse` used in `gap_check_service.py` but **not imported** |

**Cluster A verdict:** **Not ONE structural issue** — shared pipeline properties (single OpenAI call, `json.loads` without repair, concurrent sections, Gate-3 all-or-nothing) plus **at least two independent failure mechanisms** (transport/API vs parse vs model refusal vs bind/empty-prose).

---

## Cluster A — Synthesis JSON-parse / FAILED sections (Q1)

### A.1 Failure inventory (live walks)

#### P3-8 FCDO (`d838c419…`) — synthesise trace

| Metric | Value |
|--------|------:|
| `failed` / `generated` | 1 / 5 |
| `openai_input_tokens` | 55,412 |
| `openai_output_tokens` | 2,915 |
| Gate-3 blocker | `evidence_and_evaluation` |

| section_key | generation_status | text chars | failure_reason / path |
|-------------|-------------------|----------:|------------------------|
| summary_and_overview | GENERATED | 415 | bound prose |
| performance_and_conclusions | GENERATED | 389 | bound prose |
| **evidence_and_evaluation** | **FAILED** | **0** | `Unterminated string starting at: line 133 column 22 (char 8092)` — **`json.loads` in `_extract_json_payload`** |
| risk_and_safeguarding | AWAITING_REVIEW | 363 | bound prose |
| programme_management_delivery_commercial_financial | GENERATED | 219 | bound prose |
| recommendations_and_actions | AWAITING_REVIEW | 334 | bound prose |

#### P3-8 NLCF (`588c3e7d…`) — synthesise trace

| Metric | Value |
|--------|------:|
| `failed` / `generated` | 2 / 4 |
| `openai_input_tokens` | 22,438 |
| `openai_output_tokens` | 3,052 |
| Gate-3 blocker (422 `details.section_key`) | `community_involvement` |
| Additional FAILED section | `changes_and_next_steps` |

| section_key | generation_status | structured_bind_status | text chars | failure_reason / path |
|-------------|-------------------|------------------------|----------:|------------------------|
| project_story | GENERATED | **insufficient_data** | 445 | P3-8 preflight (no OpenAI) |
| **community_involvement** | **FAILED** | — | **0** | Model `INSUFFICIENT_INPUT` warnings joined → `build_failed_section` |
| difference_made | GENERATED | bound | 290 | prose |
| learning | AWAITING_REVIEW | bound | 1,043 | prose |
| **changes_and_next_steps** | **FAILED** | — | **0** | Model `INSUFFICIENT_INPUT` (same path as P3-7 NLCF) |
| spend_summary | AWAITING_REVIEW | bound | 463 | prose |

#### P3-7 NLCF (`6c756017…`) — for rotation context

| Metric | Value |
|--------|------:|
| `failed` / `generated` | 1 / 5 |
| Gate-3 blocker | `changes_and_next_steps` |

`changes_and_next_steps` FAILED with model warnings (verbatim from walk artefact):

> Insufficient evidence was available to report substantively on required indicators for this section.; Gap answers for changes made, planned changes, and support needed were skipped as not applicable, so no specific adaptation narrative could be evidenced.

Other NLCF sections on that walk: real prose (890–1,847 chars). **No** `insufficient_data` path (P3-8 policy not deployed).

#### P3-7 FCDO (`1beb588b…`) — completed reference

All six sections GENERATED → ACCEPTED; **0 synthesis failures**. Export produced; **0 Word tables** (KB lacked `logframe_ar1_actual` keys — see Cluster B).

### A.2 Failure **class** taxonomy (not per-section anecdotes)

| Class | Mechanism | Observed on | Code locus |
|-------|-----------|-------------|------------|
| **A-JSON** | OpenAI returns HTTP 200 + body, but `json.loads(content)` raises (e.g. unterminated string) | P3-8 FCDO `evidence_and_evaluation` | `report_synthesis_service._extract_json_payload` → bare `json.loads`; caught as generic `Exception` → FAILED |
| **A-MODEL** | Model returns parseable JSON with `generation_status != "GENERATED"` / `warnings[]` | P3-7/8 NLCF `changes_and_next_steps`; P3-8 `community_involvement` | `_generate_one_section` lines 212–221 → `build_failed_section` |
| **A-PREFLIGHT** | No OpenAI call; engine insufficiency prose | P3-8 NLCF `project_story` only | `section_has_synthesizable_inputs` → `build_insufficient_data_section` |
| **A-BIND/EMPTY** | (Historical / P3-B3) Claims bound, `text` empty; export starved | P3-B3 FCDO all sections | `resolve_structured_synthesis` + export reads `content.text` only — **not observed as Gate-3 FAILED on P3-7/8 walks** |

Rotating Gate-3 `section_key` across frozen walks reflects **which section drew the stochastic failure** in a given run, not section-specific code forks. All sections share the same `_generate_one_section` pipeline.

### A.3 Correlation analysis (prompt size, archetype, humaniser, proposal context)

| Hypothesis | Finding |
|------------|---------|
| **Prompt size** | No per-section prompt/token logging in walk artefacts. Walk totals only. FCDO 55k input tokens / 6 sections ≈ high aggregate context (KB + proposal injection via `build_report_inputs_for_section`). **Cannot confirm** failed section had largest prompt from captured data. |
| **Archetype** | Failed sections span `ARCH_EVIDENCE_AND_EVALUATION_REVIEW` (FCDO), `ARCH_PARTICIPATION_AND_COMMUNITY_VOICE` + `ARCH_ADAPTATION_AND_NEXT_STEPS` (NLCF). Successful siblings include other archetypes on same walk. **No archetype-exclusive code path** to FAILED. |
| **P3-4 humaniser** | Humaniser runs **after** synthesis in critique stage, not on failed sections. FCDO JSON failure occurs **before** humaniser. **Not causal** for A-JSON/A-MODEL failures. |
| **Proposal-context injection (b20b27a..HEAD)** | All walks use `build_report_inputs_for_section` with full KB subset. FCDO walks with same docset can **complete** (P3-7) or **fail one section** (P3-8). **Not deterministic** with injection alone. |
| **Output token limit / truncation** | `evidence_and_evaluation` `word_limit: 900` → `_max_tokens_for_section` = `min(2250, 2500)` = **2250** max completion tokens. Error cites **char 8092** in raw content — large JSON payload consistent with **truncated completion mid-string**. **Plausible, not proven** (raw body not captured). |
| **Concurrency** | `ME_SYNTHESIS_MAX_CONCURRENCY` default **2** — sections race in thread pool. Failures do not cluster by batch order in artefacts. **Inconclusive** as root cause. |

### A.4 Retry on malformed JSON

| Layer | Retries? | Evidence |
|-------|----------|----------|
| **OpenAI HTTP** (`OpenAIClient.create_chat_completion`) | Yes — API/transport errors, `report_synthesis` feature marked retryable | `openai_client.py` `_MAX_RETRIES` loop |
| **JSON parse** (`_extract_json_payload`) | **No** | Single `json.loads(content)`; any parse error → section FAILED immediately |
| **Model INSUFFICIENT_INPUT** | **No** | Warnings joined to `failure_reason`; no second prompt |

**Why A-JSON did not recover:** parse failure is treated as terminal section error; no re-prompt, no JSON repair pass, no fallback to partial claims.

### A.5 Raw failing model responses

Walk artefacts (`walk_p3_8_rewalk_*.json`, `walk_p3_7_rewalk_nlcf_*.json`) persist **`failure_reason` strings** and **`agent_trace_json.stages.synthesise`** aggregates (tokens, failed count). They do **not** persist raw OpenAI `message.content` for failed sections. **Raw JSON not available** in committed evidence for post-mortem of char 8092.

Local verification: `pytest tests/test_gap_check_routes.py::test_get_gap_check_returns_unanswered_gaps` **fails** with the same `NameError` as production gap-check (Cluster D) — unrelated to synthesis but confirms test gap vs prod symptom.

---

## Cluster B — FCDO logframe actuals vs KB (`logframe_ar1_actual`) (Q2)

### B.1 Docset and extraction (P3-8 FCDO walk `d838c419…`)

Walk log confirms three uploads including spreadsheet:

1. `01_FCDO_BridgeLight_Winning_Proposal.docx`
2. `02_FCDO_BridgeLight_Award_Letter.docx`
3. `BridgeLight Logframe and Finance AR1 Export.xlsx` — `extraction_status: COMPLETE`

**Indicator extractor output (xlsx structured):** 10 indicator rows (e.g. `OP1.1` actual normalized **684**).

### B.2 What reached `knowledge_bank_json` (after reconcile)

| Metric | Value |
|--------|------:|
| Total facts | 78 |
| `indicators.*` keys | 36 |
| Keys matching `*.logframe_ar1_actual` | **0** |
| `indicators.*.actual` from xlsx | **10** (e.g. `indicators.OP1.1.actual` = 684, source `BridgeLight Logframe and Finance AR1 Export.xlsx`) |
| `financials.lines.*.actual` from xlsx | 10 (spend columns — separate facet) |

**Spreadsheet actuals match source:** e.g. xlsx row `OP1.1` actual 684 = KB `indicators.OP1.1.actual` value 684.

### B.3 Pipeline trace (extractor → reconciler → KB)

```
xlsx → indicator_data_extractor → structured.indicators[].{target,actual}
     → reconciliation.input_builder._flatten_indicator_data
         field_path = f"indicators.{row_id}.{facet}"   # facet ∈ {target, actual}
     → reconciler → knowledge_bank_json.facts["indicators.OP1.1.actual"]
```

**No production code path** assigns the suffix `logframe_ar1_actual`. Grep across `app/` shows `logframe_ar1_actual` **only** in `kb_table_renderer.py` (consumer) and tests/fixtures — not in extractor, reconciler, or gap logic.

### B.4 What the table renderer expects

`kb_table_renderer.py` resolves:

```text
indicators.{OPx.y}.logframe_ar1_actual
indicators.{OPx.y}.logframe_ar1_target   # optional; falls back to proposal target
```

With P3-8 KB keys (`indicators.OP1.1.actual`), `_resolve_fact_key(…, "OP1.1.logframe_ar1_actual")` returns **None** → table rows omit actuals → **no logframe table in export**.

### B.5 Gap / satisfaction logic vs table renderer (split brain)

`logframe_completeness.has_indicator_data_actual_for_id` treats **`indicators.*.actual`** from indicator-data sources (xlsx provenance) as valid AR1 actuals. Gap engine correctly surfaces only `op2_3` / `op4_4` missing rows. **Synthesis and gap logic see the data; export table does not.**

### B.6 Root cause (Cluster B)

| Layer | Verdict |
|-------|---------|
| Extractor | **Not broken** — reads xlsx, emits actuals |
| Reconciler drop | **Not observed** — actuals present under `.actual` |
| Key-naming mismatch | **Established** — writer uses `.actual`; table renderer and unit tests use `.logframe_ar1_actual` |

This explains **zero production logframe tables** on P3-7 and P3-8 FCDO walks despite spreadsheet in docset. P3-B3 diagnosis citing 10 `logframe_ar1_actual` keys is **inconsistent with current production reconciler code** (likely artefact/labelling drift or pre-canonicalization snapshot); current HEAD never mints that suffix.

---

## Cluster C — Insufficiency routing and live vs unit prose (Q3)

### C.1 Why `project_story` got `insufficient_data`, not `changes_and_next_steps`

Offline replay of `section_has_synthesizable_inputs` logic against P3-8 NLCF KB **after Gate-2 skip** (`after_synthesis` snapshot):

| section_key | `section_has_synthesizable_inputs` | Why |
|-------------|-------------------------------------|-----|
| **project_story** | **False** | Template `required_indicators: []`. Section-level narrative requirement: no citable facts with `projectstory` token in fact keys → **not satisfied** → preflight insufficiency. |
| **community_involvement** | **True** | Indicators `community_participation_examples`, `partner_or_local_collaboration_examples` classified **`narrative`** (`NARRATIVE_INDICATORS` set in `requirement_metadata.py`). `evaluate_requirement_satisfaction` for `requirement_type == "narrative"` + `required_item_type == "indicator"` returns **`satisfied=True` without fact check** (lines 142–150). → OpenAI called → model INSUFFICIENT_INPUT → FAILED. |
| **changes_and_next_steps** | **True** | Data indicators `changes_made`, `planned_changes`, `support_needed`. All three gap items **skipped** in `gap_answers` after Gate-2. `is_gap_answer_resolved(skipped)` → `evaluate_requirement_satisfaction` returns **satisfied=True** (lines 137–140). → OpenAI called → model INSUFFICIENT_INPUT → FAILED. |

**Gate-3 422** reports first FAILED section in template merge order (`community_involvement` before `changes_and_next_steps` in accept-all scan), though **both** are FAILED.

**Design tension:** Preflight treats **skipped gaps as synthesizable inputs**; model prompt forbids fabricating from skips and returns INSUFFICIENT_INPUT. P3-8 insufficiency path never runs for those sections.

### C.2 Live insufficiency prose vs unit test

**Live text** (`project_story`, P3-8 NLCF):

> …The template requires information on **the required template items**, but no citable source…

**Unit test** (`test_insufficiency_statement_is_professional_and_submittable`) asserts named items e.g. “changes made”, section label “How you are changing what you do”.

**Same builder:** `build_insufficiency_statement` → `build_insufficient_data_section` in both paths.

**Divergence cause:** `_humanize_requirement_refs(unsatisfied_refs or list(section.get("required_indicators") or []))`.

| Context | Section | `required_indicators` | `{items}` phrase |
|---------|---------|----------------------|------------------|
| Unit test | `changes_and_next_steps` | `["changes_made", "planned_changes", "support_needed"]` | Named refs (“changes made, planned changes, and support needed”) |
| Live walk | `project_story` | **`[]`** | Fallback **“the required template items”** |

Live preflight does **not** pass `unsatisfied_refs` from `enumerate_template_requirements` — only template metadata. **Same function, different inputs** — not a forked prose builder.

### C.3 Unit test vs live synthesis path

| Step | Unit test | Live walk |
|------|-----------|-----------|
| Preflight predicate | `_empty_kb()` → false for `changes_and_next_steps` | Post-skip KB → **true** (skipped gaps satisfy data indicators) |
| OpenAI | Mock not called in preflight test | **Called** for `changes_and_next_steps` / `community_involvement` |
| Outcome | `insufficient_data` GENERATED | **FAILED** 0-char |

Unit tests prove insufficiency **when predicate is false**; live sparse docset + skip-all Gate-2 **bypasses** predicate for target sections.

---

## Cluster D — gap-check HTTP 500 (Q4)

### D.1 Observation (both P3-8 walks)

Walk harness (`full_walk.py` ~line 140) calls `GET /api/reports/{id}/gap-check` immediately after Gate-1 confirm, while job is parked at **`synthesise` / `awaiting_human`** (Gate-2 answers not yet submitted).

| Walk | gap-check HTTP | Body |
|------|----------------|------|
| P3-8 FCDO | **500** | `INTERNAL_SERVER_ERROR` |
| P3-8 NLCF | **500** | `INTERNAL_SERVER_ERROR` |

Walk continues; Gate-2 submit uses **`POST …/knowledge-bank/gate2/gap-responses`**, not gap-check.

Post-freeze, `phase2_owner_validation.py` gap-check via owner token on FCDO report **succeeds** (`readiness_message: Complete — 3 items skipped.`).

### D.2 Root cause (established in code)

`app/reports/services/gap_check_service.py`:

- `_missing_item_from_gap` instantiates **`GapCheckMissingItemResponse`**
- **`GapCheckMissingItemResponse` is not imported`** from `app.reports.schemas.gap_check`

Runtime effect when `remaining` gaps is non-empty:

```text
NameError: name 'GapCheckMissingItemResponse' is not defined
```

→ FastAPI **500** (not 409 DomainError).

**Reproduction (local, read-only):**

```text
pytest tests/test_gap_check_routes.py::test_get_gap_check_returns_unanswered_gaps
→ NameError at gap_check_service.py:86
```

**Why post-freeze validator succeeded:** After all gaps skipped, `_remaining_gaps` is empty → list comprehension never calls `_missing_item_from_gap` → no NameError.

**Why CI stayed green:** Smoke/offline replay does not exercise live `GET gap-check` with open items; unit test **fails locally** when run in isolation (same NameError).

---

## Cluster A — Is it ONE structural issue or several?

**Answer: several failure mechanisms; one shared pipeline architecture.**

Shared structural properties (one “envelope”):

1. One OpenAI JSON-object call per section, no second attempt on parse/bind failure.
2. Concurrent section generation (default concurrency 2).
3. Gate-3 accept-all requires **zero** FAILED sections — any single A-JSON or A-MODEL failure blocks export.
4. Stochastic model output — failing section identity rotates across runs.

Independent mechanisms (multiple “issues”):

1. **A-JSON** — no repair/retry after `json.loads` (truncation or malformed JSON).
2. **A-MODEL** — skipped-gap / sparse KB docsets: predicate says “has inputs”, model refuses (`INSUFFICIENT_INPUT`).
3. **A-PREFLIGHT** (P3-8 only) — only fires when predicate false; misaligned with owner intent for skip-all docsets.
4. **A-BIND/EMPTY** (P3-B3 lineage) — claims without `text`; separate from P3-7/8 Gate-3 freezes.

---

## Evidence index

| Artefact | Use |
|----------|-----|
| [`P3_7_REWALK_EVIDENCE.md`](P3_7_REWALK_EVIDENCE.md) §4, §8 | Walk outcomes, section tables, gap-check 500 |
| [`snapshots/p3_8_fcdo_gap_stage_d838c419.json`](snapshots/p3_8_fcdo_gap_stage_d838c419.json) | Gate-2 3-ref set |
| [`snapshots/p3_8_nlcf_gap_stage_588c3e7d.json`](snapshots/p3_8_nlcf_gap_stage_588c3e7d.json) | Gate-2 12-ref set |
| [`snapshots/p3_8_ledger_traces.json`](snapshots/p3_8_ledger_traces.json) | Synthesise token totals |
| `dynamic_run/walk_p3_8_rewalk_*.json` (gitignored) | Full KB, section states, accept 422 bodies |
| [`P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md`](P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md) | P3-B3 empty-text class (historical) |
| `app/reports/services/report_synthesis_service.py` | Synthesis + parse |
| `app/reports/reconciliation/input_builder.py` | `indicators.{row_id}.actual` field_path |
| `app/reports/export/kb_table_renderer.py` | `logframe_ar1_actual` consumer |
| `app/reports/gap/requirement_satisfaction.py` | Skip + narrative-indicator satisfaction |
| `app/reports/services/section_prose.py` | Insufficiency prose builder |
| `app/reports/services/gap_check_service.py` | gap-check 500 NameError |

---

## STOP

Owner review only. No remediation design in this document.
