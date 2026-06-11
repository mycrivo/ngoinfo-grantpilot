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
| Owner | `audit-p3_7_nlcf-1781215948@grantpilot-test.org` (timestamp from walk) |
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

1. FCDO gap set includes forbidden `progress_against_expected_results` (validator exit 2; offline replay G-forbidden fail).
2. Production FCDO export had prose but 0 tables; KB on this walk lacked `logframe_ar1_actual` facts.
3. NLCF `changes_and_next_steps` synthesis FAILED — accept-all honestly refused (P3-7 gate working as designed).
