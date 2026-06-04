# Failed-sections diagnosis — F1 synthesis (6643d922)

**Report:** `6643d922-150d-4000-b878-4025e7c9145a` (FCDO / BridgeLight, 72-fact KB)  
**Date:** 2026-06-04  
**Scope:** Read-only — why `detailed_output_scoring` (C) and `value_for_money` (D) have no prose while six sections succeeded.

**Sources:** Production Postgres `donor_reports.content_json`, `report_jobs.agent_trace_json`; walk artifact `FCDO_PLANTED_CONFLICT_POST_F1_WALK_6643d922.json`; prior walks `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json`, `F1_PROSE_WALK_fe6bf98b.json`; code under `app/reports/services/report_synthesis_service.py`, `app/integrations/openai_client.py`, `app/reports/ai/prompts/synthesis.py`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`.

---

## Executive verdict

Both sections failed at **F1 OpenAI call time** with **`failure_reason: "timeout"`** — the HTTP client’s **90s wall-clock limit** was exceeded before any model JSON was returned. This is **not** missing KB data, **not** JSON-parse rejection of a returned payload, and **not** the model returning `generation_status: "INSUFFICIENT_INPUT"` (that path would store the model’s `warnings[]` text as `failure_reason`, not the literal string `"timeout"`).

`agent_trace_json` has **no per-section synthesis detail** — only stage-level aggregates. The verbatim failure signatures come from **`content_json.sections[]`** (preserved through Gate 3 accept-all).

---

## 1. What F1 actually did for C and D

### Agent trace (stage-level only)

From `report_jobs.agent_trace_json.stages.synthesise` for `6643d922`:

```json
{
  "action": "synthesise_completed",
  "failed": 2,
  "degraded": true,
  "generated": 6,
  "completed_at": "2026-06-01T19:06:31.656809+00:00",
  "section_count": 8,
  "gate2_confirmed_at": "2026-06-01T19:03:57.203042+00:00"
}
```

`content_json.generation_summary` matches:

```json
{
  "failed": 2,
  "generated": 6,
  "total_sections": 8,
  "warnings": [
    "section detailed_output_scoring failed",
    "section value_for_money failed"
  ]
}
```

**No per-section errors, tokens, retries, or raw model output are recorded in `agent_trace_json`.** Diagnosis relies on `content_json` section rows and code path mapping for `failure_reason: "timeout"`.

### content_json — section C (`detailed_output_scoring`)

Stored state (production DB, 2026-06-04):

| Field | Value |
|--------|--------|
| `generation_status` | `ACCEPTED` *(Gate 3 accept-all overwrote pre-review status; synthesis-time status was `FAILED` per walk artifact)* |
| `failure_reason` | **`"timeout"`** |
| `content.text` | `""` (empty) |
| `content.evidence_used` | `[]` |
| `archetype` | `null` |
| `constraints_applied.word_limit` | `0` |
| `constraints_applied.word_limit_respected` | `false` |

Walk snapshot at post-F1 critique (`FCDO_PLANTED_CONFLICT_POST_F1_WALK_6643d922.json`):

```json
{
  "section_key": "detailed_output_scoring",
  "generation_status": "FAILED",
  "critic_flags_count": 0,
  "critic_flags": []
}
```

### content_json — section D (`value_for_money`)

| Field | Value |
|--------|--------|
| `generation_status` | `ACCEPTED` *(same Gate 3 overwrite)* |
| `failure_reason` | **`"timeout"`** |
| `content.text` | `""` |
| `content.evidence_used` | `[]` |
| `archetype` | `null` |
| `constraints_applied.word_limit` | `1200` |
| `constraints_applied.word_limit_respected` | `false` |

Walk snapshot:

```json
{
  "section_key": "value_for_money",
  "generation_status": "FAILED",
  "critic_flags_count": 0,
  "critic_flags": []
}
```

### Code path for `"timeout"`

In `report_synthesis_service._generate_one_section`, `failure_reason: exc.category` is set when `OpenAIServiceError` is raised. In `openai_client.py`, `httpx.TimeoutException` maps to:

```python
OpenAIServiceError(category="timeout", retryable=False, ...)
```

with client `timeout=90.0` seconds. **Interpretation:** the model call did not complete within 90s; F1 never received JSON to parse. Empty `content.text` confirms **no usable generation was persisted** — not “parser rejected model output.”

Contrast — model-declined path (`generation_status != "GENERATED"` in parsed JSON) would yield `failure_reason` like joined `warnings[]` or `"INSUFFICIENT_INPUT"` (see `fe6bf98b` walk below).

---

## 2. Archetype correlation (template vs succeeded sections)

From `TEMPLATE_INSTANCE_FCDO.json`:

| Section | Archetype | `word_limit` | `required_indicators` | Table cols | `min_rows` | Outcome on 6643d922 |
|---------|-----------|--------------|----------------------|------------|------------|---------------------|
| summary_and_overview | `ARCH_EXECUTIVE_REVIEW_SUMMARY` | 900 | 4 | 8 | 1 | prose ✓ |
| performance_and_conclusions | `ARCH_PERFORMANCE_CONCLUSIONS` | 1200 | 4 | 5 | 1 | prose ✓ |
| **detailed_output_scoring** | **`ARCH_OUTPUT_SCORING_TABLE`** | **null** | **6** | **10** | **1** | **failed (timeout)** |
| evidence_and_evaluation | `ARCH_EVIDENCE_AND_EVALUATION_REVIEW` | 900 | 4 | 5 | 0 | prose ✓ |
| risk_and_safeguarding | `ARCH_RISK_ASSUMPTIONS_AND_CONTROLS` | 900 | 5 | 6 | 0 | prose ✓ |
| **value_for_money** | **`ARCH_VALUE_FOR_MONEY_4E`** | 1200 | **7** | 6 | **1** | **failed (timeout)** |
| programme_management… | `ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW` | 1200 | 6 | 5 | 0 | prose ✓ |
| recommendations_and_actions | `ARCH_RECOMMENDATIONS_ACTION_PLAN` | 900 | 3 | 6 | 0 | prose ✓ |

**Finding:** The two failures are **exactly** the two sections whose archetypes are `ARCH_OUTPUT_SCORING_TABLE` and `ARCH_VALUE_FOR_MONEY_4E`. They also have the **largest table column counts (10 and 6)** and **highest required-indicator counts (6 and 7)** in the template. However, **table presence alone does not explain failure** — four other sections also define `required_tables` and generated successfully (including `programme_management` with six indicators and financial table).

**Not archetype/schema rejection:** All sections use the **same** F1 JSON envelope (`generation_status`, `generated_content.text`, etc.) in `synthesis.py`; there is **no separate table-emission schema** or stricter parser for C/D. Archetype affects prompt text (`REPORT_ARCHETYPE_RULES`) only.

**Correlation verdict:** **Partially archetype-driven** — failures align with the two table-heavy scoring/VfM archetypes and the largest section definitions, but the **mechanism is transport timeout**, not structured-output validation.

---

## 3. Failure class

**Named class: (b) token/length/time ceiling — HTTP client timeout on parallel F1 OpenAI calls, with workload skew toward C/D prompts.**

Evidence:

1. Verbatim `failure_reason: "timeout"` on both sections (not parse error, not `INSUFFICIENT_INPUT`).
2. `openai_client` 90s fixed timeout; timeout is **`retryable=False`** — one slow call → immediate section failure.
3. F1 runs up to **5 sections concurrently** (`MAX_CONCURRENT_SECTIONS = 5`) with the **full 72-fact KB** embedded in every `report_inputs` JSON (`build_report_inputs_for_section` does not section-filter facts).
4. C/D prompts include the largest `section_json` payloads (most indicators + wide tables), increasing input tokens and model work while sharing the same 90s budget.

**Ruled out for 6643d922:**

| Hypothesis | Ruled out because |
|------------|-------------------|
| (a) Table JSON schema too strict | Same JSON schema for all sections; failure is pre-response timeout |
| (c) KB shape missing for C/D | 72 facts incl. 20 `financials.lines.*`, 21 `.y1_actual` indicators; gap `detailed_output_scoring:indicator:output_scores` **answered** |
| (d) E3-style JSON flake | Would surface as parse/`ValueError` in `failure_reason`, not `"timeout"` |
| Model `INSUFFICIENT_INPUT` | Would populate `failure_reason` from model `warnings[]`; see contrasting `fe6bf98b` C below |

---

## 4. Deterministic vs flake

| Walk / report | C (`detailed_output_scoring`) | D (`value_for_money`) |
|---------------|------------------------------|------------------------|
| **6643d922** (this report, 72 facts) | `FAILED` — **`timeout`** | `FAILED` — **`timeout`** |
| **5026ab66** (prior planted-conflict, same upload set) | **Generated** (prose + critic flags) | **Generated** (prose + critic flags) |
| **fe6bf98b** (~33 facts) | `FAILED` — long model **`warnings[]`** (insufficient scored table data) | `FAILED` — **`timeout`** |

**Verdict: not deterministic.** The same FCDO template sections can succeed or fail across runs; C can fail as timeout **or** as model-declined `INSUFFICIENT_INPUT` depending on KB richness and run conditions. **6643d922’s double timeout is consistent with flake under parallel load + 90s cap**, not a fixed “C/D always fail” rule.

---

## 5. Input sufficiency (confirm only)

Production KB on `6643d922` (read-only counts):

- **72** facts; **20** `financials.lines.op*.*.y1_*` keys; **21** indicator `.y1_actual` keys
- **Section C:** `detailed_output_scoring:indicator:output_scores` → **`answered`** (“Output scoring is populated from the BridgeLight AR1 export with proposed scores A–C…”); other C checklist items **skipped** at Gate 2 (table/weightings/ratings)
- **Section D:** all seven VfM gap items **`skipped`** — but **financial line facts exist** for economy/efficiency narrative; programme_management section successfully wrote financial prose from the same KB

**Conclusion:** Data sufficient for F1 to attempt C/D; failures are **generation transport / time budget**, not reconcile or Gate 2 absence. *(Separate product note: D’s skipped VfM gap answers may increase model deliberation time but do not explain timeout on C, which has an answered output-scores gap.)*

---

## Recommended fix shape (describe only)

Smallest changes likely to make C/D generate on this report class:

1. **Raise or feature-scope HTTP timeout** for `feature="report_synthesis"` (e.g. >90s) and/or **retry on `category="timeout"`** (today `retryable=False`).
2. **Optional concurrency throttle** for synthesis — run C/D sequentially or with lower `MAX_CONCURRENT_SECTIONS` when KB fact count is large, to reduce parallel API contention.
3. **Optional prompt diet** — pass section-relevant fact/gap subsets in `build_report_inputs_for_section` for table archetypes (72-fact full dump inflates every call); keep contract shapes unchanged.
4. **Do not** start with archetype schema changes or renderer/export work — failures occur before any text is stored.

Do **not** treat as primary fix: re-answering skipped VfM gaps (helps content quality, not timeout); table JSON emitters (no such path exists in F1 today).

---

## Trace availability note (per STOP condition)

**`agent_trace_json` does not contain per-section synthesis detail for C/D.** Available signals: stage aggregate above, `content_json` section rows quoted here, `generation_summary.warnings`, and walk artifacts. Cause attribution uses **`failure_reason` + code mapping**, not inferred from section names alone.

---

**Failure class is OpenAI HTTP timeout on F1 parallel section calls, fix is increase/retry synthesis timeouts and optionally reduce prompt load or concurrency for table archetypes, deterministic=no.**
