# Bundle export discovery — `dfd17248` (2026-08-08)

Read-only observation of persisted production shapes for report
`dfd17248-9b46-48d9-8bc6-5348eab44a1c`.

**Machine-readable artefact:** [`BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json`](BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json)

## Purpose

Paths, types, cardinalities, and redacted samples only. No mapping proposal, no scoring, no adjudication reference. Free text is length/digest-redacted.

## Logical stages (present / empty / absent)

| Stage | Presence | Notes |
|-------|----------|-------|
| knowledge_bank | present | `knowledge_bank_json` object, 13 root keys |
| gaps | present | `gap_analysis_json` object, 9 root keys; items under `gaps[]` |
| content | present | `content_json` with `sections`, `generation_summary`, `export` |
| export | present | `content_json.export` object with `storage_ref` (DOCX bytes not fetched) |
| job_trace | present | latest `report_jobs.agent_trace_json` |
| indicator_actuals | empty | `indicator_actuals_json` is `{}` |

Latest job: stage `export`, status `done`.

## Root keys observed (shape only)

- **knowledge_bank_json:** `schema_version`, `facts`, `conflicts`, `gap_answers`, `gate1_confirmed_at`, `gate2_confirmed_at`, `gate3_confirmed_at`, `reconciled_at`, `reconciler_agent`, `reconciliation_outcome`, `reconciliation_version`, `unreadable_sources`, `agent_trace`
- **gap_analysis_json:** `schema_version`, `gaps`, `open_items_count`, `ready_for_gate2`, `readiness_basis`, `report_context`, `gap_agent`, `analyzed_at`, `agent_trace`
- **content_json:** `sections` (array), `generation_summary`, `export`
- **content_json.sections[0]:** includes nested `content` (`text` redacted, `claims`, `assumptions`, …), `archetype`, `constraints_applied`, …
- **gap_analysis_json.gaps[0]:** `item_key`, `section_key`, `section_label`, `question` (redacted), `rationale` (redacted), `severity`, `owner`, …

## Owner gate

Discovery is complete. **Do not author the production→ScoreableBundle mapping or the export/scorecard until the owner releases this gate** after reviewing the JSON artefact.

Script (re-runnable, owner-triggered): `scripts/audit/bundle_export_discovery.py --railway`
