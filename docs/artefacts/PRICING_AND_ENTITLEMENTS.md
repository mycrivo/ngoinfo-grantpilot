## Plans & Entitlements

### Free Plan
- Price: $0
- Fit Scans: 1 / lifetime
- Proposals: 1 / lifetime (single full draft; **no regeneration**)
- Profile setup: Manual form only
- AI limits: Standard
- Uploads: Not allowed (NGO **profile** document uploads — see clarification below)
- M&E reports: Not available (upgrade to Impact)
- Once the Fit Scan and Proposal quota is exhausted, show Growth plan upgrade CTA with a user friendly message
- Intended for evaluation only; not suitable for active grant pipelines


### Growth Plan
- Price: $39/month
- Fit Scans: 10 / month
- Proposals: 3 / month
- Proposal regeneration: up to 3 regenerations per proposal
- Profile setup: Manual form only
- AI limits: Standard
- Uploads: Not allowed (NGO **profile** document uploads — see clarification below)
- M&E reports: Not available (upgrade to Impact)
- Support: Normal support


### Impact Plan
- Price: $79/month
- Fit Scans: 10 / month
- Proposals: 5 / month
- Proposal regeneration: up to 3 regenerations per proposal
- Profile setup: Manual form only
- AI limits: Higher context + stronger reasoning
- M&E reports: 2 / month (Donor Report Writer)
- M&E document uploads: Allowed (report-source documents)
- Support: Priority support



## Quota Enforcement Rules (Server-side only)

### Fit Scan quota exhausted
- Block Fit Scan initiation
- Free Plan: show upgrade CTA (to Growth) with a user friendly message
- Growth Plan: show upgrade CTA (to Impact) with a user friendly message
- Impact Plan: show next reset date with a user friendly message

### Proposal quota exhausted
- Block “Create Proposal” action
- Existing proposals remain viewable
- Free Plan: show upgrade CTA (to Growth) with a user friendly message
- Growth Plan: show upgrade CTA (to Impact) with a user friendly message
- Impact Plan: show next reset date with a user friendly message

### M&E report quota exhausted
- Free/Growth: no M&E allowance; any M&E entry shows upgrade-to-Impact CTA
- Impact: block new report creation after 2/billing cycle; show next reset date; no purchase path


## Upload clarification (MVP)

The **"Uploads: Not allowed"** line on Free and Growth (and profile setup on all plans) refers to **NGO profile document uploads** only. **M&E report-source document uploads** are a distinct capability: allowed on **Impact** only, enforced server-side on `/api/reports/{id}/documents`.


## Rate Limits (MVP)

### Fit Scans
- Free: not allowed after the first lifetime scan; show upgrade CTA (to Growth)
- Growth: max 3/hour
- Impact: max 6/hour

### Proposal creation
- Free: 1 proposal lifetime (no regeneration)
- Growth: max 1 new proposal every 10 minutes
- Impact: max 1 new proposal every 10 minutes

### Proposal regeneration
- Free: not allowed
- Growth: max 3 regenerations per proposal
- Impact: max 3 regenerations per proposal


## Quota Accounting Rules
- Quota is decremented only after successful completion of the action:
  - Fit Scan → after valid result is generated
  - Proposal → after initial draft is generated
  - Regeneration → after regenerated content is generated successfully
  - DOCX export → after first successful export of a proposal version (idempotent on re-download)
  - M&E report → decremented only after successful report generation (atomic; exact trigger state defined at implementation)
- Failed or timed-out operations do not consume quota
- Quota checks and decrements must be atomic and transactional


“Entitlements endpoint may initialize paid-plan period boundaries once if missing (fallback until Stripe sets billing cycle).”

Quota Reset Rules:
  - Reset occurs on billing cycle anniversary (not calendar month)
  - Triggered by Stripe subscription renewal webhook
  - If webhook fails, fallback: entitlements endpoint initializes period boundaries
  - M&E **reports** counter resets on the same billing-cycle anniversary as fit scans and proposals (Impact only)

## Export Rules (MVP)
- DOCX export is supported.
- PDF export is not supported.
- First export of a proposal version consumes proposal quota.
- Multiple downloads of the same version do not re-consume quota.
- Idempotency key for non-reconsumption: `user_id + proposal_id + proposal_version`.
- Proposal quota bucket reflects:
  - `PROPOSAL_CREATE` usage, and
  - first-time `DOCX_EXPORT` usage per proposal version.
