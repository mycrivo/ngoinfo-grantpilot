LAUNCH_JOURNEYS_SPEC.md

Product: GrantPilot AI
Purpose: Define end-to-end user journeys and system behavior for all MVP flows
Audience: Founder, Cursor/Claude Code, backend/frontend engineers

1. Purpose & Authority of This Document

This document defines how GrantPilot AI is actually used by NGOs, from discovery to submission readiness.

It is the single source of truth for:

User flows and decision points

Gating logic (auth, profile, plan, quota)

System responses and messaging

Error handling and recovery behavior

Rule:
If a behavior is not explicitly defined here, it must not be implemented.

2. Core User Personas (MVP)

These personas explain why journeys differ by plan.

Persona A: Explorer NGO (Free → Growth)

Small or early-stage NGO

Unsure about eligibility

Time-poor, cost-sensitive

Wants reassurance before investing effort

Persona B: Active Applicant NGO (Growth)

Applies to multiple grants/year

Knows the basics but wants speed and structure

Will upgrade only if value is clear

Persona C: Serious / Consultant-Grade NGO (Impact)

Experienced NGO or consultant-supported

Wants high-quality, submission-ready proposals

Willing to invest if quality and rigor are evident

3. Canonical User Journeys (J1–J7)
J1. Discovery → Fit Scan (First-Time Entry from NGOInfo.org)

User intent

“Is this funding opportunity even worth my time?”

User uncertainty

“Am I eligible?”

“Will this be rejected outright?”

“Should I invest effort here?”

Trigger

User clicks CTA on NGOInfo.org funding opportunity:

“Check fit with GrantPilot AI”

Preconditions

Funding opportunity exists and is active

User may be authenticated or unauthenticated

Journey Flow

WordPress redirects to GrantPilot AI with context:

/start?opportunity_id={id}&source=wp


GrantPilot AI validates opportunity:

If invalid/expired → show friendly message + redirect to browse

Auth check:

If unauthenticated → redirect to login/signup

Context must be preserved across auth

Post-auth:

System checks minimal profile completeness

Fit Scan is initiated

User sees loading state with expectation setting

Fit Scan result is displayed

System Differentiation (vs ChatGPT)

Uses deterministic eligibility checks

Explicitly says “Not Recommended” when appropriate

Explains reasoning conservatively and clearly

Possible Outcomes

Recommended → CTA: “Draft proposal with GrantPilot AI”

Apply with Caveats → CTA: “Review gaps before drafting”

Not Recommended → CTA: “Browse other opportunities”

Failure & Edge Cases

Fit Scan quota exhausted → show plan-appropriate message

Profile too incomplete → prompt to complete key fields

AI timeout → show retry option without consuming quota

J2. Free User → First Proposal (Evaluation Journey)

User intent

“Let me see if this actually produces something usable.”

Preconditions

User on Free plan

Fit Scan quota available (1 lifetime)

Journey Flow

User clicks “Draft proposal”

System confirms this is a one-time evaluation

Proposal is generated once (no regeneration loops)

Proposal is shown with clear “Evaluation Copy” messaging

System Behavior

Proposal is complete and usable

Regeneration is not encouraged

Upgrade CTA appears after value is demonstrated

Quota Rules

Proposal quota is consumed only after successful generation

Failed generation does not consume quota

Exit States

User downloads proposal → prompted to upgrade

User returns later → blocked with friendly upgrade message

J3. Growth User → Ongoing Fit Scans & Proposals

User intent

“I’m actively applying and need efficiency.”

Preconditions

Growth plan active

Profile already exists

Journey Flow

User initiates Fit Scan (from WP or inside app)

System runs Fit Scan quickly using stored profile

User proceeds to proposal drafting

Proposal generation + limited regenerations allowed

User monitors quota unobtrusively

Quota Awareness

Quota is visible but not alarming

When near limit, system gently notifies

When exhausted:

Block action

Show upgrade CTA to Impact

Failure Handling

Regeneration failures → explain + retry

Token expiry mid-flow → silent refresh or re-auth

J4. Impact User → Consultant-Grade Workflow

User intent

“I want a serious, submission-ready proposal.”

Preconditions

Impact plan active

Journey Flow

Upload-assisted onboarding:

NGO uploads prior proposal / profile docs

System extracts structured profile with confidence flags

User reviews and confirms extracted data

Fit Scan runs with richer context

Proposal drafting uses:

NGO history

Past projects

Explicit assumptions

Consultant-Grade Behavior

Conservative language

Clear evidence grounding

Explicit caveats when data is weak

Less “creative writing,” more compliance-aware drafting

J5. Proposal Regeneration & Iteration

User intent

“This is close, but I want to refine it.”

System Rules

Max 3 regenerations per proposal

Each regeneration:

Explains what changed

Does not silently alter structure

Quota Handling

Regenerations consume regeneration allowance

Failed regenerations do not consume quota

UX Principle

Regeneration should feel intentional, not infinite.

J6. Export & Submission Readiness

User intent

“Can I submit this with confidence?”

Journey Flow

User clicks “Export proposal”

System runs readiness checks:

Missing sections

Weak assumptions

Warnings are shown (not blockers)

User exports DOCX (PDF export not supported)

Rules

Export consumes proposal quota

Multiple downloads of same version do not re-consume quota

Only latest version is exportable in MVP

J7. Errors, Recovery & Trust Preservation

Principle

Errors must never make the user feel blamed, confused, or misled.

Covered Scenarios

AI timeout

Malformed AI response

Auth token expiry

Stripe payment failure

App temporarily unavailable

System Behavior

Clear, calm, human messaging

Retry where safe

No quota loss on failures

Support escalation only if necessary

4. Cross-Journey Quota & Plan Rules

Quotas are checked before action

Quotas are decremented after success

All quota operations are atomic

Messaging differs by plan:

Free/Growth → upgrade CTA

Impact → reset date shown

5. Tone & Messaging Rules (Global)

No probabilistic or predictive claims

No AI-sounding language

Conservative, professional tone

Always explain why something happened

6. Explicitly Out of Scope (MVP)

GrantPilot AI must not:

Predict funding success

Rank NGOs

Suggest gaming applications

Imply guaranteed outcomes

Replace human judgment

Final Rule

This document is binding.
Cursor/Claude Code must not invent flows, shortcuts, or optimizations beyond what is defined here.

✅ Status

LAUNCH_JOURNEYS_SPEC.md — COMPLETE & BINDING