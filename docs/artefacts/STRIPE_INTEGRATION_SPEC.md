Products

Growth Monthly (Stripe price id: STRIPE_PRICE_ID_GROWTH)

Impact Monthly (Stripe price id: STRIPE_PRICE_ID_IMPACT)

Webhooks

checkout.session.completed

invoice.payment_failed

customer.subscription.updated

Rules

Webhooks are source of truth

Idempotency keys required

Entitlements updated atomically

Failure Handling

Grace period

Downgrade after retries

User notification

Signature Verification (Implementation):
  - Use stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
  - On failure, return 400 and log security event
  - Never process unverified webhooks