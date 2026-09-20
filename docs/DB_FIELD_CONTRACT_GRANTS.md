# DB_FIELD_CONTRACT_GRANTS.md

**Status:** Canonical (LOCKED for V2 build)  
**Applies to:** M&E Module — Report Writer V2  
**System of Record:** Railway PostgreSQL — GrantPilot Backend  
**Owner:** M&E Module / Backend  
**Migration:** next revision in the alembic chain (Cursor reads the current head; do not assume a number). Additive only.  
**Decisions:** D-084, D-088, D-089, D-094

---

## 1. Purpose

A **grant** is the durable post-award entity. A donor report is an output of a grant for one reporting period. The grant holds the **confirmed ledger**: every fact the NGO has confirmed, with source, facet, period, scope, confirmation and supersession.

Beta rule (D-084): the pipeline continues to read and write the report's `knowledge_bank_json` during a run. The ledger on the grant is written **through** at Gate 1, Gate 2 and Gate 3 confirmation. Nothing in the run reads the grant ledger in beta; the next-report workflow (post-beta) will seed a new report from it. This keeps the persistent ledger without re-pointing any pipeline stage.

No other table may store confirmed grant-level facts.

---

## 2. Table: `grants`

### 2.1 Identity & Ownership

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `id` | `id` | UUID | NO | `gen_random_uuid()` | PRIMARY KEY |
| `user_id` | `user_id` | UUID | NO | — | FK → `users.id`, ON DELETE CASCADE |

**Rules**
- Only the owning `user_id` may read or mutate a grant (403 otherwise).
- Core table `users` is never altered; FK points inward only.

### 2.2 Grant identity (as documented, not as profiled)

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `funder_name` | `funder_name` | TEXT | NO | — | As entered by the user at report start; free text |
| `funder_website` | `funder_website` | TEXT | YES | NULL | Optional; used by discovery |
| `organisation_name` | `organisation_name` | TEXT | YES | NULL | The grantee organisation **as named in the award/agreement**; NULL until confirmed at Gate 1 |
| `programme_title` | `programme_title` | TEXT | YES | NULL | As documented; NULL until confirmed |
| `grant_reference` | `grant_reference` | TEXT | YES | NULL | Funder's reference/contract number |
| `grant_start` | `grant_start` | DATE | YES | NULL | Contractual start; from confirmed facts |
| `grant_end` | `grant_end` | DATE | YES | NULL | Contractual end; MUST be ≥ `grant_start` when both set |
| `currency` | `currency` | TEXT | YES | NULL | ISO 4217, from confirmed finance facts |
| `linked_proposal_id` | `linked_proposal_id` | UUID | YES | NULL | FK → `proposals.id`, ON DELETE SET NULL |

**Rules**
- `organisation_name`, `programme_title`, `grant_reference`, `grant_start`, `grant_end`, `currency` are **projections** of confirmed ledger facts (`organisation.name`, `programme.title`, `grant.reference`, `grant.start_date`, `grant.end_date`, `grant.currency`). They are refreshed by the write-through service; they are never edited directly by an endpoint. Report covers and grant lists read these columns.
- The NGO profile is **not** a source for any of these. Profile organisation ≠ documented organisation is surfaced at Gate 1 as a confirm item (see `DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md` §5).

### 2.3 Ledger

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `ledger_json` | `ledger_json` | JSONB | NO | `'{}'::jsonb` | Shape: §3 |
| `ledger_version` | `ledger_version` | INTEGER | NO | `0` | Incremented on every write-through |
| `ledger_updated_at` | `ledger_updated_at` | TIMESTAMPTZ | YES | NULL | Set on every write-through |

### 2.4 Timestamps

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `created_at` | `created_at` | TIMESTAMPTZ | NO | `now()` | — |
| `updated_at` | `updated_at` | TIMESTAMPTZ | NO | `now()` | Updated on any mutation |

---

## 3. `ledger_json` shape

```json
{
  "schema_version": "2.0.0",
  "facts": {
    "<fact_key>": { "...": "Fact object — §3.1" }
  },
  "entities": {
    "<entity_id>": {
      "domain": "indicators | finance | beneficiaries | risks | activities | partners | other",
      "label": "string — display label as documented",
      "aliases": ["OP1.1", "Output 1.1", "Girls re-enrolled"],
      "unit": "string or null",
      "parent_entity_id": "string or null"
    }
  },
  "conflicts": [ { "...": "Conflict object — §3.3" } ],
  "answers": {
    "<answer_id>": {
      "question_text": "string",
      "answer_text": "string",
      "requirement_key": "string or null",
      "fact_keys_written": ["fact_key"],
      "not_available": false,
      "answered_at": "ISO-8601",
      "report_id": "uuid"
    }
  },
  "periods": [
    { "label": "y1", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "kind": "milestone | reporting | grant | baseline | endline" }
  ],
  "writes": [
    { "report_id": "uuid", "gate": "gate1 | gate2 | gate3", "written_at": "ISO-8601", "facts_added": 0, "facts_superseded": 0, "ledger_version": 0 }
  ]
}
```

### 3.1 Fact object (shared by `grants.ledger_json.facts` and `donor_reports.knowledge_bank_json.facts` — one shape, one definition)

```json
{
  "value": "any — number, string, ISO date, or list",
  "value_type": "integer | number | money | percent | date | date_range | text | list | boolean",
  "unit": "string or null",
  "currency": "ISO 4217 or null — REQUIRED when value_type = money",
  "facet": "baseline | milestone | target | actual | planned | revised | derived | context",
  "period": { "label": "string or null", "start": "YYYY-MM-DD or null", "end": "YYYY-MM-DD or null" },
  "scope": "string or null — disaggregation or geography, e.g. 'girls', 'District A'",
  "entity_id": "string or null — key into ledger.entities",
  "label": "string — human label for this fact as it should read in prose",
  "source": {
    "kind": "document | user_answer | derived | carry_forward",
    "document_id": "uuid or null",
    "location": "string or null — page/section/sheet/cell as extracted",
    "quote": "string or null — verbatim span ≤ 200 chars",
    "answer_id": "string or null",
    "derived_from": ["fact_key"],
    "derivation": "string or null — e.g. 'actual / milestone * 100'"
  },
  "confirmed": false,
  "confirmed_at": "ISO-8601 or null",
  "confirmed_via": "gate1 | gate2 | gate3 | carry_forward | null",
  "supersedes": "fact_key or null",
  "superseded_by": "fact_key or null",
  "confidence": "number 0–1 or null",
  "notes": "string or null"
}
```

**Rules**
- `facet = context` is for identity and narrative facts (organisation name, grant dates, objectives text). Measured facts (indicators, finance, beneficiaries) MUST carry `facet ≠ context` and a `period` with at least a `label`.
- `facet = derived` facts are written only by the deterministic derivation service (D-089). They carry `derived_from` and `derivation`. The model never writes a `derived` fact and never computes a value that a derivation could produce.
- `currency` is mandatory for money. A money fact with null currency is **unconfirmed by definition** and cannot satisfy a finance requirement.
- Supersession, never deletion: a corrected value is a new fact with `supersedes` set; the old fact gets `superseded_by`. Readers use the head of the chain.

### 3.2 Fact-key grammar (LOCKED)

```
<domain>.<entity_id>.<facet>[.<period_label>][.<scope_slug>]      — measured facts
<domain>.<attribute>                                                — context facts
```

| Domain | Entity / attribute examples |
|---|---|
| `organisation` | `name`, `registration`, `address` |
| `programme` | `title`, `objectives`, `geography`, `target_group` |
| `grant` | `reference`, `award_value`, `start_date`, `end_date`, `currency`, `reporting_frequency` |
| `indicators` | `<entity_id>` per indicator, e.g. `indicators.op1_1.actual.ar1`, `indicators.op1_1.milestone.y1`, `indicators.op1_1.target.endline`, `indicators.op1_1.baseline.baseline` |
| `finance` | `<entity_id>` per budget line or `total`, e.g. `finance.total.budget.grant`, `finance.total.actual.ar1`, `finance.line_salaries.actual.ar1`, `finance.total.variance.ar1` (derived) |
| `beneficiaries` | `total`, or group entities, e.g. `beneficiaries.total.actual.ar1.girls` |
| `risks`, `activities`, `partners`, `safeguarding`, `learning` | entity per item; facet `context` or `actual` |

**Entity id normalisation:** lowercase; any run of non-alphanumeric characters → `_`; leading/trailing `_` removed. Use the source's own identifier when one exists (`OP1.1` → `op1_1`); otherwise the first six words of the label. The original identifiers and label go into `entities[<entity_id>].aliases`. The reconciler merges entities whose aliases match case- and punctuation-insensitively (D-088).

**Period label normalisation:** `baseline`, `endline`, `grant`, `y1…yN`, `q1…q4` (with year in `start`/`end`), `ar1…arN`, or `<yyyy_mm>_<yyyy_mm>` for arbitrary ranges. Period equality is by `start`/`end` when both facts carry dates, else by label. Two facts with the same `domain.entity.facet` and **different** periods are two facts, never a conflict.

**Scope slug:** same normalisation as entity ids; present only when the fact is disaggregated.

### 3.3 Conflict object

```json
{
  "conflict_id": "string",
  "fact_keys": ["fact_key", "fact_key"],
  "metric": "domain.entity.facet",
  "period": { "label": "string", "start": "date or null", "end": "date or null" },
  "scope": "string or null",
  "values": [ { "fact_key": "string", "value": "any", "source": { "...": "§3.1 source" } } ],
  "proposed_resolution": { "kind": "choose | keep_both | needs_user", "fact_key": "string or null", "reason": "string" },
  "resolution": { "kind": "choose | keep_both | corrected", "fact_key": "string or null", "corrected_fact_key": "string or null", "resolved_at": "ISO-8601 or null", "resolved_via": "gate1 | gate3 | null" }
}
```

**Rules (D-088)**
- A conflict exists only when `metric`, `period` and `scope` are all equal and the values differ.
- `keep_both` marks both facts confirmed with a note; it is the correct resolution when the reconciler mis-grouped two different facts. It never destroys a value.
- `choose` confirms one fact; the other is **superseded**, not deleted.
- No averaging, ever.

---

## 4. Write-through service (D-084)

Triggered by the report's gate confirmations. Reads `donor_reports.knowledge_bank_json`, writes `grants.ledger_json`.

| Gate | What is written | How |
|---|---|---|
| Gate 1 confirm | every fact with `confirmed = true`; every resolved conflict; entities and periods | Merge by `fact_key`. Existing head with a different value → new fact `supersedes` it. Same value → confirmation refreshed. |
| Gate 2 confirm | facts written by the answer normaliser (`source.kind = user_answer`); the `answers` map | Same merge. |
| Gate 3 confirm | corrections made through Gate 3 replies (`corrected` resolutions, claim corrections that changed a fact) | Same merge. |

- Each write appends to `writes[]`, increments `ledger_version`, sets `ledger_updated_at`, and refreshes the §2.2 projections from the ledger heads.
- Write-through is idempotent: re-confirming a gate with unchanged facts changes nothing but `writes[]`.
- Failure of write-through **must not** block the gate confirmation in beta; it is logged with `report_id` and retried by the next confirmation. (The run's own KB remains authoritative for the run.)

---

## 5. Indexes

| Index | Purpose |
|---|---|
| `(user_id, updated_at DESC)` | My grants list |
| `(user_id, funder_name)` | Grouping and search |
| `(linked_proposal_id)` WHERE NOT NULL | Proposal bridge |

---

## 6. FK Direction Rule

| This table FK | Target | Direction |
|---|---|---|
| `user_id` | `users` | M&E → core ✓ |
| `linked_proposal_id` | `proposals` | M&E → core ✓ |

`donor_reports.grant_id` and `uploaded_documents.grant_id` point **to** this table (M&E → M&E). **No core table** may FK to `grants`.

---

## 7. Backfill of existing reports (P2.1)

For every existing `donor_reports` row without a `grant_id`: create one grant per report with `funder_name` = the report's template `funder_name` (read once, for backfill only), `linked_proposal_id` copied, ledger empty, and set `donor_reports.grant_id`. Existing `knowledge_bank_json` is **not** promoted to the ledger during backfill; it flows through on the next gate confirmation. Backfill is reversible (drop `grant_id` values; drop rows).

---

## 8. Build Enforcement

Invalid and must not be merged:
- any pipeline stage reading `grants.ledger_json` during a run in beta;
- any endpoint writing §2.2 projection columns directly;
- a money fact without currency marked confirmed;
- a `derived` fact written by a model call;
- deletion of a fact instead of supersession;
- a conflict recorded for facts whose periods differ.
