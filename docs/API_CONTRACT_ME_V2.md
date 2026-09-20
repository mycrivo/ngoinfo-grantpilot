# API_CONTRACT_ME_V2.md — §12 (V2) M&E Report Writer

**Status:** Canonical (LOCKED for V2 build). To be merged into `API_CONTRACT.md` as §12 v2 by P1.1; v1 endpoints listed in §12.20 remain served until the P8.4 cutover.  
**Scope:** `/api/grants*`, `/api/reports*`  
**Entitlement:** IMPACT for every endpoint in this section (unchanged). Free/Growth → `403 UPGRADE_REQUIRED`.  
**Feature flag:** unchanged (`ME_MODULE_ENABLED`; frontend flag in its repo).  
**Envelope conventions:** §12.0 v1 unchanged — single resources top-level, lists in named arrays.  
**Decisions:** D-084 … D-095

---

## 12.0a Display-label rule (D-095)

Every enum-typed value returned by a §12 endpoint is accompanied by a sibling `<field>_label` in user language. Examples: `status` / `status_label`, `report_basis` / `report_basis_label`, `extraction_status` / `extraction_status_label`, `severity` / `severity_label`. The frontend renders labels only and never maps enum values. A response with an enum and no label is a contract violation.

Labels are English (en-GB) in beta and come from one server-side map per enum.

---

## 12.1 Grants

### GET /api/grants

List the user's grants with their reports.

Response 200:
```json
{
  "grants": [
    {
      "id": "uuid",
      "funder_name": "string",
      "organisation_name": "string or null",
      "programme_title": "string or null",
      "grant_reference": "string or null",
      "grant_start": "YYYY-MM-DD or null",
      "grant_end": "YYYY-MM-DD or null",
      "ledger_version": 0,
      "reports": [
        { "id": "uuid", "report_type": "annual", "report_type_label": "Annual report", "reporting_period_start": "YYYY-MM-DD", "reporting_period_end": "YYYY-MM-DD", "status": "COMPLETE", "status_label": "Complete", "report_basis": "FUNDER_REQUIREMENTS", "report_basis_label": "Funder's own format", "updated_at": "ISO-8601" }
      ],
      "updated_at": "ISO-8601"
    }
  ]
}
```

### GET /api/grants/{id}

Grant detail: the fields above plus `ledger_summary` (counts by domain, last write) and `documents` (id, filename, classification + label). The full ledger is not returned in beta (no consumer).

Errors: 401 · 403 · 404 `GRANT_NOT_FOUND` · 500

---

## 12.2 POST /api/reports (V2 body)

Create a report. Either references an existing grant or creates one inline. `funder_report_template_id` is no longer accepted (422 if present).

Request:
```json
{
  "grant_id": "uuid or null",
  "grant": {
    "funder_name": "string — required when grant_id is null",
    "funder_website": "string or null",
    "linked_proposal_id": "uuid or null"
  },
  "report_type": "annual | quarterly | interim | final | other",
  "reporting_period_start": "YYYY-MM-DD",
  "reporting_period_end": "YYYY-MM-DD"
}
```

Response 200 (top-level ReportSummaryResponse V2):
```json
{
  "id": "uuid",
  "grant_id": "uuid",
  "funder_name": "string",
  "report_type": "annual", "report_type_label": "Annual report",
  "reporting_period_start": "YYYY-MM-DD",
  "reporting_period_end": "YYYY-MM-DD",
  "status": "DRAFT", "status_label": "Getting started",
  "report_basis": null, "report_basis_label": null,
  "requirement_confirmed_at": null,
  "version": 1,
  "created_at": "ISO-8601", "updated_at": "ISO-8601"
}
```

Errors: 401 · 403 · 404 `GRANT_NOT_FOUND` · 404 `PROPOSAL_NOT_FOUND` · 409 `PROFILE_INCOMPLETE` · 422 `VALIDATION_ERROR` · 500

Quota unchanged: `REPORT_CREATE` charged once at first `COMPLETE` (D6).

---

## 12.3 POST /api/reports/{id}/documents (V2 form)

Adds an optional `role` form field.

| Field | Type | Required |
|---|---|---|
| `file` | binary | YES |
| `role` | one of ENUM_REGISTRY §5.3 v2 values except reserved ones | NO |

- With `role`: `classification` set from it, `classification_source = user`, classifier skipped.
- `role = funder_guidance` routes the document to the requirements job and never to fact extraction.
- Response adds `classification_label`, `classification_source`, `extraction_status_label`.

Errors: v1 set + 422 `INVALID_ROLE`.

`GET .../documents` and `DELETE .../documents/{document_id}` unchanged in shape; responses gain labels; delete of a document supersedes its `facts_emitted` in the KB and is refused after a completed run (unchanged).

---

## 12.4 Reporting requirements

### POST /api/reports/{id}/requirements/resolve

Starts the requirements job: compiles the uploaded `funder_guidance` document if one exists; otherwise runs discovery on `funder_name` / `funder_website`; always prepares the generic instance as the fallback proposal.

Request: `{}` (optional `{"force_discovery": true}` to ignore an upload for testing; not exposed in the UI).

Response 200: `{ "job_id": "uuid", "stage": "requirements", "stage_label": "Reading your funder's requirements", "status": "queued", "status_label": "Queued" }`

Errors: 401 · 403 · 404 · 409 `REQUIREMENTS_LOCKED` (Gate 1 already confirmed) · 409 `ACTIVE_JOB_EXISTS` · 500

### GET /api/reports/{id}/requirements

The proposal the NGO must see before anything is applied.

Response 200:
```json
{
  "donor_report_id": "uuid",
  "requirement_version": 1,
  "proposed_basis": "FUNDER_REQUIREMENTS | GENERIC_FALLBACK",
  "proposed_basis_label": "string",
  "source": { "kind": "upload", "kind_label": "Uploaded by you", "title": "string", "url": null, "publisher_domain": null, "document_id": "uuid", "fetched_at": null, "is_official": true },
  "discovery_status": "found", "discovery_status_label": "We found your funder's reporting guidance",
  "candidates": [ { "candidate_id": "string", "title": "string", "url": "string", "publisher_domain": "string", "is_official": true, "doc_kind_guess": "reporting_template", "doc_kind_label": "Reporting template", "why": "string" } ],
  "preview": {
    "document_title": "string",
    "sections": [ { "section_key": "s01", "order": 1, "heading": "string", "owner": "ngo", "owner_label": "You complete this", "mandatory": true, "requirement_count": 3, "tables": [ { "table_key": "s01.t1", "title": "string", "columns": ["string"] } ] } ],
    "funder_completes": ["string"],
    "unmapped": [ { "text": "string", "source_location": "string" } ]
  },
  "generic_reason": "no_result | unavailable | no_document | null",
  "generic_reason_label": "string or null",
  "requirement_confirmed_at": null,
  "can_confirm": true
}
```

Errors: 401 · 403 · 404 · 409 `REQUIREMENTS_NOT_RESOLVED` (job not run yet) · 500

### POST /api/reports/{id}/requirements/confirm

Request:
```json
{ "decision": "use_proposed | use_candidate | use_upload | use_generic", "candidate_id": "string or null", "document_id": "uuid or null" }
```

- `use_candidate` fetches and compiles that candidate (may return `202` with a job to poll, then the same endpoint is called again with `use_proposed`).
- On success: `report_basis` set, `requirement_snapshot_json` frozen, `requirement_confirmed_at` set, `requirement_source_json.decision` recorded.

Response 200: same shape as GET with `requirement_confirmed_at` set.

Errors: 401 · 403 · 404 · 409 `REQUIREMENTS_LOCKED` · 422 `VALIDATION_ERROR` · 500

---

## 12.5 Gate conversations (one shape for gate1, gate2, gate3) — D-090

`{gate}` ∈ `gate1 | gate2 | gate3`. Preconditions: gate1 requires `requirement_confirmed_at` and the reconcile stage done; gate2 requires `gate1_confirmed_at`; gate3 requires critique done.

### GET /api/reports/{id}/gates/{gate}/conversation

Response 200:
```json
{
  "donor_report_id": "uuid",
  "gate": "gate1", "gate_label": "Confirm what we found",
  "turns": [
    { "turn_id": "string", "role": "assistant", "text": "string", "claims": [ { "span": "string", "fact_keys": ["string"] } ], "actions": [], "created_at": "ISO-8601" },
    { "turn_id": "string", "role": "user", "text": "string", "actions": [ { "action": "correct_value", "action_label": "Corrected a figure", "target": "finance.total.budget.grant", "echo": "Recorded the total budget as £1,240,000 (previously £1,184,000).", "applied": true, "applied_at": "ISO-8601" } ], "created_at": "ISO-8601" }
  ],
  "open_items": [ { "id": "string", "kind": "conflict | confirm_item | question | flag", "kind_label": "string", "summary": "string" } ],
  "open_items_count": 0,
  "can_confirm": false,
  "blocking_reason": "string or null — user language",
  "confirmed_at": "ISO-8601 or null"
}
```

The first assistant turn is generated server-side when the gate opens (Gate 1 summary; Gate 2 first batch of ≤4 questions; Gate 3 material flags).

### POST /api/reports/{id}/gates/{gate}/reply

Request: `{ "text": "string ≤ 4000 chars" }`

Behaviour: the reply compiler maps the text to actions (`DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md` §5.1), applies them, re-evaluates what depends on them (Gate 1: conflicts and derived facts; Gate 2: the evidence matrix; Gate 3: the affected flags), and returns the new assistant turn beginning with the echoes. A reply that maps to nothing returns a `redirect` action and an assistant turn explaining what this gate can take. No error is raised for "not understood".

Response 200: same shape as GET (full conversation).

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` (precondition) · 409 `GATE_ALREADY_CONFIRMED` · 422 `VALIDATION_ERROR` · 500

### GET /api/reports/{id}/gates/{gate}/items

The "view all" secondary list, in words.

- gate1: every fact (`fact_key`, `label`, `value` rendered as text, `unit`, `facet_label`, `period_label`, `source_label`, `confirmed`) grouped by domain and entity, plus conflicts with proposed treatment.
- gate2: every matrix item with `status_label`, the question text (if any), the answer or unavailable state, grouped by section heading.
- gate3: every flag with `severity_label`, `kind_label`, `claim_text`, `what_to_do`, section heading, accepted/resolved state.

Response 200: `{ "gate": "gate1", "groups": [ { "heading": "string", "items": [ {} ] } ] }`. No raw enum without its label; no internal key without a label beside it.

### POST /api/reports/{id}/gates/{gate}/confirm

Request: `{}` (gate3 also accepts `{ "accept_remaining": [ { "flag_id": "string", "reason": "string ≥ 10 chars" } ] }` for CRITICAL flags the NGO knowingly accepts).

Behaviour: sets the gate timestamp in `knowledge_bank_json` and mirrors it in `conversation_json`; triggers write-through to the grant ledger; advances the pipeline (gate1 → derive + evidence matrix + Gate 2 opening turn; gate2 → synthesis; gate3 → export readiness).

Response 200: `{ "gate": "gate1", "confirmed_at": "ISO-8601", "next": { "stage": "gap", "stage_label": "Checking what is still missing", "job_id": "uuid or null" } }`

Errors: 401 · 403 · 404 · 409 `GATE_NOT_SATISFIED` with `details.blocking_items[]` (each with `id`, `kind_label`, `summary`) · 500

---

## 12.6 GET /api/reports/{id} (V2 additions)

Adds to the v1 top-level object: `grant_id`, `grant` (the §12.1 grant summary fields), `report_type` + label, `report_basis` + label, `requirement_confirmed_at`, `requirement_summary` (document_title, section count, table count, source kind + label), `current_gate` + label, `status_label`, `sections[]` gains `heading`, `requirement_keys`, `table_rows`, flags with V2 severity + labels. Removes from V2 responses: `funder_report_template_id`, `template_name`, `gap_analysis_json`, `indicator_actuals_json` (present as `null` until P8.4 for compatibility, then dropped).

`GET /api/reports` (list) adds `grant_id`, `funder_name`, `report_type` + label, `report_basis` + label, `status_label`.

---

## 12.7 Pipeline job (unchanged shape, one stage added)

`POST /api/reports/{id}/job` and `GET /api/reports/{id}/job`: `stage` gains `requirements` (order 0). Every stage and status returns `stage_label` / `status_label` in user language ("Reading your documents", "Waiting for you to confirm what we found", …). No agent or model names appear in any label.

---

## 12.8 POST /api/reports/{id}/export (unchanged contract, V2 renderer)

Same request, headers, quota rules. Requires `gate3_confirmed_at`; refuses only on unresolved CRITICAL flags (`409 EXPORT_NOT_READY` with `details.critical_flags[]`). The DOCX is the V2 formatter's output (`ME_V2_MASTER_TASK_LIST.md` P7.1); filename `report-{id}-v{version}.docx`.

---

## 12.9 Section edit (unchanged) — PATCH /api/reports/{id}/sections/{key}

Unchanged shape; `human_edited` set; edits made here are the same as a Gate 3 `edit_section` action and are logged as one.

---

## 12.10 Error codes (additive to v1 §12.14)

| error_code | HTTP | When |
|---|---|---|
| `GRANT_NOT_FOUND` | 404 | Grant id invalid or not owned |
| `INVALID_ROLE` | 422 | Upload `role` not an allowed, non-reserved value |
| `REQUIREMENTS_NOT_RESOLVED` | 409 | Requirements read before the resolve job ran |
| `REQUIREMENTS_LOCKED` | 409 | Resolve/confirm after Gate 1 confirmation |
| `GATE_ALREADY_CONFIRMED` | 409 | Reply to a confirmed gate |

`TEMPLATE_NOT_FOUND` is retired with §12.1 v1.

---

## 12.20 Deprecated v1 endpoints (served until P8.4 cutover; removed post-beta)

`GET /api/report-templates` · `PATCH /api/reports/{id}/knowledge-bank` · `POST …/knowledge-bank/gate1/confirm` · `GET …/gap-check` · `PATCH …/gap-answers` · `POST …/knowledge-bank/gate2/gap-responses` · `POST …/knowledge-bank/gate3/confirm`.

`GET /api/reports/{id}/knowledge-bank` stays as a read (it is the gate1 "items" source) with labels added.

---

## Changelog

### 2026-09-06 — §12 V2 (Report Writer V2, retrofit)

Adds grants, reporting requirements (resolve / read / confirm), gate conversations (one shape, three gates), display-label rule, V2 create body, upload role, error codes. Deprecates the template catalogue and the form-style gate endpoints. No §1–§11 endpoint changed.
