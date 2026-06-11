# P3-2 — Extract-stage hang diagnosis

**Date:** 2026-06-11  
**Plan:** Phase 3 Plan v2 · P3-2 Worker recovery  
**Sighting:** [`P3-2_STALL_SIGHTINGS.md`](./P3-2_STALL_SIGHTINGS.md) #1

---

## Summary

Report `25ebfaad-7f8d-4130-978e-1c31ac52c609` on CI run [27202457869](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27202457869) (`p1_clean_docset`) hung in **extract** for ~39 minutes with no durable progress marker. The orphan reaper terminated the job with `failed_before_gate1` because liveness was inferred only from `classify.completed_at` — not from in-stage worker activity.

This was a **reliability gap**, not a moat/fence regression.

---

## Timeline (sighting #1)

| Phase | What happened |
|-------|----------------|
| Classify completes | `agent_trace_json.stages.classify.completed_at` written; cursor advances to `extract` |
| Extract runs | Long-running per-document extractors; **no** heartbeat or in-stage checkpoint |
| ~39m silence | `compute_last_progress_at` still equals classify completion |
| Reaper fires | Stage-aware extract threshold exceeded → `mark_job_failed` / `orphan_reaped` |
| Harness | Verdict `failed_before_gate1`; CI exit 0 masked failure until P1-3 honesty fix |

---

## Root cause

1. **Coarse liveness (D3 Route A):** Progress was stage-boundary only. A legitimately slow or blocked extract call looked identical to a dead worker from the reaper’s perspective.
2. **No lease/heartbeat:** `report_jobs` had no `last_heartbeat_at` / lease columns; the worker could not prove it was alive mid-stage.
3. **F-11 timeout asymmetry:** Per-agent ceilings (e.g. 90s×2) did not always bound wall-clock when the hung call never returned; the outer `ME_WORKER_JOB_TIMEOUT_SECONDS` (3600s) and reaper thresholds were the only backstops, using different semantics.
4. **Terminal-only recovery (D4):** Reaper always failed the job — work and spend were lost with no bounded requeue.

---

## Fix (P3-2)

| Change | Purpose |
|--------|---------|
| Migration `0017` — `last_heartbeat_at`, `lease_owner`, `lease_expires_at`, `requeue_count` | Durable liveness + reclaim metadata |
| Heartbeat on claim, stage entry, per-document classify/extract, checkpoints | Prevents false reap during long in-stage work |
| Lease on `claim_next_job` | Identifies owning worker; extends on heartbeat |
| Requeue bound **1** → terminal fail | Safety net for worker death; D4 remains backstop after bound |
| Degraded never requeued | Partial-failure jobs fail closed |
| Stage-boundary restart only | Requeued job resumes at current `stage`; no mid-stage artefact replay |
| F-11 unified timeout in `job_timeout.py` | Worker thread backstop uses same stage-aware budget as reaper |

---

## Verification

- Unit tests: `tests/test_p3_2_worker_recovery.py`, updated `tests/test_orphan_reaper.py`
- CI: scratch-Postgres `alembic upgrade head` (migration harness)
- Live re-run: extract stage should show advancing `last_heartbeat_at`; reaper must not abort a healthy long extract

---

## Non-goals

- Fixing underlying extractor latency (P2/P3-4 scope)
- Mid-stage resume from partial document extracts
- Reaper in API/cron without a live worker process
