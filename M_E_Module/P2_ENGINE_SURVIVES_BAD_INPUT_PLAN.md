# P2 — Engine survives bad input (per-document isolation + graceful degradation)

**Status:** Plan updated 2026-06-08 — **classification review pending owner approval.** No code, no DB, no pipeline changes until classification approved.

**Package tier:** Amber (P2) — coupled with P3/P4 sequentially; P3 is committed (`f6c3cf9`); **P2 build blocked on classification approval below.**

**Authority:** [CURSOR_BUILD_INSTRUCTIONS.md](./CURSOR_BUILD_INSTRUCTIONS.md) · locked **D1** (upload lanes) · locked **D6** (charge at first `COMPLETE` — implemented in **P8**, not P2).

**Framing:** P2 **completes and verifies** existing degradation machinery. It does **not** invent a new degradation model. NLCF-class evidence already shows the happy path for typed `degraded` envelopes; P2 closes the remaining **raise-and-kill** seams.

---

## Repo roots (verified 2026-06-08)

| Role | Path | Verified |
|------|------|----------|
| **Backend (build target)** | `C:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot\` | Git toplevel; `app/` present; **no** root `package.json` |
| **Frontend (reference only)** | `C:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot\ngoinfo-grantpilot-frontend\` | `package.json` name `"frontend"` |
| **Do NOT use** | `…\NGOInfo-Grantpilot\frontend\` | Phantom stub — no `package.json` |

---

## Problem statement

When one uploaded document is bad (wrong format for its lane, unreadable intake, agent STOP, storage/Docling failure), the pipeline must:

1. **Not kill the job** — continue on documents that could be read.
2. **Record the failure** as a known gap (existing `degraded_*` machinery).
3. **Surface the gap** at human review and/or as honest blank/flagged prose — **never fabricate** the missing values.
4. **Preserve** extractions and KB work from successful documents.

**Observed production-class behaviour (already working):** NLCF retry with `.docx` classified as `indicator_data` → `load_spreadsheet_json` raises `ValueError` → `persist_degraded_indicator_unparseable` → `extraction_outcome: degraded` / `DEGRADED_EXTRACTION_UNPARSEABLE` → job reaches Gate 2. Orchestrator test `test_outcome_uniform_degraded_indicator_unparseable_mixed_stage_reaches_gate1` locks this path.

**Remaining risk:** Any per-document path that **raises** into `StageFailure` still fails the **whole job**, discarding downstream progress and leaving the owner with `failed` + refund instead of a degradable run.

---

## Diagnosis (read-only) — five questions

### 1. Extract loop: catch vs propagate

**Primary file:** [`app/reports/orchestration/pipeline.py`](../app/reports/orchestration/pipeline.py) `_run_extract_stage` (L473–576).

#### Paths that **already isolate** (continue + `extract.degraded_documents`)

| Trigger | Mechanism | Evidence |
|---------|-----------|----------|
| Extractor returns `extraction_outcome: degraded` (timeout — D-035) | `dispatch_stage` → `is_degraded_result` → append doc id to `degraded_documents` | `test_outcome_uniform_degraded_proposal_extract_continues_to_gate1`, `test_outcome_uniform_degraded_extract_continues` |
| Indicator lane: spreadsheet intake fails (e.g. `.docx` as `indicator_data`) | `load_spreadsheet_json` → `ValueError` → `persist_degraded_indicator_unparseable` → degraded envelope | `test_outcome_uniform_degraded_indicator_unparseable_mixed_stage_reaches_gate1` |
| Extractor returns `extraction_outcome: unreadable` (D-039 low-content) | Service persists FAILED + unreadable envelope; if returned through dispatch without raise, same degraded list path | D-039; proposal/grant services accept unreadable like degraded |

#### Paths that **still kill the whole job**

| Trigger | Propagation chain | Gap |
|---------|-------------------|-----|
| `ProposalExtractionServiceError` / `GrantTermsExtractionServiceError` / `IndicatorDataExtractionServiceError` | Service catches `*ExtractorError`, persists error row, **re-raises** → pipeline `except …ServiceError: raise StageFailure` | Agent STOP errors (e.g. `STOP_PARSE_FAILED`, `STOP_EMPTY_INPUT` on non-empty doc) fail job instead of degrading |
| `load_document_text` failure (R2 fetch, Docling raise, disk) | **Uncaught** before extract try block (proposal/grant branches L494–515) | Storage/intake exception → `dispatch_stage` generic handler or outer `run_pipeline` → `mark_job_failed` |
| `dispatch_stage` catch-all `Exception` | Wrapped as `StageFailure` for the **stage**, not per document | Any unexpected error mid-loop aborts remaining documents |
| Classify stage: `ClassifierError` / timeout | Stage-level failure (expected for empty corpus) | Out of P2 extract scope; classify is all-or-nothing today |

**Dispatch layer:** [`app/reports/orchestration/dispatch.py`](../app/reports/orchestration/dispatch.py) — `_STOP_ERRORS` and generic `Exception` always become `StageFailure`; only **returned** degraded envelopes continue.

**Conclusion:** Degradation works when agents/services **return** typed degraded/unreadable envelopes. It does **not** work when services **raise** after partial persist, or when intake throws before the service layer. P2 build = extend the **existing** unparseable-indicator pattern to other per-document failure modes — not a new status enum or trace shape.

---

### 2. Existing degraded machinery and downstream visibility

#### What is recorded today

| Location | Field | Written when | Populated today? |
|----------|-------|--------------|------------------|
| `report_jobs.agent_trace_json.stages.classify` | `degraded_notes` | Classify degrade | **No** — list initialized but never appended (L432–468) |
| `report_jobs.agent_trace_json.stages.extract` | `degraded_documents` | Per-doc degraded/unreadable extract | **Yes** — UUID strings |
| `report_jobs.agent_trace_json.stages.reconcile` | `degraded` | Reconciler timeout/degrade (D-035) | **Yes** |
| `report_jobs.agent_trace_json.stages.gap` / `synthesise` | `degraded` | Stage-level degrade flags | **Yes** |
| `uploaded_documents.extracted_json` | `structured.extraction_outcome` | Per-doc terminal outcome | **Yes** — `complete` / `degraded` / `unreadable` / `failed` |
| `uploaded_documents.extraction_status` | DB enum | Per-doc | `FAILED` for degraded/unreadable; `COMPLETE` for success |
| `donor_reports.knowledge_bank_json` | `unreadable_sources[]` | Reconciler output | **Only** for `extraction_outcome: unreadable` at input-build time (Option B extends to degraded) |
| `donor_reports.knowledge_bank_json` | `facts{}` | E1 reconciler | Excludes degraded/failed doc candidates |
| `donor_reports.gap_analysis_json` | `gaps[]` | E3 gap agent | Missing checklist items vs KB |
| `donor_reports.status` | `DEGRADED` | Partial synthesis/export | Set when synthesis `failed > 0` or export exception (L382–385, L154–157) |

#### Reconciler input assembly (critical for visibility)

[`app/reports/reconciliation/input_builder.py`](../app/reports/reconciliation/input_builder.py) `document_dict_to_input`:

- `extraction_outcome: unreadable` → **`unreadable_sources[]`** entry (visible in KB + gap prompt).
- `extraction_outcome: degraded` or `failed` → **empty bundle** — no facts, **no** `unreadable_sources` entry **today**.

**Implication:** NLCF `.docx`-as-indicator degrades at extract and **continues**, but the failed document is **not** listed in `knowledge_bank_json.unreadable_sources` until Option B is built.

---

### 3. The moat — zero-hallucination guarantee

Degraded input must produce **gaps or honest blanks**, never invented values. Enforcement is **layered** (no single switch):

| Layer | Enforcement | File / decision |
|-------|-------------|-----------------|
| **L1 extractors** | Return `degraded` / `unreadable` terminal envelopes; no LLM on junk (D-039) | `docling_content_guard.py`, `*_extractor.py` |
| **Reconciler input** | `degraded` / `failed` extractions → **zero fact candidates** — cannot enter KB as facts | `input_builder.py` L324–325 |
| **E1 reconciler** | Must not set `resolved_value`; conflicts surfaced, not merged silently (D-040) | `knowledge_bank_reconciler.py` |
| **E1 degrade pass-through** | On reconciler parse/timeout degrade: facts marked `confirmed: false` + `interpretation_note` | `degrade_resilience.py` `DEGRADED_PASS_THROUGH_NOTE` |
| **E3 gap agent** | “DO NOT resolve gaps, invent facts, or suggest values” | `gap_compliance_agent.py` system prompt L61–65 |
| **F1 synthesis** | **CARDINAL FACT RULE:** every specific must come from `facts` or `gap_answers`; controlled uncertainty + `assumptions[]` when missing | `ai/prompts/synthesis.py` L13–19 |
| **F2 fact-safety critic** | BLOCK specifics not supported by cited `fact:` / `gap:` sources | `fact_safety_critic.py` L40–55 |
| **Human gates** | Gate 1 confirms KB; Gate 2 supplies gap answers — server-enforced | `gate_preconditions.py`, gate services |

**P2 plan constraint:** Closing extract isolation gaps must **not** weaken these layers. Specifically:

- Do **not** push degraded extract JSON into reconciler fact candidates without human confirmation.
- Do **not** change synthesis/critic/gap **prompts** in P2 (that is Plan 2 / prompt-quality — **out of scope**).
- If a visibility fix requires the model to “fill in” missing indicator tables, **STOP** — that belongs in P5 (format coverage) or explicit human Gate 2 answers.

**Honest blank behaviour:** When indicator facts are absent, synthesis prompt instructs narrative uncertainty; gap agent emits questions; critic flags unsupported specifics. Residual LLM non-compliance is mitigated by critic + human gates, not extract isolation alone — P2 does not expand prompt work.

---

## Owner decisions (2026-06-08)

| # | Decision | Status |
|---|----------|--------|
| 1 | **Option B** — map degraded extractions into existing `unreadable_sources[]` | **CONFIRMED** (see contract verification below) |
| 2 | **Degrade vs hard-fail** — per-document only; systemic failures stay hard-fail | **CONFIRMED** — see § Per-error classification (not blanket degrade) |
| 3 | **No prompt-quality work** in P2 (synthesis / gap / critic prompts) | **CONFIRMED** — Plan 2 only |

### Option B — contract verification (no schema change required)

**Verdict: Option B is safe to rely on.** It **populates** the existing `unreadable_sources[]` field only. It does **not** reshape gate response contracts or require a DB migration.

| Check | Result |
|-------|--------|
| KB schema | `UnreadableSource` already defined in [`knowledge_bank_reconciliation_v1.py`](../app/reports/schemas/knowledge_bank_reconciliation_v1.py) (`source_document_id`, `source_label`, `code`, `message`) — `code` is a free string |
| Persisted JSONB | `unreadable_sources` already in `STRUCTURED_KNOWLEDGE_BANK_KEYS` and `KnowledgeBankReconciliationOutput` |
| Gate 1 read API | `GET …/knowledge-bank` already returns `unreadable_sources` via [`KnowledgeBankResponse`](../app/reports/schemas/report_lifecycle.py) — **no response shape change** |
| Gate 1 confirm | `validate_gate1_knowledge_bank` validates facts/conflicts provenance only — **does not restrict** `unreadable_sources` entries |
| E3 gap agent | Already receives `unreadable_sources` in KB subset ([`gap_compliance_agent.py`](../app/reports/agents/gap_compliance_agent.py) L212–216) — **no prompt change in P2** |
| E1 reconciler | Already merges `bundle.unreadable_sources` into KB output (D-040) |
| API contract §12 | No new fields; no new `error_code` |

**Build change (post-approval):** Extend [`input_builder.document_dict_to_input`](../app/reports/reconciliation/input_builder.py) so `extraction_outcome: degraded` (and persisted `failed` with typed error codes) emit an `UnreadableSourceInput` using `extracted_json.error` as `code` (e.g. `DEGRADED_EXTRACTION_UNPARSEABLE`). Facts remain excluded — **zero-hallucination fence unchanged.**

**Semantic note (not a contract amendment):** D-040 documents `unreadable → unreadable_sources[]`. Option B extends **population** to include degraded extractions under the same array shape. Append a decision-log entry at build time; no API/DB schema revision.

**Out of P2 scope:** Frontend rendering of `unreadable_sources` at Gate 1 (backend exposes field today; UI may lag).

---

## Per-error classification — degrade vs hard-fail

**Rule (owner-locked):** P2 converts **single-document** failures to per-document degrade + gap flag. **Run-level / systemic** failures remain **hard-fail** via existing `StageFailure` → `mark_job_failed` (P3/P4 machinery). **Do not blanket-convert** every `*ExtractorError` or `*ExtractionServiceError`.

### Already handled — no P2 change (return path, not raise)

| Outcome / code | Classification | Notes |
|----------------|----------------|-------|
| `extraction_outcome: degraded` + `DEGRADED_EXTRACTION_TIMEOUT` | **Per-doc degrade** ✓ | D-035; timeout after retry ceiling |
| `extraction_outcome: degraded` + `DEGRADED_EXTRACTION_UNPARSEABLE` | **Per-doc degrade** ✓ | Indicator `.docx` / unsupported suffix (NLCF path) |
| `extraction_outcome: unreadable` + `UNREADABLE_DOCUMENT_LOW_CONTENT` | **Per-doc degrade** ✓ | D-039; no LLM on junk |
| Indicator `ValueError` (`Unsupported spreadsheet format: …`) | **Per-doc degrade** ✓ | Routed before agent via `persist_degraded_indicator_unparseable` |

### Extract-stage errors — proposed P2 routing

#### A. Per-document → **DEGRADE** (persist typed envelope, `degraded_documents`, Option B → `unreadable_sources[]`, continue)

| Error code | Source | Rationale |
|------------|--------|-----------|
| `STOP_EMPTY_INPUT` | `proposal_extractor`, `grant_terms_extractor`, `indicator_data_extractor` | This document yielded no extractable content after intake — user file problem, not infra |
| `STOP_STRUCTURED_OUTPUT_FAILED` | All three extractors (`error_max_structured_output_retries`) | Schema/JSON extraction failed for **this** document’s content after bounded turns — garbled/complex single file |
| `STOP_NO_RESULT` | All three extractors | Agent finished without structured output for **this** call — single-document failure |
| `ValueError` (unsupported spreadsheet suffix) | `spreadsheet_input.parse_spreadsheet_from_path` | Wrong format for indicator lane — already degraded on indicator path; **verify** proposal/grant don’t hit this |
| `load_document_text` → empty string (no exception) | Intake | Treated as `STOP_EMPTY_INPUT` / unreadable at agent — **degrade**, same as empty doc |
| `load_document_text` / Docling → corrupt or unreadable file | Per-doc intake exception (e.g. conversion error on one PDF) | Single bad file — **degrade** with intake/unreadable code |
| `load_spreadsheet_json` → corrupt `.xlsx`/`.csv` (parse error, not unsupported suffix) | openpyxl/csv parse | Single bad spreadsheet — **degrade** (mirror unparseable) |
| S3 `NoSuchKey` / missing object for **one** `storage_ref` | `DocumentStorageService.fetch_bytes` | That document’s blob missing — **degrade** this doc; siblings continue |
| `STOP_AGENT_ERROR` | Extractors | **Only when document-scoped** — e.g. model refused/errored on this prompt/content. **Degrade this doc.** |

#### B. Run-level / systemic → **HARD FAIL** (keep `StageFailure`; do not degrade)

| Error code / condition | Source | Rationale |
|------------------------|--------|-----------|
| `STOP_WRONG_CLASSIFICATION` | `*_extraction_service` preflight | Pipeline dispatch bug or corrupted row — not a user “unreadable file” signal; continuing produces wrong-agent output |
| `STOP_DOCUMENT_NOT_FOUND` | `*_extraction_service` preflight | DB/session integrity break — not document quality |
| `DocumentStorageService` init `RuntimeError` (missing `ME_DOCUMENTS_S3_*`) | Storage config | Worker misconfig — **every** fetch will fail |
| S3/boto **account/bucket** errors (`AccessDenied`, `InvalidAccessKeyId`, persistent `503` on bucket) | Storage | Infrastructure down — degrading all docs misleads user |
| `STOP_AGENT_ERROR` with **infrastructure signature** | Extractors / SDK | Auth failure, API key missing, connection refused, rate-limit/quota exhaustion, model endpoint unavailable — **same failure would hit every doc** |
| Claude SDK subprocess env failure (e.g. `ANTHROPIC_API_KEY` absent in worker) | Agent runtime | Systemic — not file-specific |
| Uncaught worker/OOM/process death | Worker | P3 orphan reaper territory — not per-doc degrade |
| `dispatch_stage` `asyncio.TimeoutError` on **stage-level** timeout (if applied) | `dispatch.py` | Stage wall breach — treat as run failure unless explicitly per-doc scoped |

#### C. `STOP_AGENT_ERROR` — split rule (not blanket)

This is the ambiguous case. **Classification:**

| Signal | Route |
|--------|-------|
| Infrastructure patterns in message/stop_reason (401, 403, 429, 5xx, `connection`, `authentication`, `api_key`, `overloaded`, subprocess spawn failure) | **HARD FAIL** |
| Document already processed successfully in same extract loop and a **later** doc hits `STOP_AGENT_ERROR` without infra signature | **DEGRADE** failed doc only |
| First document in loop hits `STOP_AGENT_ERROR` with **no** infra signature | **DEGRADE** (optimistic single-doc) — *unless* retry of a minimal probe indicates infra (implementation may use fail-closed: second consecutive identical infra-like error → hard fail) |

**Build note:** Implement a small **systemic error classifier** (shared helper, not prompt change) used at the per-document catch boundary — not a blanket `except ExtractorError: degrade`.

#### D. Out of P2 extract scope (unchanged this package)

| Stage | Behaviour today |
|-------|-----------------|
| **Classify** | Stage-level hard-fail on `ClassifierError` — not per-document degrade |
| **Reconcile / gap / synthesise / critic** | Stage-level degrade or hard-fail per existing D-035/D-040/F1 patterns — not P2 |

### Propagation paths (for build planning)

| Raised as | Caught by | Today |
|-----------|-----------|-------|
| `*ExtractionServiceError` (preflight only) | Pipeline `except …ServiceError` | Hard-fail |
| `*ExtractorError` from service `raise` after persist | `dispatch_stage` → generic `Exception` → `StageFailure` | Hard-fail |
| Degraded envelope return | `is_degraded_result` | Continue ✓ |

P2 build targets the **per-document catch** inside `_run_extract_stage` **before** exceptions reach `dispatch_stage` / `StageFailure`, applying the table above.

---

### 4. Completed work preservation

| Scenario | Preserved? | Mechanism |
|----------|------------|-----------|
| Doc A succeeds, Doc B degrades | **Yes** | A’s `extracted_json` committed before B’s degrade path; extract stage completes |
| Reconcile after partial extract | **Yes** | E1 reads all persisted `extracted_json`; degraded docs contribute no candidates |
| Job fails mid-extract (StageFailure) | **Partial** | Documents processed **before** exception retain persisted state; job → `failed`, trace may have `classify` checkpoint |
| Synthesis partial failure | **Yes** | D-047 merge preserves `GENERATED` / `ACCEPTED` / `human_edited` sections |
| Export failure after content | **Yes** | `content_json` retained; report → `DEGRADED` on export exception |

**P2 goal:** Move more cases from “job failed / refund” to “degraded run / Gate 2 with gaps” so successful doc work is never lost to a sibling failure.

---

### 5. Charge interaction (D6 vs current code)

| Model | Behaviour | Status |
|-------|-----------|--------|
| **D6 (locked, P8)** | `REPORT_CREATE` charged **once at first `COMPLETE`**; never-completed reports not charged; failed jobs not refunded via separate path | **Not implemented** — P8 |
| **Current production code** | Charge at **report create** (`record_usage` in `create_donor_report`); **`REPORT_CREATE_REFUND`** on `mark_job_failed` | **Live** (`donor_report_lifecycle_service.py`, `job_failure.py`) |

**P2 relevance:**

- A run that **degrades but reaches Gate 2 / export `COMPLETE`** is **already charged at create** today (no extra charge).
- A run that **fails outright** gets **refunded** today — converting raise-and-kill extract failures into degrade-and-continue may **reduce refunds** ( desirable product behaviour; billing alignment waits for P8).
- P2 must **not** change quota/accounting (scope fence). Document D6 for owner; implement charge move only in P8.

---

## What P2 is NOT

- **Not** P5 (`.docx` table extraction / indicator format breadth).
- **Not** prompt-quality / Plan 2 (synthesis voice, gap wording, critic tuning).
- **Not** UI work (Gate 1 “failed document” chip — may follow; backend must expose existing fields).
- **Not** P8 quota migration.
- **Not** new DB migration or new `report_jobs` / API contract fields.

---

## Proposed build (post-approval only — sketch)

### B1. Per-document extract isolation seam (primary)

In `_run_extract_stage`, wrap **each document iteration** with a per-document boundary that applies **§ Per-error classification** — not a blanket `except ExtractorError`:

1. **Verify only (no change):** indicator `ValueError` → `persist_degraded_indicator_unparseable`.
2. **Extend to proposal/grant:** wrap `load_document_text` + extract service call; on **Table A** errors → persist existing degraded/unreadable envelope helpers → append `degraded_documents` → **continue**.
3. **Hard-fail passthrough:** **Table B** errors (incl. infra-signed `STOP_AGENT_ERROR`, `STOP_WRONG_CLASSIFICATION`, `STOP_DOCUMENT_NOT_FOUND`) → re-raise / `StageFailure` unchanged.
4. **Systemic classifier:** small shared helper (code-only, not prompt) to distinguish infra vs document-scoped `STOP_AGENT_ERROR`.

Reuse agent helpers (`build_degraded_unparseable_result`, `_build_degraded_timeout_result`, unreadable builders). No new degradation mechanism.

### B2. Downstream visibility — **Option B confirmed**

Extend `input_builder.document_dict_to_input` so `extraction_outcome: degraded` (and typed `failed`) populate existing **`unreadable_sources[]`** with `extracted_json.error` as `code`. Facts remain excluded. No API/DB schema change (see § Owner decisions).

### B3. Classify `degraded_notes` (optional, low priority)

Populate `degraded_notes` when classifier returns `intake_outcome: unreadable` — cosmetic trace completeness; not blocking Gate 2.

### B4. Tests (required)

Extend [`tests/test_orchestrator_gate1.py`](../tests/test_orchestrator_gate1.py) patterns:

| Test | Assert |
|------|--------|
| Mixed success + service-error degrade | Job → `awaiting_human` / `gap`; failed doc in `degraded_documents`; sibling docs `COMPLETE` extract |
| Mixed success + `load_document_text` failure | Same |
| KB / gap visibility (Option B) | `knowledge_bank_json.unreadable_sources` includes degraded doc with typed `code` |
| Systemic failure regression | Simulated infra `STOP_AGENT_ERROR` / storage misconfig still hard-fails whole job |
| No-fabrication smoke | Reconciler `facts` contain **no** values from degraded doc ids |
| Regression | Existing degraded timeout + unparseable tests remain green |

Explicit assertion: **no** `mark_job_failed` / `StageFailure` for single-doc extract failure in scoped scenarios.

---

## Scope fence and STOP conditions

| Condition | Action |
|-----------|--------|
| Fix requires **new** API/DB field beyond existing `degraded_*` / `unreadable_sources` | **STOP** — contract amendment |
| Fix requires **synthesis/gap/critic prompt** changes | **STOP** — Plan 2 |
| Fix requires **P5** format parsing (make `.docx` indicator succeed) | **STOP** — wrong package |
| Fix touches **quota/charge** | **STOP** — P8 |
| Cannot preserve zero-hallucination without inventing reconciler facts | **STOP** — report to owner |

---

## Acceptance criteria (P2 done)

1. Multi-document job with **one** failed extract (NLCF-class `.docx` indicator, agent STOP, or intake error) reaches **`awaiting_human` at Gate 1 or Gate 2** — not indefinite `running`, not whole-job `failed` unless **all** documents fail or a **stage-level** agent fails (reconcile/gap — out of extract scope).
2. Failed document id appears in **`extract.degraded_documents`** with typed **`extracted_json`** on the document row.
3. Successful documents’ extractions and reconciled facts **persist** unchanged.
4. Missing data surfaces as **Gate 2 gap** and/or **honest blank/assumption** in synthesis — **no new fabricated indicator values** in KB or content (test-backed).
5. Tests prove per-document isolation + no-fabrication smoke; existing orchestrator degrade tests remain green.
6. Option B: degraded docs appear in **`unreadable_sources[]`** on KB read — no new API fields.

---

## Sequencing

```
P3 committed (f6c3cf9) → classification approval (this doc) → P2 build → P4 (if coupled)
```

Do **not** parallelize P2 with P4.

---

## STOP — awaiting owner approval of per-error classification

**Locked (owner 2026-06-08):** Option B · no prompt work · per-doc degrade vs systemic hard-fail principle.

**Pending your approval:** The **§ Per-error classification** tables (especially **Table A / B / C** and `STOP_AGENT_ERROR` split) before any code is written.

**No code until classification approved.**

---

## Changelog

| Date | Author | Note |
|------|--------|------|
| 2026-06-08 | Cursor P2 diagnosis | Read-only trace; plan only |
| 2026-06-08 | Cursor P2 plan update | Owner decisions locked; Option B verified; per-error classification added |
