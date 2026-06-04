# F1 payload trim + synthesis timeout retry (2026-06-04)

**Per-section fact subsetting** (`report_inputs_builder.subset_facts_for_section`): always include `grant.*`, `reporting.*`, `objectives.*`; add generous archetype namespaces (`indicators.*` / `financials.*` from `required_tables[].data_source` and `_ARCHETYPE_FACT_PREFIXES`); match `required_indicators` tokens in fact keys. All answered `gap_answers` and full NGO/template/report envelope unchanged — only which `facts{}` entries are embedded per call.

**6643d922 regression guard:** unit test asserts the six working sections' trimmed payloads are supersets of every fact key those sections cited in `content_json.evidence_used` (fixture `tests/fixtures/synthesis/bridgelight_6643d922_cited_keys.json`).

**Timeout retry:** `openai_client` marks `category="timeout"` as `retryable=True` only when `feature="report_synthesis"`; existing `_MAX_RETRIES=1` yields exactly one retry (two attempts total). Non-synthesis timeouts stay non-retryable.

**Concurrency (2026-06-04 follow-up):** F1 section parallelism reduced **5 → 2** (`ME_SYNTHESIS_MAX_CONCURRENCY`, default `2`). Tunable without redeploy via env; expect longer wall time (~4 batches vs ~2 for 8 sections) but fewer parallel OpenAI calls crossing the 90s wall.

**Unchanged:** httpx client `timeout=90.0`; synthesis timeout retry (`_MAX_RETRIES=1`); per-section payload trim; F1 output schema.
