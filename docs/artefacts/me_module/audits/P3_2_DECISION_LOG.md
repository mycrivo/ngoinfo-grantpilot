# P3-2 decision log entry

**Date:** 2026-06-11  
**Supersedes:** ME_MODULE_DECISION_LOG.md entry **DECISION (2026-06-08) — P3 orphan reaper (D3 Route A, D4)**  
**Plan:** Phase 3 Plan v2 · P3-2 Worker recovery  
**Diagnosis:** [`P3_2_EXTRACT_HANG_DIAGNOSIS.md`](./P3_2_EXTRACT_HANG_DIAGNOSIS.md)

---

## Context

Live sighting #1 ([`P3-2_STALL_SIGHTINGS.md`](./P3-2_STALL_SIGHTINGS.md)): ~39m extract hang; orphan reaper aborted on classify-completed silence. D3 Route A (no migration, stage `completed_at` only) and D4 (terminal fail, no requeue) were insufficient for worker recovery.

**Disambiguation:** This entry supersedes **reaper D4** (fail-only recovery) and **D3 Route A** (no heartbeat migration). It does **not** change **stage-D4** (indicator extractor degrade path) or extractor timeout tables.

---

## Decision

1. **Migration Route B (0017):** Add `last_heartbeat_at`, `lease_owner`, `lease_expires_at`, `requeue_count` (default 0) on `report_jobs`.
2. **Liveness:** Worker updates heartbeat on claim, stage entry, per-document classify/extract loops, and stage checkpoints. Reaper `compute_last_progress_at` prefers `last_heartbeat_at` over stage `completed_at`.
3. **Lease:** `claim_next_job` sets lease owner + expiry; heartbeat extends lease (`ME_WORKER_LEASE_SECONDS`, default 120s).
4. **Requeue policy:** On stale running job, **requeue once** (`requeue_count` 0→1, `status=queued`, stage unchanged) then **terminal fail** via `mark_job_failed` / `orphan_reaped` — reaper-D4 remains backstop after bound exhausted.
5. **Degraded never requeued:** Report `DEGRADED` or stage trace with degraded markers → terminal fail only.
6. **Stage-boundary restart only:** Requeued job resumes at current `stage`; no mid-stage artefact replay.
7. **F-11 timeout unification:** `job_timeout.py` shares stage-aware budget with orphan reaper; worker thread backstop calls unified `fail_job_wall_clock_exceeded`.
8. **CI guard:** Scratch-Postgres `alembic upgrade head` in workflow before merge.

---

## Behaviour changes from superseded D3/D4

| Prior (D3 Route A + D4) | P3-2 |
|-------------------------|------|
| No migration | Alembic 0017 |
| Liveness = `started_at` + stage `completed_at` | + `last_heartbeat_at` |
| Reaper always terminal fail | Requeue bound 1, then terminal fail |
| No reclaim metadata | Lease owner + expiry on claim/heartbeat |

---

## Out of scope

- Worker infra restart policy (Railway)
- Mid-stage document-level resume
- Automatic requeue for degraded/partial-failure jobs

---

*Append reference to ME_MODULE_DECISION_LOG.md when owner merges P3-2 package.*
