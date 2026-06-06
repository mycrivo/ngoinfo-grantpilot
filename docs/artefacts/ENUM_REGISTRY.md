Status: Canonical (LOCKED FOR BUILD)
Scope: All enum types and enum-like fields in GrantPilot backend
Non-negotiable: Prevent Postgres ENUM drift and duplicate-type errors.

============================================================
1) Enum Implementation Rule (non-negotiable)
============================================================

- SQLAlchemy model enums must use:
  - postgresql.ENUM(..., create_type=False)
- Alembic migrations must explicitly and idempotently create enum types:
  - create if not exists
  - safe on partial deploys / retries
- Enum changes:
  - Adding values is allowed (with explicit migration)
  - Removing/renaming values requires careful strategy and is out of MVP scope

============================================================
2) DEPLOYED Postgres ENUM types (already exist in DB)
============================================================

2.1 applicant_type (public.applicant_type)
- NGO
- INDIVIDUAL
- ACADEMIC_INSTITUTION
- CONSORTIUM
- MIXED

2.2 deadline_type (public.deadline_type)
- FIXED
- ROLLING
- VARIES

2.3 opportunity_status (public.opportunity_status)
- DRAFT
- READY
- PUBLISHED
- ARCHIVED

Important:
- These types already exist in Railway DB. Do not recreate them.
- All models must reference them with create_type=False.

============================================================
3) Enum-like text fields (MVP; not Postgres ENUM unless required)
============================================================

3.1 users.auth_provider (text)
- Allowed: email | google
- Default: email

3.2 ngo_profiles.profile_status (text) (planned)
- Allowed: DRAFT | COMPLETE
- Default: DRAFT
- Note: Keep as text for MVP to avoid enum churn, unless you explicitly want it as Postgres ENUM.

### 3.3 usage_ledger.action_type (text field with application validation)

**Implementation Strategy (MVP):**
- Field type: TEXT (not Postgres ENUM)
- Validation: Application-level (Python enum + service layer)
- Rationale: Flexibility for MVP; easy addition of new action types

**Allowed Values (application-validated):**
- FIT_SCAN
- PROPOSAL_CREATE
- PROPOSAL_REGEN
- DOCX_EXPORT
- REPORT_CREATE *(M&E — Stage J)*
- REPORT_EXPORT *(M&E — Stage J)*

**Python / DB aliasing (CRITICAL — do not drift):**

| Python attribute (`UsageLedger`) | DB column |
|----------------------------------|-----------|
| `event_type` | `action_type` |
| `occurred_at` | `created_at` |
| `metadata_json` | `metadata` |

New M&E action types use DB column name **`action_type`**, not `event_type`.

**Validation Location:**
- `app/models/usage_ledger.py`: Python Enum class for type hints
- `app/services/quota_service.py`: Validation in `record_usage()` function

**Database Constraint:**
- None (validated before insert)
- Invalid values will raise `ValueError` in service layer

**Post-MVP Migration Path:**
If action types stabilize and we need DB-level enforcement:
1. Create Postgres ENUM type: `CREATE TYPE usage_action_type AS ENUM (...)`
2. Alter column: `ALTER TABLE usage_ledger ALTER COLUMN action_type TYPE usage_action_type USING action_type::usage_action_type`
3. Update SQLAlchemy model: `postgresql.ENUM(..., create_type=False)`
4. Requires coordinated migration + code deployment

**Current Status:** TEXT field (deployed in migration 0005_commercial_spine.py)

============================================================
4) Future enums (reserved; for Prompt 8+)
============================================================

4.1 Plan names
- FREE | GROWTH | IMPACT

**Field:** `user_plans.plan_name` (TEXT + CHECK constraint)

**Rules:**
- Plan enum is exactly **FREE | GROWTH | IMPACT** — no third tier.
- M&E (Donor Report Writer) is bundled on **IMPACT** ($79/mo): 2 reports/month (see `PRICING_AND_ENTITLEMENTS.md`, Decision D-048).
- JWT `plan` claim and `GET /api/me/entitlements` reflect the active plan from this enum.

4.2 Usage action types — see §3.3 (includes M&E additions)

These are registry-only until the corresponding tables exist.

============================================================
5) M&E Module enums (Stage B — LOCKED)
============================================================

Implementation: TEXT columns + CHECK constraints in `0014_me_module_*.py` migrations (Stage C).
Python enums in `app/reports/` must match exactly.

### 5.1 donor_reports.status

| Value | Meaning |
|-------|---------|
| DRAFT | Created; intake not started |
| EXTRACTING | Pipeline running pre–Gate 1 |
| AWAITING_REVIEW | Halted at human gate |
| GENERATING | Synthesis/critic running |
| DEGRADED | Partial section success |
| COMPLETE | All sections accepted; export ready |

**Field:** `donor_reports.status` · Default: `DRAFT`

### 5.2 Partial-success interaction

When `status = DEGRADED`, `content_json.generation_summary` MUST reflect failed sections. Export allowed only when Gate 3 satisfied per API §12.13.

### 5.3 uploaded_documents.classification

| Value | Meaning |
|-------|---------|
| proposal | Winning proposal / application |
| grant_letter | Funder award letter |
| mou | Memorandum of understanding |
| indicator_data | Spreadsheet / CSV indicators |
| photo | Image evidence |
| deck | Presentation |
| other | Unclassified |

**Nullable** until classifier runs.

### 5.4 uploaded_documents.extraction_status

| Value | Meaning |
|-------|---------|
| PENDING | Uploaded; not yet processed |
| PROCESSING | Docling / extractor running |
| COMPLETE | extracted_json populated |
| FAILED | extraction error |

**Default:** `PENDING`

### 5.5 funder_report_templates.reporting_frequency

| Value | Meaning |
|-------|---------|
| end_of_grant | Final / end-of-grant report |
| annual | Annual progress / review |
| quarterly | Quarterly performance |
| interim | Interim reporting period |
| final | Final report (distinct from end_of_grant where funder uses both) |

### 5.6 report_jobs.stage

| Value | Order | Meaning |
|-------|-------|---------|
| classify | 1 | Document classifier |
| extract | 2 | Specialist extractors |
| reconcile | 3 | Knowledge-bank reconciler → Gate 1 |
| gap | 4 | Gap/compliance → Gate 2 |
| synthesise | 5 | Section synthesis |
| critique | 6 | Fact-safety critic → Gate 3 |
| export | 7 | docxtpl render |

### 5.7 report_jobs.status

| Value | Meaning |
|-------|---------|
| queued | Waiting for worker |
| running | Agent executing |
| awaiting_human | Server-enforced gate halt |
| failed | Terminal error |
| done | Stage or pipeline complete |

**Default:** `queued`

### 5.8 content_json section generation_status (enum-like)

| Value | Meaning |
|-------|---------|
| GENERATED | AI draft ready for Gate 3 review |
| FAILED | Section generation failed |
| AWAITING_REVIEW | Pending human review |
| ACCEPTED | Human accepted; export-eligible |

### 5.9 critic_flags.severity (enum-like, in JSONB)

| Value | Meaning |
|-------|---------|
| BLOCK | Must resolve or accept before export |
| WARN | Advisory |

### 5.10 M&E quota entitlements (API / usage_ledger — Stage J)

| Entitlement key | usage_ledger.action_type | Period |
|-----------------|--------------------------|--------|
| reports | REPORT_CREATE | BILLING_CYCLE (2/month on IMPACT) |
| report_exports | REPORT_EXPORT | Idempotent per report version |

**Cross-reference:** `PRICING_AND_ENTITLEMENTS.md` (Stage J extension), `API_CONTRACT.md` §12.0, §12.14.
