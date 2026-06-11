# P3-1 package report — Eval harness + FCDO gates

**Package:** P3-1  
**Status:** Shipped  
**Commit:** `bd72572`  
**CI:** smoke [27342062753](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27342062753), offline-replay [27342064122](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27342064122)

## Shipped

- Content-keyed eval modules: `citation_pr`, `gap_pr`, `output_rubric`, `gates`, `fixtures`, `offline_replay`
- `tests/test_p3_eval_harness.py` — 7 named gates (incl. G-charge-once, G-honest-exit)
- `scripts/audit/offline_replay.py` CLI
- Smoke extension + `p3-offline-replay.yml` (push/schedule)
- CP-2: `P3_1_NLCF_GOLDEN_PROPOSAL.md`
- Gate3 fix: `get_or_create_user_plan` timestamps + orchestrator IMPACT plan seed
- Honest exit: `p0-audit-walk` PIPESTATUS check

## Commits

- (this commit)

## Fence judgments

- Anti-bent-ruler: all assertions content-keyed; no token/cost/timestamp gates
- NLCF gates proposal-only per CP-2
