# P3-3 package report — Cost truth (DYN-10)

**Package:** P3-3  
**Status:** Shipped  
**Closes:** DYN-10 in `ME_MODULE_DYNAMIC_AUDIT_2026-06-08.md`

## Shipped

- `app/reports/agents/token_usage.py` — `SdkUsageAccumulator`, `TokenUsageResolution`, `extract_token_counts`
- SDK extractors (D2/D3/D4): sub-turn `AssistantMessage.usage` aggregation; `estimated` + `cost_usd` on agent traces
- SDK query_fn paths on classifier, reconciler, gap, critic aligned to same accumulator
- Trace schemas: additive `estimated`, `cost_usd` on extraction/reconcile/gap/critic traces
- `tests/test_token_usage.py` — unit + proposal extractor integration tests
- Recorded fixtures: additive `"estimated": true` on legacy 16-token captures (P3-1 gates unaffected)

## Resolution order

1. Sum `AssistantMessage.usage` across stream (authoritative when present)
2. Sum `ResultMessage.model_usage` per model
3. Fall back to `ResultMessage.usage` — `estimated: true` when `num_turns > 1`
4. Attach `cost_usd` from `ResultMessage.total_cost_usd` when SDK supplies it

## Non-goals

- No P3-1 eval gate on token/cost values
- No retroactive re-run of live prod traces to replace `input_tokens: 16` snapshots
