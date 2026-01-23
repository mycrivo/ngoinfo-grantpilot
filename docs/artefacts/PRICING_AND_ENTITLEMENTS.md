## Plans & Entitlements

### Free Plan
- Price: $0 
- Fit Scans: 1 / lifetime
- Proposals: 1 / lifetime (single full draft; no regeneration)
- Profile setup: Manual form only
- AI limits: Standard
- Uploads: Not allowed
- Once the fit scan and proposal quota is exhaused, show Growth plan upgrade CTA with a user friendly message
- Intended for evaluation only; not suitable for active grant pipelines


### Growth Plan
- Price: $39/month
- Fit Scans: 10 / month
- Proposals: 3 / month
- Profile setup: Manual form only
- AI limits: Standard
- Uploads: Not allowed

### Impact Plan
- Price: $79/month
- Fit Scans: 20 / month
- Proposals: 5 / month
- Profile setup: Manual Form Only
- AI limits: Higher context + stronger reasoning



## Quota Enforcement Rules

- Fit Scan quota exhausted:
  - Block Fit Scan initiation
  - Free Plan: show upgrade CTA (to Growth) with a user friendly message
  - Growth plan: show upgrade CTA (to Impact) with a user friendly message
  - Impact plan: show next reset date with a user friendly message
  - Show the date when the plan resets if the quota exhausted for Impact plan, with a user friendly message

- Proposal quota exhausted:
  - Block “Create Proposal” action
  - Existing proposals remain viewable
   - Free Plan: show upgrade CTA (to Growth) with a user friendly message
  - Show upgrade CTA for Growth plan, with a user friendly message
  - Show the date when the plan resets if the quota exhausted for Impact plan, with a user friendly message

## Rate Limits (MVP)
- Fit Scans:
  - Free: none after the first try, should be shown upgrade CTA (to Growth) with a user friendly message
  - Growth: max 3/hour
  - Impact: max 6/hour
  - Proposal regeneration:
  - Max 3 regenerations per proposal
  - Proposal creation: max 1 new proposal every 10 minutes (all plans) except Free. Free gets only 1 proposal in lefetime

 ## Quota Accounting Rules
  - Quota is decremented only after successful completion of the action:
  -   Fit Scan → after valid result is generated
  -   Proposal → after initial draft is generated
  - Failed or timed-out operations do not consume quota
  - Quota checks and decrements must be atomic and transactional


All enforcement is server-side.

## Export Rules (MVP)
- DOCX export is supported.
- PDF export is not supported.
