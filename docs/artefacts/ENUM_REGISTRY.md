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

### 3.3 Usage Ledger action_type (text field, MVP)

**Field:** `usage_ledger.action_type` (text, not null)

**Allowed Values (application-validated):**
- FIT_SCAN
- PROPOSAL_CREATE
- PROPOSAL_REGEN
- DOCX_EXPORT

**Validation:**
- Enforced in `app/services/quota_service.py`
- If invalid action_type provided → raise ValueError
- SQLAlchemy model uses `Enum` type with Python-only validation (no DB constraint)

**Migration Path (Post-MVP):**
If action types stabilize and performance matters:
1. Create Postgres ENUM type `usage_action_type`
2. Alter column to use ENUM
3. Update SQLAlchemy models with `create_type=False`

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

4.1 Plan names (planned)
- FREE | GROWTH | IMPACT

4.2 Usage action types (planned)
- FIT_SCAN | PROPOSAL_CREATE | PROPOSAL_REGEN | DOCX_EXPORT

These are registry-only until the corresponding tables exist.
