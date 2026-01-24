Status: Canonical (LOCKED FOR BUILD)
System of record: Railway Postgres (GrantPilot DB)
Applies to: users table, auth linkage, NGO profile domain, and profile completeness rules
Migration rules: All schema changes via Alembic only. No manual DB edits.

============================================================
0) Global DB Conventions (based on deployed schema)
============================================================

Primary keys
- UUID is the standard PK type across tables.
- DB-side UUID default is NOT guaranteed for all tables.
  - users.id has DB default: gen_random_uuid()
  - other tables may require application-generated UUID unless a DB default is explicitly set in migration.

Timestamps
- users/auth tables use timestamptz (timestamp with time zone)
- funding_opportunities uses timestamp WITHOUT time zone
- Rule for new tables: use timestamptz for consistency with users/auth (do not change funding_opportunities)

============================================================
1) Canonical Table: users (DEPLOYED)
============================================================

1.1 Columns (deployed)
- id (uuid, PK, not null, default gen_random_uuid())
- email (text, not null, unique)
- full_name (text, nullable)
- avatar_url (text, nullable)
- google_sub (text, nullable, unique)
- auth_provider (text, not null, default 'email')
- created_at (timestamptz, not null, default now())
- updated_at (timestamptz, not null, default now())
- last_login_at (timestamptz, nullable)

1.2 Identity + Account Linking (authoritative)
- Accounts are linked by email across OAuth and Magic Link.
- users.id is the canonical ownership key for all user-owned resources (e.g., ngo_profiles).
- Email is treated as a user attribute (can change), not as a foreign-key anchor for domain objects.
- auth_provider is descriptive and must not be used as an authorization gate.

============================================================
2) Canonical Table: auth_refresh_tokens (DEPLOYED)
============================================================

2.1 Columns (deployed)
- id (uuid, PK, not null) — NOTE: no DB default observed; app should set UUID unless migration adds default
- user_id (uuid, not null, FK → users.id ON DELETE CASCADE)
- token_hash (text, not null, unique)
- issued_at (timestamptz, not null, default now())
- expires_at (timestamptz, not null)
- revoked_at (timestamptz, nullable)
- replaced_by_token_id (uuid, nullable, FK → auth_refresh_tokens.id)

2.2 Rules
- Only one active refresh token per user (enforced in application logic).
- On login/refresh, prior refresh tokens should be revoked and replaced safely (idempotent).

============================================================
3) Canonical Table: auth_magic_link_tokens (DEPLOYED)
============================================================

(Kept brief here; actual schema is controlled by existing migration and DB field contract if present.)
- Token records must remain auditable: requested_ip, user_agent, issued_at, expires_at, consumed_at.
- Token must be stored as token_hash (never plain token).

============================================================
4) Canonical Table: funding_opportunities (DEPLOYED — DO NOT CHANGE)
============================================================

4.1 Columns (deployed)
- id (uuid, PK, not null) — NOTE: no DB default observed; app should set UUID unless migration adds default
- created_at (timestamp without time zone, not null)
- updated_at (timestamp without time zone, not null)
- source_url (text, not null)
- application_url (text, not null)
- title (text, not null)
- donor_organization (text, not null)
- funding_type (text, not null) — free-form
- applicant_type (applicant_type ENUM, not null)
- location_text (text, not null)
- focus_areas (text, not null) — free-form; multiple focus areas may be comma-separated
- deadline_type (deadline_type ENUM, not null)
- application_deadline (date, nullable)
- currency (text, nullable)
- amount_min (numeric, nullable)
- amount_max (numeric, nullable)
- total_funding_available (numeric, nullable)
- short_summary (text, not null)
- overview_text (text, nullable)
- eligibility_criteria (text, nullable)
- application_process (text, nullable)
- status (opportunity_status ENUM, not null)
- is_active (boolean, not null, default true)
- is_archived (boolean, not null, default false)
- last_verified (date, nullable)
- requirements_json (jsonb, not null)
- organization_types (text, nullable)
- geographic_focus (text, nullable)
- contact_information (text, nullable)
- processing_status (text, nullable)
- parsing_confidence (numeric, nullable)
- internal_notes (text, nullable)

4.2 Constraints (deployed)
- Primary key: (id)
- Check constraint:
  - If deadline_type = FIXED then application_deadline must be NOT NULL
  - (deadline_type <> 'FIXED' OR application_deadline IS NOT NULL)

4.3 Enum types (see ENUM_REGISTRY.md)
- applicant_type: NGO | INDIVIDUAL | ACADEMIC_INSTITUTION | CONSORTIUM | MIXED
- deadline_type: FIXED | ROLLING | VARIES
- opportunity_status: DRAFT | READY | PUBLISHED | ARCHIVED

4.4 Rule
- Per MVP: Keep this table as-is (avoid churn). Future normalization is out of scope.

============================================================
5) Canonical Table: ngo_profiles (TO BE CREATED IN PROMPT 4)
============================================================

Purpose
- Stores the NGO profile used for fit scans and proposal generation.

5.1 Ownership & Cardinality (MVP)
- ngo_profiles.user_id references users.id
- Constraint: UNIQUE(user_id) — exactly 1 profile per user

5.2 Required columns (MVP)
- id (uuid, PK, not null) — choose DB default or app-generated UUID, but document explicitly in migration
- user_id (uuid, not null, FK → users.id, unique)

- organization_name (text, not null)
- country_of_registration (text, not null) — store FULL country name
- mission_statement (text, not null)

- focus_sectors (jsonb, not null, default '[]') — array of strings (free-form)
- geographic_areas_of_work (jsonb, not null, default '[]') — array of strings (free-form)
- target_groups (jsonb, not null, default '[]') — array of strings (free-form)

- past_projects (jsonb, not null, default '[]') — array of objects (see schema)

- profile_status (text, not null, default 'DRAFT') — enum-like: DRAFT|COMPLETE
- completeness_score (int, not null, default 0) — 0..100
- missing_fields (jsonb, not null, default '[]') — array of strings

- created_at (timestamptz, not null, default now())
- updated_at (timestamptz, not null, default now())
- last_completed_at (timestamptz, nullable)

5.3 Optional columns (MVP)
- year_of_establishment (int, nullable)
- contact_person_name (text, nullable)
- contact_email (text, nullable)
- website (text, nullable)

- full_time_staff (int, nullable)
- annual_budget_amount (numeric, nullable) — exact amount (no bands)
- annual_budget_currency (text, nullable, default 'USD')

- monitoring_and_evaluation_practices (text, nullable)
- funders_worked_with_before (jsonb, not null, default '[]') — array of strings (free-form)

5.4 JSON Schema (authoritative)
- focus_sectors / geographic_areas_of_work / target_groups / funders_worked_with_before:
  - JSONB array of strings
- past_projects:
  - JSONB array of objects with keys:
    - title (string, required for “valid project”)
    - donor (string, optional)
    - duration (string, optional)
    - location (string, optional)
    - summary (string, optional but recommended)

5.5 Validation rules (API layer)
- country_of_registration: full human-readable country name
- year_of_establishment: reasonable bounds when provided
- annual_budget_amount: >= 0 when provided
- arrays must be arrays; null is not allowed (use []).

============================================================
6) Profile Completeness & Status Rules (authoritative)
============================================================

6.1 Persistence
- Completeness is computed in service layer and persisted to:
  - completeness_score
  - missing_fields
  - profile_status
  - last_completed_at when status becomes COMPLETE

6.2 Minimum requirements for COMPLETE (MVP)
Required:
- organization_name present and non-empty
- country_of_registration present and non-empty
- mission_statement present and non-empty
- focus_sectors has at least 1 entry
- geographic_areas_of_work has at least 1 entry
- target_groups has at least 1 entry
- past_projects has at least 1 “valid project” where title is present and non-empty

Optional (do NOT block completion):
- contact details, staff, budget, M&E, funders list, website

6.3 Scoring model (MVP, informational only)
- Score is informational (0..100), not a separate gate beyond COMPLETE rules.
- Suggested scoring:
  - Core identity (org name + country): 20
  - Mission statement: 15
  - Focus sectors present: 15
  - Geographic areas present: 15
  - Target groups present: 15
  - At least 1 valid past project: 20
  - Cap at 100
- missing_fields must list only missing items from 6.2.

6.4 Update behavior
- On any create/update of ngo_profiles:
  - recompute completeness_score, missing_fields, profile_status
  - if status transitions to COMPLETE, set last_completed_at = now()

============================================================
7) Authorization Rules (summary)
============================================================

- users: read/write only by the authenticated subject (and admin).
- ngo_profiles: user-owned. Only accessible where ngo_profiles.user_id == current_user.id.
- No multi-user NGO access in MVP.