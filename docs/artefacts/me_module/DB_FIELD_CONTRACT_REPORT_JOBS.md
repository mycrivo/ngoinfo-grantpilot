# DB_FIELD_CONTRACT_REPORT_JOBS.md

**Status:** Canonical (LOCKED — Stage B structure)  
**Applies to:** M&E Module — async pipeline execution state  
**System of Record:** Railway PostgreSQL — GrantPilot Backend  
**Owner:** M&E Module / Backend  
**Migration:** Migrations `0014_me_module_tables` + `0015_donor_reports_gap_analysis_json` applied; alembic head = `0015_gap_analysis_json`; deployed to production.

---

## 1. Purpose

This contract defines persistence for **report jobs** — async pipeline state for the M&E agent pipeline.

Each job row tracks:
- Current pipeline **stage** (classify → export)
- Execution **status** (queued, running, awaiting human, failed, done)
- **Agent trace** for inspectability and cost accounting
- Timestamps for worker lifecycle

The worker process (`app/reports/worker/`) reads/writes this table behind `run_pipeline(report_id)`.

---

## 2. Table: `report_jobs`

### 2.1 Identity

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `id` | `id` | UUID | NO | `gen_random_uuid()` | PRIMARY KEY |
| `donor_report_id` | `donor_report_id` | UUID | NO | — | FK → `donor_reports.id`, ON DELETE CASCADE |

**Rules**
- At most one **active** job per report (status ∈ `queued`, `running`, `awaiting_human`) — enforced in service layer.
- Historical completed/failed jobs may be retained for audit (append pattern) or superseded — implementation choice locked Stage C; contract allows multiple rows per report with query for latest active.

---

### 2.2 Pipeline Stage & Status

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `stage` | `stage` | TEXT | NO | `'classify'` | CHECK — ENUM_REGISTRY §5.6 |
| `status` | `status` | TEXT | NO | `'queued'` | CHECK — ENUM_REGISTRY §5.7 |

**Allowed `stage` values:**  
`classify` | `extract` | `reconcile` | `gap` | `synthesise` | `critique` | `export`

**Allowed `status` values:**  
`queued` | `running` | `awaiting_human` | `failed` | `done`

| Status | Meaning |
|--------|---------|
| `queued` | Accepted by worker; not yet started |
| `running` | Agent work in progress for current `stage` |
| `awaiting_human` | Pipeline halted at Gate 1, 2, or 3 — server-enforced |
| `failed` | Unrecoverable error; see `error` |
| `done` | Stage or full pipeline completed (context-dependent) |

**Gate mapping (informative):**

| Gate | `stage` when `awaiting_human` | Notes |
|------|-------------------------------|-------|
| Gate 1 | `gap` | After reconcile completes (`stages.reconcile` trace written); human confirms knowledge bank |
| Gate 2 | `synthesise` | After gap agent completes (`stages.gap` trace written); human answers gaps |
| Gate 3 | `export` | After critic completes (`stages.critique` trace written); human accepts sections |

---

### 2.3 Trace & Error

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `agent_trace_json` | `agent_trace_json` | JSONB | NO | `'{}'::jsonb` | Shape: §2.4 |
| `error` | `error` | TEXT | YES | NULL | Set when `status = failed` |

---

### 2.4 `agent_trace_json` shape (runtime — from orchestrator + worker)

The orchestrator appends per-stage entries via `_append_stage_trace` (`app/reports/orchestration/pipeline.py`): a **`stages` object** keyed by pipeline stage name. The worker may add top-level **`failed_stage`** (on `StageFailure`) and **`failure`** (on terminal failure — `app/reports/worker/job_failure.py`).

```json
{
  "stages": {
    "classify": {
      "completed_at": "ISO-8601",
      "document_count": 0,
      "degraded_notes": []
    },
    "extract": {
      "completed_at": "ISO-8601",
      "degraded_documents": ["uuid"]
    },
    "reconcile": {
      "completed_at": "ISO-8601",
      "degraded": false
    },
    "gap": {
      "completed_at": "ISO-8601",
      "readiness_score": 0,
      "gap_count": 0,
      "degraded": false
    },
    "synthesise": {
      "completed_at": "ISO-8601",
      "action": "synthesise_completed",
      "section_count": 0,
      "generated": 0,
      "failed": 0,
      "degraded": false,
      "gate2_confirmed_at": "ISO-8601 or null"
    },
    "critique": {
      "completed_at": "ISO-8601",
      "action": "parked_at_critique_boundary | critique_completed",
      "section_count": 0,
      "verified": 0,
      "flagged": 0,
      "unverified": 0,
      "skipped": 0,
      "critic_blocks": 0,
      "gate2_confirmed_at": "ISO-8601 or null"
    },
    "export": {
      "completed_at": "ISO-8601",
      "action": "export_boundary_not_implemented",
      "gate3_confirmed_at": "ISO-8601 or null"
    }
  },
  "failed_stage": "string (optional — worker, on StageFailure)",
  "failure": {
    "event": "pipeline_exception | pipeline_timeout",
    "message": "string",
    "at": "ISO-8601"
  }
}
```

**Rules**
- Only stages that have completed (or been parked/failed at a boundary) appear under `stages`; keys are stage names from ENUM_REGISTRY §5.6.
- Each stage value is the trace `entry` dict written by the orchestrator for that stage — field sets vary by stage (see code paths above).
- `failure` is set only when the worker marks the job `failed`.

---

### 2.5 Timestamps

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `started_at` | `started_at` | TIMESTAMPTZ | YES | NULL | Set when worker picks up job |
| `finished_at` | `finished_at` | TIMESTAMPTZ | YES | NULL | Set when job reaches terminal state |

---

## 3. Indexes

| Index | Purpose |
|-------|---------|
| `(donor_report_id, started_at DESC)` | Latest job for report |
| `(status)` WHERE `status IN ('queued', 'running', 'awaiting_human')` | Worker queue poll |
| `(donor_report_id)` | FK lookup |

---

## 4. FK Direction Rule

| This table FK | Target | Direction |
|---------------|--------|-----------|
| `donor_report_id` | `donor_reports` | M&E → M&E ✓ |

**No core table** FKs to `report_jobs`.

---

## 5. Relationship to Other Artefacts

- `DB_FIELD_CONTRACT_DONOR_REPORTS.md`
- `API_CONTRACT.md` §12.12 — `GET /api/reports/{id}/job`
- `ENUM_REGISTRY.md` §5.6, §5.7

---

## 6. Build Enforcement

- Worker MUST NOT run inside sync API request handlers.
- Pipeline MUST NOT advance past `awaiting_human` without corresponding gate confirmation in `donor_reports.knowledge_bank_json`.
- `agent_trace_json` required for cost accounting on every agent invocation.
