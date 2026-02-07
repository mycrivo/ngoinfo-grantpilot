# DB_FIELD_CONTRACT_STRIPE_EVENTS.md

**Status:** Canonical (LOCKED FOR BUILD)  
**System of Record:** Railway Postgres (GrantPilot DB)  
**Applies to:** stripe_events table (Stripe webhook event store)  
**Migration rules:** All schema changes via Alembic only. No manual DB edits.

## 1. Purpose
This contract defines an event-store-first persistence layer for Stripe webhooks to ensure:
- idempotency (duplicate delivery safe)
- auditability (raw payload preserved)
- recoverability (replay possible)

**Rule:** Persist the raw event BEFORE processing any business logic.

## 2. Table: `stripe_events`

### 2.1 Identity

| Field | Type | Constraints |
|---|---|---|
| id | UUID | Primary key; not null (DB default or app-generated UUID must be explicit in migration) |
| stripe_event_id | TEXT | Not null; UNIQUE (idempotency key) |

### 2.2 Event Content

| Field | Type | Constraints |
|---|---|---|
| event_type | TEXT | Not null |
| payload | JSONB | Not null |

### 2.3 Processing Audit

| Field | Type | Constraints |
|---|---|---|
| received_at | TIMESTAMPTZ | Not null; default now() |
| processed_at | TIMESTAMPTZ | Nullable |
| processing_result | TEXT | Nullable; allowed values: SUCCESS \| FAILED \| SKIPPED |
| error_message | TEXT | Nullable |

**Rules**
- processed_at NULL means “not processed yet”.
- processing_result is set only after processing attempt completes.
- payload must store the full Stripe event JSON as received (no partial storage).

## 3. Indexes
Required:
- UNIQUE(stripe_event_id)
Recommended:
- Index on (received_at DESC)
- Index on (event_type)
- Index on (processing_result) if operational dashboards require it

## 4. Persistence Rules (Non-negotiable)
- Append-only: rows MUST NOT be updated except processed_at / processing_result / error_message.
- Rows MUST NOT be deleted in MVP.
- Webhook handler MUST short-circuit duplicates by stripe_event_id.

## 5. Relationship to Other Artefacts
Must remain consistent with:
- STRIPE_INTEGRATION_SPEC.md (event-store-first + idempotency rules)
- API_CONTRACT.md (webhook endpoint behavior)

## 6. Build Enforcement
Any implementation that processes a webhook without first persisting the raw event row is invalid.
