# Track 3 — Phase 2 STOP 3 evidence pack (2026-07-19)

Owner-triggered witnessed walk. Execution delegated to Cursor. **Only prod mutation:** `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE` set/unset on the worker. **No fixes of any kind** — findings are evidence.

---

## Pre-flight

| Check | Result |
|-------|--------|
| PR #9 | Merged as `1a7ccde` (contains feature commit `67f94ca`) |
| Worker service | `exemplary-encouragement` — `startCommand=python -m app.reports.worker` |
| Worker deploy before flag | `SUCCESS` on `1a7ccde` |
| Web service | `ngoinfo-grantpilot` — flag key never set |

---

## Flag window

| Item | Value |
|------|-------|
| Flag | `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE` |
| Service | worker `exemplary-encouragement` only |
| Read-back start | `true` |
| Window start UTC | `2026-07-19T08:05:11.736690+00:00` |
| Window end UTC | `2026-07-19T08:46:21.812309+00:00` |
| Duration | **2470.1s** (~41.2 min) |
| Read-back end | absent / `None` (key unset) |
| Artefact | [`TRACK3_PHASE2_FLAG_WINDOW_2026-07-19.json`](TRACK3_PHASE2_FLAG_WINDOW_2026-07-19.json) |

**Window-exposure statement:** any concurrent real proposal extract on this worker would have degraded while the flag was on. Acceptable pre-launch (no live customers); re-evaluate post-launch.

---

## Audible-flag WARNING (first induced extract)

Captured from Railway worker logs during answered-branch extract:

```
proposal_extractor FAULT INJECTION ACTIVE: ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE is set — forcing timeout-degrade path (per-attempt ceiling 0.05s)
```

Artefact: [`TRACK3_PHASE2_FAULT_WARNING_CAPTURE_2026-07-19.txt`](TRACK3_PHASE2_FAULT_WARNING_CAPTURE_2026-07-19.txt)

Also mirrored in window log pull: [`TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt`](TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt) (timeout attempt=1/2 and 2/2 ceiling=0.05s lines).

---

## First prod checkpoint firing

**Induced report (answered):** `b007f125-cf33-4bba-8acf-6eccde27d063`

Full extract-stage payload (first prod observation):

[`TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json`](TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json)

| Field | Value |
|-------|-------|
| `proposal_checkpoint.degraded_code` | `DEGRADED_EXTRACTION_TIMEOUT` |
| `attempts` | 2 |
| `proposal_fault_injected` | `true` |
| `proposal_fault_flag` | `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE` |
| Job park | `awaiting_human` / `extract` |

Skip branch induced report `46fdb1b1-f03c-4266-bdfc-69ed3bbf549f` fired the same checkpoint shape (see walk log `CHECKPOINT_STATE`).

---

## Run 1 — answered branch (induced)

| Item | Value |
|------|-------|
| Report ID | `b007f125-cf33-4bba-8acf-6eccde27d063` (induced) |
| Owner | `audit-track3-p2-answered-1784448315@grantpilot-test.org` |
| Ack | `proceed_with_gap` |
| Gate 2 elevated refs | exactly `community_participation_examples`, `partner_or_local_collaboration_examples` |
| Funder-facing | yes — questions as English copy |
| Internal ID leaks | **none** (`internal_identifier_leaks: []`) |
| Answers | distinct traceable marker texts submitted for both elevated items |
| Synthesis → Gate 3 → export | **done** |
| Community provenance | claims bound with `gap:community_involvement:indicator:community_participation_examples` and `…partner_or_local_collaboration_examples` |
| Duration | **361.0s** |
| Cost | **~$0.1238** total USD |
| Evidence | [`TRACK3_PHASE2_ANSWERED_b007f125.json`](TRACK3_PHASE2_ANSWERED_b007f125.json) |

**Observation (evidence, not a fix):** walk helper `community_checks.contains_*_marker` was false on a shallow section dump, while marker strings and `gap:` provenance are present deeper in the same evidence JSON (markers counted in file; claims show `source_refs` / `evidence_used` with `gap:…`). Treat nested draft content as authoritative for provenance.

**Ops note (evidence):** first resume used a non-owner session → HTTP **404** on job GET; second resume as owner succeeded. Not a 401.

---

## Run 2 — skip branch (induced)

| Item | Value |
|------|-------|
| Report ID | `46fdb1b1-f03c-4266-bdfc-69ed3bbf549f` (induced) |
| Ack | `proceed_with_gap` |
| Gate 2 | same exact two elevated items; funder-facing; no internal ID leaks |
| Action | skip both elevated items with valid skip reasons |
| Community section | `structured_bind_status=insufficient_data`; honest “could not be drafted…” blank; empty `claims` / `evidence_used` |
| Invented narrative | absent on community section (`invented_markers_absent: true` at helper level; no TRACK3 answer markers) |
| Export | **done** |
| Duration | **564.9s** |
| Cost | **~$0.105** total USD |
| Evidence | [`TRACK3_PHASE2_SKIP_46fdb1b1.json`](TRACK3_PHASE2_SKIP_46fdb1b1.json) |
| Community inspect | [`TRACK3_PHASE2_SKIP_COMMUNITY_INSPECT.json`](TRACK3_PHASE2_SKIP_COMMUNITY_INSPECT.json) |

**Observation (evidence, not a fix):** helper top-level `community_checks.insufficient_data` was `false` while nested `structured_bind_status` is `insufficient_data`. Nested bind status is the honest signal.

---

## AUTH_REFRESH_DIAG (both runs)

| Item | Value |
|------|-------|
| Source log | [`TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log`](TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log) |
| `AUTH_REFRESH_DIAG` count | **0** |
| 401 subtype | none observed |
| Proactive refresh | not invoked |
| Reactive 401 | not invoked |
| Capture file | [`TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt`](TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt) |

Synthesis legs completed without client auth-refresh events. Instrumentation remains live.

---

## Cost / duration — Track 2 full-export baseline

| Run | Induced report | Duration | Est. total USD | Export |
|-----|----------------|----------|----------------|--------|
| Answered | `b007f125…` | 361.0s | 0.1238 | done |
| Skip | `46fdb1b1…` | 564.9s | 0.1050 | done |

These are the first Track 2 full-export baselines under induced proposal timeout-degrade + Track 3 elevation.

---

## Decision log

- Table **D-057** + narrative DECISION appended in [`ME_MODULE_DECISION_LOG.md`](../ME_MODULE_DECISION_LOG.md)
- Covers: first prod checkpoint, Track 3 prod-validation outcome, auth diagnostics, induced report IDs, window start/end, window-exposure statement

---

## Invariants held

1. Flag set/unset was the **only** prod mutation.
2. Flag was **not** active outside the declared window (read-back end absent).
3. Web service never carried the flag.
4. **No fixes** applied regardless of findings (shallow helper mismatches, 404 resume mistake, zero auth-diag lines — all evidence).

---

## STOP 3

Full evidence pack delivered above. **No further action.**
