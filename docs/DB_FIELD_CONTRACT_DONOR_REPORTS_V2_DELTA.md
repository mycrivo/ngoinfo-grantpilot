# DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md

**Status:** Canonical (LOCKED for V2 build) — applies **on top of** `DB_FIELD_CONTRACT_DONOR_REPORTS.md` v1. Where they conflict, this delta wins.  
**Applies to:** M&E Module — Report Writer V2  
**Migration:** same revision as `grants` (additive). Nothing is dropped.  
**Decisions:** D-084, D-085, D-086, D-087, D-090, D-091, D-092, D-094

---

## 1. What changes

| v1 | V2 |
|---|---|
| Report bound to one `funder_report_templates` row | Report bound to a **grant** and carries its own immutable **requirement snapshot** |
| `funder_report_template_id` NOT NULL | **Nullable**, deprecated; not set by V2 create; no engine read from P3 on (D-094) |
| Gap analysis as a slug checklist (`gap_analysis_json`) | **Requirement → Evidence matrix** (`evidence_matrix_json`); `gap_analysis_json` deprecated, kept readable |
| Gates as forms with separate confirm endpoints | Gates as **conversations** logged in `conversation_json`; confirmation timestamps unchanged |
| Critic severity `BLOCK | WARN` | `CRITICAL | IMPORTANT | SUGGESTION` (D-092) |
| Cover fields from profile and create form | Cover fields from **confirmed facts** via the grant projections |

---

## 2. New columns on `donor_reports`

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `grant_id` | `grant_id` | UUID | YES* | NULL | FK → `grants.id`, ON DELETE RESTRICT. *NULL only for pre-V2 rows until backfill; V2 create sets it |
| `report_type` | `report_type` | TEXT | YES | NULL | CHECK: `annual | quarterly | interim | final | other` |
| `report_basis` | `report_basis` | TEXT | YES | NULL | CHECK: `FUNDER_REQUIREMENTS | GENERIC_FALLBACK`; NULL until requirements confirmed |
| `requirement_snapshot_json` | `requirement_snapshot_json` | JSONB | NO | `'{}'::jsonb` | Shape: `REPORT_REQUIREMENT_SNAPSHOT_SCHEMA.md` |
| `requirement_source_json` | `requirement_source_json` | JSONB | NO | `'{}'::jsonb` | Shape: §3 |
| `requirement_confirmed_at` | `requirement_confirmed_at` | TIMESTAMPTZ | YES | NULL | Snapshot immutable from this moment |
| `requirement_version` | `requirement_version` | INTEGER | NO | `0` | Incremented on each (re-)resolve before confirmation |
| `evidence_matrix_json` | `evidence_matrix_json` | JSONB | NO | `'{}'::jsonb` | Shape: §4 |
| `conversation_json` | `conversation_json` | JSONB | NO | `'{}'::jsonb` | Shape: §5 |

**Changed constraint:** `funder_report_template_id` → NULL allowed. Existing FK and index retained.

**Naming:** `_json` suffix, no aliasing — unchanged rule.

---

## 3. `requirement_source_json` shape

```json
{
  "kind": "upload | web_official | web_candidate | generic | none",
  "discovery_status": "not_run | running | found | no_result | unavailable",
  "document_id": "uuid or null — uploaded_documents.id when kind = upload",
  "url": "string or null",
  "title": "string or null",
  "publisher_domain": "string or null",
  "is_official": "boolean or null",
  "fetched_at": "ISO-8601 or null",
  "confidence": "number 0–1 or null",
  "candidates": [
    {
      "candidate_id": "string",
      "url": "string",
      "title": "string",
      "publisher_domain": "string",
      "is_official": true,
      "doc_kind_guess": "reporting_template | grantee_guidance | proposal_form | funder_annual_report | other",
      "score": 0.0,
      "fetched_at": "ISO-8601 or null",
      "why": "one sentence, in user language"
    }
  ],
  "decision": {
    "kind": "use_proposed | use_candidate | use_upload | use_generic | null",
    "candidate_id": "string or null",
    "document_id": "uuid or null",
    "decided_at": "ISO-8601 or null"
  },
  "generic_reason": "no_document | no_result | unavailable | user_choice | null",
  "resolver_version": "string"
}
```

**Rules (D-086)**
- Precedence when resolving: `upload` → `web_official` → `web_candidate` → `generic`. A `web_candidate` (non-official domain) is never proposed as the default; it is listed and requires an explicit `use_candidate` decision.
- `unavailable` (provider failure) is a state, not an error: the proposal returned to the NGO is `generic` with `generic_reason = unavailable` and the upload path remains open.
- The chosen document is fetched and stored as an `uploaded_documents` row with role `funder_guidance` and `classification_source = system`, so provenance and re-reads are the same as for an upload.

---

## 4. `evidence_matrix_json` shape (D-091)

One item per requirement and per required table in the confirmed snapshot. The **single** satisfaction judgement: Gate 2 questions, synthesis eligibility, disclosures and critic traceability all read this object; none re-judges.

```json
{
  "schema_version": "1.0.0",
  "snapshot_version": 0,
  "ledger_version_seen": 0,
  "evaluated_at": "ISO-8601",
  "judge": { "model_used": "string", "latency_ms": 0, "input_tokens": 0, "output_tokens": 0 },
  "items": [
    {
      "requirement_key": "s03.r1",
      "section_key": "s03",
      "table_key": "string or null",
      "status": "satisfied | partial | missing | answered | unavailable | funder_owned | not_applicable",
      "evidence": ["fact_key"],
      "missing": "plain-language description of what is absent, or null",
      "question": {
        "question_id": "string",
        "text": "plain language; names the missing thing; quotes the period comparator when one exists",
        "comparator_fact_key": "string or null",
        "priority": 1,
        "asked_in_turn": "turn_id or null",
        "answered_by": "answer_id or null"
      },
      "disclosure": "the sentence the writer will use if this stays unavailable, or null",
      "output_location": { "section_key": "s03", "table_key": "string or null" },
      "judged_at": "ISO-8601"
    }
  ],
  "summary": { "total": 0, "satisfied": 0, "partial": 0, "missing": 0, "answered": 0, "unavailable": 0, "funder_owned": 0, "not_applicable": 0 }
}
```

**Status rules**
- `satisfied` — confirmed evidence covers the requirement. A `target` never satisfies a requirement for an `actual`; a money fact with null currency never satisfies a finance requirement.
- `partial` — some evidence; `missing` names the remainder; a question is generated for the remainder.
- `missing` — no evidence; question generated.
- `answered` — the NGO's Gate 2 answer wrote a fact; `evidence` now includes it.
- `unavailable` — the NGO said not available; `disclosure` is set and **must** be used by the writer verbatim or near-verbatim.
- `funder_owned` — the funder completes it; never asked, never written.
- `not_applicable` — the snapshot marks the requirement as not applying to this report type.

The matrix is re-evaluated after Gate 1 confirmation and after each Gate 2 reply; `ledger_version_seen` records what it saw. `readiness_score` and `ready_for_gate2` from v1 are **removed**: Gate 2 is satisfied when no `missing`/`partial` item with `mandatory = true` remains unanswered or un-declared-unavailable.

---

## 5. `conversation_json` shape (D-090)

```json
{
  "schema_version": "1.0.0",
  "gates": {
    "gate1": {
      "turns": [
        {
          "turn_id": "string",
          "role": "assistant | user",
          "text": "string — assistant summaries are claim-bound like report prose",
          "claims": [ { "span": "string", "fact_keys": ["fact_key"] } ],
          "actions": [ { "...": "Action object — §5.1" } ],
          "created_at": "ISO-8601"
        }
      ],
      "open_items": ["conflict_id | fact_key | question_id | flag_id"],
      "confirmed_at": "ISO-8601 or null"
    },
    "gate2": { "turns": [], "open_items": [], "confirmed_at": null },
    "gate3": { "turns": [], "open_items": [], "confirmed_at": null }
  }
}
```

### 5.1 Action object

```json
{
  "action": "confirm_fact | correct_value | clarify_period | resolve_conflict | keep_both | add_fact | answer | not_available | accept_flag | correct_claim | edit_section | redirect | none",
  "target": "fact_key | conflict_id | question_id | flag_id | section_key | null",
  "payload": { "value": "any", "period": {}, "scope": "string", "text": "string", "fact_key_written": "string" },
  "applied": true,
  "echo": "one sentence in user language stating exactly what was recorded",
  "applied_at": "ISO-8601"
}
```

**Rules**
- The reply compiler maps a user turn to zero or more actions. Every applied action produces an `echo`; the next assistant turn begins with the echoes. A reply that maps to nothing produces a `redirect` action with a plain explanation of what this gate can take.
- Actions are the only path by which a conversation mutates the knowledge bank. No free text is stored as a fact.
- Gate 1 assistant summaries are generated prose and therefore claim-bound: every number, date and name in them carries `fact_keys`. A summary containing an unbound number is invalid.
- Gate 2 assistant turns contain at most **four** `question_id`s (D-090).
- `gate1_confirmed_at`, `gate2_confirmed_at`, `gate3_confirmed_at` in `knowledge_bank_json` remain the pipeline's gate timestamps; `conversation_json.gates.*.confirmed_at` mirrors them.

### 5.2 Gate 1 confirm items that are not facts

Two system-generated confirm items appear in the Gate 1 summary whenever they apply and must be resolved by an action:
- **Organisation identity:** profile organisation ≠ organisation named in the award/agreement → `resolve_conflict` on `organisation.name`.
- **Reporting period:** period entered at report creation ≠ contractual period read from the award/agreement for this report type → `clarify_period`.

Neither the profile nor the create form is a fact source for the cover (D-084 §2.2 of the grants contract).

---

## 6. `content_json` additions (V2)

Section objects gain:

```json
{
  "section_key": "s03",
  "requirement_keys": ["s03.r1", "s03.r2"],
  "table_rows": [
    {
      "table_key": "s03.t1",
      "rows": [ { "cells": [ { "text": "string", "fact_key": "fact_key or null" } ] } ],
      "empty_reason": "string or null — the honest sentence when no facts exist"
    }
  ],
  "disclosures_used": ["requirement_key"],
  "inputs_ref": "string — pointer to the persisted per-section input bundle for audit",
  "critic_flags": [
    {
      "flag_id": "string",
      "claim_text": "string",
      "severity": "CRITICAL | IMPORTANT | SUGGESTION",
      "kind": "unsupported | number_mismatch | date_mismatch | wrong_period | contradiction | omission | requirement_unmet | style",
      "expected": "any or null", "found": "any or null",
      "fact_keys": ["fact_key"],
      "what_to_do": "one sentence in user language",
      "accepted": false, "accepted_at": null,
      "resolved_by_action": "action id or null"
    }
  ]
}
```

- `table_rows` is the **structured** channel for required tables (replaces KB-binding). Every cell that states a value carries a `fact_key`; free-text cells carry null.
- Severity meanings: CRITICAL blocks export until resolved or explicitly accepted with a reason; IMPORTANT and SUGGESTION never block. `accept-all` is removed.
- `generation_summary.critic_blocks` counts CRITICAL only.

---

## 7. Status and stage (unchanged enums, one addition)

- `donor_reports.status` unchanged.
- `report_jobs.stage` gains `requirements` (order 0: discovery + compilation). Derived-number computation is not a stage; it runs at the end of `reconcile` and after every ledger mutation.
- V1 §2.4's `export → COMPLETE` rule stands; the honest-status carry-through fix stays post-beta as recorded.

---

## 8. Deprecations (kept readable, not written by V2)

| Item | Status |
|---|---|
| `funder_report_template_id` | nullable; V2 create leaves NULL; no read from P3 onward |
| `gap_analysis_json` | not written by V2; `evidence_matrix_json` replaces it |
| `indicator_actuals_json` | not written by V2; facts carry facets and periods |
| Gate endpoints `12.5`, `12.5a`, `12.6`, `12.7`, `12.7a`, `12.8a` | served until P8.4 cutover; removed post-beta |

---

## 9. Indexes (additions)

| Index | Purpose |
|---|---|
| `(grant_id, reporting_period_start DESC)` | Reports for a grant |
| `(user_id, report_basis)` | Beta instrumentation |

---

## 10. Build Enforcement

Invalid and must not be merged:
- V2 create requiring or reading `funder_report_template_id`;
- any stage after P3 reading `funder_report_templates`;
- synthesis starting without `requirement_confirmed_at`;
- a Gate 2 assistant turn with more than four questions;
- a Gate 1 assistant summary with an unbound number, date or name;
- a fact written from conversation text without an action record;
- a critic flag without `what_to_do`;
- export blocked by any severity other than CRITICAL.
