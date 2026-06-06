# Orchestrator Seam Ground-Truth Audit

**Date:** 2026-05-30  
**Scope:** Read-only inspection of committed code under `app/reports/agents/` (D1, D2, D3, D4, E1, E3, `claude_sdk_env.py`), `app/reports/worker/`, `app/reports/models/`, gate1/gate2 routes and services, M&E persistence services, migrations `0014` and `0015`.  
**Method:** Code observation only; no behavior changes.

---

## 1. Per-Agent Invocation Contract

| Agent | Entry point (primary) | Sync / async | Required inputs & typical source | Return type & shape | Persistence side-effects |
|-------|----------------------|--------------|----------------------------------|---------------------|--------------------------|
| **D1 — document classifier** | `async def classify_document_text(text: str, *, filename: str \| None = None, mime_type: str \| None = None, model: str \| None = None, query_fn: QueryFn \| None = None) -> ClassifierResult` | **Async** (sync wrapper: `classify_document_text_sync(...)`) | `text` — caller-supplied Docling text or excerpt; optional `filename` / `mime_type` from `uploaded_documents`; optional `model`, `query_fn` (tests). Alternate path: `classify_document_from_path(path, *, mime_type, model, query_fn)` reads file via Docling adapter first. | `ClassifierResult` (Pydantic): `intake_outcome` (`complete` \| `unreadable`), optional `classification` (`proposal` \| `grant_letter` \| `mou` \| `indicator_data` \| `other`), `confidence`, `justification`, `unreadable_code`, agent metadata (`agent_name`, `model_class`, `model_used`, tokens, `latency_ms`, `timestamp`, `truncated`). | **Return-only.** No `app/reports/services/*` wrapper persists classification. Target column documented in agent docstring: `uploaded_documents.classification`. No committed production caller writes that column after classify (only tests and `scripts/live_classifier_run.py`). |
| **D2 — proposal extractor** | `async def extract_proposal_text(text: str, *, filename: str \| None = None, model: str \| None = None, query_fn: QueryFn \| None = None) -> ProposalExtractorResult` | **Async** (sync: `extract_proposal_text_sync`; path helper: `extract_proposal_from_path`) | `text` — caller-supplied Docling text; `filename` from document record when called via service. Service precondition: `uploaded_documents.classification == "proposal"`. | `ProposalExtractorResult`: `envelope` (`ProposalExtractedEnvelope` with `structured` `ProposalExtractionOutput`, `agent_trace`, timestamps), plus `model_used`, token counts, `timestamp`, `truncated`, `content_hash`. | **Service persists:** `extract_and_persist_proposal(db, document_id, text, *, query_fn)` → `uploaded_documents.extracted_json`, `uploaded_documents.extraction_status` (`PROCESSING` → `COMPLETE` \| `FAILED`). Agent itself is return-only. |
| **D3 — grant-terms extractor** | `async def extract_grant_terms_text(text: str, *, filename: str \| None = None, model: str \| None = None, query_fn: QueryFn \| None = None, per_attempt_timeout_seconds: float \| None = None) -> GrantTermsExtractorResult` | **Async** (sync: `extract_grant_terms_text_sync`; path: `extract_grant_terms_from_path`) | Same pattern as D2; service requires `classification in ("grant_letter", "mou")`. | `GrantTermsExtractorResult`: `envelope` (`GrantTermsExtractedEnvelope` / `GrantTermsExtractionOutput`), metadata fields, optional `content_hash`. On timeout exhaustion returns degraded envelope (does not raise). | **Service persists:** `extract_and_persist_grant_terms(db, document_id, text, *, query_fn)` → `uploaded_documents.extracted_json`, `extraction_status`. |
| **D4 — indicator-data extractor** | `async def extract_indicator_data_text(text: str, *, filename: str \| None = None, model: str \| None = None, query_fn: QueryFn \| None = None, per_attempt_timeout_seconds: float \| None = None) -> IndicatorDataExtractorResult` | **Async** (path: `extract_indicator_data_from_path` parses spreadsheet first) | `text` — spreadsheet JSON string from caller; service requires `classification == "indicator_data"`. Path variant reads file via spreadsheet parser. | `IndicatorDataExtractorResult`: `envelope` (`IndicatorDataExtractedEnvelope`), metadata, `content_hash`, `truncated`. Degraded result on timeout exhaustion (does not raise). | **Service persists:** `extract_and_persist_indicator_data(db, document_id, spreadsheet_json, *, content_hash, query_fn, per_attempt_timeout_seconds)` → `uploaded_documents.extracted_json`, `extraction_status`. |
| **E1 — knowledge-bank reconciler** | `async def reconcile_bundle(bundle: ReconciliationInputBundle, *, query_fn: QueryFn \| None = None, model: str \| None = None, per_attempt_timeout_seconds: float \| None = None) -> KnowledgeBankReconcilerResult` | **Async** | `bundle` built from DB via `reconcile_documents(documents: list[Any], *, query_fn, model)` which calls `build_reconciliation_bundle(documents)` on `UploadedDocument` rows (`classification`, `extracted_json`, ids). Fixture path: `reconcile_from_fixture(manifest_path, ...)`. | `KnowledgeBankReconcilerResult`: `envelope` (`KnowledgeBankReconciledEnvelope` with `structured` `KnowledgeBankReconciliationOutput`: `facts`, `conflicts`, `unreadable_sources`, `reconciliation_outcome`, etc.), token/latency metadata. Degraded envelope on timeout/error exhaustion. | **Service persists:** `reconcile_and_persist(db, donor_report_id, *, query_fn)` → `donor_reports.knowledge_bank_json` via `envelope_to_knowledge_bank_json`. Explicitly **does not** set `gate1_confirmed_at`. On `KnowledgeBankReconcilerError`, writes minimal error dict to `knowledge_bank_json` then re-raises. |
| **E3 — gap/compliance agent** | `async def run_gap_compliance(*, knowledge_bank_json: dict[str, Any], template_payload: dict[str, Any], report_context: dict[str, Any] \| None = None, query_fn: QueryFn \| None = None, model: str \| None = None) -> GapComplianceAgentResult` | **Async** | `knowledge_bank_json` from `donor_reports` (must pass `require_gate1_confirmed` in service); `template_payload` assembled from `FunderReportTemplate` (`report_sections_json`, etc.); optional `report_context` (defaults `{"report_type": "annual"}`). | `GapComplianceAgentResult` (dataclass): `envelope` (`GapCompliancePersistedEnvelope` with `structured` `GapComplianceOutput`: `readiness_score`, `ready_for_gate2`, `gaps[]`), `model_used`, token/latency fields. | **Service persists:** `run_gap_compliance_and_persist(db, donor_report_id, *, report_context, query_fn, model)` → `donor_reports.gap_analysis_json` via `envelope_to_gap_analysis_json`. Agent is return-only. |

**Supporting module — `claude_sdk_env.py`**

| Symbol | Signature | Role |
|--------|-----------|------|
| `merge_claude_subprocess_env(extra: dict[str, str] \| None = None) -> dict[str, str]` | Sync | Builds `ClaudeAgentOptions.env`; injects `ANTHROPIC_API_KEY` from process env when present. Used by D2/D3/D4 `build_agent_options`. |
| `anthropic_api_key_configured() -> bool` | Sync | Returns whether `ANTHROPIC_API_KEY` is non-empty in process env. |

**Object storage (not an agent):** `DocumentStorageService` — S3-compatible upload/download for raw uploads (`storage_ref` on `uploaded_documents`). Not invoked by agents directly in audited paths.

---

## 2. Calling-Convention Comparison

### Messages-API agents (D1, E1, E3) vs SDK-subprocess agents (D2, D3, D4)

| Dimension | D1 classifier | E1 reconciler | E3 gap/compliance | D2 proposal | D3 grant-terms | D4 indicator-data |
|-----------|---------------|---------------|-------------------|-------------|----------------|-------------------|
| **Production runtime** | `anthropic.AsyncAnthropic.messages.create` when `query_fn is None` | Same (`_call_anthropic_messages`) | Same | `claude_agent_sdk.query` (default import) | Same | Same |
| **Test / inject hook** | Optional `query_fn` async iterator (SDK-style message objects) | Optional `query_fn` | Optional `query_fn` | Optional `query_fn` (required internally by `_run_extractor_query`) | Optional `query_fn` | Optional `query_fn` |
| **Call-site async pattern** | `await classify_document_text(...)` or `asyncio.run(...)` via sync wrapper | `await reconcile_bundle(...)` / `reconcile_documents(...)` | `await run_gap_compliance(...)` | `await extract_proposal_text(...)` | `await extract_grant_terms_text(...)` | `await extract_indicator_data_text(...)` |
| **Subprocess spawn** | None in-repo (HTTP client only) | None in-repo | None in-repo | Delegated to `claude_agent_sdk.query`; module docstring in `claude_sdk_env.py` states SDK **shells out to `claude` CLI** | Same | Same |
| **Completion detection** | Parse JSON from message text; validate via `_ClassifierOutput` | Parse JSON from message text; validate reconciler schema | Parse JSON from message text; validate gap schema | `async for message in query_fn(...)`: completion on `isinstance(message, ResultMessage)` with `subtype == "success"` and `structured_output` | Same pattern | Same pattern |
| **Termination / stdout close** | N/A (HTTP response) | N/A | N/A | **UNKNOWN — not determinable from code** (handled inside `claude_agent_sdk` package, not vendored in repo) | Same | Same |
| **Timeout — outer** | `asyncio.wait_for(..., timeout=TIMEOUT_SECONDS)`; default **60s** (`ME_CLASSIFIER_TIMEOUT_SECONDS`) | Per-attempt `asyncio.wait_for`; default **180s** (`ME_RECONCILER_TIMEOUT_SECONDS`); up to **2** attempts | `asyncio.wait_for`; default **180s** (`ME_GAP_COMPLIANCE_TIMEOUT_SECONDS`) | `asyncio.wait_for`; default **90s** (`ME_CLASSIFIER_TIMEOUT_SECONDS`) | Per-attempt `asyncio.wait_for`; default **90s**; **2** attempts | Per-attempt `asyncio.wait_for`; default **90s**; **2** attempts |
| **Timeout — inner (SDK)** | N/A | N/A | N/A | `API_TIMEOUT_MS = TIMEOUT_SECONDS * 1000` in `ClaudeAgentOptions.env` via `merge_claude_subprocess_env` | Same | Same |
| **On timeout expiry** | Raises `ClassifierError(code="STOP_TIMEOUT", ...)` | After max attempts: returns **degraded** `KnowledgeBankReconcilerResult` (no raise). Intermediate attempts log warning. | **`asyncio.TimeoutError` propagates uncaught** from `run_gap_compliance` (not wrapped as `GapComplianceAgentError`) | Raises `ProposalExtractorError(code="STOP_TIMEOUT", ...)` | After max attempts: returns **degraded** result (no raise) | After max attempts: returns **degraded** result (no raise) |
| **Primary exception types** | `ClassifierError` (`STOP_EMPTY_INPUT`, `STOP_TIMEOUT`, `STOP_API_ERROR`, `STOP_NO_RESULT`, `STOP_PARSE_FAILED`, `STOP_STRUCTURED_OUTPUT_FAILED`, `STOP_AGENT_ERROR`) | `KnowledgeBankReconcilerError` (same STOP-* family); degraded path returns result instead of raising | `GapComplianceAgentError` (`STOP_API_ERROR`, `STOP_NO_RESULT`, `STOP_AGENT_ERROR`, `STOP_VALIDATION_FAILED`, `STOP_PARSE_FAILED`); plus uncaught `asyncio.TimeoutError` | `ProposalExtractorError` (STOP-* including `STOP_TIMEOUT`) | `GrantTermsExtractorError` on hard failures; timeout → degraded return | `IndicatorDataExtractorError` on hard failures; timeout → degraded return |
| **Hang manifestation** | Blocks until `wait_for` fires → `ClassifierError STOP_TIMEOUT` | Blocks per attempt; eventually degraded result | Blocks until `wait_for` → `asyncio.TimeoutError` to caller | Blocks until `wait_for` → `ProposalExtractorError STOP_TIMEOUT` | Blocks per attempt; eventually degraded return | Same as D3 |
| **Crash / malformed empty return** | `ClassifierError STOP_NO_RESULT` or `STOP_PARSE_FAILED` | `KnowledgeBankReconcilerError` or degraded envelope | `GapComplianceAgentError STOP_NO_RESULT` / `STOP_VALIDATION_FAILED` | `ProposalExtractorError STOP_NO_RESULT` / validation errors | `GrantTermsExtractorError STOP_NO_RESULT` or degraded on timeout | Same as D3 |
| **Platform notes in code** | None | None | None | `claude_sdk_env.py`: headless Railway workers must pass `ANTHROPIC_API_KEY` in `options.env` so CLI does not require interactive `/login` | Same | Same |

---

## 3. Worker + `run_pipeline` Behavior

### `run_pipeline` (current stub)

**Location:** `app/reports/worker/run_pipeline.py`

**Behavior observed:**

1. Opens session (`db` param or new `SessionLocal()`).
2. Loads **one** `ReportJob` for `donor_report_id`: `.order_by(ReportJob.started_at.desc().nullslast()).first()` — **not** the specific job row selected by `poll_once`.
3. If no job: logs warning and returns.
4. Sets `job.status = running`, `job.started_at = job.started_at or now`, commits.
5. Immediately sets `job.status = done`, `job.finished_at = now`, commits.
6. **Does not:** invoke any agent, update `job.stage`, write `agent_trace_json`, touch `donor_reports`, or set `awaiting_human`.
7. **On exception:** `session.rollback()`. Sets `job.status = failed`, `job.error = "run_pipeline stub failed"`, `job.finished_at` **only when `db is None`** (`owns_session=True`). When called from `job_runner` with `db=session`, **does not** set failed status; re-raises.

### `job_runner` loop

**Location:** `app/reports/worker/job_runner.py`

| Step | Observed behavior |
|------|-------------------|
| **Claim** | `poll_once()` selects first `ReportJob` where `status == 'queued'`, ordered by `started_at ASC NULLS FIRST`. **No** `SELECT FOR UPDATE`, **no** status transition at claim time, **no** row locking. |
| **Invoke** | Synchronous call: `run_pipeline(job.donor_report_id, db=session)`. |
| **Success** | `run_pipeline` commits `done` inside shared session; `poll_once` closes session in `finally`. Returns `processed = 1`. |
| **Failure** | Exception propagates from `run_pipeline` to `run_forever`, which logs `"Worker poll cycle failed"` and sleeps 5s. Job may remain `queued` (if failure before running commit), `running` (if failure after running commit), or `done` (if stub completed). **`failed` is not set** when `run_pipeline` is called with external session. |
| **Hang** | **No timeout** on `run_pipeline` or `poll_once`. Worker thread/process blocks until the hung call returns. |
| **Idle** | When no queued job, sleeps `POLL_INTERVAL_SECONDS` (5). |
| **`run_forever`** | Infinite loop; catches all exceptions per cycle, does not exit process on agent/pipeline failure. |

### Job creation

**No committed code path** under `app/` or `scripts/` instantiates or inserts a `ReportJob` row. Only the SQLAlchemy model and a unit test with `_FakeJob` mock exist. **UNKNOWN — not determinable from code** how production jobs are enqueued (may be unimplemented).

---

## 4. Job/Report Schema and Halt/Resume Capacity

### `report_jobs.status` (migration `0014` CHECK + `ReportJobStatus` enum)

`queued` | `running` | `awaiting_human` | `failed` | `done`

### `report_jobs.stage` (`ReportJobStage` enum)

`classify` | `extract` | `reconcile` | `gap` | `synthesise` | `critique` | `export`

### Relevant columns

| Table | Column | Backing purpose |
|-------|--------|-----------------|
| `report_jobs` | `stage` | Single text stage pointer (default `'classify'`). **No separate `last_completed_stage` column.** |
| `report_jobs` | `status` | Job lifecycle (`queued` … `done`). |
| `report_jobs` | `agent_trace_json` | JSONB default `'{}'` — intended per-agent trace aggregate. |
| `report_jobs` | `error` | Failure message text. |
| `report_jobs` | `started_at`, `finished_at` | Timing. |
| `donor_reports` | `knowledge_bank_json` | E1 output; gate stamps: `gate1_confirmed_at`, `gate2_confirmed_at`, `gate3_confirmed_at` (ISO strings in persisted JSON); `gap_answers`. |
| `donor_reports` | `gap_analysis_json` | E3 output (`gap_agent`, `analyzed_at`, `gaps`, etc.). |
| `donor_reports` | `indicator_actuals_json` | Reserved for later stages (not written by audited agents). |
| `donor_reports` | `content_json` | Reserved for synthesis output (not written by audited agents). |
| `donor_reports` | `status` | Donor report lifecycle (`DRAFT`, `EXTRACTING`, `AWAITING_REVIEW`, `GENERATING`, `DEGRADED`, `COMPLETE`) — separate from `report_jobs.status`. |
| `uploaded_documents` | `classification` | D1 target field. |
| `uploaded_documents` | `extracted_json` | D2/D3/D4 per-document extraction envelopes. |
| `uploaded_documents` | `extraction_status` | `PENDING` \| `PROCESSING` \| `COMPLETE` \| `FAILED`. |

**Migration note:** `0014` creates `donor_reports.gap_analysis_json`; `0015` adds the same column idempotently if missing on older deployments.

### Halt/resume representational assessment

| Requirement | Can existing schema represent it? | Evidence |
|-------------|-----------------------------------|----------|
| **(a) Status distinct from `failed` and `done` meaning “awaiting gate confirmation”** | **Column value exists; no committed writer.** | `awaiting_human` is in DB CHECK and `ReportJobStatus` enum. Grep of `app/` shows **zero assignments** to `awaiting_human`. Stub sets only `running` → `done`. |
| **(b) Durable record of which stage last completed** | **Partial / ambiguous.** | Only `report_jobs.stage` exists. No `last_completed_stage`. Committed code does not update `stage` during stub run. Intended semantics of `stage` (cursor vs. last-completed) **UNKNOWN — not determinable from code** (no orchestrator). |
| **(c) Durable per-stage outputs to resume from** | **Yes, at rest — not wired by pipeline.** | `uploaded_documents.classification` + `extracted_json` (classify/extract); `donor_reports.knowledge_bank_json` (reconcile); `donor_reports.gap_analysis_json` (gap). Services write these when invoked directly. `run_pipeline` does not invoke agents or populate them. |
| **`agent_trace_json` population** | **Column exists; unused.** | Only defined on model; no writes in `app/reports/`. |
| **Gate confirmation state** | **Yes.** | `knowledge_bank_json.gate1_confirmed_at`, `gate2_confirmed_at`, `gate3_confirmed_at` (schema keys in `STRUCTURED_KNOWLEDGE_BANK_KEYS`). |

**Representational gaps (factual):**

1. `awaiting_human` is never set by committed runtime code.
2. No dedicated last-completed-stage column; single `stage` field only.
3. `agent_trace_json` is never populated by committed runtime code.
4. No committed `ReportJob` insert/enqueue path in `app/`.
5. `run_pipeline` stub does not read or advance stage; halt/resume semantics are unimplemented at the worker seam.

---

## 5. Gate-1 Resume-Trigger Finding

### What `gate1/confirm` does today

**Route:** `POST /api/reports/donor-reports/{donor_report_id}/knowledge-bank/gate1/confirm`  
**Handler:** `confirm_knowledge_bank_gate1` → `confirm_gate1(db, donor_report_id, user_id, knowledge_bank_json=body.knowledge_bank_json)`

**Service behavior (`gate1_confirmation_service.confirm_gate1`):**

1. Loads `DonorReport`; enforces ownership.
2. Strips incoming `gate1_confirmed_at` from payload.
3. Validates via `validate_gate1_confirm_payload`.
4. Sets `gate1_confirmed_at` to current UTC ISO timestamp.
5. Overwrites `donor_reports.knowledge_bank_json` with confirmed payload.
6. Commits and returns persisted JSON.

**Does not:** touch `report_jobs`, change job `status`/`stage`, enqueue work, or call `run_pipeline`.

### Does any code read `gate1_confirmed_at` to resume or advance the pipeline?

| Consumer | Behavior |
|----------|----------|
| `gate_preconditions.require_gate1_confirmed` | **Precondition gate only** — raises `DomainError(GATE1_NOT_CONFIRMED)` if missing. Used by `run_gap_compliance_and_persist` and Gate 2 services. |
| `gap_compliance_agent.build_gap_compliance_prompt` | Includes `gate1_confirmed_at` in prompt context (read-only for E3). |
| Gate 2 route/service | Reads `gate2_confirmed_at`; same pattern — precondition for downstream stages, not worker resume. |

**Finding:** **No committed code path** reads `gate1_confirmed_at` to re-enqueue a job, transition `report_jobs.status` from `awaiting_human` to `queued`/`running`, or invoke `run_pipeline` / any agent after human confirmation. Gate 1 confirmation **unlocks E3 when E3 is invoked explicitly** (e.g. via `run_gap_compliance_and_persist`); it does **not** trigger automatic pipeline continuation.

---

## 6. Gaps the Orchestrator Build Must Resolve

Factual observations only (no proposed designs):

1. **`run_pipeline` is a no-op stub** — sets `running` then `done`; no agent dispatch, no stage progression, no gate halts.
2. **No orchestrator module** wires D1→D2/D3/D4→E1→(Gate 1 halt)→E3→(Gate 2 halt) in sequence.
3. **`ReportJob` enqueue/creation** — no insert path in committed `app/` or `scripts/` code.
4. **Worker claim race** — no atomic claim (`SELECT FOR UPDATE` / status flip at pickup); concurrent workers could process the same `queued` row.
5. **`poll_once` / `run_pipeline` job mismatch** — poll selects one job row; `run_pipeline` re-queries by `donor_report_id` and may update a different row if multiple jobs exist per report.
6. **`awaiting_human` never assigned** — enum and DB constraint exist; no runtime writer.
7. **`report_jobs.stage` never updated** by worker stub; no last-completed-stage tracking.
8. **`agent_trace_json` never written** by committed runtime code.
9. **Failure handling gap when `run_pipeline(db=session)`** — exceptions after `running` commit leave job stuck in `running`; exceptions before commit leave job in `queued`; `failed` status only when `owns_session=True`.
10. **No worker-level timeout** — hung agent call blocks worker indefinitely.
11. **D1 classification persistence** — no `extract_and_persist` / classify service; no production caller writes `uploaded_documents.classification`.
12. **Gate 1 confirm does not resume pipeline** — timestamp is write-only from HTTP; no worker re-trigger.
13. **E3 timeout inconsistency** — `asyncio.TimeoutError` escapes `run_gap_compliance` uncaught (unlike D1’s wrapped `ClassifierError`).
14. **Mixed degraded vs raise conventions** — D3/D4/E1 return degraded envelopes on timeout exhaustion; D2 raises; E3 raises on API errors but not on outer timeout.
15. **SDK subprocess lifecycle** — spawn/exit detection lives outside repo in `claude_agent_sdk`; in-repo code only iterates `query()` messages until `ResultMessage`.
16. **`donor_reports.status` vs `report_jobs.status`** — two parallel status enums; stub pipeline does not coordinate them.
17. **Per-document extraction services require pre-set `classification`** — orchestrator must classify (D1) and persist labels before D2/D3/D4 services will run; that chain is not implemented in worker.

---

*End of audit. Observation only — no code changes.*
