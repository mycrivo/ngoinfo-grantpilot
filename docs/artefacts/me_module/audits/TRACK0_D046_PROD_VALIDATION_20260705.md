# Track 0 — D-046 prod validation (final)

- **Date:** 2026-07-05 (UTC)
- **Base URL:** https://ngoinfo-grantpilot-production.up.railway.app
- **Frontend:** https://grantpilot.ngoinfo.org
- **Backend commit:** `fcf35e5`
- **Frontend commit:** `f485d56`
- **Verdict:** **PARTIAL PASS** — happy path + instrumentation verified in prod; checkpoint halt / retry / proceed not observed (no natural dual-fail under 180s ceiling)

---

## Summary

| Case | Description | Prod result |
|------|-------------|-------------|
| **A** | Happy path → Gate 1, no checkpoint | **PASS** |
| **B** | Checkpoint halt (`EXTRACT` + `awaiting_human`) | **Not observed** |
| **C** | Retry re-enqueue clears checkpoint | **Not observed** |
| **D** | Proceed with gap → Gate 1 + unreadable_sources | **Not observed** |
| **E** | Trace instrumentation on live extraction | **PASS** (via Case A) |
| **F** | Ack API deployed | **PASS** (404 smoke) |

Checkpoint paths (B–D) are covered by CI (`tests/test_proposal_extraction_checkpoint.py`, frontend vitest) but did not fire in prod during this walk because proposal extraction succeeded on first attempt in all completed runs after the 180s ceiling deploy.

---

## Case A — Happy path (PASS)

**Report:** `1062cce7-e6ef-4e9d-8906-88a3f42888ed`  
**User:** `track0-d046-happy-1783288859@grantpilot-test.org`  
**Template:** FCDO (full 3-file docset)

| Check | Result | Evidence |
|-------|--------|----------|
| Reached Gate 1 | PASS | `status=awaiting_human`, `stage=gap` |
| No extract checkpoint | PASS | `proposal_checkpoint` absent from job trace |
| Proposal not degraded | PASS | `extraction_outcome=complete` |
| D-046 trace fields | PASS | See below |

**Live proposal attempt trace (attempt 1):**

```json
{
  "attempt_number": 1,
  "outcome": "complete",
  "wall_clock_ms": 98150,
  "timeout_ceiling_seconds": 180.0,
  "silence_profile": "none",
  "message_type_counts": {
    "UserMessage": 1,
    "ResultMessage": 1,
    "SystemMessage": 1,
    "AssistantMessage": 5
  },
  "stream_completed": true,
  "stream_cancelled": false
}
```

**Interpretation:** Mode C stream fix + 180s ceiling working — proposal completed in ~98s on first attempt with full instrumentation persisted. Pre-D-046 bench at 90s showed ~40–60% first-attempt timeout; this run is consistent with Mode B improvement.

---

## Cases B–D — Checkpoint hunt (not observed)

**Method:** Automated hunt via `scripts/audit/track0_d046_prod_validation.py`  
**Runs:** 9 full-docset enqueues + 2 proposal-only enqueues (supplemental, queue-limited)

| Outcome | Count |
|---------|-------|
| Reached Gate 1 (proposal succeeded) | 6 |
| Timed out while queued / in reconcile | 5 |
| `EXTRACT` + `awaiting_human` + `proposal_checkpoint` | **0** |

**DB query (post-walk):** zero rows with `proposal_checkpoint` in `report_jobs.agent_trace_json`.

**Why checkpoint did not appear (expected, not a regression):**

1. **180s ceiling (D-046 WS2)** — dual-fail (both attempts timeout) is now rarer; happy-path first-attempt success is the intended outcome.
2. **Hunt batch queue pressure** — multiple concurrent track0 reports queued behind worker; several hunts timed out at poll ceiling before extract finished (operational noise, not product failure).
3. **Pre-deploy baseline** — prod report `7cc6412b` had dual-fail under 90s; that behaviour should be less frequent post-`fcf35e5`.

**Follow-up:** Re-run Cases B–D when a prod report naturally hits checkpoint, or use a dedicated staging env with a lower `ME_PROPOSAL_TIMEOUT_SECONDS` for inducement only.

---

## Case F — Ack endpoint smoke (PASS)

`POST /api/reports/{id}/jobs/proposal-checkpoint/ack` on happy-path report (no checkpoint):

- **Status:** 404
- **Body:** `CHECKPOINT_NOT_FOUND` — confirms route is mounted on prod after `fcf35e5`.

---

## Frontend (deploy sanity)

| Check | Result |
|-------|--------|
| Railway `grantpilot-frontend` | Online after `f485d56` |
| `/reports/{id}/reading` HTTP | 200 |
| Checkpoint UI contract | Unit tests (`lib/proposal-checkpoint.test.ts`, routing test) — 11 vitest passing at deploy |

Manual browser verification of checkpoint UI was **not performed** (no prod report reached checkpoint state).

---

## CI cross-check (same commits as prod)

GitHub Actions on `fcf35e5` push:

- **Smoke Test** — success (includes `test_proposal_extractor_agent.py`, `test_proposal_extraction_checkpoint.py`)
- **P3 Offline Replay** — success

---

## Artefacts

| File | Description |
|------|-------------|
| `docs/artefacts/me_module/audits/dynamic_run/track0_d046_prod_validation_20260705T230457Z.json` | Machine-readable walk log (Case A pass + hunt failures) |
| `scripts/audit/track0_d046_prod_validation.py` | Reusable prod validation script |

---

## Track 0 exit criteria vs outcome

| Criterion | Met? |
|-----------|------|
| Happy path without checkpoint | **Yes** |
| Checkpoint UI on real timeout | **No** (no dual-fail observed) |
| Retry / proceed flows in prod | **No** (blocked on checkpoint) |
| Trace fields on live extraction | **Yes** |
| Recorded audit artefact | **Yes** (this file) |

**Recommendation:** Accept D-046 prod deploy for happy path + instrumentation. Treat B–D as **deferred prod confirmation** — monitor for first natural checkpoint (Track 2 metrics) or re-run hunt after worker queue is idle with `PROPOSAL_ONLY_HUNT=1` and extended poll window.
