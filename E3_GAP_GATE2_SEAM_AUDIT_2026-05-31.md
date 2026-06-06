# E3 / Gap → Gate 2 Seam Audit — Ground Truth

**Date:** 2026-05-31  
**Scope:** Read-only observation of committed code for E3 (gap/compliance agent), gap stage boundary, and Gate 2. Synthesis, critic, Gate 3, and export are out of scope except where the gap/Gate 2 boundary stops.  
**Method:** Static inspection of listed modules; no code changes. Live DB queries attempted — see §2.

---

## 1. E3 invocation contract

### Entry points

| Function | Location | Sync/async |
|----------|----------|------------|
| `run_gap_compliance(*, knowledge_bank_json, template_payload, report_context=None, query_fn=None, model=None) -> GapComplianceAgentResult` | `app/reports/agents/gap_compliance_agent.py` | **Async** |
| `run_gap_compliance_and_persist(db, donor_report_id, *, report_context=None, query_fn=None, model=None) -> GapComplianceAgentResult` | `app/reports/services/gap_compliance_service.py` | **Async** |
| `run_gap_compliance_and_persist_sync(db, donor_report_id, *, report_context=None, query_fn=None, model=None) -> GapComplianceAgentResult` | same | **Sync** (wraps async via `asyncio.run`) |

There is **no HTTP route** that invokes E3. `app/reports/router.py` mounts health, lifecycle, gate1, and gate2 only — no gap-compliance route.

### Required inputs and sources

**Agent (`run_gap_compliance`):**

| Input | Source when called via service |
|-------|-------------------------------|
| `knowledge_bank_json` | `donor_reports.knowledge_bank_json` (loaded in service) |
| `template_payload` | Assembled in service from `FunderReportTemplate` row linked by `donor_reports.funder_report_template_id`: `funder_name`, `template_name`, `report_sections_json`, `format_rules_json`, `terminology_map_json` |
| `report_context` | Optional caller arg; defaults to `{"report_type": "annual"}` in agent if omitted |
| `query_fn` | Optional test hook; production path uses Anthropic Messages API when `None` |
| `model` | Optional; defaults to `ME_GAP_COMPLIANCE_MODEL` env or `ME_RECONCILER_MODEL` or `"claude-sonnet-4-6"` |

**Inside the agent (derived from inputs):**

- `enumerate_template_requirements(template_payload["report_sections_json"], report_context=ctx)` → checklist (`TemplateRequirement` list).
- Prompt built by `build_gap_compliance_prompt()` includes: `report_context`, template subset (`funder_name`, `template_name`, `report_sections_json`, `format_rules_json`, `terminology_map_json`), checklist (non-`section` requirements only), and knowledge-bank subset (`schema_version`, `facts`, `conflicts`, `unreadable_sources`, `gap_answers`, `gate1_confirmed_at`).

**Service preconditions (before agent call):**

- Report row must exist (`404 DONOR_REPORT_NOT_FOUND`).
- `require_gate1_confirmed(report.knowledge_bank_json)` — see §3.
- Template row must exist (`404 FUNDER_TEMPLATE_NOT_FOUND`).

### Return type and shape

**`GapComplianceAgentResult`** (dataclass):

- `envelope: GapCompliancePersistedEnvelope`
- `model_used: str`
- `latency_ms`, `input_tokens`, `output_tokens` (optional)

**`GapCompliancePersistedEnvelope`** (`app/reports/schemas/gap_compliance_v1.py`):

- `schema_version`, `gap_agent` (`"gap_compliance_agent"`), `analyzed_at`, `report_context`, `structured`, `agent_trace`, optional `error`

**`GapComplianceOutput`** (inside `envelope.structured`):

- `schema_version` (`"1.0.0"`)
- `readiness_score` (0–100)
- `ready_for_gate2` (bool) — computed in agent: `readiness_score == 100 and not gaps`
- `gaps[]` — each `GapComplianceGapItem`: `item_key`, `section_key`, `section_label`, `required_item_type` (`indicator` \| `table` \| `section`), `required_item_ref`, `severity`, `question`, `rationale`

LLM returns only `readiness_score` and `gaps`; agent validates against `allowed_item_keys` from template checklist.

### Persistence

- **Agent:** return-only (no DB writes).
- **Service:** on success, overwrites `donor_reports.gap_analysis_json` via `envelope_to_gap_analysis_json(result.envelope)` and commits. Idempotent re-run (comment in service).
- **Persisted JSON shape** (`envelope_to_gap_analysis_json`): flattens `structured` fields to top level plus `gap_agent`, `analyzed_at`, `report_context`, optional `agent_trace`, optional `error`. Top-level keys include `readiness_score`, `ready_for_gate2`, `gaps`, `schema_version`.

### Failure surface

**Exception types:**

| Type | When |
|------|------|
| `GapComplianceAgentError` | Codes: `STOP_PARSE_FAILED`, `STOP_VALIDATION_FAILED`, `STOP_API_ERROR`, `STOP_NO_RESULT`, `STOP_AGENT_ERROR` (from agent internals) |
| `asyncio.TimeoutError` | **`asyncio.wait_for(..., timeout=TIMEOUT_SECONDS)` around `_run_gap_query` in `run_gap_compliance` — not caught or re-wrapped** |
| `DomainError` | `GATE1_NOT_CONFIRMED` (409) from `require_gate1_confirmed` in service |
| `NotFoundError` | Missing report or template in service |

**Timeout wrapping (confirmed still true):**

```python
# gap_compliance_agent.py lines 328–332
structured_output, ... = (
    await asyncio.wait_for(
        _run_gap_query(prompt, query_fn=query_fn, model=model),
        timeout=TIMEOUT_SECONDS,
    )
)
```

No `try/except asyncio.TimeoutError` in agent or service. Service catches **`GapComplianceAgentError` only** — not `asyncio.TimeoutError`.

**Degraded path:** E3 does **not** return a degraded envelope on failure. Failures raise (or timeout propagates). No degraded outcome analogous to reconciler/extractor degraded envelopes.

**API path:** Production uses `AsyncAnthropic` Messages API (`_call_anthropic_messages`); client constructed with `timeout=float(TIMEOUT_SECONDS)`. API failures wrap as `GapComplianceAgentError(STOP_API_ERROR, ...)`.

**Orchestrator dispatch:** `app/reports/orchestration/dispatch.py` does **not** list `GapComplianceAgentError`. E3 is **not** invoked through `dispatch_stage` anywhere in committed code.

---

## 2. Template dependency + DB fact-check

### What `template_payload` E3 requires

Built in `gap_compliance_service.py` from `FunderReportTemplate`:

| Field | Used by E3 |
|-------|------------|
| `funder_name` | Included in prompt JSON |
| `template_name` | Included in prompt JSON |
| `report_sections_json` | **Primary driver** — passed to `enumerate_template_requirements()` |
| `format_rules_json` | Included in prompt JSON |
| `terminology_map_json` | Included in prompt JSON |

### What E3 computes gaps against

`enumerate_template_requirements()` (`app/reports/gap/template_requirements.py`) walks `report_sections_json` and emits requirements for:

1. Each visible section (`section_key`, `label`, `required` default true, `conditional_display` evaluated against `report_context.report_type`).
2. Each entry in `section.required_indicators[]` → type `indicator`.
3. Each entry in `section.required_tables[]` where `table_key` present and `min_rows >= 1` → type `table`.

Item keys: `{section_key}:{item_type}:{item_ref}`.

The LLM checklist in the prompt **excludes** `required_item_type == "section"` entries (`_requirements_for_prompt`), but `allowed_item_keys` for validation includes all enumerated requirements (including sections).

E3 compares the checklist against knowledge-bank satisfaction (facts with `source_document_id`, `gap_answers` in KB per system prompt). **Empty or placeholder `report_sections_json` yields an empty checklist** — no indicator/table gaps to evaluate; agent can still return `readiness_score: 100` with empty `gaps`.

Populated FCDO/NLCF template structure (for reference, from committed artefact file, not DB): `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` contains multiple sections with `required_indicators`, `required_tables` (with `min_rows`), labels, tone, etc. Tests load these from disk (`tests/test_gap_compliance_agent.py`); they are **not** inserted by any migration or production seed script in the repo.

### Lifecycle default template (code fact)

`app/reports/services/donor_report_lifecycle_service.py` → `get_or_create_default_funder_template()` creates when missing:

- `funder_name = "__default__"`
- `template_name = "__lifecycle_default__"`
- `report_sections_json = []`
- `format_rules_json = {}`
- `terminology_map_json = {}`

Reports created via lifecycle create route without `funder_report_template_id` use this template.

### Factual DB check

**Status: UNKNOWN — not determinable from code** for live/production database contents.

- Audit environment has no usable `DATABASE_URL` / app settings; no query was executed against Railway or any remote DB.
- Donor report ID `e41b1641-71e6-4ae5-8b0d-d4927b74bdef` does **not** appear anywhere in the committed codebase.
- **From code only:**
  - (a) Template row count in production: **UNKNOWN**.
  - (b) Whether a `__default__` / `__lifecycle_default__` row exists in prod and whether its `report_sections_json` is empty: **UNKNOWN** (code that creates it sets `[]`).
  - (c) Which template the prod donor report `e41b1641-…` links to: **UNKNOWN**.
  - Whether a real FCDO/NLCF row with populated sections exists in prod DB: **UNKNOWN**.

**Repo fact:** No migration or application seed loads `TEMPLATE_INSTANCE_FCDO.json` or `TEMPLATE_INSTANCE_NLCF.json` into `funder_report_templates`. Only runtime creation paths found: lifecycle default template, test seeds (`tests/worker_validation_seed.py`, gap/gate tests).

---

## 3. Gate 1 precondition for E3

### `require_gate1_confirmed`

**Location:** `app/reports/services/gate_preconditions.py`

**Check:** `(knowledge_bank_json or {}).get("gate1_confirmed_at")` must be truthy.

**On failure:** `DomainError(error_code="GATE1_NOT_CONFIRMED", status_code=409, message="Gate 1 human confirmation is required before gap-check")`.

### Where enforced for E3

| Call site | Purpose |
|-----------|---------|
| `run_gap_compliance_and_persist()` | Before loading template and calling agent |
| `submit_gate2_gap_responses()` | Before Gate 2 intake (Gate 2 also requires Gate 1) |

E3 agent itself does **not** call `require_gate1_confirmed`; it only receives `gate1_confirmed_at` inside the prompt payload.

### What confirms Gate 1 (for resumed jobs)

**Route:** `POST /api/reports/donor-reports/{donor_report_id}/knowledge-bank/gate1/confirm` → `confirm_gate1()` in `gate1_confirmation_service.py`.

**Writes:**

- Validates payload via `validate_gate1_confirm_payload`.
- Sets `knowledge_bank_json.gate1_confirmed_at` to ISO timestamp (UTC).
- Overwrites full `knowledge_bank_json` with caller-supplied payload + stamp.
- Calls `re_enqueue_gate1_job()` then commits.

**`re_enqueue_gate1_job`:** Finds `report_jobs` for the donor report where `status == awaiting_human` and `stage == gap`, picks most recent by `started_at desc`, sets `status = queued`. Does **not** change `stage`.

**Orchestrator resume read:** `_park_gap_boundary()` reads `report.knowledge_bank_json.get("gate1_confirmed_at")`; raises `StageFailure` if missing.

---

## 4. Current orchestrator gap-boundary behavior

**Module:** `app/reports/orchestration/pipeline.py`

### After reconcile (initial walk)

`_halt_gate1()` after successful reconcile stage:

- Sets `job.stage = "gap"`
- Sets `job.status = "awaiting_human"`
- Appends reconcile trace to `agent_trace_json.stages.reconcile`
- Does **not** call E3 or write `gap_analysis_json`

### On resumed job with `stage == "gap"`

First check in `run_orchestrated_walk()`:

```python
if stage == ReportJobStage.GAP.value:
    _park_gap_boundary(session, job)
    return
```

**`_park_gap_boundary`:**

- Loads `DonorReport`; requires `gate1_confirmed_at` in `knowledge_bank_json` (else `StageFailure`).
- Appends trace to `agent_trace_json.stages.gap` with `action: "parked_at_gap_boundary"`.
- Sets `status = awaiting_human`, `stage = gap` (unchanged).
- **Does not** invoke `run_gap_compliance_and_persist` or any E3 code.
- **Does not** advance stage to `synthesise`.

**Confirmed:** E3 is **not** run by the orchestrator today. Gate 1 slice parks at gap boundary after human confirm + re-enqueue (`tests/test_orchestrator_gate1.py::test_outcome_f_g_resume_after_gate1_confirm` asserts parked trace).

### Inputs already available at gap boundary (not consumed by E3 in pipeline)

| Data | Location |
|------|----------|
| Confirmed knowledge bank | `donor_reports.knowledge_bank_json` (incl. `gate1_confirmed_at`, `facts`, `gap_answers`) |
| Funder template | `donor_reports.funder_report_template_id` → `FunderReportTemplate` columns |
| Job cursor | `report_jobs.stage == "gap"`, `status` after re-enqueue briefly `queued` then `awaiting_human` after park |
| Prior stage outputs | `uploaded_documents.*`, reconcile output in KB |
| Gap output column | `donor_reports.gap_analysis_json` (default `{}`; unchanged by pipeline today) |

**Uniform dispatch:** `dispatch.py` is used for classify, extract, reconcile only — not gap.

---

## 5. Gate 2 — current state + resume trigger

### Route

**`POST /api/reports/donor-reports/{donor_report_id}/knowledge-bank/gate2/gap-responses`**

Handler: `submit_gap_responses_gate2` → `submit_gate2_gap_responses()` in `gate2_gap_answer_service.py`.

Auth: `get_current_user`; ownership enforced (`report.user_id == user_id`).

### Service behavior (`submit_gate2_gap_responses`)

**Reads:**

- `donor_reports.knowledge_bank_json` — Gate 1 stamp, existing `gap_answers`
- `donor_reports.gap_analysis_json` — via `require_gap_analysis()` → list of gap dicts from E3 output

**Preconditions:**

1. `require_gate1_confirmed(knowledge_bank_json)`
2. `require_gap_analysis(gap_analysis_json)` — non-empty analysis with `gap_agent` or `analyzed_at`, and `gaps` list (may be empty list)

**Validates:**

- Every `item_key` in request must appear in E3 surfaced gaps (`GATE2_UNKNOWN_GAP_KEYS` 422 if not)

**Writes (to `knowledge_bank_json` only):**

- Merges responses into `gap_answers[item_key]` (answered with provenance, or skipped with reason)
- **Clears** `gate2_confirmed_at` on any partial submit (`kb.pop("gate2_confirmed_at", None)`)
- Sets `gate2_confirmed_at` ISO timestamp **only when** every E3 gap has a resolved answer/skip (`_remaining_gaps` empty)
- Does **not** write `gap_analysis_json` or `report_jobs`

**Returns:** `gate2_confirmed_at`, `gate2_unlocked`, `gap_answers`, `remaining_gaps`.

### `require_gate2_confirmed`

Checks `knowledge_bank_json.gate2_confirmed_at` truthy → else `GATE2_NOT_CONFIRMED` (409).

**Committed usage:** `tests/test_gate2_gap_answers.py` only. **No** production service, orchestrator, or synthesis path calls it in `app/` (grep).

### Gate 2 resume / re-enqueue trigger

**Finding:** **No committed code path** reads `gate2_confirmed_at` to re-enqueue a job, change `report_jobs.status` from `awaiting_human` to `queued`, or advance `report_jobs.stage` toward `synthesise`.

**Contrast with Gate 1:** `confirm_gate1()` includes `re_enqueue_gate1_job()`. Gate 2 service has **no** analogous `re_enqueue_gate2_job` or worker trigger.

**Gap vs Gate 1 resume (mirror question):** Gate 1 resume exists (re-enqueue → worker → park at gap). Gate 2 resume trigger **does not exist** in committed code.

---

## 6. Schema capacity — gap / Gate 2 / synthesise boundary

### Enums (`app/reports/models/enums.py`)

| Enum | Values relevant to this audit |
|------|-------------------------------|
| `ReportJobStage` | Includes `gap`, **`synthesise`**, `critique`, `export` |
| `ReportJobStatus` | Includes **`awaiting_human`**, `queued`, `running`, `failed`, `done` |

DB check constraints in migration `0014_me_module_tables.py` match these literals.

### Columns and JSON keys

| Concern | Storage | Notes |
|---------|---------|-------|
| E3 gap output | `donor_reports.gap_analysis_json` (JSONB, default `{}`) | Written only by `run_gap_compliance_and_persist` when invoked |
| Gate 1 confirmation | `knowledge_bank_json.gate1_confirmed_at` | ISO string |
| Gate 2 confirmation | `knowledge_bank_json.gate2_confirmed_at` | ISO string; cleared on partial Gate 2 submit |
| Human gap answers | `knowledge_bank_json.gap_answers` | Map keyed by E3 `item_key` |
| Gate 3 (downstream) | `knowledge_bank_json.gate3_confirmed_at` | Defined in schema keys; not used in gap/Gate 2 code |
| Job lifecycle | `report_jobs.stage`, `report_jobs.status`, `report_jobs.agent_trace_json`, `report_jobs.error`, timestamps | Single source of truth for worker |
| Synthesis output (downstream) | `donor_reports.content_json` | Column exists; not written in gap/Gate 2 paths |

### Migrations 0014 and 0015

**`0014_me_module_tables`:** Creates `funder_report_templates`, `donor_reports` (including `knowledge_bank_json`, **`gap_analysis_json`**, `indicator_actuals_json`, `content_json`), `uploaded_documents`, `report_jobs` with stage/status check constraints.

**`0015_donor_reports_gap_analysis_json`:** Adds `gap_analysis_json` to `donor_reports` **if column missing**. On fresh install from 0014, column already exists — migration is idempotent guard only.

### Can schema represent "halted at Gate 2, resumable" like Gate 1?

**Partially — at rest, not wired.**

| Gate 1 pattern (implemented) | Gate 2 equivalent (schema only) |
|------------------------------|----------------------------------|
| `status=awaiting_human`, `stage=gap` | Could use `status=awaiting_human`, `stage=synthesise` (or remain `gap` — **no committed convention** for Gate 2 halt stage cursor) |
| `gate1_confirmed_at` in KB | `gate2_confirmed_at` in KB |
| `re_enqueue_gate1_job()` | **No function exists** |
| Orchestrator park/resume handler | **No Gate 2 / synthesise handler** in `pipeline.py` |

**Representational observations (not proposals):**

- JSONB fields can hold Gate 2 state and gap answers today.
- `report_jobs` enums include `synthesise` and `awaiting_human`.
- **No** committed convention for which `stage` value means "halted at Gate 2 awaiting human" (Gate 1 halt uses `stage=gap` even though E3 has not run).
- **No** worker re-enqueue on Gate 2 confirm — unlike Gate 1.

---

## 7. Gaps the gap/Gate 2 build must resolve (factual observations only)

1. **E3 not in orchestrator** — `pipeline.py` never calls `run_gap_compliance_and_persist` or `run_gap_compliance`. Gap stage on resume calls `_park_gap_boundary` only.

2. **No HTTP entry for E3** — Gap analysis runs only if something calls the service directly; lifecycle routes do not trigger E3.

3. **Gate 1 re-enqueue does not reach E3** — After `confirm_gate1`, worker re-queues job but orchestrator parks again at gap without running E3 (`test_outcome_f_g_resume_after_gate1_confirm`).

4. **No Gate 2 re-enqueue** — `submit_gate2_gap_responses` updates KB only; no `report_jobs` transition to `queued` and no worker continuation.

5. **E3 timeout leaks `asyncio.TimeoutError`** — Not wrapped as `GapComplianceAgentError`; service does not catch it; `dispatch_stage` is not used for E3 anyway.

6. **E3 not in dispatch wrapper** — `GapComplianceAgentError` absent from `dispatch.py` `_STOP_ERRORS`; orchestrator has no gap stage dispatch path.

7. **Default lifecycle template is empty** — `report_sections_json=[]` for `__default__` / `__lifecycle_default__`; E3 checklist would be empty for reports created without a real funder template ID.

8. **FCDO/NLCF templates in repo are file artefacts** — Populated templates exist under `docs/artefacts/me_module/` for tests; no committed DB seed loads them into `funder_report_templates`.

9. **Prod DB template/report linkage unknown** — Cannot verify template row count, default template contents, or template for donor report `e41b1641-71e6-4ae5-8b0d-d4927b74bdef` from this audit environment.

10. **`require_gate2_confirmed` unused outside tests** — Gate 2 stamp is written by gap-answer service but nothing in `app/` consumes it for pipeline advance yet.

11. **Stage cursor semantics ambiguous for Gate 2 halt** — Gate 1 halt sets `stage=gap` before E3 runs; no committed code defines post-E3 or post-Gate-2 stage cursor for synthesise boundary.

12. **Gate 2 requires E3 output first** — `require_gap_analysis` blocks Gate 2 route until `gap_analysis_json` populated by E3 service; with pipeline not running E3, Gate 2 HTTP path is unreachable unless E3 invoked separately.

13. **Migration 0015 redundant on 0014-created DBs** — `gap_analysis_json` already in 0014; 0015 only adds if missing.

---

*End of audit. No code modified except this report.*
