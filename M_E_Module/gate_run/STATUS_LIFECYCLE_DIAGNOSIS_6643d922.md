# Status lifecycle diagnosis — `6643d922-150d-4000-b878-4025e7c9145a`

**Date:** 2026-06-04 (read-only pass)  
**Target:** Production Railway Postgres, deploy `a6b430c`  
**Scope:** `donor_reports.status` state machine vs persisted contradictions. No code/data changes.

---

## 1. Legal status set

| Source | Role |
|--------|------|
| `app/reports/models/enums.py` — `DonorReportStatus` | Python enum (ORM) |
| `alembic/versions/0014_me_module_tables.py` — `ck_donor_reports_status` | PostgreSQL CHECK (authoritative at runtime) |
| `docs/artefacts/ENUM_REGISTRY.md` §5.1 | Contract documentation |

**Full legal values (identical across all three):**

| Value | ENUM_REGISTRY §5.1 meaning |
|-------|----------------------------|
| `DRAFT` | Created; intake not started |
| `EXTRACTING` | Pipeline running pre–Gate 1 |
| `AWAITING_REVIEW` | Halted at human gate |
| `GENERATING` | Synthesis/critic running |
| `DEGRADED` | Partial section success |
| `COMPLETE` | All sections accepted; export ready |

Default at insert: `DRAFT` (`donor_reports.status` server default + `create_donor_report`).

---

## 2. De-facto state machine (every writer of `donor_reports.status`)

Only **three production modules** assign `donor_reports.status`. No other path under `app/reports/` writes this field. Pipeline orchestration (`pipeline.py`) updates **`report_jobs`** only — not `donor_reports.status`.

| # | File / function | Value set | Trigger / stage | Bumps `updated_at`? |
|---|-----------------|-----------|-----------------|---------------------|
| W1 | `donor_report_lifecycle_service.create_donor_report` | `DRAFT` | Report create (HTTP lifecycle) | **Yes** — explicit `updated_at=now` at create |
| W2 | `report_synthesis_service.synthesise_and_persist` | `DEGRADED` if `generation_summary.failed > 0` | Stage F1 synthesis commit | **No** |
| W2b | same | `DRAFT` **only if** prior status was `DEGRADED` **and** `failed == 0` | F1 synthesis full recovery | **No** |
| W3a | `report_export_service.export_and_persist` | `GENERATING` | Stage H export start (pre-render commit) | **No** |
| W3b | same | `COMPLETE` | Stage H export success | **No** |
| W3c | same | `DEGRADED` | Stage H export exception handler | **No** |

**Never written in current code:** `EXTRACTING`, `AWAITING_REVIEW` (enum + CHECK exist; no assignment). `AWAITING_REVIEW` appears only on **section** `generation_status` inside `content_json` (F2 critic path in `report_fact_safety_service.py`), not on the report row.

**`updated_at` model:** `app/reports/models/donor_report.py` — `server_default=now()` only; **no** SQLAlchemy `onupdate`. Every writer after W1 commits JSONB/status changes without touching `updated_at`.

### Derived lifecycle (report row only)

```
CREATE ──► DRAFT
              │
              │  (pipeline stages A–E, gates 1–2: no donor_reports.status change)
              │
              ▼
         F1 synthesise_and_persist
              ├── failed > 0 ──► DEGRADED
              └── failed = 0 and was DEGRADED ──► DRAFT
              │   (if status is anything else, e.g. COMPLETE, unchanged on full success)
              │
              ▼
         export_and_persist (requires gate3_confirmed_at)
              ├── start ──► GENERATING
              ├── success ──► COMPLETE   ◄── intended terminal after export
              └── failure ──► DEGRADED
```

### D-047 vs code

Decision D-047 states synthesis clears `DEGRADED → DRAFT` on full completion. **Code matches that narrow rule** but does **not** define `DRAFT` as the universal post-synthesis terminal:

- On **8/8 success** when status is already **`COMPLETE`**, synthesis **does not** move status (no branch fires).
- **`COMPLETE` is the legitimate terminal** set by export (W3b), not DRAFT. ENUM_REGISTRY §5.1: *"All sections accepted; export ready."*
- **`DRAFT` after synthesis** only applies when recovering from **`DEGRADED`**, not when replacing a prior **`COMPLETE`**.

**Parallel job state machine** (`report_jobs.stage` / `report_jobs.status`) is independent — gates halt as `awaiting_human`; export sets job `done`. Product code does not sync job cursor back from `done` when ad-hoc synthesis re-runs.

---

## 3. Timeline — `6643d922` (production DB + trace)

**Single job row** (`089cea6a-a323-4a82-af8f-d5858f7a88e5`). No additional `report_jobs` rows.

### `donor_reports` (current)

| Field | Value |
|-------|--------|
| `status` | **`COMPLETE`** |
| `created_at` | `2026-06-01T18:30:27.340003+00:00` |
| `updated_at` | `2026-06-01T18:30:27.340003+00:00` (unchanged since create) |
| `knowledge_bank_json.gate1_confirmed_at` | `2026-06-01T18:37:57.940429+00:00` |
| `knowledge_bank_json.gate2_confirmed_at` | `2026-06-01T19:03:57.203042+00:00` |
| `knowledge_bank_json.gate3_confirmed_at` | `2026-06-04T15:17:08.371437+00:00` |
| `content_json.export` | **absent** (`has_export = false`) |
| `content_json.generation_summary` | `generated: 8`, `failed: 0` (8/8 in DB now) |

### `report_jobs` (current)

| Field | Value |
|-------|--------|
| `stage` | **`critique`** |
| `status` | **`awaiting_human`** |
| `started_at` | `2026-06-01T18:30:31.289059+00:00` |
| `finished_at` | `2026-06-04T15:17:11.715540+00:00` |
| `error` | `null` |

### Unified event timeline (from `agent_trace_json.stages` + row timestamps)

| When (UTC) | Layer | Event |
|------------|-------|--------|
| 2026-06-01 18:30:27 | report | Created — `DRAFT`, `updated_at` set |
| 2026-06-01 18:30:31 | job | Enqueued — `classify` / `running` |
| 2026-06-01 18:30:47 | trace | `classify` completed (3 docs) |
| 2026-06-01 18:35:16 | trace | `extract` completed |
| 2026-06-01 18:37:45 | trace | `reconcile` completed |
| 2026-06-01 18:37:57 | KB | **Gate 1** confirmed |
| 2026-06-01 19:01:48 | trace | **Gap failure recorded** (`failed_stage: gap`, JSON parse) — superseded by later gap success |
| 2026-06-01 19:03:52 | trace | `gap` completed (readiness 11, 41 gaps) |
| 2026-06-01 19:03:57 | KB | **Gate 2** confirmed |
| *(synthesis + F2 — trace overwritten later; gate-run artefact `GATE_RUN_NOTE_2026-06-04.md` records export/awaiting_human pre Gate 3)* |
| 2026-06-04 15:17:08 | KB | **Gate 3** confirmed (`confirm_gate3`) |
| 2026-06-04 15:17:11 | trace | **`export_completed`** — `report.status → COMPLETE`, job `finished_at` set, R2 artefact written |
| 2026-06-04 19:55:20 | trace | **`synthesise_completed`** (6 generated / 2 failed) + **`parked_at_critique_boundary`** — from full Stage-F harness `run_stage1_f1`, **after** export |
| *(post-19:55, not in job trace)* | content | Convergence run (`a6b430c`) — 8/8 sections in `content_json`; no job-trace update |

**Artefact cross-check:** `GATE_RUN_NOTE_2026-06-04.md` — pre Gate 3 `DRAFT`, post export `COMPLETE` / job `done`. `FULL_RUN_NOTE_2026-06-04.md` — F1 STOP 6/8 at deploy `d8dd190`. `SYNTHESIS_CONVERGENCE_2026-06-04.md` — PASS 8/8 at `a6b430c`, synthesis-only.

---

## 4. Contradiction reconciliations

### C1 — `COMPLETE` while synthesis still had two failed sections (D-047 expects `DRAFT`)

**Verdict: Explained and consistent with the state machine (not a synthesis postcondition bug in isolation).**

- **`COMPLETE` was set by W3b** during the **2026-06-04 15:17** gate-run export (`export_and_persist`), when content still had **6 prose + 2 failed** sections (gate-run note). That is a **valid terminal transition** per code and ENUM_REGISTRY §5.1.
- The **19:55** full Stage-F harness re-ran F1 (`run_stage1_f1` → `synthesise_and_persist`) **after** export, producing **6/8** again. On deploy **`d8dd190`** (pre-`a6b430c`), synthesis **did not yet** implement `failed > 0 → DEGRADED` on the report row — so **`COMPLETE` was not downgraded**.
- The **convergence run** (`a6b430c`) brought content to **8/8** with `failed = 0`. Because status was **`COMPLETE`** (not `DEGRADED`), the W2b branch **`DEGRADED → DRAFT` did not run** — by design in current code.
- **D-047 “clear to DRAFT on full completion”** is therefore **misleading if read as universal terminal**; it only clears **`DEGRADED`**. Interpreting “post-convergence status should be `DRAFT`” against a report that **already exported to `COMPLETE`** is **not what the code implements**.

**Implication for Stage F:** `COMPLETE` reflects **an export of older 6/8 content**, not the current 8/8 `content_json`. Closing the gate requires a **fresh export** (and likely clearing stale job/gate state), not assuming `DRAFT` means “ready to walk forward.”

---

### C2 — `updated_at` frozen at 2026-06-01 despite 2026-06-04 writes

**Verdict: Explained and consistent with the state machine (operational gap, not mystery).**

- **Every 2026-06-04 write path** (synthesis, gate3 KB stamp, export, harness job mutation) **deliberately does not set `updated_at`** — only W1 does.
- The ORM column has **no `onupdate`**; PostgreSQL has **no trigger** on this table in migration `0014`.
- June 4 commits **did go through the row** (status `COMPLETE`, KB gates, `content_json`, job trace) — the timestamp simply **was never maintained** after create.

This is a **schema/implementation omission**, not evidence that writes failed or hit a different report.

---

### C3 — `gate3_confirmed_at` set vs job `critique` / `awaiting_human`

**Verdict: Explained and a genuine defect — stale job cursor from ad-hoc harness, not ambiguous Gate 3.**

| Observation | Explanation |
|-------------|-------------|
| `gate3_confirmed_at` present | Real **`confirm_gate3()`** call during **15:17 gate run**, before export. Same event referenced in export trace. |
| Job `critique` / `awaiting_human` | **Not live pipeline state.** After export had set job **`export` / `done`**, the full Stage-F script **`run_stage1_f1`** (`M_E_Module/gate_run/_execute_full_stage_f_6643d922.py` lines 237–259) **manually** rewrote the same job to **`critique` / `awaiting_human`** and overwrote trace `critique` with `parked_at_critique_boundary` — **without** clearing **`finished_at`** (still **15:17:11**). |
| Missing `critique_completed` in trace | Gate-run F2 had `critique_completed`; full-run harness **overwrote** critique trace when re-parking after re-synthesis. |
| Gate 3 stamp vs job stage | **Same gate event** (15:17 confirm); **job cursor is stale** relative to that event — harness rolled job **backward** across export completion. |

Production **`confirm_gate3`** expects job at **`export` / `awaiting_human`** for re-enqueue (`gate3_confirmation_service.re_enqueue_gate3_job`). The 15:17 run satisfied that. The 19:55 harness ** violated** the implied ordering by resetting to **`critique`** after **`COMPLETE`**.

**Not unexplained** — evidence: trace timestamps (export 15:17 before synthesise 19:55), harness source, `finished_at` orphan.

---

## 5. Summary table

| Question | Answer |
|----------|--------|
| Is `COMPLETE` legitimate terminal? | **Yes** — set by export success (W3b). Not a bug that status is `COMPLETE`. |
| Should post-convergence status be `DRAFT` per D-047? | **Only if recovering from `DEGRADED`.** After export, **`COMPLETE` persists** through later 8/8 synthesis. |
| Is Stage F “one render from closed”? | **No** — `content_json.export` was **wiped** by post-export re-synthesis (pre-resume full overwrite / no export sibling to merge). Job cursor **stale**. Need **new F2 → Gate 3 → export** on 8/8 content, not status normalization alone. |
| `updated_at` trustworthy? | **No** for “last mutation” — frozen at create unless a future writer adds `onupdate`. |

---

## 6. STOP — pass complete

State machine mapped; all three contradictions assigned verdicts above. No fixes applied.

**Evidence sources:** production SELECT (2026-06-04); `app/reports/services/{donor_report_lifecycle_service,report_synthesis_service,report_export_service}.py`; `app/reports/orchestration/pipeline.py`; `app/reports/services/gate3_confirmation_service.py`; `M_E_Module/gate_run/{GATE_RUN_NOTE,FULL_RUN_NOTE,SYNTHESIS_CONVERGENCE}_2026-06-04.md`; `ENUM_REGISTRY.md` §5.1.
