# Synthesis convergence run — 2026-06-04

**Report:** `6643d922-150d-4000-b878-4025e7c9145a`

## Precondition guards

- Production: https://ngoinfo-grantpilot-production.up.railway.app
- Deploy SHA: `a6b430c8745e88cb833c226f7cf6e8588ac22c15`
- Resume (`a6b430c`) + trim + retry + concurrency fixes present: **True**
- `ME_SYNTHESIS_MAX_CONCURRENCY`: 2

## Baseline (pre-loop)

- Incomplete sections: **2**
- GENERATED (non-empty): 6
- FAILED/empty: 2
- ACCEPTED: 0
- human_edited: 0

| section_key | status | failure | text_len | human_edited |
|-------------|--------|---------|----------|--------------|
| summary_and_overview | FAILED | server_error | 0 | False |
| performance_and_conclusions | FAILED | timeout | 0 | False |
| detailed_output_scoring | GENERATED | None | 4792 | False |
| evidence_and_evaluation | GENERATED | None | 7213 | False |
| risk_and_safeguarding | GENERATED | None | 4559 | False |
| value_for_money | GENERATED | None | 3406 | False |
| programme_management_delivery_commercial_financial | GENERATED | None | 2496 | False |
| recommendations_and_actions | GENERATED | None | 1622 | False |

## Per-pass results

### Pass 1

- Incomplete: 2 → 0
- Regenerated keys: `['summary_and_overview', 'performance_and_conclusions']`
- Expected keys: `['performance_and_conclusions', 'summary_and_overview']`
- Tokens in/out: 30028 / 2924
- Wall time (s): 174.6
- Retries: 1
- Assertions — monotonic: **True**, preservation: **True**, selection: **True**

## Cumulative cost vs baseline

- Cumulative tokens in/out (all passes): **30028 / 2924**
- Reference single full pass (~8 sections, pre-resume): **~109735** input tokens

## Verdict: **PASS**


F2 / Gate 3 / export: **not run** (synthesis-only convergence proof).