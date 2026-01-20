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

$39/month (annual gets 2 months free): 3 proposals/month, limited Fit Scans, one-time onboarding assist

$79/month (annual gets 2 months free): 5 proposals/month, “unlimited” Fit Scans only for NGOInfo-published opportunities (must include fair-use controls), one-time onboarding assist, richer context limits

MVP constraints:

Upload-assisted onboarding allowed, but must be phased

MVP upload formats: PDF (text) + DOCX only

No OCR, no PPTX ingestion in MVP

No WordPress SSO in MVP (handoff via deep links + post-auth redirect)

Auth includes Google OAuth + email/password + password reset

Stack (locked):

Backend: FastAPI on Railway

Frontend: Next.js on Vercel

DB: PostgreSQL

File storage: S3-compatible object storage (not Postgres blobs)

Payments: Stripe

AI: OpenAI API

4) Claude’s review rules (anti-drift)

Claude must follow these rules while reviewing the 12 docs:

R1: Do not invent.
If information is missing, say “MISSING” and propose questions or placeholders, not new designs.

R2: Don’t broaden scope.
Do not propose features outside the MVP scope unless explicitly marked “defer”.

R3: Find contradictions.
If two docs conflict, cite both and flag the conflict.

R4: Every critique must map to a fix.
If you flag a gap, propose exactly what line/section should be added.

R5: Write for implementability.
Specs must be sufficient for Cursor to implement without guessing.

5) Definition of Done for the review

A document passes review when:

It contains enough detail for implementation

It contains no contradictions with other documents

It includes edge cases and failure modes where relevant

It avoids prohibited claims and language

It clearly states what is in/out of scope

6) Required output format (Claude must follow)

Claude must produce output in exactly this format:

A) Executive Summary

“Overall readiness score” (1–10) for this spec set

Top 5 risks to implementation

Top 5 missing items (if any)

B) Doc-by-doc review (for each of the 12 docs)

For each doc:

Status: PASS / PASS WITH CHANGES / FAIL

Missing sections (bullets)

Contradictions (bullets with doc references)

Ambiguities that would cause engineering guesswork

Concrete edits required (section headings + what to add)

C) Cross-cutting issues

Anything that spans multiple docs (e.g., auth vs WP handoff)

D) Final “No-Drift” checklist

List of assumptions Claude refused to make

List of questions for the founder

7) The 12 docs Claude will review (foundation set)

PRODUCT_NORTH_STAR.md

MVP_SCOPE_LOCK.md

PRICING_AND_ENTITLEMENTS.md

LAUNCH_JOURNEYS_SPEC.md

AUTH_AND_SSO_STRATEGY.md

WORDPRESS_TO_GRANTPILOT_INTEGRATION.md

FIT_SCAN_PRODUCT_SPEC.md

FIT_SCAN_CRITERIA_MATRIX.md

OPENAI_PROMPTS_LIBRARY.md

API_CONTRACT.md

STRIPE_INTEGRATION_SPEC.md

DEV_ENVIRONMENT_SETUP.md

Claude must not request new documents unless strictly necessary to validate these.

8) Final instruction

Claude must behave as a spec auditor, not a product ideation assistant.

If something is missing: label it MISSING, propose exact additions, and ask targeted questions.A8	NGOINFO_V2_POSITIONING.md	WordPress + GrantPilot narrative
#	Artefact	Purpose
B1	LAUNCH_JOURNEYS_SPEC.md	All journeys end-to-end
B2	ONBOARDING_AND_ACTIVATION_SPEC.md	First 10-minute experience
B3	WORDPRESS_TO_GRANTPILOT_INTEGRATION.md	CTA → app handoff
B4	WP_APP_HANDOFF_CONTRACT.md	URL formats, UTMs, redirect rules
B5	AUTH_AND_SSO_STRATEGY.md	Google + email auth
B6	ACCOUNT_SESSIONS_AND_DEVICE_RULES.md	Sessions, refresh, multi-device
B7	QUOTA_AND_BILLING_JOURNEYS.md	Warnings, exhaustion
B8	CANCELLATION_REFUND_AND_DUNNING_JOURNEYS.md	Failures, retries
B9	FAILURE_AND_RECOVERY_JOURNEYS.md	Graceful degradation
C. UX, UI & Trust Layer
#	Artefact	Purpose
C1	UI_SCREENS_SPEC.md	Screen-level requirements
C2	UX_COPY_AND_MICROCOPY.md	Human, trust-safe copy
C3	FORM_VALIDATION_AND_ERRORS.md	Field validation & messages
C4	EMPTY_LOADING_ERROR_STATES.md	Skeletons & retry UX
C5	UI_COMPONENT_LIBRARY.md	Reusable UI primitives
C6	DESIGN_TOKENS_AND_BRAND_USAGE.md	Prevent UI drift
C7	ACCESSIBILITY_BASELINE.md	A11y minimums
C8	TRUST_UX_AND_AI_DISCLOSURE.md	Explain Fit Scan + uncertainty
C9	ROUTING_AND_DEEPLINK_MATRIX.md	Every CTA → route mapping
D. Fit Scan (Primary moat)
#	Artefact	Purpose
D1	FIT_SCAN_PRODUCT_SPEC.md	What Fit Scan is / isn’t
D2	FIT_SCAN_CRITERIA_MATRIX.md	Eligibility, alignment, readiness
D3	FIT_SCAN_DATA_REQUIREMENTS.md	Required inputs
D4	FIT_SCAN_DECISION_LOGIC.md	Tie-breakers & overrides
D5	FIT_SCAN_OUTPUT_SCHEMA.json	Canonical explainable output
D6	FIT_SCAN_UI_SPEC.md	Visual breakdown
D7	FIT_SCAN_GUARDRAILS.md	Language & risk constraints
D8	CITATIONS_AND_EVIDENCE_POLICY.md	Evidence rules
E. Documents, Uploads & Profile Intelligence
#	Artefact	Purpose
E1	DOCUMENT_STORAGE_ARCHITECTURE.md	S3/R2 strategy
E2	UPLOAD_AND_PARSING_PIPELINE.md	Upload → extract → confirm
E3	PROFILE_SCHEMA.md	Canonical NGO profile
E4	PROFILE_EXTRACTION_SPEC.md	PDF/DOCX parsing
E5	CONFIDENCE_AND_CITATION_MODEL.md	Explain extraction
E6	PROFILE_VERSIONING_AND_CONFLICTS.md	Re-uploads & overrides
E7	DOCUMENT_LIMITS_BY_PLAN.md	Plan-based limits
E8	DOCUMENT_RETENTION_AND_PURGE_RULES.md	GDPR + cleanup
F. Proposal Workspace (Consultant-grade)
#	Artefact	Purpose
F1	PROPOSAL_WORKSPACE_SPEC.md	Section-based drafting
F2	RFP_REQUIREMENTS_MAPPING.md	Compliance matrix
F3	EVIDENCE_AND_ASSUMPTIONS_MODEL.md	Traceability
F4	READINESS_CHECK_SPEC.md	Pre-export validation
F5	EXPORT_AND_VERSIONING_SPEC.md	DOCX/PDF + versions
G. AI & Prompt Governance (NEW – critical)
#	Artefact	Purpose
G1	OPENAI_PROMPTS_LIBRARY.md	All system + task prompts
G2	PROMPT_VERSIONING_AND_CHANGELOG.md	Track regressions
G3	PROMPT_TESTING_AND_QUALITY.md	Output benchmarks
G4	PROMPT_FALLBACK_STRATEGIES.md	GPT failures & degradation
G5	PROMPT_INJECTION_AND_DATA_POISONING_DEFENSES.md	AI-specific threats
G6	AI_COST_AND_MODEL_STRATEGY.md	Model choice + cost ceilings
H. Backend Architecture & Contracts
#	Artefact	Purpose
H1	SYSTEM_ARCHITECTURE_OVERVIEW.md	Component diagram
H2	DOMAIN_MODEL.md	Module boundaries
H3	API_CONTRACT.md	Behavior rules
H4	OPENAPI_SPEC.yaml	FE/BE truth
H5	ERROR_HANDLING_STANDARD.md	Errors & request IDs
H6	EVENTS_CATALOG.md	Event-driven system
H7	IDEMPOTENCY_AND_RETRY_POLICY.md	Prevent duplicates
H8	RATE_LIMITING_AND_COST_GUARDS.md	Abuse & spend control
I. Data, Persistence & Seeding
#	Artefact	Purpose
I1	DB_SCHEMA.md	Tables & constraints
I2	MIGRATIONS_POLICY.md	Alembic discipline
I3	USAGE_AND_QUOTA_LEDGER.md	Enforcement
I4	DATA_RETENTION_AND_DELETION.md	User rights
I5	FUNDING_OPPORTUNITIES_SCHEMA_AND_SEEDING.md	Opportunity model
I6	CSV_IMPORT_EXPORT_SPEC.md	Weekly seeding
I7	SEED_DATA_STRATEGY.md	Dev/staging fixtures
J. Billing & Payments
#	Artefact	Purpose
J1	STRIPE_INTEGRATION_SPEC.md	Webhooks, lifecycle
J2	BILLING_PORTAL_AND_INVOICES.md	Customer self-service
J3	FAILED_PAYMENT_HANDLING.md	Retries, grace
K. Emails, Support & Communication
#	Artefact	Purpose
K1	TRANSACTIONAL_EMAILS_SPEC.md	Mandatory emails
K2	LIFECYCLE_EMAILS_PLAN.md	Activation & retention
K3	EMAIL_TEMPLATES_AND_VARIABLES.md	Template contract
K4	EMAIL_DELIVERABILITY_SETUP.md	SPF/DKIM/DMARC
K5	SUPPORT_INBOX_AND_SLA_RULES.md	Support ops
L. Frontend Architecture
#	Artefact	Purpose
L1	FRONTEND_APP_ARCHITECTURE.md	Routing & auth guards
L2	STATE_MANAGEMENT_STRATEGY.md	FE state discipline
L3	ERROR_BOUNDARY_STRATEGY.md	FE resilience
L4	PERFORMANCE_BUDGET.md	Load targets
M. Dev, Testing, Monitoring & Release (NEW – hard-won lessons)
#	Artefact	Purpose
M1	DEV_ENVIRONMENT_SETUP.md	Local + staging parity
M2	TESTING_STRATEGY.md	Unit → E2E
M3	ACCEPTANCE_TESTS_BY_JOURNEY.md	Release gates
M4	MONITORING_AND_ALERTS_SPEC.md	Metrics & alerts
M5	OBSERVABILITY_AND_DEBUG_RUNBOOK.md	Debug discipline
M6	RELEASE_AND_ROLLBACK_PLAYBOOK.md	Safe launches
M7	STAGING_ENVIRONMENT_POLICY.md	Controlled testing
N. AI / Dev Execution Governance
#	Artefact	Purpose
N1	AI_DEV_README.md	Cursor/Claude constitution
N2	CONTEXT_PACK_INDEX.md	Context minimisation
N3	CURRENT_STATE_AND_KNOWN_ISSUES.md	Prevent re-breaking
N4	TASK_BRIEF_TEMPLATE.md	Structured execution
N5	DEFINITION_OF_DONE.md	Completion checklist


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
- 🚧 OPENAI_PROMPTS_LIBRARY.md
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
- OPENAI_PROMPTS_LIBRARY.md  

Phase 3 – UX + Acquisition  
- LAUNCH_JOURNEYS_SPEC.md  
- WORDPRESS_TO_GRANTPILOT_INTEGRATION.md  

Rule:
Cursor/Claude must only implement artefacts marked ✅ or 🚧.
Nothing ⏸️ or ❌ may be implemented without explicit instruction.
