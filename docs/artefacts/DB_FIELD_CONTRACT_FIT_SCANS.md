# DB_FIELD_CONTRACT_FIT_SCANS.md

**Status:** Canonical (LOCKED FOR BUILD)  
**Applies to:** Fit Scan v1 (MVP)  
**System of Record:** Railway PostgreSQL — GrantPilot Backend  
**Owner:** Product / Backend (not ingestion, not auth)

---

## 1. Purpose

This contract defines how **Fit Scan results** are persisted.

A Fit Scan is a **first-class, immutable product artefact** that:
- Belongs to a specific user
- Evaluates a specific funding opportunity
- Consumes commercial quota
- Must be auditable and reproducible

No other table may store Fit Scan outputs.

---

## 2. Table: `fit_scans`

### 2.1 Identity & Ownership

| Field | Type | Constraints |
|-----|-----|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK → users.id, ON DELETE CASCADE |
| funding_opportunity_id | UUID | FK → funding_opportunities.id |

**Rules**
- Each Fit Scan belongs to exactly one user
- Multiple users may run scans on the same opportunity
- Users may run multiple scans over time (append-only)

---

### 2.2 Commercial Context (Snapshot at Time of Scan)

| Field | Type | Constraints |
|-----|-----|-------------|
| plan_at_time_of_scan | TEXT | Required; FREE \| GROWTH \| IMPACT |

**Rules**
- Value MUST reflect the user’s active plan **at execution time**
- Must NOT be recomputed later
- Used for audit, dispute resolution, and analytics

---

### 2.3 Prompt & Evaluation Metadata

| Field | Type | Constraints |
|-----|-----|-------------|
| prompt_version | TEXT | Required |
| model_rating | TEXT | STRONG \| MODERATE \| WEAK |
| overall_recommendation | TEXT | RECOMMENDED \| APPLY_WITH_CAVEATS \| NOT_RECOMMENDED |

**Rules**
- `prompt_version` MUST equal the version string declared in `OPENAI_PROMPTS_LIBRARY.md` (e.g. `1.0.0`)
- No environment variable is used for prompt versioning in MVP
- `model_rating` and `overall_recommendation` MUST BOTH be persisted
- Mapping between the two is governed by `FIT_SCAN_CRITERIA_MATRIX.md`

---

### 2.4 Scoring & Results

| Field | Type | Description |
|-----|-----|-------------|
| subscores | JSONB | `{ eligibility, alignment, readiness }` |
| result_json | JSONB | Full structured Fit Scan output |

**Rules**
- `subscores` MUST include numeric values (0–100)
- `result_json` MUST store the complete GP-F02 output after post-processing
- `result_json` is the authoritative record for:
  - rationale
  - risk flags
  - cited fields
  - assumptions
- No partial results may be persisted

---

### 2.5 Timestamps

| Field | Type | Constraints |
|-----|-----|-------------|
| created_at | TIMESTAMPTZ | Default `now()` |

---

## 3. Indexes

| Index | Purpose |
|-----|---------|
| `(user_id, created_at DESC)` | Retrieve user scan history |
| `(funding_opportunity_id)` | Opportunity-level analysis |
| `(user_id, funding_opportunity_id)` | Optional dedup / analytics |

---

## 4. Persistence Rules (Non-Negotiable)

1. **Append-only**
   - Fit Scans MUST NOT be updated or overwritten
   - No “re-run overwrites previous” behavior

2. **Atomicity**
   - Quota decrement + row insert MUST occur in the same transaction
   - If persistence fails, quota MUST NOT be consumed

3. **Failure Handling**
   - Failed or degraded AI runs MUST NOT create a row
   - Invalid JSON or contract violation MUST abort persistence

4. **No Derived Field Persistence**
   - Fields defined as `derived.*` in `PROMPT_INPUTS_FIELD_MAPPING.md`
     MUST NOT be persisted separately
   - Only final evaluated outputs belong here

---

## 5. Access Control

- Only the owning `user_id` may read a Fit Scan
- Attempted access by another user MUST return `403 FORBIDDEN`
- There is no admin override in MVP

---

## 6. Relationship to Other Artefacts

This contract is governed by and MUST remain consistent with:

- `PROMPT_INPUTS_FIELD_MAPPING.md`
- `OPENAI_PROMPTS_LIBRARY.md`
- `FIT_SCAN_CRITERIA_MATRIX.md`
- `FIT_SCAN_PRODUCT_SPEC.md`
- `API_CONTRACT.md`
- `PRICING_AND_ENTITLEMENTS.md`

If any conflict arises, this file governs **persistence only**.

---

## 7. Explicit Non-Goals (MVP)

The following are intentionally out of scope:

- Updating or deleting Fit Scans
- Soft deletes or status flags
- Versioned rescans or “compare scans”
- Aggregated analytics tables

These may be added only via a new artefact version.

---

## 8. Build Enforcement

Any implementation that:
- Persists Fit Scan outputs outside this table
- Omits `plan_at_time_of_scan`
- Recomputes prompt version dynamically
- Updates an existing Fit Scan row

is **invalid** and must not be merged.

## 9. Plan at time of scan
plan_at_time_of_scan Source (Authoritative):
  - Query user_plans table for current user_id
  - Use user_plans.plan_name (current active plan)
  - If no plan record exists, default to "FREE"
  - Value MUST be captured at Fit Scan execution time (not retroactively)