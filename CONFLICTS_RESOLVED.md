CONFLICTS_RESOLVED.md

Purpose: log cross-artefact conflict fixes against locked MVP decisions.

Changes applied
- ARTEFACTS_V1_LOCKED.md: Updated plan names/quotas to Free/Growth/Impact with 1/10/20 Fit Scan limits and removed passwords; clarified auth is Google OAuth + Email Magic Link.
- CLAUDE_CODE_CONTEXT_PACK.md: Same pricing/auth alignment as above; removed password/reset/verification references.
- PRICING_AND_ENTITLEMENTS.md: Removed annual pricing; set DOCX-only upload note for Impact onboarding; added DOCX-only export rule and “no PDF export”; ensured quotas match locked numbers.
- MVP_SCOPE_LOCK.md: Switched auth to OAuth + Magic Link; removed password reset; removed annual mentions; set export to DOCX-only (no PDF).
- STRIPE_INTEGRATION_SPEC.md: Plans limited to Growth/Impact monthly using STRIPE_PRICE_ID_GROWTH / STRIPE_PRICE_ID_IMPACT; removed Pro/annual.
- AUTH_AND_SSO_STRATEGY.md: Removed password, reset, email verification; clarified OAuth + Magic Link only.
- TESTING_STRATEGY.md: Removed password/verification flows; added Magic Link; updated smoke flows to include plan selection + Stripe checkout/webhook entitlements + DOCX export; noted PDF export unsupported.
- LAUNCH_JOURNEYS_SPEC.md: Export journey now DOCX-only; PDF export explicitly unsupported.
- API_CONTRACT.md: Export clarified as DOCX-only (no PDF).
- WORDPRESS_TO_GRANTPILOT_INTEGRATION.md: Auth context clarified as Google OAuth or Email Magic Link.

Remaining checks
- No references remain to Pro plans, passwords/resets/verification, PDF export, or unlimited fit scans within edited artefacts.
