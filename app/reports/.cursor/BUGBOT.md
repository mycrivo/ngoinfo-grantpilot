# Bugbot rules — M&E engine (app/reports)

In addition to the root rules:

- **Fixture vocabulary.** Flag any funder name, fixture organisation name, fixture phrase, or numeric "expected count" inside a prompt string, agent file, hint table, or engine module. The engine must be funder-neutral.
- **Structure source.** Flag any read of `funder_report_templates` for report structure, section lists, table columns, requirement slugs, archetypes or owner sets. Structure comes from `requirement_snapshot_json` only.
- **Model arithmetic.** Flag any prompt asking a model to compute a percentage, variance, total or difference, and any code path where a numeric value written into report content is not bound to a fact key or a `derived` fact.
- **Fact shape.** Flag writes to `knowledge_bank_json.facts` or `grants.ledger_json.facts` that omit `facet`, `period` (for measured facts), `source.kind`, or that delete a fact instead of superseding it. Flag money facts confirmed without `currency`.
- **Conflict rule.** Flag conflict detection that compares facts with different periods or scopes, and any resolution path that discards a value without `superseded_by`.
- **Single judgement.** Flag a second implementation of "is this requirement satisfied" outside the evidence matrix service.
- **Conversation actions.** Flag any code that writes conversation text into facts or answers without an action record and an echo.
- **Guidance documents.** Flag any extractor path that can consume a `funder_guidance` or `funder_feedback` document into facts.
- **Critic severity.** Flag any export or gate block on a severity other than CRITICAL, and any `accept-all` style bypass.
- **Labels.** Flag any API response from this package returning an enum, stage or status without a user-language label, or a label containing an agent, model or stage name.
