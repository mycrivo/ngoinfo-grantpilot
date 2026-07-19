# Track 0 - D-046 prod validation

- **Started:** 2026-07-05T22:00:59.839170+00:00
- **Finished:** 2026-07-05T23:04:57.472885+00:00
- **Base URL:** https://ngoinfo-grantpilot-production.up.railway.app
- **Backend:** `fcf35e5` | **Frontend:** `f485d56`
- **Verdict:** PARTIAL (4 pass / 2 fail)
- **JSON artefact:** `docs\artefacts\me_module\audits\dynamic_run\track0_d046_prod_validation_20260705T230457Z.json`

## Results

| Check | Pass | Detail |
|-------|------|--------|
| A1_reached_gate1 | yes | status=awaiting_human stage=gap error=None |
| A2_no_extract_checkpoint | yes | checkpoint_present=False |
| A3_proposal_not_degraded | yes | extraction_outcome='complete' |
| A4_proposal_traces_when_present | yes | {"has_traces": true, "silence_profile": true, "message_type_counts": true, "stream_completed": true, "stream_cancelled": true} |
| B0_checkpoint_hunt_retry | **no** | no checkpoint in 4 attempts |
| D0_checkpoint_hunt_proceed | **no** | no checkpoint in 4 attempts |
