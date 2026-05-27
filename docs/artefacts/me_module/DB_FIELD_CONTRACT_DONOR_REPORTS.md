# DB_FIELD_CONTRACT_DONOR_REPORTS.md

**Status:** Canonical (LOCKED — Stage B structure)  
**Applies to:** M&E Module — Donor Report Writer  
**System of Record:** Railway PostgreSQL — GrantPilot Backend  
**Owner:** M&E Module / Backend  
**Migration:** `alembic/versions/0014_me_module_*.py` (Stage C — not yet applied)

---

## 1. Purpose

This contract defines persistence for **donor reports** — the post-award equivalent of `proposals`.

A donor report:
- Belongs to exactly one user
- Is bound to one funder report template
- May optionally link to a GrantPilot proposal (`linked_proposal_id`)
- Holds the reconciled knowledge bank, indicator actuals, and generated section content
- Supports partial success via `DEGRADED` status (inherited from proposal product)

No other table may store generated report content or knowledge-bank state.

---

## 2. Table: `donor_reports`

### 2.1 Identity & Ownership

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `id` | `id` | UUID | NO | `gen_random_uuid()` | PRIMARY KEY |
| `user_id` | `user_id` | UUID | NO | — | FK → `users.id`, ON DELETE CASCADE |

**Rules**
- Only the owning `user_id` may read or mutate a report (403 otherwise).
- Core table `users` is never altered for M&E; FK points inward only.

---

### 2.2 Template & Grant Link

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `funder_report_template_id` | `funder_report_template_id` | UUID | NO | — | FK → `funder_report_templates.id`, ON DELETE RESTRICT |
| `linked_proposal_id` | `linked_proposal_id` | UUID | YES | NULL | FK → `proposals.id`, ON DELETE SET NULL |

**Rules**
- `linked_proposal_id` is set when the grant was won via GrantPilot; NULL for Path C (won elsewhere).
- Deleting a proposal clears the link; the report persists.

---

### 2.3 Reporting Period

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `reporting_period_start` | `reporting_period_start` | DATE | NO | — | — |
| `reporting_period_end` | `reporting_period_end` | DATE | NO | — | MUST be ≥ `reporting_period_start` |

---

### 2.4 Lifecycle Status

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `status` | `status` | TEXT | NO | `'DRAFT'` | CHECK — see ENUM_REGISTRY §5.1 |

**Allowed values:** `DRAFT` | `EXTRACTING` | `AWAITING_REVIEW` | `GENERATING` | `DEGRADED` | `COMPLETE`

| Status | Meaning |
|--------|---------|
| `DRAFT` | Created; intake not started or documents not yet submitted |
| `EXTRACTING` | Background pipeline running classify/extract/reconcile (pre–Gate 1) |
| `AWAITING_REVIEW` | Pipeline halted at a human gate (Gate 1, 2, or 3); see `report_jobs` for stage |
| `GENERATING` | Synthesis + critic running (post–Gate 2, pre–Gate 3 complete) |
| `DEGRADED` | Partial success — some sections generated, others failed; persisted work retained |
| `COMPLETE` | All sections confirmed; export available |

**Partial-success rule:** If some sections succeed and others fail, persist as `DEGRADED` with per-section status in `content_json` — never discard completed sections.

---

### 2.5 JSONB Payloads

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `knowledge_bank_json` | `knowledge_bank_json` | JSONB | NO | `'{}'::jsonb` | Shape: §2.6 |
| `indicator_actuals_json` | `indicator_actuals_json` | JSONB | NO | `'{}'::jsonb` | Shape: §2.7 |
| `content_json` | `content_json` | JSONB | NO | `'{}'::jsonb` | Shape: §2.8 |

**Naming:** All JSONB columns use `_json` suffix (locked Stage A/B). Python attribute name matches DB column name (no aliasing).

---

### 2.6 `knowledge_bank_json` shape (contract summary)

```json
{
  "facts": {
    "<fact_key>": {
      "value": "any",
      "unit": "string or null",
      "source_document_id": "uuid or null",
      "source_label": "string or null",
      "confirmed": false,
      "confirmed_at": "ISO-8601 or null",
      "confirmed_by_user": true
    }
  },
  "conflicts": [
    {
      "fact_key": "string",
      "values": [{"value": "any", "source_document_id": "uuid", "source_label": "string"}],
      "resolved_value": "any or null",
      "resolved_at": "ISO-8601 or null"
    }
  ],
  "gap_answers": {
    "<gap_item_key>": {
      "answer_text": "string",
      "answered_at": "ISO-8601"
    }
  },
  "gate1_confirmed_at": "ISO-8601 or null",
  "gate2_confirmed_at": "ISO-8601 or null",
  "gate3_confirmed_at": "ISO-8601 or null"
}
```

Full synthesis mapping: `REPORT_INPUTS_FIELD_MAPPING.md`.

---

### 2.7 `indicator_actuals_json` shape (contract summary)

```json
{
  "indicators": [
    {
      "indicator_key": "string",
      "label": "string",
      "target": "number or string or null",
      "actual": "number or string or null",
      "unit": "string or null",
      "disaggregation": {},
      "reporting_period_note": "string or null",
      "source_document_id": "uuid or null"
    }
  ],
  "financials": {
    "budget_total": "number or null",
    "spent_to_date": "number or null",
    "currency": "string or null",
    "notes": "string or null"
  },
  "beneficiary_summary": {
    "total_reached": "number or null",
    "disaggregation": {},
    "source_document_id": "uuid or null"
  }
}
```

---

### 2.8 `content_json` shape (contract summary)

Mirrors proposal `content_json` section pattern with critic extensions:

```json
{
  "sections": [
    {
      "section_key": "string",
      "label": "string",
      "generation_status": "GENERATED | FAILED | AWAITING_REVIEW | ACCEPTED",
      "content": {
        "text": "string",
        "assumptions": ["string"],
        "evidence_used": ["string"]
      },
      "critic_flags": [
        {
          "claim_text": "string",
          "severity": "BLOCK | WARN",
          "reason": "string",
          "source_required": true,
          "accepted": false,
          "accepted_at": "ISO-8601 or null"
        }
      ],
      "failure_reason": "string or null",
      "constraints_applied": {
        "word_limit": 0,
        "word_limit_respected": true
      },
      "human_edited": false,
      "last_edited_at": "ISO-8601 or null"
    }
  ],
  "generation_summary": {
    "total_sections": 0,
    "generated": 0,
    "failed": 0,
    "awaiting_review": 0,
    "accepted": 0,
    "critic_blocks": 0,
    "warnings": ["string"]
  }
}
```

---

### 2.9 Versioning & Timestamps

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `version` | `version` | INTEGER | NO | `1` | Incremented on full regeneration |
| `created_at` | `created_at` | TIMESTAMPTZ | NO | `now()` | — |
| `updated_at` | `updated_at` | TIMESTAMPTZ | NO | `now()` | Updated on any mutation |

---

## 3. Indexes

| Index | Purpose |
|-------|---------|
| `(user_id, created_at DESC)` | Dashboard list |
| `(user_id, status)` | Filter in-progress reports |
| `(funder_report_template_id)` | Template analytics |
| `(linked_proposal_id)` WHERE NOT NULL | Proposal bridge lookup |

---

## 4. FK Direction Rule

| This table FK | Target | Direction |
|---------------|--------|-----------|
| `user_id` | `users` | M&E → core ✓ |
| `linked_proposal_id` | `proposals` | M&E → core ✓ |
| `funder_report_template_id` | `funder_report_templates` | M&E → M&E ✓ |

**No core table** may FK to `donor_reports`.

---

## 5. Relationship to Other Artefacts

Must remain consistent with:

- `DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md`
- `DB_FIELD_CONTRACT_REPORT_JOBS.md`
- `FUNDER_TEMPLATE_SCHEMA.md`
- `REPORT_INPUTS_FIELD_MAPPING.md`
- `API_CONTRACT.md` §12
- `ENUM_REGISTRY.md` §5

---

## 6. Build Enforcement

Any implementation that:

- Persists report content outside this table
- Omits `_json` suffix on JSONB columns
- Uses Python↔DB aliasing without explicit `mapped_column("db_name", ...)`
- Allows pipeline to advance past a gate without persisted confirmation timestamps

is **invalid** and must not be merged.

---

## 7. SQLAlchemy parity note (Stage C)

Expected model pattern — attribute name equals DB column name for this table:

```python
knowledge_bank_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
```

Contrast with core `usage_ledger` where Python `event_type` maps to DB `action_type` — aliasing is explicit when used.
