GrantPilot – FINAL v1 Artefact Table (Locked)

Rule: No production code is written unless the relevant artefacts exist and are referenced in the task brief.

A. Product & Strategy (Why this product exists)
#	Artefact	Purpose
A1	PRODUCT_NORTH_STAR.md	Vision, target NGOs, core problem, non-goals
A2	MVP_SCOPE_LOCK.md	Hard scope boundaries; prevents creep
A3	PRICING_AND_ENTITLEMENTS.md	$39 / $79 plans, limits, fair use
A4	VALUE_PROPOSITION_AND_MOAT.md	Differentiation vs Instrumentl, Grantable, ChatGPT
A5	NON_CLAIMS_AND_RISK_POSITIONING.md	Explicitly disallowed claims
A6	ICP_AND_PERSONAS.md	NGO archetypes, buying triggers
A7	SUCCESS_METRICS_AND_KPIS.md	Activation, conversion, retention targets
B. End-to-End User Journeys (Product contract)
0) Objective (Claude’s job)

You are reviewing 12 “foundation” specification documents for the GrantPilot ground-up rebuild.

Your job is NOT to design the product.
Your job is to validate completeness, internal consistency, and implementation readiness without inventing new features, new flows, new pricing, or new assumptions.

Output must be strictly grounded in the documents provided.

1) What GrantPilot is (non-negotiable)

GrantPilot is an AI-assisted, consultant-grade grant proposal workflow for NGOs, integrated with NGOInfo.org (WordPress) as the discovery layer.

North Star: Reduce wasted effort and improve submission readiness.

Core wedge: Fit Scan → Evidence-backed Drafting → Readiness Check → Export.

2) What GrantPilot is NOT (non-negotiable)

Claude must never introduce specs that imply:

guarantees of funding or success

probability of winning predictions

acting as a fundraising agent or donor intermediary

claims that outcomes will improve unless explicitly stated as “can help” or “aims to”

No “AI magic” claims.

3) Locked plan & constraints

Pricing (locked for MVP):

Free: $0 — 1 Fit Scan lifetime, 1 proposal lifetime

Growth: $39/month — 10 Fit Scans/month, 3 proposals/month

Impact: $79/month — 20 Fit Scans/month, 5 proposals/month

MVP constraints:

Upload-assisted onboarding allowed, but must be phased. Its not in scope for the current build, so ignore. 

MVP upload formats: None

No OCR, no PPTX ingestion in MVP

No WordPress SSO in MVP (handoff via deep links + post-auth redirect)

Auth includes Google OAuth + Email Magic Link (no passwords, password reset, or email verification)

Stack (locked):

Backend: FastAPI on Railway
Frontend: Next.js on Railway (Node runtime; server-rendered or hybrid as needed)
Edge/CDN: Cloudflare in front of grantpilot.ngoinfo.org (TLS, caching for static assets)
DB: PostgreSQL on Railway

File storage: S3-compatible object storage (not Postgres blobs)
Payments: Stripe
Email: Resend
AI: OpenAI API

Notes (non-negotiable):
- Frontend remains a “thin client”: no secrets, no Stripe secrets, no JWT signing keys.
- Backend remains the source of truth for auth, entitlements, quota, persistence, and AI execution.
- Cloudflare must NOT cache authenticated or user-specific routes.



## Completion Status (as of 2026-01-20)

Legend:
✅ Complete and binding  
🚧 In progress (blocking build until completed)  
⏸️ Deferred (explicitly post-MVP)  
❌ Missing (must be created before build)

### Core (Binding for MVP)
- ✅ CLAUDE_CODE_CONTEXT_PACK.md
- ✅ MVP_SCOPE_LOCK.md
- 🚧 PRICING_AND_ENTITLEMENTS.md
- 🚧 LAUNCH_JOURNEYS_SPEC.md
- 🚧 AUTH_AND_SSO_STRATEGY.md
- 🚧 FIT_SCAN_PRODUCT_SPEC.md
- 🚧 FIT_SCAN_CRITERIA_MATRIX.md
- 🚧 LLM_PROMPTS_LIBRARY.md
- 🚧 API_CONTRACT.md
- 🚧 STRIPE_INTEGRATION_SPEC.md
- 🚧 DEV_ENVIRONMENT_SETUP.md
- 🚧 WORDPRESS_TO_GRANTPILOT_INTEGRATION.md

### Explicitly Deferred (Post-MVP)
- Advanced analytics & dashboards
- Predictive scoring / win probability
- Human consultant review workflows
- Multi-org user roles
- White-label exports

## Build Sequencing (Non-Negotiable)

Phase 0 – Foundations  
- AUTH_AND_SSO_STRATEGY.md  
- API_CONTRACT.md  
- DEV_ENVIRONMENT_SETUP.md  

Phase 1 – Commercial Spine  
- PRICING_AND_ENTITLEMENTS.md  
- STRIPE_INTEGRATION_SPEC.md  

Phase 2 – Core Product  
- FIT_SCAN_PRODUCT_SPEC.md  
- FIT_SCAN_CRITERIA_MATRIX.md  
- LLM_PROMPTS_LIBRARY.md  

Phase 3 – UX + Acquisition  
- LAUNCH_JOURNEYS_SPEC.md  
- WORDPRESS_TO_GRANTPILOT_INTEGRATION.md  

Rule:
Cursor must only implement artefacts marked ✅ or 🚧.
Nothing ⏸️ or ❌ may be implemented without explicit instruction.
