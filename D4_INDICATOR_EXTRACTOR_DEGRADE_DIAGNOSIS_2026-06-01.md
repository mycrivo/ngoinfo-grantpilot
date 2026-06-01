# D4 Indicator Extractor Degrade Diagnosis — Prod FCDO Walk

**Report:** `fe6bf98b-70b7-46f2-9bc2-a1306546af18`  
**Date:** 2026-06-01  
**Method:** Read-only — prod DB (`uploaded_documents`, `report_jobs`, `donor_reports`), Railway worker logs, committed code paths. No pipeline re-run, no model calls.

---

## Verdict (3 lines)

1. **Degraded documents:** Both `indicator_data` uploads failed in D4 — `03_FCDO_BridgeLight_Logframe_Data_Table.docx` (`20fd328f…`) with **`DEGRADED_EXTRACTION_UNPARSEABLE`** (intake rejected `.docx` before any LLM call), and **`BridgeLight Logframe and Finance AR1 Export.xlsx`** (`48ae7659…`) with **`DEGRADED_EXTRACTION_TIMEOUT`** after **2/2** attempts at the **90.0s** per-attempt ceiling.
2. **Failure mode (missing actuals):** The `.xlsx` is the spreadsheet that reached D4’s Claude Agent SDK path; both attempts hit `asyncio.TimeoutError` with **no** `input_tokens` / `output_tokens` / `latency_ms` recorded — the subprocess never returned a completed extraction within 90s. The `.docx` never reached the SDK (`model_used: null`, `attempt_count: null`).
3. **Fix class:** **Two distinct classes** — (d) **format/routing** for the Word logframe table (`.docx` routed to D4 but intake only accepts `.xlsx`/`.csv`), and (a) **latency/timeout** for the AR1 export spreadsheet (payload ~29k JSON chars, not truncated; 180s+ wall time observed on the same extractor class in gate history under the same 90s ceiling).

---

## 1. Document identification

| Document ID | Filename | Ext / MIME | Size (bytes) | D1 classification | Extractor routed | D4 outcome |
|-------------|----------|------------|--------------|-------------------|------------------|------------|
| `20fd328f-b396-46fe-ba2c-aa81a5cc1210` | `03_FCDO_BridgeLight_Logframe_Data_Table.docx` | `.docx` / `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | 39,790 | **`indicator_data`** | **D4** (`indicator_data_extractor`) | **`degraded`** — `DEGRADED_EXTRACTION_UNPARSEABLE` |
| `48ae7659-5859-4c5e-a144-b4b76b5622f3` | `BridgeLight Logframe and Finance AR1 Export.xlsx` | `.xlsx` / `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 13,119 | **`indicator_data`** | **D4** (`indicator_data_extractor`) | **`degraded`** — `DEGRADED_EXTRACTION_TIMEOUT` |

**Upload order** (from `uploaded_documents.created_at`): proposal → grant letter → logframe `.docx` → AR1 `.xlsx`.

**Source:** prod DB query on `uploaded_documents` for report `fe6bf98b…`; upload IDs cross-matched to `STAGE_E_SMOKE_WALK_d26278c.log` lines 4–7.

**Which was the indicator spreadsheet?**  
Both uploads were classified `indicator_data` and both were dispatched to D4 per `pipeline.py` `_run_extract_stage` (`classification == INDICATOR_DATA` branch). The **`.xlsx`** is the only file that passed spreadsheet intake and invoked the Claude SDK. The **`.docx`** was also routed to D4 but failed at `load_spreadsheet_json` → `parse_spreadsheet_from_path` because `.docx` is not a supported suffix (`spreadsheet_input.py:104–110`).

**Was the other degrade in a different extractor?** **No.** The other two uploads completed in D2/D3:

| Document | Classification | Extractor | Status |
|----------|----------------|-----------|--------|
| `01_FCDO_BridgeLight_Winning_Proposal.docx` | `proposal` | `proposal_extractor` | `COMPLETE` |
| `02_FCDO_BridgeLight_Award_Letter.docx` | `grant_letter` | `grant_terms_extractor` | `COMPLETE` |

Both degraded IDs appear only in the extract-stage `degraded_documents` list; no other extractor recorded them.

---

## 2. Failure mode

### 2a. `20fd328f…` — Logframe `.docx` — UNPARSEABLE (no LLM)

**Code path:** `_run_extract_stage` → `load_spreadsheet_json` → `parse_spreadsheet_from_path` raises `ValueError("Unsupported spreadsheet format: .docx")` → `persist_degraded_indicator_unparseable` (`pipeline.py:395–411`, `document_intake.py:70–88`, `indicator_data_extractor.py:382–395`).

**Worker log (verbatim):**
```
indicator_data_extractor unparseable filename=03_FCDO_BridgeLight_Logframe_Data_Table.docx
extract returned degraded envelope — walk continues
```

**Persisted `extracted_json` (prod DB):**
- `extraction_outcome`: `degraded`
- `degraded_code`: `DEGRADED_EXTRACTION_UNPARSEABLE`
- `error`: `DEGRADED_EXTRACTION_UNPARSEABLE`
- `extracted_at`: `2026-05-31T22:13:51.452527Z`
- `agent_trace`: `model_used: null`, `attempt_count: null`, `input_tokens: null`, `latency_ms: null`
- `structured.indicators`: `[]` (0 rows)

**Not:** timeout, token limit, parser cold-start on openpyxl (parser never invoked), or empty LLM return.

---

### 2b. `48ae7659…` — AR1 `.xlsx` — TIMEOUT (2 × 90s)

**Code path:** Spreadsheet intake succeeded → `extract_indicator_data_text` → `asyncio.wait_for(_run_extractor_query(...), timeout=90.0)` → both attempts raised `asyncio.TimeoutError` → `_build_degraded_timeout_result` (`indicator_data_extractor.py:561–596`).

**Worker log (verbatim):**
```
indicator_data_extractor timeout attempt=1/2 ceiling=90.0s
indicator_data_extractor timeout attempt=2/2 ceiling=90.0s
extract returned degraded envelope — walk continues
```

**Persisted `extracted_json` (prod DB):**
- `extraction_outcome`: `degraded`
- `degraded_code`: `DEGRADED_EXTRACTION_TIMEOUT`
- `error`: `DEGRADED_EXTRACTION_TIMEOUT`
- `extracted_at`: `2026-05-31T22:17:02.580714Z`
- `agent_trace`: `attempt_count: 2`, `max_turns: 3`, `model_used: "haiku"`, `input_tokens: null`, `output_tokens: null`, `latency_ms: null`, `content_hash: "2d7be56d6bd645841c353d38bcc6cc09210a4bc0205c2098e47bcf05c017eb74"`
- `structured.indicators`: `[]` (0 rows)

**Wall-clock evidence (extract stage timeline):**
- Classify completed: `2026-05-31T22:11:51.303102+00:00`
- Logframe `.docx` degrade persisted: `22:13:51Z` (after ~2 min for D2 + D3 on prior docs)
- AR1 `.xlsx` degrade persisted: `22:17:02Z` → **~191s after docx degrade**, consistent with **two full 90s attempt ceilings** (180s) plus overhead
- Extract stage `completed_at`: `2026-05-31T22:17:02.595846+00:00`

**Timeout configuration:** Prod backend has **`ME_CLASSIFIER_TIMEOUT_SECONDS` unset** (Railway variables query returned `null`); D4 default is **`TIMEOUT_SECONDS = 90`** (`indicator_data_extractor.py:48`). Per-attempt SDK env: `API_TIMEOUT_MS = 90000` (`indicator_data_extractor.py:225–236`).

**Size / token evidence:**
- Prod file size: **13,119 bytes** (DB).
- Local parse of repo bundle copy of the same filename: **29,278 JSON chars**, **`truncated: false`**, 1 sheet / 20 rows — well below `MAX_INPUT_CHARS = 120_000` (`indicator_data_extractor.py:52`).
- **No token figures** on the degraded record → the timeout fired before a successful SDK response was parsed; this is **not** an oversized-payload rejection at intake.

**Not observed in logs/traces:** exception type other than timeout, parser/init error on openpyxl, or garbled JSON return from a completed call.

---

### Downstream symptom (actuals absent)

Prod `knowledge_bank_json.facts` for this report: **33 facts, 0 keys containing `.actual` or `actual`**. Reconcile completed (`reconciliation_outcome: complete`, `reconcile.degraded: false`) but with **empty D4 indicator rows** from both `indicator_data` documents — consistent with synthesis seeing targets (from proposal) but no tabular actuals.

---

## 3. Retry behaviour

| Document | Attempts before degrade | Same failure each attempt? | Retry changed outcome? |
|----------|-------------------------|----------------------------|------------------------|
| `20fd328f…` (`.docx`) | **0 SDK attempts** — immediate intake degrade | N/A (no retry loop entered) | No |
| `48ae7659…` (`.xlsx`) | **2** (`attempt_count: 2` in DB) | **Yes** — both logged as `timeout attempt=N/2 ceiling=90.0s` | **No** — second attempt also timed out; terminal `DEGRADED_EXTRACTION_TIMEOUT` |

Retry logic: `for attempt in range(1, MAX_EXTRACTION_ATTEMPTS + 1)` with `MAX_EXTRACTION_ATTEMPTS = 2` (`indicator_data_extractor.py:49, 561–589`). Only `asyncio.TimeoutError` triggers retry; unparseable intake bypasses this loop entirely.

---

## 4. Fix class

| Document | Fix class | One-line fix direction (direction only) |
|----------|-----------|----------------------------------------|
| `20fd328f…` `.docx` | **(d) format/content + routing** — Word logframe table classified `indicator_data` but D4 intake accepts only `.xlsx`/`.csv` | Route Word-embedded tables through a text/table intake path (Docling or proposal-style) **or** reclassify and extract via a non-spreadsheet extractor; do not send `.docx` to `parse_spreadsheet_from_path`. |
| `48ae7659…` `.xlsx` | **(a) latency/timeout** — Claude Agent SDK subprocess did not finish within **90s** per attempt × 2 | Raise D4 per-attempt wall clock (and/or total extract-stage budget) so intermittent SDK runs that gate history shows can exceed 180s wall still complete; not a payload-size fix. |

**Not supported by evidence for the `.xlsx` degrade:**
- **(b) size/token limit** — JSON ~29k chars, not truncated; no token usage recorded.
- **(c) parser cold-start/init** — openpyxl parse succeeded; `content_hash` persisted before timeout path.
- **(e) other/undetermined** for the `.xlsx` — timeout is explicitly logged and persisted.

**Primary cause of missing indicator actuals in KB:** the **`.xlsx` timeout degrade** (the AR1 export is the intended actuals carrier). The **`.docx` unparseable degrade** is a secondary gap (same D4 route, zero rows, no actuals).

---

## 5. Reproducibility

### `48ae7659…` — AR1 `.xlsx` (timeout)

| Question | Finding |
|----------|---------|
| Document-specific or systemic? | **Intermittent latency under fixed 90s ceiling**, not deterministic “bad sheet format.” Same extractor + model (`haiku`) passed gate runs on a **different, smaller** test workbook (`tests/fixtures/indicator_extractor/fcdo_bridgelight_indicator_data.xlsx`, 6,314 bytes, 7,387 JSON chars). |
| Evidence | `tests/D4_INDICATOR_GATE_AUDIT.md`: stability run **`stability_1` wall_ms = 179,853** (~180s) with `complete` outcome on the gate fixture; stderr in that session included `indicator_data_extractor timeout attempt=1/2 ceiling=90.0s` — i.e. **first attempt can timeout and second can succeed**. Prod walk: **both** attempts timed out → degrade. |
| Prod vs repo file | Prod persisted `content_hash = 2d7be56d…`; local parse of repo `M_E_Module/.../BridgeLight Logframe and Finance AR1 Export.xlsx` yields `db2e9bee…` (same **13,119-byte** size on prod DB). **Cannot determine from available evidence** whether the uploaded bytes differ from the current repo copy or parsing environment differs; failure mode (timeout) is independent of that mismatch. |
| Shape/size systemic? | **Not proven systemic for all sheets** — this upload is small (20 rows, 1 sheet, no truncation). Failure aligns with **SDK slowness / cold subprocess** under a **90s cap**, not sheet dimensions alone. |

### `20fd328f…` — Logframe `.docx` (unparseable)

| Question | Finding |
|----------|---------|
| Document-specific or systemic? | **Deterministic for any `.docx` routed to D4** — `parse_spreadsheet_from_path` only accepts `.xlsx`/`.csv` (`spreadsheet_input.py:104–110`). |
| Evidence | Worker log + `DEGRADED_EXTRACTION_UNPARSEABLE` with null `attempt_count`; no LLM invocation. Classifier assigned `indicator_data` to a Word file containing tabular logframe content (FCDO test bundle design). |

---

## Evidence index

| Source | Location |
|--------|----------|
| Upload ID ↔ filename | `STAGE_E_SMOKE_WALK_d26278c.log:4–7` |
| Extract degrade list | `report_jobs.agent_trace_json.stages.extract` (prod DB); `F1_PROSE_WALK_fe6bf98b.json:15–19` |
| Per-document extraction payloads | `uploaded_documents.extracted_json` (prod DB) |
| Worker stderr | `railway logs --service exemplary-encouragement --since 2026-05-31T22:10:00Z --until 2026-05-31T22:18:00Z` |
| D4 intake / timeout code | `app/reports/orchestration/pipeline.py:395–428`, `document_intake.py:70–88`, `indicator_data_extractor.py:48–52, 382–596` |
| Gate latency precedent | `tests/D4_INDICATOR_GATE_AUDIT.md` §2 (`stability_1` 179,853 ms) |
| KB actuals absent | Prod DB: 0 fact keys matching `*.actual` / `actual` on report `fe6bf98b…` |

---

**STOP** — diagnosis only; no remediation performed.
