# FRONTEND_ARCHITECTURE_SPEC.md

**Status:** Canonical — Frontend Build Guide  
**Version:** 1.0  
**Last Updated:** 2026-02-09  
**Depends On:** LAUNCH_JOURNEYS_SPEC.md, API_CONTRACT.md, AUTH_AND_SSO_STRATEGY.md, PRICING_AND_ENTITLEMENTS.md, mvp_execution_plan_FINAL_2.md  
**Stack:** Next.js 15 (App Router), React, Tailwind CSS, hosted on Railway  

---

## 0. Two-Platform Architecture

GrantPilot operates across two platforms with distinct roles:

| Platform | Role | What Lives Here |
|----------|------|-----------------|
| **NGOInfo.org** (WordPress) | Showroom + Discovery | Marketing pages, funding opportunity listings, blog, pricing display, SEO content, "Browse Funding Opportunities" experience |
| **grantpilot.ngoinfo.org** (Next.js) | Workspace + Execution | Auth, NGO profile, Fit Scan results, proposal generation, export, billing management |

**The handoff:** Users discover opportunities on WordPress → click "Check Fit with GrantPilot AI" → land on the GrantPilot app with opportunity context preserved. This is the primary acquisition funnel.

**Design principle:** The GrantPilot app should feel like a focused workspace, not a marketing site. WordPress is the showroom — GrantPilot is where work happens. Clean, professional, tool-like. Think Notion or Linear, not a landing page.

---

## 1. Design Language

### 1.1 Visual Continuity with NGOInfo

From the WordPress design (attached screenshot), the NGOInfo brand uses:
- **Primary colour:** Deep blue/navy (`#1a1f71` range) for headers and primary CTAs
- **Accent colour:** Purple/violet gradient for highlight sections
- **Secondary accent:** Orange/coral for secondary CTAs ("Buy Now" buttons)
- **Typography:** Clean sans-serif, professional weight
- **Tone:** Trustworthy, institutional, not flashy

The GrantPilot app should complement this but shift toward a **workspace aesthetic**:
- Retain the navy/blue primary for brand continuity
- Use white/light grey backgrounds for workspace areas (readability over style)
- Reserve colour for status indicators and CTAs, not decoration
- Typography: one professional sans-serif family (e.g., DM Sans, Source Sans 3, or similar — NOT Inter, NOT system defaults)
- Minimal decoration — the content IS the interface

### 1.2 Status Colour System

These colours appear repeatedly across Fit Scan results, proposal sections, and quota indicators:

| Status | Colour | Usage |
|--------|--------|-------|
| RECOMMENDED / GENERATED / STRONG / HIGH | Green (e.g., `emerald-600`) | Positive outcomes |
| APPLY_WITH_CAVEATS / MODERATE / MEDIUM | Amber (e.g., `amber-500`) | Caution states |
| NOT_RECOMMENDED / WEAK / LOW / FAILED | Red (e.g., `rose-600`) | Negative outcomes or failures |
| MANUAL_REQUIRED / Informational | Slate/grey | Neutral, requires action |
| Upgrade CTA | Brand purple/primary | Commercial upsell |

### 1.3 Tone of UI Copy

Per LAUNCH_JOURNEYS_SPEC.md Section 5:
- No probabilistic or predictive claims
- No AI-sounding language ("powered by advanced AI", "leveraging machine learning")
- Conservative, professional tone
- Always explain WHY something happened
- Errors never blame the user

---

## 2. Page Map & Navigation

### 2.1 Complete Page List

```
PUBLIC (no auth required)
├── /login                          Login / signup page
├── /auth/callback                  OAuth + magic link token exchange (invisible handler)
├── /auth/magic-link                Magic link landing (from email click)
├── /start?opportunity_id=X         WordPress handoff entry point
│
AUTHENTICATED (auth required — redirect to /login if no session)
├── /dashboard                      Home — overview of fit scans, proposals, quota
├── /profile                        NGO profile form (create + edit)
├── /profile/completeness           Profile completeness detail (could be section of /profile)
├── /fit-scan/{id}                  Fit Scan result detail
├── /proposal/new?opportunity_id=X  Proposal generation (loading → result)
├── /proposal/{id}                  Proposal viewer (sections, status, actions)
├── /proposal/{id}/export           Export confirmation + download trigger
├── /billing                        Plan info, quota usage, upgrade/manage billing
├── /billing/success                Post-checkout success (Stripe redirect landing)
├── /billing/cancel                 Post-checkout cancel (Stripe redirect landing)
```

### 2.2 Navigation Structure

**Sidebar or top nav (authenticated pages):**

```
[GrantPilot Logo]

Dashboard              → /dashboard
My Profile             → /profile
Plans & Billing        → /billing

[User avatar/name]
  └── Logout
```

That's it. Three nav items plus logout. Fit scans and proposals are accessed FROM the dashboard or from WordPress deep links — they don't need top-level nav.

**No navigation on public pages** (login, callback, start). These are single-purpose entry points.

### 2.3 Mobile Considerations

MVP is desktop-first but must be usable on tablet. Proposal content is long-form text — mobile phone is not the primary use case for NGO grant writers. Use responsive Tailwind but don't over-invest in mobile-specific layouts for MVP.

---

## 3. Page-by-Page Specification

---

### 3.1 `/start` — WordPress Handoff Entry Point

**Journey:** J1 (Discovery → Fit Scan)  
**Purpose:** Receive context from WordPress, gate through auth + profile, then initiate Fit Scan  
**This is the most critical page — it's the primary acquisition funnel.**

**URL:** `/start?opportunity_id={uuid}&source=wp`

**Flow (state machine):**

```
1. Parse opportunity_id from URL
   ├── Missing/invalid → Error state: "This opportunity link is invalid. Browse opportunities on NGOInfo.org" [link]
   │
2. Check auth
   ├── Not authenticated → Store opportunity_id in sessionStorage → Redirect to /login
   │                       (after login, /auth/callback reads sessionStorage and redirects back to /start)
   │
3. Validate opportunity (GET /api/fit-scans endpoint will validate, or add a lightweight opportunity check)
   ├── Opportunity not found / inactive → Error: "This opportunity is no longer available." [Browse other opportunities]
   │
4. Check profile completeness (GET /api/ngo-profile/completeness)
   ├── Profile missing → Redirect to /profile with banner: "Complete your profile to check fit"
   ├── Profile DRAFT (missing required fields) → Redirect to /profile with specific missing fields highlighted
   │
5. Check Fit Scan quota (from GET /api/me/entitlements)
   ├── Quota exhausted → Show upgrade message per plan (see Section 5)
   │
6. Initiate Fit Scan (POST /api/fit-scans)
   ├── Show loading state: "Checking your eligibility and fit..."
   ├── Expectation setting text: "This usually takes 15-30 seconds"
   │
7. Display result → Redirect to /fit-scan/{id}
```

**Loading state design:**
- Progress indicator (not a spinner — a stepped progress bar or animated status)
- Brief text explaining each step: "Checking eligibility..." → "Assessing alignment..." → "Evaluating readiness..."
- No fake progress — use real status if possible, or a simple "Analysing..." animation

**Key principle:** This page should feel like a funnel, not a form. The user clicked a CTA on WordPress with intent — get them to their result as fast as possible with minimum friction.

---

### 3.2 `/login` — Authentication Page

**Journey:** J1 (auth gate), all journeys  
**Purpose:** Sign in or sign up via Google OAuth or Email Magic Link

**Layout:**
```
┌─────────────────────────────────────────┐
│                                         │
│         [GrantPilot Logo]               │
│                                         │
│    Sign in to GrantPilot                │
│                                         │
│    [Continue with Google] ← primary     │
│                                         │
│    ──── or ────                         │
│                                         │
│    Email: [________________]            │
│    [Send Magic Link]       ← secondary  │
│                                         │
│    New here? We'll create your account  │
│    automatically.                       │
│                                         │
└─────────────────────────────────────────┘
```

**Behaviour:**
- "Continue with Google" → calls `GET /api/auth/google/start` → redirects to Google
- "Send Magic Link" → calls `POST /api/auth/magic-link/request` → shows confirmation: "Check your email. We sent a login link to {email}."
- No separate signup page — account creation is implicit on first login
- If user came from `/start` (opportunity context), show subtle context: "Sign in to check your fit for [Opportunity Title]"

**States:**
- Default (form)
- Magic link sent (confirmation message)
- Error (rate limited, email error)
- Loading (during Google redirect)

**API calls:**
- `GET /api/auth/google/start` → get authorization URL
- `POST /api/auth/magic-link/request` → send magic link

---

### 3.3 `/auth/callback` — Token Exchange Handler

**Purpose:** Invisible page that handles post-OAuth and post-magic-link token exchange

**This page has no UI** (or minimal "Signing you in..." spinner). It's purely functional:

**OAuth flow:**
1. Extract `code` and `state` from URL query params
2. Call `POST /api/auth/exchange` with `{ "code": auth_code }`
3. Receive tokens + user
4. Store access_token and refresh_token in memory (React state/context — NOT localStorage)
5. Decode `state` to get redirect intent (opportunity_id)
6. If opportunity_id exists → redirect to `/start?opportunity_id={id}`
7. If no redirect intent → redirect to `/dashboard`

**Magic link flow:**
- Handled separately at `/auth/magic-link?token=xxx`
- Calls `POST /api/auth/magic-link/consume` with token
- Same token storage + redirect logic

**Error handling:**
- Invalid/expired code → redirect to `/login` with error message
- Network failure → retry once, then show error with "Try again" link

---

### 3.4 `/dashboard` — Home

**Journey:** J3, J4 (returning users)  
**Purpose:** Overview of recent activity, quick access to fit scans and proposals, quota awareness

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Dashboard                                                │
│                                                          │
│ ┌─ Quota Overview ────────────────────────────────────┐ │
│ │  Plan: Growth          Resets: March 12, 2026       │ │
│ │  Fit Scans: 3 of 10   Proposals: 1 of 3            │ │
│ │  [Manage Plan]                                      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ ┌─ Profile Status ────────────────────────────────────┐ │
│ │  ● Complete (85%)     [Edit Profile]                │ │
│ │  Tip: Adding budget info strengthens fit scans      │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                          │
│ Recent Fit Scans                                         │
│ ┌──────────────────────────────────────────────────────┐ │
│ │  USAID Climate Resilience Fund    RECOMMENDED    →   │ │
│ │  UK Aid Direct Grant              CAVEATS        →   │ │
│ │  Swiss SNSF Partnership           NOT REC.       →   │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ My Proposals                                             │
│ ┌──────────────────────────────────────────────────────┐ │
│ │  USAID Climate Fund    4/5 sections    [View] [Export]│ │
│ │  Draft · Created Feb 8                               │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ [Check fit for a new opportunity →]                      │
│   (links to NGOInfo.org funding listings)                │
└──────────────────────────────────────────────────────────┘
```

**API calls on page load (MVP):**
- `GET /api/me/entitlements` → quota + plan info
- `GET /api/ngo-profile/completeness` → profile status

**Recent activity panels (MVP):**
- CTA-first (no backend list calls)
- “Recent Fit Scans” and “My Proposals” render empty states + CTAs
- Optional: show “last created in this session” links (in-memory only; no persistence)

**Post-MVP enhancement (deferred):**
If/when we add list endpoints to `API_CONTRACT.md`:
- `GET /api/fit-scans` → list user's fit scans (newest first)
- `GET /api/proposals` → list user's proposals (newest first)
Then update `/dashboard` to show “last 5 items” for each list.
Until then, the MVP dashboard MUST NOT depend on list endpoints.

**Empty states:**
- No fit scans yet → "Find funding opportunities on NGOInfo.org and check your fit" [Browse Opportunities →]
- No proposals yet → "Run a Fit Scan first, then generate your proposal"
- Profile incomplete → prominent banner: "Complete your profile to get started" [Complete Profile →]

---

### 3.5 `/profile` — NGO Profile Form

**Journey:** J1 (profile gate), J3, J4 (profile maintenance)  
**Purpose:** Create and edit the NGO profile used for fit scans and proposals

**This is the most complex form in the app.** It needs to feel manageable, not overwhelming.

**Structure: Multi-section form (single page, scrollable sections — NOT multi-step wizard)**

Why single page, not a wizard: NGO staff may already know some fields and want to skip around. A wizard forces sequential completion. A single scrollable form with clear sections and a floating progress indicator lets users fill in any order.

**Sections:**

```
┌─ Profile Completeness Bar ──────────────── 65% ─────┐
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░                             │
│  Missing: Past Projects, Target Groups               │
└──────────────────────────────────────────────────────┘

Section 1: Organisation Identity (REQUIRED)
├── Organisation Name *         [text input]
├── Country of Registration *   [searchable dropdown — full country names]
├── Year of Establishment       [number input]
├── Website                     [URL input]
├── Contact Person Name         [text input]
├── Contact Email               [email input]

Section 2: Mission & Focus (REQUIRED)
├── Mission Statement *         [textarea, 200-500 chars recommended]
├── Focus Sectors *             [multi-select tags: Education, Health, Agriculture, WASH, 
│                                Governance, Climate, Gender, Livelihoods, Protection, Other]
├── Geographic Areas of Work *  [tag input — free-form: "Kisumu County", "Northern Uganda", etc.]
├── Target Groups *             [tag input — free-form: "Women farmers", "Youth", "Refugees", etc.]

Section 3: Track Record (REQUIRED — at least 1 past project)
├── Past Projects *             [repeatable card entry]
│   ├── Project Title *         [text]
│   ├── Donor/Funder            [text]
│   ├── Duration                [text, e.g., "2022-2024"]
│   ├── Location                [text]
│   └── Summary                 [textarea]
│   [+ Add another project]

Section 4: Capacity (OPTIONAL — but strengthens fit scans)
├── Full-Time Staff             [number]
├── Annual Budget Amount        [number]
├── Annual Budget Currency      [dropdown: USD, GBP, EUR, INR, KES, etc.]
├── M&E Practices               [textarea]
├── Previous Funders            [tag input — free-form: "USAID", "DFID", "Ford Foundation"]

[Save Profile]
```

**Field marking:**
- `*` = Required for COMPLETE status
- Grey helper text below each field explaining what it's used for
- e.g., under Focus Sectors: "Select the thematic areas your organisation works in. These are matched against funder requirements."

**Completeness indicator:**
- Floating/sticky progress bar at top showing completeness %
- Lists which required fields are still missing
- When all required fields are complete → green banner: "Profile complete — you can now run Fit Scans"

**Past Projects UX:**
- Collapsible card for each project
- "Add project" button adds a new card
- At least 1 project with a title is required for COMPLETE status
- Recommendation text: "Adding more projects with outcomes helps generate stronger proposals"

**API calls:**
- On load: `GET /api/ngo-profile` → populate form (404 means first-time → empty form)
- On save: `POST /api/ngo-profile` (create) or `PUT /api/ngo-profile` (update)
- After save: `GET /api/ngo-profile/completeness` → update completeness indicator

**Save behaviour:**
- Save button always saves everything (not per-section)
- After save, re-fetch completeness and update the progress bar
- If profile transitions from DRAFT → COMPLETE, show success message
- If user came from `/start` (opportunity context), show "Profile complete — checking your fit now..." and redirect back to `/start`

---

### 3.6 `/fit-scan/{id}` — Fit Scan Result

**Journey:** J1 (result display), J3, J4  
**Purpose:** Display the Fit Scan assessment with clear recommendation and actionable next steps

**This is where GrantPilot proves its value. The result must feel authoritative, not generic.**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                    │
│                                                          │
│  Fit Scan: USAID Climate Resilience Fund 2026           │
│  Scanned: Feb 8, 2026                                   │
│                                                          │
│  ┌─ Overall Recommendation ──────────────────────────┐  │
│  │                                                    │  │
│  │   🟢 RECOMMENDED                                  │  │
│  │                                                    │  │
│  │   "Your organisation's focus on climate-smart      │  │
│  │   agriculture in East Africa aligns well with      │  │
│  │   this opportunity. Strong thematic and geographic  │  │
│  │   alignment, with adequate documentation readiness."│  │
│  │                                                    │  │
│  │   [Draft Proposal with GrantPilot AI →]            │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Scores ──────────────────────────────────────────┐  │
│  │  Eligibility    ████████████████████  100          │  │
│  │  Alignment      ████████████████░░░░   80          │  │
│  │  Readiness      ██████████████░░░░░░   70          │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Risk Flags ──────────────────────────────────────┐  │
│  │  ⚠ TIMING (HIGH) — Deadline in 12 days            │  │
│  │  ⚠ EVIDENCE (MEDIUM) — No past projects in this   │  │
│  │    thematic area                                   │  │
│  │  ℹ PROCESS (LOW) — 8 submission items required     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Recommended Modifications ───────────────────────┐  │
│  │  • Strengthen proposal with local climate data     │  │
│  │  • Add M&E framework with specific indicators     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Recommendation display by outcome:**

| Outcome | Colour | CTA |
|---------|--------|-----|
| RECOMMENDED | Green banner | "Draft Proposal with GrantPilot AI →" |
| APPLY_WITH_CAVEATS | Amber banner | "Review Gaps, Then Draft Proposal →" |
| NOT_RECOMMENDED | Red banner (softer) | "Browse Other Opportunities →" (links to NGOInfo.org) |

**Data source:** `GET /api/fit-scans/{id}` response

**Score bars:**
- Visual progress bars (0-100) with colour coding: green (70+), amber (40-69), red (<40)
- Numeric score shown alongside

**Risk flags:**
- Severity-based icons: HIGH = red warning, MEDIUM = amber, LOW = grey info
- Each flag has a description from the API response

**CTA logic:**
- RECOMMENDED or CAVEATS → show "Draft Proposal" button → navigates to `/proposal/new?opportunity_id={opp_id}&fit_scan_id={scan_id}`
- NOT_RECOMMENDED → show "Browse Other Opportunities" → links to NGOInfo.org funding listings
- Free plan and fit scan used → additionally show subtle upgrade CTA below

---

### 3.7 `/proposal/new` — Proposal Generation

**Journey:** J2 (first proposal), J3, J4  
**Purpose:** Generate a proposal from a Fit Scan result

**URL:** `/proposal/new?opportunity_id={uuid}&fit_scan_id={uuid}`

**This is a loading/progress page, not a form.** The user already provided inputs via their profile and the fit scan. Proposal generation is a backend operation.

**Flow:**
```
1. Pre-flight checks (before calling API):
   ├── Verify auth
   ├── Show opportunity title and fit scan summary
   ├── Free plan: show one-time evaluation notice
   │   "This is your one-time evaluation proposal. Make it count!"
   │   [Generate Proposal] ← explicit user confirmation
   │
2. Call POST /api/proposals
   ├── Show generation progress:
   │   "Generating your proposal..."
   │   "Analysing funder requirements..."
   │   "Writing executive summary..."       ← timed text rotation
   │   "Drafting approach section..."
   │   "This usually takes 30-60 seconds"
   │
3. On success → redirect to /proposal/{id}
   On total failure → show error with retry option
```

**Why explicit confirmation before generation:**
- It consumes quota
- Free users get exactly 1 proposal — they should understand this
- Growth/Impact users should see which opportunity they're generating for

**API call:** `POST /api/proposals { funding_opportunity_id, fit_scan_id }`

---

### 3.8 `/proposal/{id}` — Proposal Viewer

**Journey:** J2, J3, J4, J5 (viewing + regeneration), J6 (export)  
**Purpose:** Display the generated proposal with per-section status and actions

**This is the centrepiece of the product. Where the user sees the value.**

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                                    │
│                                                          │
│  Proposal: USAID Climate Resilience Fund 2026           │
│  Version 1 · Generated Feb 8, 2026                      │
│  Status: 4 of 5 sections generated · 1 failed           │
│                                                          │
│  [Regenerate (2 remaining)] [Export DOCX ↓]             │
│                                                          │
│  ┌─ Section Navigation (sidebar or tabs) ─────────────┐ │
│  │  ✅ Executive Summary                               │ │
│  │  ✅ Problem Statement                               │ │
│  │  ✅ Approach & Methodology                          │ │
│  │  ❌ M&E Framework (Failed)                          │ │
│  │  📝 Budget Template (Manual Required)               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─ Active Section Content ──────────────────────────┐  │
│  │                                                    │  │
│  │  EXECUTIVE SUMMARY                                 │  │
│  │  ──────────                                        │  │
│  │                                                    │  │
│  │  Women Empowerment Initiative has trained 1,200    │  │
│  │  women farmers in climate-smart agriculture across │  │
│  │  Kisumu, Siaya, and Busia counties since 2021...   │  │
│  │                                                    │  │
│  │  ┌─ Assumptions ─────────────────────────────────┐ │  │
│  │  │  • Baseline data will be collected in Month 1  │ │  │
│  │  └───────────────────────────────────────────────┘ │  │
│  │                                                    │  │
│  │  ┌─ Evidence Used ───────────────────────────────┐ │  │
│  │  │  • prompt_inputs.ngo.past_projects            │ │  │
│  │  │  • prompt_inputs.ngo.mission_statement        │ │  │
│  │  └───────────────────────────────────────────────┘ │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Section status rendering:**

| Status | Icon | Section Appearance |
|--------|------|--------------------|
| `GENERATED` | ✅ | Full content shown, readable, copy-friendly |
| `FAILED` | ❌ | Red banner: "This section could not be generated. It will be retried on regeneration, or write it manually." |
| `MANUAL_REQUIRED` | 📝 | Grey banner: "This section requires manual input. GrantPilot cannot generate this content (e.g., budget templates, uploaded documents)." |

**Section navigation:**
- Left sidebar (desktop) or horizontal tabs (tablet)
- Each section shows status icon + label
- Click to scroll to section or switch active tab

**Actions:**
- **Regenerate:** Button shows remaining count: "Regenerate (2 remaining)"
  - Free plan: button hidden/disabled with tooltip "Upgrade to regenerate"
  - 0 remaining: disabled with "Regeneration limit reached"
  - Clicking triggers `POST /api/proposals/{id}/regenerate` → same loading pattern → page refreshes with new content
- **Export DOCX:** Button triggers `POST /api/proposals/{id}/export` → browser downloads file

**Assumptions & Evidence:**
- Shown collapsed by default under each section
- Expandable disclosure: "View assumptions (2)" / "View evidence sources (3)"
- These help the user verify and edit the content — they're the "show your work" for consultant-grade output

**Version indicator:**
- "Version 1" / "Version 2" shown in header
- After regeneration, version increments
- No version history in MVP — only latest version shown

**API calls:**
- On load: `GET /api/proposals/{id}` → full content_json
- Regenerate: `POST /api/proposals/{id}/regenerate`
- Export: `POST /api/proposals/{id}/export` → file download

---

### 3.9 `/billing` — Plans & Billing

**Journey:** Upgrade flows, quota management  
**Purpose:** Show current plan, quota usage, and access to Stripe Customer Portal

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  Plans & Billing                                         │
│                                                          │
│  ┌─ Current Plan ────────────────────────────────────┐  │
│  │  GROWTH · $39/month                               │  │
│  │  Next billing: March 12, 2026                     │  │
│  │  [Manage Billing →]  (opens Stripe Customer Portal)│  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Usage This Period ───────────────────────────────┐  │
│  │  Fit Scans:  ████████░░  8 of 10                  │  │
│  │  Proposals:  ████░░░░░░  1 of 3                   │  │
│  │  Resets: March 12, 2026                           │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ Upgrade ─────────────────────────────────────────┐  │
│  │                                                    │  │
│  │   IMPACT · $79/month                              │  │
│  │   20 Fit Scans · 5 Proposals · Consultant-grade   │  │
│  │   [Upgrade to Impact →]                           │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Free plan version:**
- No "Current Plan" card — instead: "You're on the Free plan (evaluation only)"
- Show plan comparison: Growth vs Impact
- Two upgrade CTAs: [Start Growth →] [Start Impact →]
- Both → `POST /api/billing/checkout { plan: "GROWTH" | "IMPACT" }` → redirect to Stripe Checkout

**Manage Billing:**
- Calls `GET /api/billing/portal` → opens Stripe Customer Portal in new tab
- Stripe handles payment method updates, invoice history, plan changes, cancellation

**API calls:**
- On load: `GET /api/me/entitlements` → plan, quota, billing period
- Upgrade: `POST /api/billing/checkout` → redirect to Stripe
- Manage: `GET /api/billing/portal` → redirect to Stripe Portal

---

### 3.10 `/billing/success` and `/billing/cancel`

**Purpose:** Landing pages after Stripe Checkout

**Success:**
```
✅ You're now on the Growth plan!

Your subscription is active. You now have access to 10 Fit Scans 
and 3 proposals per month.

[Go to Dashboard →]
```

**Cancel:**
```
No worries — you can upgrade any time.

Your Free plan is still active. When you're ready, 
plans start at $39/month.

[Back to Dashboard →]
```

---

## 4. Shared Components

### 4.1 Auth Provider / Token Management

A React context that wraps the entire app:
- Stores access_token and refresh_token in React state (NOT localStorage — per AUTH_AND_SSO_STRATEGY.md)
- Provides `useAuth()` hook: `{ user, isAuthenticated, accessToken, login, logout }`
- Automatic token refresh: on 401 response, call `/api/auth/refresh`, retry original request once, redirect to /login if refresh fails
- Token stored in memory means user loses session on page refresh — acceptable for MVP (they re-login). Post-MVP: consider httpOnly cookies or encrypted session storage.

### 4.2 API Client

A thin `fetch` wrapper:
- Base URL: `NEXT_PUBLIC_API_BASE_URL`
- Automatically attaches `Authorization: Bearer {access_token}` header
- Handles 401 → trigger token refresh → retry
- Handles 429 → show "Rate limited. Please wait and try again."
- Parses JSON responses
- On error, extracts `error_code` and `message` from standard error envelope

### 4.3 Quota Gate Component

Reusable component that checks quota before allowing an action:
- Props: `action` (FIT_SCAN | PROPOSAL_CREATE | etc.), `children` (the gated button/CTA)
- If quota available → render children normally
- If quota exhausted → render upgrade CTA with plan-appropriate messaging:
  - Free → "Upgrade to Growth for more Fit Scans" [Upgrade →]
  - Growth → "Upgrade to Impact for more capacity" [Upgrade →]
  - Impact → "Your quota resets on {date}"

### 4.4 Error Boundary / Error Display

Consistent error handling across the app:
- Network errors → "Something went wrong. Please check your connection and try again."
- 500 errors → "We're experiencing a temporary issue. Please try again in a moment."
- 404 → "This page doesn't exist." [Back to Dashboard]
- Quota errors → plan-specific upgrade messaging (see 4.3)
- Profile incomplete → redirect to /profile with context

**Per J7 (LAUNCH_JOURNEYS_SPEC):** Errors must never blame the user. Always explain what happened and offer a path forward.

### 4.5 Loading States

Consistent loading patterns:
- **Page-level:** Skeleton screens (grey placeholder blocks matching expected layout)
- **Action-level:** Button shows spinner + disabled state, text changes to "Generating..." / "Saving..."
- **AI operations (Fit Scan, Proposal):** Dedicated loading screens with progress text (see 3.1, 3.7)

---

## 5. Quota & Upgrade Messaging (Cross-Cutting)

This is pulled from PRICING_AND_ENTITLEMENTS.md and LAUNCH_JOURNEYS_SPEC.md. It appears across many pages.

### Fit Scan Quota Exhausted

| Plan | Message | CTA |
|------|---------|-----|
| Free | "You've used your free Fit Scan. Upgrade to Growth to check fit for more opportunities." | [Upgrade to Growth — $39/mo →] |
| Growth | "You've used all 10 Fit Scans this month. Upgrade to Impact for 20 scans per month." | [Upgrade to Impact — $79/mo →] |
| Impact | "You've used all 20 Fit Scans this month. Your quota resets on {date}." | No CTA (just the date) |

### Proposal Quota Exhausted

| Plan | Message | CTA |
|------|---------|-----|
| Free | "You've used your free proposal. Upgrade to Growth to generate more proposals." | [Upgrade to Growth — $39/mo →] |
| Growth | "You've reached 3 proposals this month. Upgrade to Impact for 5 per month." | [Upgrade to Impact — $79/mo →] |
| Impact | "You've reached 5 proposals this month. Your quota resets on {date}." | No CTA |

### Regeneration Not Allowed

| Plan | Message |
|------|---------|
| Free | "Regeneration isn't available on the Free plan. Upgrade to refine your proposals." |
| Growth/Impact (limit reached) | "You've used all 3 regenerations for this proposal." |

---

## 6. Data Flow Summary

### Which API endpoints each page calls

| Page | API Calls |
|------|-----------|
| `/login` | `GET /api/auth/google/start`, `POST /api/auth/magic-link/request` |
| `/auth/callback` | `POST /api/auth/exchange` |
| `/auth/magic-link` | `POST /api/auth/magic-link/consume` |
| `/start` | `GET /api/ngo-profile/completeness`, `GET /api/me/entitlements`, `POST /api/fit-scans` |
| `/dashboard` | `GET /api/me/entitlements`, `GET /api/ngo-profile/completeness` |
| `/profile` | `GET /api/ngo-profile`, `POST /api/ngo-profile`, `PUT /api/ngo-profile`, `GET /api/ngo-profile/completeness` |
| `/fit-scan/{id}` | `GET /api/fit-scans/{id}` |
| `/proposal/new` | `POST /api/proposals` |
| `/proposal/{id}` | `GET /api/proposals/{id}`, `POST /api/proposals/{id}/regenerate`, `POST /api/proposals/{id}/export` |
| `/billing` | `GET /api/me/entitlements`, `POST /api/billing/checkout`, `GET /api/billing/portal` |

### Post-MVP enhancement (deferred)

If/when we add list endpoints to `API_CONTRACT.md`:
- `GET /api/fit-scans` → list user's fit scans (newest first)
- `GET /api/proposals` → list user's proposals (newest first)

Then update `/dashboard` to show “last 5 items” for each list.
Until then, the MVP dashboard MUST NOT depend on list endpoints.

---

## 7. Frontend-Only State (Not in Backend)

| State | Storage | Lifetime |
|-------|---------|----------|
| Auth tokens | React context (memory) | Until page close or logout |
| Redirect intent (opportunity_id from /start) | sessionStorage | Survives OAuth redirect, cleared after use |
| UI preferences (sidebar collapsed, etc.) | React state | Per session |

**No localStorage for tokens.** This is a security decision per AUTH_AND_SSO_STRATEGY.md. Users will need to re-authenticate on page refresh. For MVP, this is acceptable — the auth flow is fast (Google OAuth is one click, magic link is one email).

---

## 8. File Structure (Next.js App Router)

```
app/
├── layout.tsx                    Root layout (fonts, global styles)
├── (public)/                     Public routes (no auth required)
│   ├── login/page.tsx
│   ├── auth/
│   │   ├── callback/page.tsx     OAuth code exchange
│   │   └── magic-link/page.tsx   Magic link consume
│   └── start/page.tsx            WordPress handoff
│
├── (authenticated)/              Auth-required routes (shared layout with nav)
│   ├── layout.tsx                Sidebar nav + auth guard
│   ├── dashboard/page.tsx
│   ├── profile/page.tsx
│   ├── fit-scan/[id]/page.tsx
│   ├── proposal/
│   │   ├── new/page.tsx          Generation loading page
│   │   └── [id]/page.tsx         Proposal viewer
│   └── billing/
│       ├── page.tsx              Plan + quota
│       ├── success/page.tsx      Post-checkout
│       └── cancel/page.tsx       Post-checkout cancel
│
├── components/
│   ├── auth/
│   │   ├── AuthProvider.tsx      Context + token management
│   │   ├── AuthGuard.tsx         Redirect if not authenticated
│   │   └── LoginForm.tsx         Google + Magic Link form
│   ├── dashboard/
│   │   ├── QuotaOverview.tsx
│   │   ├── FitScanList.tsx
│   │   └── ProposalList.tsx
│   ├── profile/
│   │   ├── ProfileForm.tsx       Main form with all sections
│   │   ├── PastProjectCard.tsx   Repeatable project entry
│   │   ├── TagInput.tsx          Reusable tag input for sectors, areas
│   │   └── CompletenessBar.tsx   Progress indicator
│   ├── fit-scan/
│   │   ├── RecommendationBanner.tsx
│   │   ├── ScoreBar.tsx
│   │   └── RiskFlagList.tsx
│   ├── proposal/
│   │   ├── SectionNav.tsx        Section sidebar/tabs
│   │   ├── SectionContent.tsx    Content renderer by status
│   │   ├── GenerationProgress.tsx Loading state for generation
│   │   └── AssumptionsList.tsx
│   ├── billing/
│   │   ├── PlanCard.tsx
│   │   ├── UsageBar.tsx
│   │   └── UpgradeCTA.tsx
│   └── shared/
│       ├── QuotaGate.tsx         Reusable quota check wrapper
│       ├── ErrorDisplay.tsx      Standard error UI
│       ├── LoadingSkeleton.tsx   Page-level skeleton
│       └── StatusBadge.tsx       Coloured status indicator
│
├── lib/
│   ├── api-client.ts             Fetch wrapper with auth headers
│   ├── auth.ts                   Token management utilities
│   └── constants.ts              Quota limits, plan names, etc.
│
└── styles/
    └── globals.css               Tailwind imports + CSS variables
```

---

## 9. Build Sequence Recommendation

**When to build frontend** (per CTO guidance in mvp_execution_plan_FINAL_2.md):

Start AFTER C-07B (proposal creation) is deployed and one real proposal has been generated end-to-end. At that point, all API response shapes are validated against real data.

**Suggested frontend build order:**

| Priority | Pages | Rationale |
|----------|-------|-----------|
| 1 | Auth (login, callback, magic-link) + AuthProvider | Gate for everything else |
| 2 | Profile form | Required before any Fit Scan or Proposal |
| 3 | /start + /fit-scan/{id} | Primary acquisition funnel from WordPress |
| 4 | /proposal/new + /proposal/{id} | Core value — what users pay for |
| 5 | Dashboard | Home base for returning users |
| 6 | Billing (checkout, portal, success/cancel) | Monetisation |
| 7 | Polish: loading states, error handling, empty states | Production readiness |

---

## 10. What This Document Does NOT Cover

- Visual design mockups / pixel-level layouts (that's Cursor's job with this spec as input)
- CSS specifics beyond the colour system and design language
- Animation details
- Responsive breakpoints
- Accessibility (WCAG) — aim for baseline accessibility but not a formal audit for MVP
- Testing strategy for frontend (unit tests for components are post-MVP)

---

## Changelog

### v1.0 (2026-02-09)
- Initial frontend architecture spec
- All pages mapped to LAUNCH_JOURNEYS_SPEC journeys (J1-J7)
- Component hierarchy defined
- API data flow documented
- Missing list endpoints flagged for backend

---

**END OF DOCUMENT**
