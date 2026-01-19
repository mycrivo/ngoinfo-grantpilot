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

If something is missing: label it MISSING, propose exact additions, and ask targeted questions.