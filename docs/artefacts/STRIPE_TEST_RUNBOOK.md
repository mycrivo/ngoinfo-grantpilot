# STRIPE_TEST_RUNBOOK.md

## Purpose
Short, deterministic steps to validate Stripe billing in test mode (MVP).

## Required Environment Variables (no secrets shown)
- STRIPE_MODE=test
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_ID_GROWTH
- STRIPE_PRICE_ID_IMPACT
- STRIPE_CHECKOUT_SUCCESS_URL
- STRIPE_CHECKOUT_CANCEL_URL
- STRIPE_PORTAL_RETURN_URL (recommended)

## Stripe CLI Setup
1. Install Stripe CLI (https://stripe.com/docs/stripe-cli)
2. Authenticate:
```
stripe login
```

## Webhook Listener
Forward Stripe events to the running backend:
```
stripe listen --forward-to <BACKEND_BASE_URL>/api/billing/webhook
```

## Checkout Flow (Test)
1. Create a checkout session:
```
curl -X POST <BACKEND_BASE_URL>/api/billing/checkout \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"plan": "GROWTH"}'
```
2. Open the returned `checkout_url` and complete payment using a Stripe test card.

Expected DB state (after webhook delivery):
- `user_plans.plan_name = GROWTH`
- `user_plans.stripe_subscription_id` set
- `billing_period_start/end` set
- `stripe_events` contains the raw event and processing_result=SUCCESS

## Trigger Webhook Events (CLI)
```
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_failed
```

Expected effects:
- `checkout.session.completed` → plan set to GROWTH or IMPACT
- `customer.subscription.updated` → plan & billing period synced
- `customer.subscription.deleted` → plan downgraded to FREE
- `invoice.payment_failed` → no downgrade (event recorded only)

## Idempotency Check
Re-send the same event ID (Stripe may do this automatically). The backend should:
- return 200
- not double-apply user_plans changes
