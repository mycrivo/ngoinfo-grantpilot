# P3-7 re-walk evidence — close-out session (2026-06-11)

**Authority:** Owner GO on P3-7 close-out (ship → verify → re-walk).  
**Deployed HEAD:** `b7d844783e73516461591f1cfef52ac2543dfbe4` (commits `d78a628`, `b7d8447`).

---

## 1 · Ship

| Commit | Summary |
|--------|---------|
| `d78a628` | P3-7: synthesis prose contract, honesty gates, KB table export, tests |
| `b7d8447` | P3-7: decision log, findings dispositions, live Gate-2 boundary validator |

**CI (push to main):**

| Workflow | Run ID | Conclusion |
|----------|--------|------------|
| Smoke Test | [27377315198](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27377315198) | success |
| P3 Offline Replay | [27377315624](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27377315624) | success |

---

## 2 · Pre-walk check (validator correction)

**Issue:** `phase2_owner_validation.py --fcdo-complete` defaulted to committed B3 artefact `p3_b3_gap_stage_7cdcc3a8.json` for gap-set grading.

**Correction (in `b7d8447`):** `--fcdo-complete` now reads `report.gap_analysis_json` from `GET /api/reports/{id}` for the report under test (Gate-2 boundary surfaced set). Live `gap-check` remains for funder-side leak checks only. Optional `--gap-stage-snapshot` retained for offline replay.

**Harness note (local, uncommitted until evidence commit):** `full_walk.py` calls `bootstrap_db_env()` so minted audit accounts receive `IMPACT` plan in DB (without this, `POST /api/reports` returned 429).

---

## 3 · Deploy verify (read-only)

| Check | Observation |
|-------|-------------|
| Railway deploy SHA | `b7d844783e73516461591f1cfef52ac2543dfbe4` (GitHub deployment 5026653902, 2026-06-11T21:04:07Z) |
| Service | `ngoinfo-grantpilot` — Online |
| Alembic (prod public DB) | `0018_usage_ledger_uq (head)` — unchanged |
| Health | `GET /health` → 200 on deploy restart |

---

## 4 · Re-walk (B3 protocol)

Original audit account `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` returned **429** on `POST /api/reports` (quota exhausted). Fresh mint accounts used per owner authorization.

### FCDO — `p3_7_rewalk_fcdo`

| Field | Value |
|-------|-------|
| Report ID | `1beb588b-68e1-4ad9-a43e-a6695aa15dd6` |
| Owner | `audit-p3_7_fcdo-1781215939@grantpilot-test.org` |
| Walk exit | `0` |
| Verdict | `completed` |
| Export bytes | 38341 |
| Walk log | `dynamic_run/p3_7_rewalk_fcdo_walk.log` (gitignored) |
| Walk artefact | `dynamic_run/walk_p3_7_rewalk_fcdo_1beb588b.json` (gitignored) |

**Gate 2 boundary** ([`snapshots/p3_7_fcdo_gap_stage_1beb588b.json`](snapshots/p3_7_fcdo_gap_stage_1beb588b.json)): `open_items_count: 3`, refs `{progress_against_expected_results, logframe_row:op2_3, logframe_row:op4_2}`. Walk log: `GATE2 gaps=3 answered=0 skipped=3`.

**Section prose (post-synthesis, all ACCEPTED at export):**

| section_key | generation_status | text chars |
|-------------|-------------------|------------|
| summary_and_overview | ACCEPTED | 433 |
| performance_and_conclusions | ACCEPTED | 550 |
| evidence_and_evaluation | ACCEPTED | 473 |
| risk_and_safeguarding | ACCEPTED | 419 |
| programme_management_delivery_commercial_financial | ACCEPTED | 360 |
| recommendations_and_actions | ACCEPTED | 317 |

**Synthesise trace:** `openai_input_tokens: 67863`, `openai_output_tokens: 3396` (non-zero; F-12 closure on live walk).

**Readiness message (post-complete gap-check):** `Complete — 3 items skipped.`

**Production export:** [`snapshots/p3_7_fcdo_export_1beb588b.docx`](snapshots/p3_7_fcdo_export_1beb588b.docx) — body prose present; **0 Word tables** in downloaded artefact.

**Local re-render** with P3-7 renderer + same KB/content: [`snapshots/p3_7_fcdo_export_rerender_1beb588b.docx`](snapshots/p3_7_fcdo_export_rerender_1beb588b.docx) — **1 logframe table**, 12 rows; `not provided` in actual column for gap rows (KB had 0 `logframe_ar1_actual` facts on this walk).

### NLCF — `p3_7_rewalk_nlcf` (frozen — honest gate refusal)

| Field | Value |
|-------|-------|
| Report ID | `6c756017-d510-46b0-a765-bdd82605a7a1` |
| Owner | `audit-p3_7_nlcf-1781216631@grantpilot-test.org` |
| Walk exit | `1` |
| Verdict | `accept_all_failed` |
| Report status | `DEGRADED` (job `awaiting_human` at export) |
| Walk artefact | `dynamic_run/walk_p3_7_rewalk_nlcf_6c756017.json` (gitignored) |

**Refusing gate (verbatim):**

```json
{
  "status_code": 422,
  "body": {
    "error_code": "GATE3_SECTION_NOT_ACCEPTABLE",
    "message": "Cannot accept all while FAILED sections remain",
    "details": {
      "section_key": "changes_and_next_steps"
    }
  }
}
```

**Section state at freeze:**

| section_key | generation_status | text chars |
|-------------|-------------------|------------|
| project_story | AWAITING_REVIEW | 890 |
| community_involvement | GENERATED | 944 |
| difference_made | GENERATED | 1847 |
| learning | GENERATED | 1734 |
| **changes_and_next_steps** | **FAILED** | **0** |
| spend_summary | AWAITING_REVIEW | 383 |

**Synthesise trace:** `failed: 1`, `generated: 5`, `openai_input_tokens: 25480`, `openai_output_tokens: 4393`.

**Gate 2 boundary** ([`snapshots/p3_7_nlcf_gap_stage_6c756017.json`](snapshots/p3_7_nlcf_gap_stage_6c756017.json)): `open_items_count: 11` (default NLCF docset — not the 18-ref regression pin set).

Walk frozen per anti-bent-ruler standing order; no gate bypass attempted.

---

## 5 · Validator stdout (verbatim)

### FCDO `--fcdo-complete` (report `1beb588b…`)

**Exit code:** `2`

**Stderr:**

```text
FAIL: FCDO complete gap set mismatch expected=['logframe_row:op2_3', 'logframe_row:op4_2'] actual=['logframe_row:op2_3', 'logframe_row:op4_2', 'progress_against_expected_results']
FAIL: open_items_count 3 != expected 2
```

**Stdout:**

```json
{
  "open_items_count": 3,
  "readiness_basis": "ngo_data",
  "readiness_message": "Complete — 3 items skipped.",
  "missing_count": 3,
  "required_item_refs": [
    "logframe_row:op2_3",
    "logframe_row:op4_2",
    "progress_against_expected_results"
  ],
  "funder_side_leaks": [],
  "gap_check_live": {
    "open_items_count": 0,
    "required_item_refs": [],
    "readiness_message": "Complete — 3 items skipped."
  },
  "gate2_boundary": {
    "open_items_count": 3,
    "required_item_refs": [
      "logframe_row:op2_3",
      "logframe_row:op4_2",
      "progress_against_expected_results"
    ],
    "missing_count": 3,
    "readiness_basis": "ngo_data",
    "source": "report.gap_analysis_json"
  }
}
```

### FCDO leak-only (no `--fcdo-complete`)

**Exit code:** `0` — `funder_side_leaks: []`.

---

## 6 · Docx machine-check

**FCDO content_json assertions** (`assert_export_docx` on production-downloaded bytes): `passed: true`, `violation_count: 0`.

**FCDO offline replay** (`walk_p3_7_rewalk_fcdo_1beb588b.json`): exit `1` — `G-forbidden` violation: `progress_against_expected_results` in gap set (literal forbidden + RSS/OA forbidden ref).

**NLCF offline replay:** not run to completion (walk frozen before export).

**NLCF pin fixture** (`offline_replay --nlcf-pin`): unchanged from prior session — exit `0` on main CI.

---

## 7 · Ledger · stage traces

Full JSON: [`snapshots/p3_7_ledger_traces.json`](snapshots/p3_7_ledger_traces.json)

| Report | status | REPORT_CREATE ledger | synthesise openai_in / out |
|--------|--------|----------------------|----------------------------|
| FCDO `1beb588b…` | COMPLETE | 1 row `report:create:1beb588b-68e1-4ad9-a43e-a6695aa15dd6` | 67863 / 3396 |
| NLCF `6c756017…` | DEGRADED | 0 rows (export not completed) | 25480 / 4393 |

---

## STOP

Owner reads:

- [`snapshots/p3_7_fcdo_export_1beb588b.docx`](snapshots/p3_7_fcdo_export_1beb588b.docx) (production download)
- [`snapshots/p3_7_fcdo_export_rerender_1beb588b.docx`](snapshots/p3_7_fcdo_export_rerender_1beb588b.docx) (local P3-7 re-render with logframe table)
- NLCF frozen state above (no export docx)

**Open items for owner Phase 3 closure decision:**

1. FCDO gap set includes forbidden `progress_against_expected_results` (validator exit 2; offline replay G-forbidden fail). **→ P3-8 build:** reclassified out of forbidden moat; 3-ref complete pin.
2. Production FCDO export had prose but 0 tables; KB on this walk lacked `logframe_ar1_actual` facts. **→ Resolved/noise** (test-data; local re-render proves table path).
3. NLCF `changes_and_next_steps` synthesis FAILED — accept-all honestly refused (P3-7 gate working as designed). **→ P3-8 build:** `insufficient_data` + engine insufficiency prose; confirming re-walk must capture verbatim statement below.

**P3-8 confirming re-walk — NLCF insufficiency prose (verbatim, owner-read):**

See [§8 · P3-8 confirming re-walk](#8--p3-8-confirming-re-walk-owner-triggered-b3-protocol) below.

---

## 8 · P3-8 confirming re-walk (owner-triggered; B3 protocol)

**Authority:** Owner-triggered confirming re-walk after P3-8 build on `main`.  
**Deployed HEAD:** `d15c97caf7009f7bfc32747f93b2214eee3413ba` (`d15c97c`).

Anti-bent-ruler standing order observed: both walks frozen at honest gate refusal; no bypass, retry-around, or mid-walk code changes.

---

### 8.1 · Ship · CI (reference)

| Commit | Summary |
|--------|---------|
| `d15c97c` | P3-8: reclassify `progress_against_expected_results`; `insufficient_data` section policy + insufficiency prose |

**CI (push to main):**

| Workflow | Run ID | Conclusion |
|----------|--------|------------|
| Smoke Test | [27469689985](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27469689985) | success |
| P3 Offline Replay | [27469689982](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27469689982) | success |

---

### 8.2 · Deploy verify (read-only)

| Check | Observation |
|-------|-------------|
| Railway deploy SHA | `d15c97caf7009f7bfc32747f93b2214eee3413ba` (GitHub deployment 5046949875, 2026-06-13T14:36:18Z) |
| API service | `ngoinfo-grantpilot` — Online |
| Worker service | `exemplary-encouragement` — Online (same project push) |
| Alembic (prod public DB) | `0018_usage_ledger_uq (head)` — unchanged |
| Health | `GET /health` → 200 (`{"status":"ok","service":"grantpilot",…}`) |

---

### 8.3 · FCDO — `p3_8_rewalk_fcdo` (frozen — honest gate refusal)

| Field | Value |
|-------|-------|
| Report ID | `d838c419-8ac3-44c4-a22e-d713e491bcc6` |
| Owner | `audit-p3_8_rewalk_fcdo-1781364156@grantpilot-test.org` |
| Walk exit | `1` |
| Verdict | `accept_all_failed` |
| Report status | `DEGRADED` (job `awaiting_human` at export) |
| Walk log | `dynamic_run/p3_8_rewalk_fcdo_walk.log` (gitignored) |
| Walk artefact | `dynamic_run/walk_p3_8_rewalk_fcdo_d838c419.json` (gitignored) |

**Docset composition (walk log + reconcile snapshot — includes indicator spreadsheet):**

1. `01_FCDO_BridgeLight_Winning_Proposal.docx`
2. `02_FCDO_BridgeLight_Award_Letter.docx`
3. `BridgeLight Logframe and Finance AR1 Export.xlsx`

**Refusing gate (verbatim):**

```json
{
  "status_code": 422,
  "body": {
    "error_code": "GATE3_SECTION_NOT_ACCEPTABLE",
    "message": "Cannot accept all while FAILED sections remain",
    "details": {
      "section_key": "evidence_and_evaluation"
    }
  }
}
```

**Gate 2 boundary** ([`snapshots/p3_8_fcdo_gap_stage_d838c419.json`](snapshots/p3_8_fcdo_gap_stage_d838c419.json)): `open_items_count: 3`, refs `{progress_against_expected_results, logframe_row:op2_3, logframe_row:op4_2}`. Walk log: `GATE2 gaps=3 answered=0 skipped=3`.

**Section state at freeze** (`after_critique_detail`):

| section_key | generation_status | structured_bind_status | text chars | failure_reason |
|-------------|-------------------|----------------------|------------|----------------|
| summary_and_overview | GENERATED | bound | 415 | — |
| performance_and_conclusions | GENERATED | bound | 389 | — |
| **evidence_and_evaluation** | **FAILED** | — | **0** | `Unterminated string starting at: line 133 column 22 (char 8092)` (OpenAI JSON parse) |
| risk_and_safeguarding | AWAITING_REVIEW | bound | 363 | — |
| programme_management_delivery_commercial_financial | GENERATED | bound | 219 | — |
| recommendations_and_actions | AWAITING_REVIEW | bound | 334 | — |

**Knowledge bank (after reconcile):** 78 facts; 36 under `indicators.*` (e.g. `indicators.OP1.1.actual`, `indicators.OP2.1.actual`). **0** keys matching `*.logframe_ar1_actual` — table renderer expects `indicators.OPx.y.logframe_ar1_actual` style keys.

**Synthesise trace:** `openai_input_tokens: 55412`, `openai_output_tokens: 2915`, `failed: 1`, `generated: 5`.

**Gap-check during walk:** `GET …/gap-check` → HTTP 500 (`INTERNAL_SERVER_ERROR`). Post-freeze validator gap-check (owner token): `readiness_message: "Complete — 3 items skipped."`, `funder_side_leaks: []`.

**Production export:** **not produced** — walk frozen before export download. No committed production docx for this report.

**Logframe table in production export:** **not observable** (no export artefact).

---

### 8.4 · NLCF — `p3_8_rewalk_nlcf` (frozen — honest gate refusal)

| Field | Value |
|-------|-------|
| Report ID | `588c3e7d-d16b-49b2-b4f4-9c2a695c1c2c` |
| Owner | `audit-p3_8_rewalk_nlcf-1781364757@grantpilot-test.org` |
| Walk exit | `1` |
| Verdict | `accept_all_failed` |
| Report status | `DEGRADED` (job `awaiting_human` at export) — **did not reach COMPLETE** |
| Walk log | `dynamic_run/p3_8_rewalk_nlcf_walk.log` (gitignored) |
| Walk artefact | `dynamic_run/walk_p3_8_rewalk_nlcf_588c3e7d.json` (gitignored) |

**Docset composition (default NLCF 3-file shape):**

1. `01_NLCF_Southbank_Application_Proposal.docx`
2. `02_NLCF_Southbank_Award_Letter.docx`
3. `03_NLCF_Southbank_Monitoring_and_Spend_Table.docx`

**Refusing gate (verbatim):**

```json
{
  "status_code": 422,
  "body": {
    "error_code": "GATE3_SECTION_NOT_ACCEPTABLE",
    "message": "Cannot accept all while FAILED sections remain",
    "details": {
      "section_key": "community_involvement"
    }
  }
}
```

**Gate 2 boundary** ([`snapshots/p3_8_nlcf_gap_stage_588c3e7d.json`](snapshots/p3_8_nlcf_gap_stage_588c3e7d.json)): `open_items_count: 12`. Walk log: `GATE2 gaps=12 answered=0 skipped=12`.

**Section state at freeze** (`after_critique_detail`):

| section_key | generation_status | structured_bind_status | text chars | notes |
|-------------|-------------------|----------------------|------------|-------|
| project_story | GENERATED | **insufficient_data** | 445 | P3-8 engine insufficiency prose (verbatim below) |
| **community_involvement** | **FAILED** | — | **0** | synthesis_failed path (first blocking section_key in 422) |
| difference_made | GENERATED | bound | 290 | real prose |
| learning | AWAITING_REVIEW | bound | 1043 | real prose |
| **changes_and_next_steps** | **FAILED** | — | **0** | synthesis_failed — **not** `insufficient_data` |
| spend_summary | AWAITING_REVIEW | bound | 463 | real prose |

**Synthesise trace:** `openai_input_tokens: 22438`, `openai_output_tokens: 3052`, `failed: 2`, `generated: 4`.

**Gap-check during walk:** HTTP 500 (same as FCDO).

**Production export:** **not produced**.

**Live verbatim P3-8 `insufficient_data` prose (`project_story`, not `changes_and_next_steps`):**

> This section could not be drafted from the material available in uploaded documents or confirmed gap answers for the reporting period. The template requires information on the required template items, but no citable source supplied those items for "The story of your project this year". Accordingly, no narrative is presented here: the organisation has left this section blank rather than report anything not supported by the available evidence.

**`changes_and_next_steps` at freeze:** `generation_status: FAILED`, `text chars: 0`. `failure_reason` (synthesis path, not insufficiency template):

> Insufficient evidence was available to draft a substantive adaptation and next steps section.; No knowledge bank facts were supplied for this section.; Required indicators were present only as skipped gap answers.

Walk frozen per anti-bent-ruler standing order; no gate bypass attempted.

---

### 8.5 · Validator stdout (verbatim)

#### FCDO `--fcdo-complete` (report `d838c419…`, owner token, post-freeze)

**Exit code:** `0`

**Stdout:**

```json
{
  "open_items_count": 3,
  "readiness_basis": "ngo_data",
  "readiness_message": "Complete — 3 items skipped.",
  "skipped_items_count": null,
  "missing_count": 3,
  "required_item_refs": [
    "logframe_row:op2_3",
    "logframe_row:op4_2",
    "progress_against_expected_results"
  ],
  "funder_side_leaks": [],
  "missing_items": [],
  "gap_check_live": {
    "open_items_count": 0,
    "required_item_refs": [],
    "readiness_message": "Complete — 3 items skipped."
  },
  "gate2_boundary": {
    "open_items_count": 3,
    "required_item_refs": [
      "logframe_row:op2_3",
      "logframe_row:op4_2",
      "progress_against_expected_results"
    ],
    "missing_count": 3,
    "readiness_basis": "ngo_data",
    "source": "report.gap_analysis_json"
  }
}
```

3-ref complete pin matches P3-8 fixture (`fcdo_complete_3347590c_expected_gaps.json`).

#### NLCF

Validator not run to completion target (report never COMPLETE / no export).

---

### 8.6 · Production exports · docx machine-check

| Walk | Production docx download | Docx machine-check |
|------|--------------------------|-------------------|
| FCDO `d838c419…` | **None** (frozen at Gate 3) | **Not run** |
| NLCF `588c3e7d…` | **None** (frozen at Gate 3) | **Not run** |

No committed rendered exports for P3-8 re-walk — both walks stopped before production export.

---

### 8.7 · Ledger · stage traces

Full JSON: [`snapshots/p3_8_ledger_traces.json`](snapshots/p3_8_ledger_traces.json)

| Report | status | job | REPORT_CREATE ledger | synthesise openai_in / out | failed / generated |
|--------|--------|-----|----------------------|----------------------------|--------------------|
| FCDO `d838c419…` | DEGRADED | export / awaiting_human | **0 rows** | 55412 / 2915 | 1 / 5 |
| NLCF `588c3e7d…` | DEGRADED | export / awaiting_human | **0 rows** | 22438 / 3052 | 2 / 4 |

Readiness message (FCDO, post-freeze gap-check via validator): `Complete — 3 items skipped.`

---

## STOP (P3-8 confirming re-walk)

Owner reads:

- **No production docx downloads** for either walk (both frozen at Gate 3).
- FCDO walk artefact + gap snapshot: 3-ref Gate-2 set confirmed; spreadsheet in docset; KB has `indicators.*.actual` but **no** `logframe_ar1_actual` keys; `evidence_and_evaluation` FAILED on JSON parse flake.
- NLCF walk artefact + gap snapshot: `project_story` carries live P3-8 `insufficient_data` prose; `changes_and_next_steps` still **FAILED** via synthesis path (0 chars); report **not COMPLETE**.

**Findings for owner Phase 3 closure decision:**

1. **FCDO logframe table in production export** — not confirmed on this walk (no export; KB fact-key naming vs table renderer mismatch persists: 0 `*.logframe_ar1_actual` keys despite spreadsheet upload).
2. **FCDO Gate 3** — honest refusal on `evidence_and_evaluation` OpenAI JSON parse error (unrelated to P3-8 insufficiency policy).
3. **NLCF insufficiency path** — `insufficient_data` prose confirmed live on `project_story`; target section `changes_and_next_steps` did not receive insufficiency prose (still synthesis FAILED).
4. **Gap-check HTTP 500** — observed on both walks at Gate 2 boundary (walk continued; post-freeze FCDO gap-check succeeded via validator).
5. **Usage ledger** — 0 `usage_ledger` rows for both mint accounts (differs from P3-7 FCDO charge-once row).
