# DB_FIELD_CONTRACT_USER_PLANS.md

**Status:** Canonical (LOCKED FOR BUILD)  
**System of Record:** Railway Postgres (GrantPilot DB)  
**Applies to:** user_plans table (billing projection / entitlements cache)  
**Migration rules:** All schema changes via Alembic only. No manual DB edits.

## 1. Purpose
This contract defines the persisted projection of a user’s active plan used for:
- entitlements checks
- quota cycle boundaries (billing period)
- audit of plan at time of usage

**Billing source of truth:** Stripe  
**DB role:** cache/projection only (never a custom subscription state machine)

## 2. Table: `user_plans`

### 2.1 Identity & Ownership

| Field | Type | Constraints |
|---|---|---|
| id | UUID | Primary key; not null (DB default or app-generated UUID must be explicit in migration) |
| user_id | UUID | Not null; FK → users.id; ON DELETE CASCADE; UNIQUE(user_id) |

**Rules**
- At most one user_plans row per user (current-plan projection).
- If a user has no row, application behavior may treat them as FREE (MVP compatibility), but preferred behavior is to create a row at registration with plan_name=FREE.

### 2.2 Plan Projection Fields (MVP-required)

| Field | Type | Constraints |
|---|---|---|
| plan_name | TEXT | Not null; allowed values: FREE \| GROWTH \| IMPACT; default FREE (application validated per ENUM_REGISTRY.md) |
| stripe_subscription_id | TEXT | Nullable; recommended UNIQUE when present |
| billing_period_start | TIMESTAMPTZ | Nullable |
| billing_period_end | TIMESTAMPTZ | Nullable |
| plan_activated_at | TIMESTAMPTZ | Nullable |

**Rules**
- For FREE users:
  - stripe_subscription_id MUST be NULL
  - billing_period_start/end MAY be NULL
- For paid users (GROWTH/IMPACT):
  - stripe_subscription_id MUST be present
  - billing_period_start/end MUST be synced from Stripe subscription current_period_start/end
- plan_name updates MUST occur only via webhook-driven sync (Stripe is source of truth).

### 2.3 Optional Fields (Allowed, not required for MVP)
If present in deployed schema or intentionally added later, the following are allowed:
- stripe_status (TEXT; e.g., active | trialing | past_due | canceled) — for UX/diagnostics only
- cancel_at_period_end (BOOLEAN) — for UX messaging only

### 2.4 Indexes / Constraints
Required:
- UNIQUE(user_id)
- Index on (user_id)
Recommended:
- UNIQUE(stripe_subscription_id) (partial/nullable-safe)
- Index on (billing_period_end)

## 3. Relationship to Other Artefacts
Must remain consistent with:
- STRIPE_INTEGRATION_SPEC.md
- PRICING_AND_ENTITLEMENTS.md
- ENUM_REGISTRY.md
- API_CONTRACT.md (Billing API section)

## 4. Build Enforcement
Any implementation that:
- derives entitlements from anything other than Stripe-synced user_plans values, or
- mutates plan state without Stripe webhook confirmation,
is invalid for MVP.
