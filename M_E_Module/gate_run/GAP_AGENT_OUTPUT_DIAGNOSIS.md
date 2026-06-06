# E3 gap-agent output failure modes — read-only diagnosis

**Date:** 2026-06-05  
**Scope:** `gap_compliance_agent` only (model call, input assembly, output handling).  
**Method:** Source, configuration, and committed artefacts only. No pipeline run, no model call, no code change.

**Evidence artefacts referenced (not re-run):**
- [`M_E_Module/gate_run/STAGE_F_WALK_PARKED_2026-06-05.md`](STAGE_F_WALK_PARKED_2026-06-05.md)
- [`M_E_Module/gate_run/STAGE_F_GAP_RESUME_RESULT.json`](STAGE_F_GAP_RESUME_RESULT.json) (2026-06-05 resume failure)
- [`docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`](../../docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json)

---

## 1. API and model

**Answer:** Production gap agent calls the **Anthropic Messages API** (`client.messages.create`) with model string **`claude-sonnet-4-6`** by default (after alias resolution).

**Configuration chain:**

| Setting | Value | Location |
|---------|--------|----------|
| Default model env | `ME_GAP_COMPLIANCE_MODEL` → fallback `ME_RECONCILER_MODEL` → fallback `"claude-sonnet-4-6"` | [`app/reports/agents/gap_compliance_agent.py`](../../app/reports/agents/gap_compliance_agent.py) L42 |
| Short-name alias map | `"sonnet"` → `"claude-sonnet-4-6"` (etc.) | same file L50–54, `_api_model_id()` L125–126 |
| Production call | `AsyncAnthropic(...).messages.create(model=api_model, ...)` | same file L308–321, `_call_anthropic_messages` |

**Orchestrator path:** `query_fn_gap` defaults to `None` in [`OrchestrationContext`](../../app/reports/orchestration/pipeline.py) L83; pipeline passes it to `run_gap_compliance` L200. With `query_fn=None`, the agent uses `_call_anthropic_messages` (direct Anthropic), not OpenAI or a shared wrapper beyond the Anthropic SDK client.

**Shared mechanism with E1:** E1 reconciler uses the same pattern — `AsyncAnthropic().messages.create(...)` with prompt-instruction JSON, no structured-output API params ([`knowledge_bank_reconciler.py`](../../app/reports/agents/knowledge_bank_reconciler.py) L716–728). E1 default model differs; E1 `MAX_OUTPUT_TOKENS` is **16384** vs E3 **8192** (see Q3).

---

## 2. Output enforcement — the format question

**Answer:** **Prompt-instruction only.** No assistant prefill, no tool use / forced tool schema, no native structured outputs, no `response_format` / `json_schema` / `json_object` mode.

**Relevant call parameters (production path):**

```python
response = await client.messages.create(
    model=api_model,
    max_tokens=MAX_OUTPUT_TOKENS,
    temperature=0,
    system=_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": prompt}],
)
```

Source: [`gap_compliance_agent.py`](../../app/reports/agents/gap_compliance_agent.py) L315–321.

**System prompt enforcement (text only):**

```
OUTPUT FORMAT:
- Return a single JSON object only — no markdown fences, no prose, no tools.
- JSON schema: { "readiness_score": ..., "gaps": [ ... ] }
```

Source: same file L79–96 (`_SYSTEM_PROMPT`).

**Post-hoc parsing:** Response text is joined from text blocks and passed to `_parse_json_from_text()` → `json.loads()` (L328–338, L140–162). There is no API-level guarantee of JSON shape.

**Test / SDK path (`query_fn` provided):** Reads `message.structured_output` if present (L363–366) — production orchestrator does not inject this; it is for mocked tests.

**Decisive for prose failure:** With prompt-instruction only, the model **can** emit reasoning prose (as observed on attempt 2 of the 2026-06-05 run). Nothing in the API call prevents it.

---

## 3. Output ceiling — the truncation question

**Answer:** **`max_tokens=8192`** on every gap Anthropic call.

| Constant | Value | Location |
|----------|--------|----------|
| `MAX_OUTPUT_TOKENS` | **8192** | [`gap_compliance_agent.py`](../../app/reports/agents/gap_compliance_agent.py) L46 |
| Passed as | `max_tokens=MAX_OUTPUT_TOKENS` | same file L317 |

Not env-configurable (hardcoded module constant). Compare E1: `MAX_OUTPUT_TOKENS = 16384` in [`knowledge_bank_reconciler.py`](../../app/reports/agents/knowledge_bank_reconciler.py) L95.

**Observed failure alignment (committed artefact, not re-run):** Attempt 1 on FCDO walk produced **~33,091 characters** of JSON before `Unterminated string` parse error ([`STAGE_F_WALK_PARKED_2026-06-05.md`](STAGE_F_WALK_PARKED_2026-06-05.md), worker logs cited in park doc). At ~4 chars/token that is **~8,000+ output tokens**, consistent with hitting an **8192 output-token ceiling** and truncating mid-string.

Exact `output_tokens` from the failed gap call: **requires a run — not done** (failure did not persist token counts on the job row; trace not written on hard fail).

---

## 4. Failure-mode handling

**Answer:** **No `stop_reason` / `finish_reason` inspection on the production Anthropic path.** Truncation, prose, empty body, and malformed JSON all collapse into the same parse/retry path.

**Production path (`_call_anthropic_messages`):**
- Does **not** read `response.stop_reason`.
- Extracts text → `_parse_json_from_text` → `GapComplianceAgentError("STOP_PARSE_FAILED", ...)` on `JSONDecodeError` (L140–155).
- Empty text blocks → `STOP_NO_RESULT` (L331–336).

**`query_fn` path (tests / optional injection):**
- Reads `stop_reason` only when `is_error` is true (L355–370) — not for `max_tokens` truncation on success-shaped messages.

**Retry behaviour (shipped `332ef68`):**
- Retries once on `STOP_PARSE_FAILED` and `STOP_NO_RESULT` only (L427–460).
- **Does not** distinguish truncation (`stop_reason=max_tokens`) from other parse failures.
- A max-token truncation therefore **feeds the same retry** as an empty-body flake; a second prose response fails loud with both raw snippets (as on 2026-06-05).

**Not retried:** `STOP_API_ERROR`, `STOP_AGENT_ERROR`, `STOP_VALIDATION_FAILED`, `STOP_TIMEOUT`.

---

## 5. Output volume — what the model must emit

**Answer:** The model emits **verbose per-gap records**, not compact key-only references. Downstream does **not** reconstruct question text from keys.

**Per-gap LLM shape** ([`gap_compliance_v1.py`](../../app/reports/schemas/gap_compliance_v1.py) L54–62, L16–24):

| Field | Role |
|-------|------|
| `item_key`, `section_key`, `section_label`, `required_item_type`, `required_item_ref`, `severity` | Identity (from checklist) |
| `question` | **Full funder-aware question string** (`min_length=1`) |
| `rationale` | **Brief explanation string** (`min_length=1`) |

**System prompt drives verbosity** (L71–72, L92–93): questions must use template section label/tone/terminology; rationale required per gap.

**Scaling:** Output size grows with **(number of unsatisfied checklist items) × (question + rationale length)**. Each gap repeats `section_label` and generates bespoke question text. There is no schema path for “key only, hydrate later.”

**Persisted shape:** `envelope_to_gap_analysis_json` stores gaps as-is ([`gap_compliance_v1.py`](../../app/reports/schemas/gap_compliance_v1.py) L70–82) — no downstream compression.

**Deterministic additions:** Logframe-missing rows can be merged from code ([`_merge_deterministic_logframe_gaps`](../../app/reports/agents/gap_compliance_agent.py) L278–305) with pre-written questions; LLM gaps still follow the verbose shape above.

---

## 6. Input assembly — what the model receives

**Answer:** **Single call, entire checklist, full template JSON, and full knowledge bank** (subject to one character cap). **No chunking or batching.**

**Assembly** ([`build_gap_compliance_prompt`](../../app/reports/agents/gap_compliance_agent.py) L190–227):

| Payload block | Contents |
|---------------|----------|
| `checklist` | All non-`section` requirements — compact keys only (L175–187) |
| `template` | **Full** `report_sections_json`, `format_rules_json`, `terminology_map_json`, names (L201–207) |
| `knowledge_bank` | **Full** `facts`, `conflicts`, `unreadable_sources`, `gap_answers`, gate stamp (L212–219) |
| `derived.logframe_missing_actuals` | Deterministic pre-pass rows (L209–211) |

**Bounds:**
- `MAX_INPUT_CHARS = 120_000` — hard **character** truncate of serialised JSON (L45, L221–223). Not token-aware. No checklist batching.

**FCDO checklist size (from committed template, static count):**

Source: [`TEMPLATE_INSTANCE_FCDO.json`](../../docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json)

| Component | Count |
|-----------|--------|
| Sections | 8 |
| `required_indicators` (all sections) | **39** |
| `required_tables` with `min_rows ≥ 1` | **8** |
| **Non-section checklist items in prompt** | **47** |
| Plus derived logframe row requirements | 0–N when logframe enabled and actuals missing ([`logframe_completeness.py`](../../app/reports/gap/logframe_completeness.py)) |

**Approximate input weight:** Full FCDO template JSON is ~386 lines; BridgeLight-scale KB is tens of facts with provenance blobs. Serialised prompt likely **tens of thousands of input tokens** for FCDO. Exact gap-stage `input_tokens`: **requires a run — not done** (failed gap did not persist trace). Reference: E1 on same fixture class reported **~20,818 input tokens** in reconciler `agent_trace` (resume artefact KB block).

**Funder variance:** Checklist cardinality is **data-driven from `report_sections_json`** ([`enumerate_template_requirements`](../../app/reports/gap/template_requirements.py) L44–94). Larger templates → larger prompt and potentially larger gap output if many items unsatisfied.

---

## 7. The funder-less / generic path

**Answer:** **Defined, but empty checklist** — not an error, not a separate canonical checklist.

**Report creation:** `funder_report_template_id` is **NOT NULL** on `donor_reports` ([`donor_report.py`](../../app/reports/models/donor_report.py) L23–26). API may omit template ID; service resolves via [`_resolve_funder_template`](../../app/reports/services/donor_report_lifecycle_service.py) L76–90:

- Explicit ID → load that template (404 if missing/inactive).
- `None` → [`get_or_create_default_funder_template`](../../app/reports/services/donor_report_lifecycle_service.py) L42–73 with `funder_name="__default__"`, `template_name="__lifecycle_default__"`, **`report_sections_json=[]`**, empty format/terminology rules.

**Gap stage:** Always loads template by `report.funder_report_template_id` ([`pipeline.py`](../../app/reports/orchestration/pipeline.py) L184–194). Fails `StageFailure("Funder template not found")` only if DB row missing — not for “generic” reports.

**E3 behaviour with default template:**
- `enumerate_template_requirements([])` → **empty checklist** (no indicators/tables/sections enumerated from empty JSON).
- Logframe pass inactive (`format_rules_json={}`).
- Agent may return `readiness_score: 100`, `gaps: []` if invoked.
- Documented in [`E3_GAP_GATE2_SEAM_AUDIT_2026-05-31.md`](../../E3_GAP_GATE2_SEAM_AUDIT_2026-05-31.md) § “Default lifecycle template is empty.”

**No funder-less canonical checklist** exists beyond this empty default shell.

---

## Verdict

The evidence **partially confirms both root causes** of the 2026-06-05 failure modes and **refutes neither**:

1. **No structural enforcement (prose failure):** Confirmed. E3 uses **prompt-instruction-only** JSON on Anthropic Messages — identical enforcement class to E1, with no prefill, tools, or structured-output API. Attempt 2 prose (`"I'll systematically check each checklist item…"`) is consistent with this design.

2. **Output ceiling too low for volume (truncation failure):** Strongly supported. `MAX_OUTPUT_TOKENS=8192` (half of E1's 16384) while the model must emit **verbose multi-field gap objects** for dozens of unsatisfied FCDO items. Attempt 1's **~33k characters** ending in `Unterminated string` at char 33091 aligns with **max-token truncation**; the code never checks `stop_reason=max_tokens`, so truncation is indistinguishable from other parse errors and triggers the transport retry.

The **funder-less path is defined** (default empty template, always a template FK on the report) but **not useful for compliance checking** until a real funder template is bound at report creation.

**Next session (decision, not this pass):** Whether to add structural enforcement, raise/decompose output, batch by section, or handle `stop_reason=max_tokens` without retry — to be decided from these findings on a **fresh fixture**, not `1c9f7ffa`.

---

## Requires a run — not done

| Question | Why |
|----------|-----|
| Exact gap-stage `input_tokens` / `output_tokens` on FCDO | Failed run did not persist agent trace; not computed offline |
| Whether prompt hit `MAX_INPUT_CHARS` truncate on FCDO walk | Needs serialised prompt length at runtime |
| Logframe-derived checklist count on BridgeLight fixture | Needs KB + template at gap invocation time |
