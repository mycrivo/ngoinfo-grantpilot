# STRIPE_INTEGRATION_SPEC.md
Billing for GrantPilot (Stripe-as-Source-of-Truth)

## 0) Purpose (Why this file exists)
This document defines the billing architecture and operational rules for GrantPilot MVP.

**Non-negotiable principle:** **Stripe is the source of truth** for all billing/subscription state.
Our database stores a **projection/cache** of the minimum subscription facts needed for:
- entitlements (plan + billing period boundaries)
- access control decisions
- UX messaging (next renewal date, “manage billing” link)
- operational troubleshooting

We do **not** build a custom subscription state machine, retry logic, invoice logic, or billing UI.

---

## 1) Responsibility Split (Sync vs Delegate)

### 1.1 What Stripe owns (we delegate)
Stripe owns the subscription lifecycle end-to-end:
- Subscription state machine (active, trialing, past_due, canceled, etc.)
- Payment collection + retries (dunning)
- Invoices + receipts
- Upgrades/downgrades and proration rules
- Cancellation workflows and grace-period behavior
- Self-service billing UI via **Stripe Customer Portal**
- Tax handling (if enabled in Stripe)

**We do not re-implement any of the above.**

### 1.2 What GrantPilot owns (we implement)
We implement only the “thin layer” required for product integration:
- `POST /api/billing/checkout` → create a Stripe Checkout Session (subscription mode)
- `GET /api/billing/portal` → create a Stripe Customer Portal session
- `POST /api/billing/webhook` → verify, persist, and process Stripe events
- Minimal DB projection updates in `user_plans`
- Audit/event store in `stripe_events` (event-store-first pattern)

---

## 2) Pricing / Plans (MVP)
Authoritative plan entitlements: `PRICING_AND_ENTITLEMENTS.md`

Billing plans in Stripe (MVP):
- **GROWTH** (monthly) → `STRIPE_PRICE_ID_GROWTH`
- **IMPACT** (monthly) → `STRIPE_PRICE_ID_IMPACT`
- **FREE** is not a Stripe plan; it is the “no paid subscription” state.

**Plan-name enum (registry):** FREE | GROWTH | IMPACT

---

## 3) Data Model (DB as cache + event store)

### 3.1 Users table (customer linkage)
`users.stripe_customer_id` (nullable, unique)
- Set once when we create (or first observe) a Stripe Customer for the user.
- Used to map webhook events to the user when metadata is missing.

### 3.2 user_plans table (subscription projection / cache)
`user_plans` is the canonical “access/entitlements cache” in our DB, but it is **derived from Stripe**.

Minimum fields expected in `user_plans` (names must match actual schema):
- `plan_name` → FREE | GROWTH | IMPACT
- `stripe_subscription_id` → Stripe subscription id (nullable when FREE)
- `billing_period_start` / `billing_period_end` → from Stripe subscription current period
- `plan_activated_at` → first time user becomes paid (or last paid activation)

Optional (recommended if schema already supports it; do not invent schema silently):
- `stripe_status` (active/past_due/trialing/canceled) for UX + diagnostics
- `cancel_at_period_end` (boolean) for UX messaging

**Rule:** `user_plans.plan_name` is updated **only** via webhook processing (or explicit reconciliation job if added later).

### 3.3 stripe_events table (audit + replay safety)
We must persist raw Stripe events before processing them.

Table: `stripe_events`
- `stripe_event_id` UNIQUE (idempotency)
- `event_type`
- `payload` JSONB
- `received_at`
- `processed_at`
- `processing_result` (SUCCESS | FAILED | SKIPPED)
- `error_message` (nullable)

This table is the safety net: lost processing is recoverable because events are stored.

---

## 4) Environment Variables
See `ENV_VARS_REFERENCE.md` for the authoritative list. Stripe-related vars used by MVP:

Required (MVP):
- `STRIPE_MODE` = test | live
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_GROWTH`
- `STRIPE_PRICE_ID_IMPACT`
- `STRIPE_CHECKOUT_SUCCESS_URL`
- `STRIPE_CHECKOUT_CANCEL_URL`

Recommended add (practical necessity for Portal return navigation):
- `STRIPE_PORTAL_RETURN_URL` (e.g., https://grantpilot.ngoinfo.org/dashboard)

If `STRIPE_PORTAL_RETURN_URL` is introduced, `ENV_VARS_REFERENCE.md` must be updated accordingly.

---

## 5) Stripe Checkout (Upgrade flow)

### 5.1 Endpoint: POST /api/billing/checkout
**Auth required.**

Request:
- `{ "plan": "GROWTH" | "IMPACT" }`

Behavior:
1. Validate requested plan against allowed paid plans for MVP.
2. Retrieve or create Stripe Customer:
   - If `users.stripe_customer_id` exists → use it
   - Else create a new customer in Stripe and persist the id on `users.stripe_customer_id`
3. Create Stripe Checkout Session (mode=subscription) with:
   - price id from env (`STRIPE_PRICE_ID_GROWTH` or `STRIPE_PRICE_ID_IMPACT`)
   - `success_url` = `STRIPE_CHECKOUT_SUCCESS_URL`
   - `cancel_url` = `STRIPE_CHECKOUT_CANCEL_URL`
   - `customer` = Stripe customer id
   - include metadata sufficient to map back to user:
     - `metadata.user_id` = our user UUID
     - `metadata.plan` = requested plan name
   - (recommended) `client_reference_id` = our user UUID
4. Return:
   - `{ "checkout_url": "<Stripe hosted checkout URL>" }`

**Important:** access is granted only after webhook confirms payment/subscription via Stripe event(s).  
Do not “optimistically upgrade” based on checkout creation.

---

## 6) Stripe Customer Portal (Self-service billing)

### 6.1 Endpoint: GET /api/billing/portal
**Auth required.**

Behavior:
1. If user has no `stripe_customer_id` → return a 400 with a clear message (“No billing account”).
2. Create Stripe Customer Portal session:
   - `customer` = stripe_customer_id
   - `return_url` = `STRIPE_PORTAL_RETURN_URL` (recommended) or another explicit frontend route
3. Return:
   - `{ "portal_url": "<Stripe portal session URL>" }`

### 6.2 Portal configuration (in Stripe Dashboard)
Configure Stripe Portal so users can:
- update payment method
- download invoices/receipts
- cancel subscription
- (optional) switch between Growth and Impact, if enabled

**We do not build any of these UIs ourselves.**

---

## 7) Webhooks (High-stakes: must be robust)

### 7.1 Endpoint: POST /api/billing/webhook
**No auth** (Stripe calls directly).

Mandatory steps:
1. Verify signature using `STRIPE_WEBHOOK_SECRET`
   - If verification fails → return 400 and log a security event (no processing).
2. Parse event.
3. **Event-store-first idempotency pattern:**
   - If `stripe_events` already has `event.id` → return 200 immediately
   - Insert raw event into `stripe_events` (must succeed before any mutation)
   - If insert fails → return 500 (Stripe will retry)
4. Process event by type (Section 8).
5. Update `stripe_events.processed_at`, `processing_result`, `error_message` accordingly.
6. Return 200 once persisted and processed successfully.

**Rule:** Returning 200 without persisting the raw event is not allowed.

### 7.2 Idempotency and ordering
- Stripe can deliver duplicates and out-of-order events.
- Idempotency is guaranteed by unique `stripe_event_id`.
- For out-of-order correctness, when in doubt, fetch the subscription object from Stripe using the subscription id present in the event and sync from that.

---

## 8) Event Types: What we sync (and what we don’t)

### 8.1 Minimal event set (MVP)
We process the following events:

#### A) checkout.session.completed
Purpose: initial activation after successful hosted checkout.

We sync:
- Identify user:
  - Prefer `metadata.user_id`
  - Fallback via `customer` → match to `users.stripe_customer_id`
- Derive subscription id from the session → set `user_plans.stripe_subscription_id`
- Determine plan_name from:
  - `metadata.plan` (preferred) AND/OR price id mapping
- Fetch subscription (recommended) and sync:
  - `billing_period_start`, `billing_period_end`
  - (optional) `stripe_status`

Result:
- Set `user_plans.plan_name = GROWTH|IMPACT`
- Set period boundaries
- Set `plan_activated_at` if not set (or update per your policy)

#### B) customer.subscription.updated
Purpose: plan change, renewal, cancel-at-period-end, status changes.

We sync from the subscription object:
- Price id → plan_name mapping (Growth vs Impact)
- `current_period_start`, `current_period_end` → billing period boundaries
- (optional) status (`active`, `past_due`, `trialing`, etc.)
- (optional) cancel_at_period_end flag

Access-control rule (MVP):
- Treat `active` and `trialing` as paid.
- Treat `past_due` as paid **during dunning** (Stripe retries); do not downgrade purely on payment_failed.
- Downgrade only when Stripe indicates cancellation/ended state (typically via subscription.deleted).

Quota reset rule:
- When `billing_period_start/end` moves forward (renewal), treat that as the new quota cycle boundary (per `PRICING_AND_ENTITLEMENTS.md`).

#### C) customer.subscription.deleted
Purpose: subscription ended/canceled.

We sync:
- Downgrade to FREE:
  - `user_plans.plan_name = FREE`
  - clear `stripe_subscription_id`
  - set billing period boundaries to NULL (or retain last known, per your schema policy)

#### D) invoice.payment_failed
Purpose: payment attempt failed (Stripe dunning begins).

We do:
- Record event outcome in `stripe_events`
- Optionally log an internal alert/metric
- **Do not downgrade** here. Stripe will retry and/or later cancel the subscription if it fails permanently.

### 8.2 Events we explicitly ignore (MVP)
Unless future scope expands, these are SKIPPED:
- `payment_intent.*` (Stripe internal mechanics)
- `charge.*`
- `invoice.created` (noise)
- `checkout.session.expired`

If an ignored event is persisted, it should be marked `processing_result=SKIPPED`.

---

## 9) Mapping Rules (Stripe → Plan)
We must derive plan_name deterministically.

Mapping:
- If Stripe subscription item price id == `STRIPE_PRICE_ID_GROWTH` → plan_name = GROWTH
- If Stripe subscription item price id == `STRIPE_PRICE_ID_IMPACT` → plan_name = IMPACT
- Otherwise → treat as unknown price id:
  - Do not mutate entitlements
  - Mark stripe_events as FAILED with “UNKNOWN_PRICE_ID”
  - Raise alert (misconfiguration risk)

**Never** infer plan tier from invoice amount or currency.

---

## 10) Failure Handling & Operational Recovery

### 10.1 Webhook persistence failure
If raw event insert fails:
- Return 500
- Stripe retries automatically
- No state mutation occurs, so no corruption

### 10.2 Processing failure after persistence
If processing fails:
- Mark stripe_events as FAILED with error_message
- Return 500 (so Stripe retries), OR return 200 after marking FAILED if you want manual replay only.
  - MVP recommendation: return 500 for transient errors; return 200 only for “permanent parse/config” errors to avoid infinite retries.

### 10.3 Manual reconciliation (admin-only, post-MVP optional)
If needed later, add an admin-only command/job:
- Given a user_id or stripe_customer_id, fetch the latest subscription from Stripe and re-sync `user_plans`.
This is a fallback, not the primary mechanism.

---

## 11) Security Requirements
- Stripe secrets must never be present in frontend.
- Webhook verification is mandatory; never process unverified requests.
- Store raw event payloads for audit, but avoid logging full payloads to application logs (PII risk).
- Ensure webhook endpoint is excluded from auth middleware but protected by signature verification.

---

## 12) Testing Strategy (MVP)
Use Stripe test mode + Stripe CLI:
- Confirm checkout session creation returns a valid URL.
- Complete a test checkout → verify webhook updates `user_plans` to GROWTH/IMPACT.
- Cancel subscription in portal → verify webhook downgrades to FREE.
- Trigger payment failure scenario → verify no downgrade occurs on `invoice.payment_failed`.

Definition of Done:
- Stripe checkout works end-to-end in test mode.
- Portal session works and returns to frontend.
- Webhooks persist-first and are idempotent.
- `user_plans` reflects Stripe reality after each billing action.
