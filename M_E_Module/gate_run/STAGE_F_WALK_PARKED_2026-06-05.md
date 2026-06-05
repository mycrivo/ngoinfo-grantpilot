# Stage F walk — parked 2026-06-05

Handoff for a clean next-session start. **No further work on fixture `1c9f7ffa` or gap output-size this session.**

## (a) Proven and shipped

| Item | Status |
|------|--------|
| Engine does not fabricate (critic BLOCK path) | Proven on prior walks |
| Resumable synthesis (D-047 merge, not overwrite) | Shipped `a6b430c` |
| Gate 1 end-to-end via real API/orchestrator | Proven on pristine fixture creation + confirm |
| **E3 gap-agent JSON transport retry** | **Shipped — commit `1c6452a`** |
| **POST `/job` failed-gap reclaim** | **Shipped — same commit** |

**Retry + reclaim (this commit):**

- `MAX_GAP_COMPLIANCE_ATTEMPTS=2` — E1-style for-loop in `gap_compliance_agent.py`; one retry on `STOP_PARSE_FAILED` / `STOP_NO_RESULT`; loud fail-closed with both raw snippets on double failure; `attempt_count` on `gap_analysis_json.agent_trace`.
- `enqueue_report_job` — 409 on `queued` / `running` / `awaiting_human`; reclaims only `failed` + `gap` + `gate1_confirmed_at`; resumes at failed stage; clears `error` / `finished_at` / failure trace; no spurious `classify` row.

Unit tests: `tests/test_gap_compliance_agent.py` (retry), `tests/test_report_lifecycle_routes.py` (reclaim, no hijack of awaiting_human).

## (b) Open blocker — E3 gap output-size defect

**Not fixed by the transport retry.** Separate launch blocker for next session.

On the large FCDO checklist, the gap agent persistently fails even after one retry:

| Attempt | Failure mode | Raw head (evidence) |
|---------|--------------|---------------------|
| 1 | Truncated JSON — `Unterminated string starting at: line 411 column 19 (char 33091)` | `{"readiness_score": 11, "gaps": [{"item_key": "summary_and_overview:indicator:overall_progress", ...` (cuts off mid-question string, ~33k chars) |
| 2 | Prose, not JSON — `Expecting value: line 1 column 1 (char 0)` | `"I'll systematically check each checklist item against the knowledge bank, applying the satisfaction rules strictly.\n\n**Satisfaction check:**..."` |

Observed on resume run 2026-06-05 after retry+reclaim deploy. Artefact: `STAGE_F_GAP_RESUME_RESULT.json`.

The retry addresses empty/non-JSON **transport flakes** only; it does not address checklist size, output token ceiling, or model dropping to reasoning prose.

## (c) Next action (next session, read-only first)

Run a **read-only diagnostic** of E3 output-size handling before any code change:

1. Is the full FCDO checklist sent in one prompt call?
2. Is `MAX_OUTPUT_TOKENS` (8192) sufficient for the gap list cardinality?
3. Should gap analysis be decomposed into smaller calls (by section or batch)?

Use a **fresh fixture** — not `1c9f7ffa`. Real product paths only.

## (d) Fixture rule

Drive Stage F only through **real product paths** (API mint → create report → upload → POST job → poll → gate confirms). **Never** `M_E_Module/gate_run/_execute_*` harness scripts or manual job/KB/cursor writes. Out-of-path runs contaminated both `6643d922` and `1c9f7ffa`.

---

## Abandoned fixture — `1c9f7ffa-9853-40e7-86c2-5c9e41300be6`

**Do not reuse for Stage F walk.**

| Field | Value |
|-------|--------|
| Tag | `stage-f-validation-2026-06-05` |
| Primary job | `e9e8adaf-d72c-4fef-bba9-52769221dd70` — terminal `gap` / `failed` (post-retry persistent gap failure) |
| Spurious jobs (terminal, do not advance) | `c16ccb58` (`reconcile` / `failed`), `1f26c2dc` (`extract` / `failed`) |
| KB state (contaminated) | ~71 facts; **1** unresolved OP3.3 unit-representation conflict; Gate 1 re-stamped `2026-06-05T13:25:26Z` after spurious reconcile overwrote original 59-fact / 11-resolved bank |
| `donor_reports.status` | `DRAFT` |
| Gate 2 | Not reached — no `gap_analysis_json` |

Left as-is. No restore, no re-run, no advance.
