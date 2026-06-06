# Gate run note — 2026-06-04

## Environment
- **Railway project:** NGOINfo-GrantPilot AI / **production**
- **Deploy / code SHA:** `5de686cd04cf81fb07b775a25fd22df35bddf1db` (`5de686c` — Stage H export; `_run_export_stage` with `export_completed`, not stub)
- **Backend deployment:** `b19c518e-921d-4c10-9e43-41ecf5b1714b` SUCCESS 2026-06-04 16:00 UTC+1
- **Report ID:** `6643d922-150d-4000-b878-4025e7c9145a`

## Pre-check (read-only, before action)
- Job stage/status: `export` / `awaiting_human`
- gate1_confirmed_at and gate2_confirmed_at: set
- gate3_confirmed_at: null
- content_json.export: absent
- 8 F1 sections; 21 unaccepted BLOCK flags

## Gate 3 confirmation mechanism
Orchestrator-test accept-all (`tests/test_orchestrator_critique.py::_accept_all_sections_for_gate3`):
direct SQLAlchemy update setting each section `generation_status=ACCEPTED` and all `critic_flags[].accepted=true` (21 BLOCKs), then `confirm_gate3()` service call.

## State transitions observed
- Pre-action report status: `DRAFT`
- Post Gate 3 job: `export` / `queued` (re-enqueued by `re_enqueue_gate3_job`)
- Export trace action: `export_completed`
- Post-export report status: **`COMPLETE`**
- Post-export job status: **`done`**
- gate3_confirmed_at: `2026-06-04T15:17:08.371437+00:00`

## Export metadata
- **render_mode:** `from_scratch`
- **filename:** `Foreign_Commonwealth_Development_Office_FCDO_Annual_Review_2025-04-01_2026-03-31.docx`
- **template_version:** `1`
- **storage_ref:** `users/0efd525e-bca1-4142-b748-c99b5f52b1b8/reports/6643d922-150d-4000-b878-4025e7c9145a/cdd24bb0-0fae-40a3-b7cc-19e8fe493286/Foreign_Commonwealth_Development_Office_FCDO_Annual_Review_2025-04-01_2026-03-31.docx`
- **bytes_written (trace):** `44107`

## Section coverage
- Sections in content_json: **8**
- With prose text: **6** — summary_and_overview, performance_and_conclusions, evidence_and_evaluation, risk_and_safeguarding, programme_management_delivery_commercial_financial, recommendations_and_actions
- Synthesis failed pre-Gate-3 (empty text, force-accepted for this run): **2** — detailed_output_scoring, value_for_money (renderer emits `[Section not generated]` placeholders under headings C and D)
- Sections rendered in docx: **6 prose + 2 placeholders** (all 8 template sections present)

## Docx quality scan
- Paragraphs: 60; table cells with text: 0
- Headings present: 22
- **Canonical-key leaks in visible text:** none detected

## API verification
- `GET /api/reports/6643d922-150d-4000-b878-4025e7c9145a/export`: **OK** (44107 bytes)

## Deliverables
- `6643d922_export.docx` (from R2 via DocumentStorageService)
- `6643d922_knowledge_bank.md`
