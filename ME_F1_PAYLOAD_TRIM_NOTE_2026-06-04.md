# F1 payload trim + synthesis timeout retry (2026-06-04)

**Per-section fact subsetting** (`report_inputs_builder.subset_facts_for_section`): always include `grant.*`, `reporting.*`, `objectives.*`; add generous archetype namespaces (`indicators.*` / `financials.*` from `required_tables[].data_source` and `_ARCHETYPE_FACT_PREFIXES`); match `required_indicators` tokens in fact keys. All answered `gap_answers` and full NGO/template/report envelope unchanged — only which `facts{}` entries are embedded per call.

**6643d922 regression guard:** unit test asserts the six working sections' trimmed payloads are supersets of every fact key those sections cited in `content_json.evidence_used` (fixture `tests/fixtures/synthesis/bridgelight_6643d922_cited_keys.json`).

**Timeout retry:** `openai_client` marks `category="timeout"` as `retryable=True` only when `feature="report_synthesis"`; existing `_MAX_RETRIES=1` yields exactly one retry (two attempts total). Non-synthesis timeouts stay non-retryable.

**Unchanged:** httpx client `timeout=90.0`; `MAX_CONCURRENT_SECTIONS=5`. If C/D still fail after trim, concurrency throttle is the next lever — not implemented here.
