TRANSACTIONAL_EMAILS_SPEC.md

Status: Canonical (LOCKED FOR MVP BUILD)
Scope: GrantPilot Transactional Emails (MVP)
Non-goal: Lifecycle / marketing / growth emails

This document defines the authoritative specification for all transactional emails sent by GrantPilot backend.

This file must be read alongside:

BRAND_AND_FRONTEND_SPEC.md

mvp_execution_plan_FINAL_2.md

API_CONTRACT.md

GUARDRAILS_RUNTIME_AND_SECURITY.md

ENV_VARS_REFERENCE.md

Only the email types defined in this file are allowed in MVP.

1) Scope – Final Transactional Email Set (MVP)

The following four email types are approved for MVP:

Magic Link Login

Welcome (First Successful Login – Magic Link or Google)

Proposal Draft Ready

Subscription Activated

All other emails (quota warnings, payment failures, lifecycle nudges, fit scan, DOCX export, etc.) are explicitly out of scope for MVP and must not be implemented unless this document is updated.

2) Core Principles

Transactional emails are:

Product-critical

User-trust critical

Security-sensitive

Brand-defining

They must be:

Idempotent (no duplicates for same event)

Secure (no sensitive token leakage)

Deterministic (clear trigger conditions)

Observable (structured logging)

Brand-consistent (as per BRAND_AND_FRONTEND_SPEC.md)

Failure to send a non-authentication email must not crash the core product flow.

3) Brand & Visual Governance

All emails must strictly follow BRAND_AND_FRONTEND_SPEC.md.

3.1 Brand Hierarchy

Header must always display:

NGOInfo
GrantPilot
AI-powered funding intelligence

Order must not change.

AI must never dominate product naming.

Product name remains:
NGOInfo GrantPilot

Never use:

GrantPilot AI

NGOINFO’S GrantPilot AI

3.2 Logo Usage

Logo must use the canonical public URL defined in BRAND_AND_FRONTEND_SPEC.md.

Logo must be hosted on ngoinfo.org

Must use HTTPS

Must not be base64 embedded unless explicitly approved

Must not reference Railway URLs

3.3 Layout Rules

All emails must:

Use max width 600px

White background

Primary CTA in brand primary color

Clear H1 title

Single primary CTA

Plain-text fallback version

No marketing banners

No emojis

No hype language

4) Provider & Environment Variables

Provider (MVP): Resend

Env vars must match ENV_VARS_REFERENCE.md exactly.

Required:

EMAIL_PROVIDER

EMAIL_API_KEY

EMAIL_FROM_NAME

EMAIL_FROM_ADDRESS

EMAIL_SUPPRESS_SENDING

No illustrative or placeholder names allowed.

All user-facing links must use the public frontend base URL (never Railway internal URLs).

5) Idempotency (Mandatory)

Idempotency is REQUIRED.

An email_events table (or equivalent) must exist.

Minimum fields:

id

event_key (UNIQUE)

event_type

user_id

to_email

status (sent | failed | suppressed)

provider_message_id

error_message (safe, truncated)

created_at

Before sending:

Check event_key uniqueness

Do not send if already successfully sent

Event Keys:

Magic Link:
token_id or token_hash

Welcome:
user:{user_id}:welcome

Proposal Draft Ready:
proposal:{proposal_id}:draft_ready

Subscription Activated:
stripe:{stripe_event_id}:subscription_activated

6) Non-Production Safety

If EMAIL_SUPPRESS_SENDING=true:

Do not call provider

Log status = suppressed

Still record event row

Do not error

Optional (recommended):
Allowlist outbound domains in staging.

7) Email Specifications
7.1 Magic Link Login

Trigger:
User requests magic link.

Subject:
Your secure login link – NGOInfo

Title:
Secure access to your NGOInfo account

Body:

You requested secure access to your NGOInfo GrantPilot account.

Use the button below to log in securely.

Primary CTA:
Log in to NGOInfo GrantPilot

Button URL:
Full magic link URL (token must not be displayed prominently)

Security Block (small text):

This link is personal to you.

It expires in 15 minutes.

Do not forward this email.

Fallback:
Plain-text URL included below button.

Security Rules:

Token must never be logged.

Token must never appear in structured logs.

Access/refresh tokens must never be emailed.

Failure Behavior:

If provider fails:
Return 500 only if API_CONTRACT requires it for magic link request.
Otherwise log safely.

7.2 Welcome Email (First Login Only)

Trigger:

First successful login event for a user, regardless of provider:

Magic Link first successful login

Google OAuth first successful login

Must send only once.

Detection Logic:

If user.first_login_at is null:

Set first_login_at

Send welcome email

Event Key:
user:{user_id}:welcome

Subject:
Welcome to NGOInfo

Title:
Welcome to NGOInfo GrantPilot

Body:

You’re now part of a growing community of NGOs using smarter tools to find funding and develop stronger proposals.

NGOInfo was created to support organisations navigating complex funding landscapes with clarity and structure.

GrantPilot is our AI-powered funding assistant. It helps you:

Assess donor fit

Generate structured proposal drafts

Refine submissions

Maintain proposal history

We believe technology should strengthen organisations creating real change.

If you ever have feedback, you can simply reply to this email.

Primary CTA:
Go to Dashboard

Secondary Text Link:
Explore NGOInfo.org

This email must never resend on subsequent logins.

7.3 Proposal Draft Ready

Trigger:
Initial proposal draft generation completes successfully and is persisted.

Event Key:
proposal:{proposal_id}:draft_ready

Subject:
Your proposal draft is ready – NGOInfo

Title:
Your proposal draft is ready

Body:

Your AI-generated proposal for:

[Opportunity Title]

is now available inside your NGOInfo GrantPilot dashboard.

You can review, refine, or export your draft at any time.

Primary CTA:
View Proposal

Link Policy:

Must use public frontend URL

Must not use Railway URL

Failure Behavior:

Must not block proposal creation response.

7.4 Subscription Activated

Trigger:
Stripe webhook confirms subscription activation and plan is persisted.

Event Key:
stripe:{stripe_event_id}:subscription_activated

Subject:
Your subscription is active – NGOInfo

Title:
Your plan is now active

Body:

Your [Plan Name] plan is now active within NGOInfo GrantPilot.

You now have access to:

Proposal generation

Fit scoring

Proposal history

Primary CTA:
Manage Billing

Link:
Stripe billing portal session URL (generated via existing billing service logic)

Failure Behavior:

Must not block webhook response.
Webhook must still return 200 if email fails.

8) Logging & Observability

For every send attempt:

Log structured event:

event_type

user_id

to_email

event_key

status

provider_message_id (if available)

timestamp

Never log:

Magic link token

Access tokens

Refresh tokens

Stripe secrets

9) Explicitly Out of Scope (MVP)

The following are NOT part of this spec:

Lifecycle conversion emails (3 / 10 / 21 day)

Quota exhaustion

Fit scan ready

DOCX export ready

Payment failed

Renewal reminders

Upgrade prompts

These require a separate Lifecycle Email Strategy document.

END OF FILE