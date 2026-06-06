# Full Stage-F run note — 2026-06-04

## Precondition guards

- **Production target:** https://ngoinfo-grantpilot-production.up.railway.app
- **Railway project:** NGOINfo-GrantPilot AI / production
- **Deployed SHA:** `d8dd1905ead539c80e9597c626d9b502f1c82fdd`
- **GitHub main SHA:** `d8dd1905ead539c80e9597c626d9b502f1c82fdd`
- **Four fixes present (renderer + trim/retry + concurrency):** True
- **ME_SYNTHESIS_MAX_CONCURRENCY effective:** 2

## Stage 1 — F1 synthesis

- **Wall time (s):** 422.0
- **Generated / failed:** 6 / 2
- **OpenAI tokens in/out:** 93176 / 8067
- **OpenAI HTTP posts / retries:** 11 / 5

| Section | status | failure | text_len | critic_flags | blocks |
|---------|--------|---------|----------|--------------|--------|
| summary_and_overview | FAILED | server_error | 0 | 0 | 0 |
| performance_and_conclusions | FAILED | timeout | 0 | 0 | 0 |
| detailed_output_scoring | GENERATED | None | 4792 | 0 | 0 |
| evidence_and_evaluation | GENERATED | None | 7213 | 0 | 0 |
| risk_and_safeguarding | GENERATED | None | 4559 | 0 | 0 |
| value_for_money | GENERATED | None | 3406 | 0 | 0 |
| programme_management_delivery_commercial_financial | GENERATED | None | 2496 | 0 | 0 |
| recommendations_and_actions | GENERATED | None | 1622 | 0 | 0 |

## Hard gate: **STOP**

- generated=6 failed=2 timeout_sections=['performance_and_conclusions']

Walk-forward (F2 / Gate 3 / export) **not executed** — hard gate not met.
