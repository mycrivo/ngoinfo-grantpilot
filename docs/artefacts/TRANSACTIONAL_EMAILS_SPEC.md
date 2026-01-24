Status: Canonical (LOCKED FOR BUILD)
Scope: Transactional email events for GrantPilot MVP
Non-goal: Marketing emails and newsletters (out of scope)

============================================================
1) Principles
============================================================

- Transactional emails are product-critical and must be reliable.
- Email sending must be:
  - asynchronous (queue/background task) where possible
  - idempotent (same event should not spam duplicates)
  - observable (logs/traceability)
- Sensitive data must not be included beyond what is needed.

============================================================
2) Email Provider & Env Vars
============================================================

Provider (MVP): Resend
From address: support@ngoinfo.org
Reply-to: support@ngoinfo.org

Required environment variables (names illustrative; align with your ENV_VARS_REFERENCE.md if present):
- EMAIL_PROVIDER
- EMAIL_API_KEY
- EMAIL_FROM
- EMAIL_REPLY_TO (optional)
- EMAIL_BASE_URL (public frontend URL used in links)
- EMAIL_SUPPRESS_SENDING=false|true (non-prod safety switch)

============================================================
3) Required Email Events (MVP)
============================================================

3.1 Authentication & Account
A) Magic Link Login
- Trigger: user requests magic link
- Template variables: login_link, expiry_minutes, support_email

B) Welcome / First Login (optional but recommended)
- Trigger: first successful login (new user created)
- Variables: dashboard_link, profile_link

C) Security Notice (optional)
- Trigger: login from new device/IP (future)
- MVP: do not implement unless fast

3.2 Profile
D) Profile Completion Confirmation
- Trigger: profile transitions from DRAFT to COMPLETE
- Variables: profile_link

3.3 Fit Scan
E) Fit Scan Result Ready
- Trigger: fit scan completes successfully
- Variables: fit_scan_link, opportunity_title, overall_fit_rating

F) Fit Scan Quota Exhausted
- Trigger: user attempts fit scan but quota exhausted
- Variables: upgrade_link (Free→Growth, Growth→Impact), reset_date (Impact), support_link

3.4 Proposals
G) Proposal Draft Ready
- Trigger: initial proposal draft completes successfully
- Variables: proposal_link, opportunity_title

H) Proposal Regeneration Completed
- Trigger: regeneration completes successfully (Growth/Impact only)
- Variables: proposal_link, regeneration_count_remaining

I) Proposal Quota Exhausted
- Trigger: user attempts proposal creation but quota exhausted
- Variables: upgrade_link or reset_date, support_link

J) DOCX Export Ready
- Trigger: export completes and file is available
- Variables: download_link, proposal_title

3.5 Billing / Subscription (Stripe)
K) Subscription Activated
- Trigger: Stripe webhook confirms subscription active
- Variables: plan_name, billing_portal_link

L) Payment Failed / Past Due
- Trigger: Stripe indicates payment failure
- Variables: billing_portal_link, grace_period_days (if any)

M) Subscription Cancelled
- Trigger: cancelled at period end or immediate cancel
- Variables: billing_portal_link, access_end_date

N) Plan Changed
- Trigger: upgrade/downgrade confirmed
- Variables: old_plan, new_plan, effective_date


### MVP Logging Strategy
  - Use Resend dashboard for delivery monitoring
  - Application logs include: user_id, email_to, template_name, timestamp
  - Post-MVP: Add email_events table for correlation and audit trail
  
============================================================
4) Idempotency & Logging
============================================================

Minimum logging requirements (MVP):
- Log one structured event per attempted send:
  - event_type
  - user_id (if applicable)
  - email_to
  - provider_message_id (if available)
  - status: queued|sent|failed|suppressed
  - error_code/error_message (if failed)
  - created_at

Optional (recommended) DB table: email_events
- If not adding a table in MVP, logs must include request_id/correlation_id.

Idempotency rule:
- For each event that can repeat, define a key:
  - Magic link: key = token id/hash
  - Proposal draft ready: key = proposal_id + "draft_ready"
  - Export ready: key = export_id
  - Subscription activated: key = stripe_event_id
- Do not send if a successful send already exists for the same key.

============================================================
5) Templates
============================================================

MVP template requirements:
- Keep copy short and explicit.
- Each template must declare:
  - Subject
  - Required variables
  - Primary CTA link

Do not embed large content blocks in emails (e.g., full proposal text). Use links.

============================================================
6) Non-Prod Safety
============================================================

- In non-prod, allow suppression to avoid emailing real users.
- Option: restrict outbound to allowlist domains (e.g., your own email) during staging.
