# Plan 1 Frontend Read-Only Audit

**Audit date:** 2026-05-30  
**Scope:** GrantPilot Next.js UI — routes, components, navigation, API client, auth, billing, states, M&E readiness. Read-only.

---

## 0. Repo Confirmed / Files Read / Missing / Search Summary

### Workspace guard result

| Check | Result |
|-------|--------|
| **Cursor workspace root** | **Backend repo** — `requirements.txt`, `app/main.py`, `app/reports/` present; **no** root `package.json` or `*.tsx` |
| **STOP condition** | Triggered at workspace root (not opened as frontend-only repo) |
| **Frontend audit target** | **Located and audited:** `ngoinfo-grantpilot-frontend/` (nested sibling to backend; excluded from backend git per `DEPLOYMENT_STATE_2026-05-30.md`) |

**Recommendation:** Re-open Cursor workspace at `ngoinfo-grantpilot-frontend/` for Plan 1 UI implementation work.

### Frontend repo evidence

| Item | Value |
|------|-------|
| Path | `ngoinfo-grantpilot-frontend/` |
| `package.json` name | `"frontend"` (`ngoinfo-grantpilot-frontend/package.json` L2) |
| Framework | **Next.js 15.5.12** (App Router) — `package.json` L17 |
| React | 19.1.0 — `package.json` L15–16 |
| API client | `lib/api-client.ts` |
| Auth provider | `components/auth/AuthProvider.tsx` |

### Spec files (in frontend repo)

| File | Status |
|------|--------|
| `docs/contracts/FRONTEND_ARCHITECTURE_SPEC.md` | **Read** |
| `docs/contracts/BRAND_AND_FRONTEND_SPEC.md` | **Read** (partial — design tokens; no M&E/pricing) |
| `docs/contracts/PRICING_AND_ENTITLEMENTS.md` | Present (copy of backend artefact; not re-read line-by-line) |
| `docs/contracts/API_CONTRACT.md` | Present |

### Source areas read

`app/` routes (all pages), `components/` (auth, nav, dashboard, billing, fit-scan, proposal, shared), `lib/api-client.ts`, `lib/plans.ts`, `lib/auth-intent.ts`, `lib/api/proposals.ts`, `lib/profile-service.ts`, `.env.example`, `next.config.ts`.

### DOCX / M&E assets in frontend repo

**NOT FOUND** — no `/reports` routes, no M&E components, no `NEXT_PUBLIC_ME_*` env vars.

### Search-term summary (frontend `*.ts` / `*.tsx` / docs; excludes `node_modules`, `.next`)

| Term | Count / summary | Notable locations |
|------|-----------------|-------------------|
| **Impact Pro** | **0** in code | — |
| **$99** | **0** in code | — |
| **99** (bare) | **0** in `*.ts/tsx` | — |
| **20 Fit / 20 scans** | **4 code hits** | `lib/plans.ts` L21 (`fitScansLimit: 20`); `components/shared/QuotaGate.tsx` L35, L42; docs mirror in `docs/contracts/FRONTEND_ARCHITECTURE_SPEC.md` L598, L708–709 |
| **$19 / add-on / one-off / pay-per-report** | **0** product hits | — |
| **localStorage** | **6 refs** | `AuthProvider.tsx` L46, L59, L66, L81, L90; `api-client.ts` L90, L107 |
| **sessionStorage** | **9 refs** | `lib/auth-intent.ts` L20–54; `UpgradeWall.tsx` L34; `billing/success/page.tsx` L10–13 |
| **sk_live / sk_test / STRIPE_SECRET / OPENAI / OPENAI_API_KEY** | **0** in app code | Docs only (`docs/contracts/GUARDRAILS_RUNTIME_AND_SECURITY.md`) |
| **process.env** | **2** | `lib/api-client.ts` L38 (`NEXT_PUBLIC_API_BASE_URL`); `proposal/[id]/page.tsx` L313 (same) |
| **jwt.sign / SECRET** | **0** in app code | — |
| **/reports** | **0** | — |
| **donor report** | **0** | — |
| **M&E / ME_MODULE / NEXT_PUBLIC_ME** | **0** | — |
| **report-templates** | **0** | — |
| **entitlement / quota** | **Widespread** | `/start`, `/dashboard`, `/billing`, `QuotaOverview`, `QuotaGate`, `UpgradeWall`, `UpgradeNudge`, `LimitReached` |
| **plan** | **Widespread** | `lib/plans.ts`, billing, auth user.plan |
| **linked_proposal** | **0** | — |
| **funding_opportunity** | **~15+ hits** | Pre-award flows only: `start/page.tsx`, `fit-scan/[id]`, `proposal/new`, `dashboard`, `lib/api/proposals.ts` |

---

## 1. Executive Verdict

| Question | Answer |
|----------|--------|
| **Real state vs stale spec** | **Core pre-award UI is implemented** and largely matches `FRONTEND_ARCHITECTURE_SPEC.md` routes (dashboard, profile, fit-scan, proposal, billing, `/start` handoff). Spec and bundled docs still describe **20 Fit Scans on Impact**; code mirrors that in `lib/plans.ts`. **M&E is entirely absent** from code and spec page map. |
| **Ready to bind M&E UI once backend ships?** | **Partially.** Shared infrastructure (`api-client`, auth, layout, quota/upgrade patterns) is reusable. **Blockers:** no `/reports` routes, no `lib/api/reports.ts`, no `reports` entitlements type, no feature flag, nav has no Reports entry, no Impact-only gate component for M&E. |
| **Genuine blockers** | Zero M&E surface; entitlements types omit `reports`; hardcoded Impact **20** fit-scan marketing copy; no Path C entry (direct to reports without WordPress opportunity). |

**Bottom line:** Pre-award product UI is production-shaped. Plan 1 M&E UI work starts from **greenfield** under `(authenticated)/reports/` with dependency on backend list/detail/template APIs and entitlements extension.

---

## 2. Actual Route Map

| Route | Auth | Status | Primary file |
|-------|------|--------|--------------|
| `/` | Public | **Redirect** → `/login` | `app/page.tsx` L3–4 |
| `/login` | Public | **Implemented** | `app/(public)/login/page.tsx` |
| `/auth/callback` | Public | **Implemented** | `app/(public)/auth/callback/page.tsx` |
| `/auth/magic-link` | Public | **Implemented** | `app/(public)/auth/magic-link/page.tsx` |
| `/start?opportunity_id=` | Public* | **Implemented** (WordPress handoff) | `app/(public)/start/page.tsx` |
| `/dashboard` | Authed | **Implemented** | `app/(authenticated)/dashboard/page.tsx` |
| `/profile` | Authed | **Implemented** | `app/(authenticated)/profile/page.tsx` |
| `/fit-scan/[id]` | Authed | **Implemented** | `app/(authenticated)/fit-scan/[id]/page.tsx` |
| `/proposal/new` | Authed | **Implemented** | `app/(authenticated)/proposal/new/page.tsx` |
| `/proposal/[id]` | Authed | **Implemented** | `app/(authenticated)/proposal/[id]/page.tsx` |
| `/billing` | Authed | **Implemented** | `app/(authenticated)/billing/page.tsx` |
| `/billing/success` | Authed | **Implemented** | `app/(authenticated)/billing/success/page.tsx` |
| `/billing/cancel` | Authed | **Implemented** | `app/(authenticated)/billing/cancel/page.tsx` |
| `/reports` | — | **NOT FOUND** | — |
| `/reports/*` (SCR 2–8) | — | **NOT FOUND** | — |

\*`/start` runs unauthenticated through auth redirect; full flow requires login.

**Layout:** Authenticated shell = `AuthGuard` + `AppNav` sidebar — `app/(authenticated)/layout.tsx` L6–17.

---

## 3. Current UI State — Dashboard / Proposal / Fit Scan / Billing

| Surface | Current state | Backend calls | Plan-1 weaknesses (integration, not visual) |
|---------|---------------|---------------|---------------------------------------------|
| **Dashboard** | Quota overview (fit + proposal only), profile completeness card, recent fit scans & proposals lists | `GET /api/me/entitlements`, `GET /api/fit-scans?limit=5`, `GET /api/proposals?limit=5`, profile completeness | No M&E quota tile or report history; empty states nudge toward NGOInfo.org / fit scan — not Path C M&E |
| **Fit Scan `/start`** | Multi-step: validate opportunity → profile → quota → create scan; upgrade wall for Free; LimitReached/UpgradeNudge for paid exhaustion | `POST /api/funding-opportunities/validate`, entitlements, `POST /api/fit-scans` | **Requires `funding_opportunity_id`** from WordPress; no parallel “start report without opportunity” |
| **Fit Scan detail** | Scores, risks, recommendation banner, CTA → proposal/new with opportunity + fit_scan ids | `GET /api/fit-scans/{id}`, entitlements | CTA always ties to opportunity; no optional “create donor report” link |
| **Proposal new** | Pre-flight, generation progress, quota gates, upgrade wall | pre-flight, `POST /api/proposals`, entitlements | Opportunity-scoped query params required |
| **Proposal detail** | Section nav, regenerate (max 3 client-side), export modal (direct fetch to API) | `GET /api/proposals/{id}`, regenerate, export | `REGEN_MAX = 3` hardcoded L61; export uses raw fetch + bearer token L313+ |
| **Profile** | Full NGO profile form, completeness, tag inputs | profile service / NGO API | No M&E-specific profile hints |
| **Billing** | Usage bars (fit + proposal), Stripe checkout (Growth/Impact), portal for paid users | entitlements, checkout, portal | Plan cards omit **M&E reports/month** and support tier; Impact shows **20** fits from `PLAN_DETAILS` |

---

## 4. M&E Frontend Presence

**Answer: NO** — no M&E UI exists in the frontend repository.

| Wireframe (SCR) | Present? | Evidence |
|-----------------|----------|----------|
| SCR 1 — Reports dashboard | **No** | No `app/(authenticated)/reports/` directory |
| SCR 2 — Funder/template choice | **No** | No `report-templates` API client |
| SCR 3 — Upload | **No** | — |
| SCR 4 — Agent progress | **No** | — |
| SCR 5 — Gate 1 | **No** | — |
| SCR 6 — Gate 2 | **No** | — |
| SCR 7 — Gate 3 | **No** | — |
| SCR 8 — Export | **No** | — |

No references to `donor report`, `linked_proposal`, `NEXT_PUBLIC_ME_MODULE_ENABLED`, or `/reports` in application code.

---

## 5. Navigation & Cohesion

| Aspect | Current state | Gap |
|--------|---------------|-----|
| **Nav items** | Dashboard, My Profile, Plans & Billing — `AppNav.tsx` L10–14 | **No “Reports”** (or Donor Reports) |
| **Product story** | Sidebar + dashboard center **Fit Scan → Proposal** pipeline | M&E not visible as third pillar |
| **Brand header** | NGOInfo logo in nav — `AppNav.tsx` L23–30 | Consistent with brand spec |
| **Post-login default** | `/dashboard` (via auth redirect patterns) | No M&E entry for Path C users |
| **Recommended change** | Add **Reports** nav item (Impact-gated or upgrade wall for others); optional dashboard card “New donor report” | Required for Plan 1 cohesion |

Fit Scan + Proposals **do** read as one product today; Reports would appear bolted-on until nav and dashboard quotas include M&E.

---

## 6. Thin-Client & Ownership Findings

| Finding | Location | Severity | Notes |
|---------|----------|----------|-------|
| **Refresh token in `localStorage`** | `AuthProvider.tsx` L35, L59, L81–90; `api-client.ts` L39, L90, L107 | **MEDIUM** | Persists `gp_refresh_token` across sessions. Report only — may conflict with in-memory-only target in `AUTH_AND_SSO_STRATEGY` if that doc requires it. Access token kept in React state (good). |
| **Auth/checkout intent in `sessionStorage`** | `lib/auth-intent.ts` L20–54; `UpgradeWall.tsx` L34; `billing/success/page.tsx` L10–13 | **LOW** | Non-secret routing hints (`opportunity_id`, post-checkout redirect). Acceptable for UX. |
| **Hardcoded plan limits in UI copy** | `lib/plans.ts` L5–25; consumed by billing, `UpgradeWall`, `QuotaGate`, `LimitReached`, `UpgradeNudge` | **HIGH** | Impact `fitScansLimit: 20` conflicts with canonical **10**. Marketing bullets can diverge from API `entitlements.*.limit`. |
| **Client-authored quota exhaustion messages** | `QuotaGate.tsx` L21–78 | **MEDIUM** | Messages embed plan limits (“20 scans”) rather than reading API limits/messages. Server must remain authoritative; UI should prefer API envelope + `entitlements` numbers. |
| **Client-side quota pre-check** | `/start`, `/proposal/new` check `remaining <= 0` before POST | **LOW** | OK as UX if server enforces; not a bypass by itself. |
| **`REGEN_MAX = 3` hardcoded** | `proposal/[id]/page.tsx` L61 | **LOW** | Should use `entitlements.proposal_regenerations.limit_per_proposal` from API. |
| **Proposal export via direct `fetch`** | `proposal/[id]/page.tsx` ~L313 | **LOW** | Uses `NEXT_PUBLIC_API_BASE_URL` + bearer token; no secret keys. Duplicates auth header logic outside `apiRequest`. |
| **Secrets in client bundle** | `.env.example` only `NEXT_PUBLIC_*` | **None found** | No Stripe/OpenAI secrets in TS source. |
| **M&E gating in frontend** | N/A | **BLOCKER (missing)** | When built, gating must follow **403/402 from API**, not client-only plan checks. |

---

## 7. Stale Pricing / Copy Drift

| UI string / constant | Location | Current | Target | Severity |
|---------------------|----------|---------|--------|----------|
| Impact fit scans limit | `lib/plans.ts` L21 | `fitScansLimit: 20` | **10** | **HIGH** |
| Growth exhausted → Impact upsell | `QuotaGate.tsx` L35 | “Upgrade to Impact for **20 scans** per month” | **10 scans** | **HIGH** |
| Impact fit scan exhausted | `QuotaGate.tsx` L42 | “You've used all **20** Fit Scans” | **10** | **HIGH** |
| Impact limit display | `LimitReached.tsx` L21 | Uses `PLAN_DETAILS.IMPACT.fitScansLimit` (20) | **10** | **HIGH** |
| Upgrade nudge copy | `UpgradeNudge.tsx` L70 | “{n} fit scans” from PLAN_DETAILS (20 on Impact) | **10** + mention **2 M&E reports** on Impact | **HIGH** |
| Billing plan cards | `billing/page.tsx` L184–197, `PlanCard` | Fit + proposal + regen only | Add **2 donor reports/mo** on Impact; **no M&E** on Growth | **HIGH** |
| Impact Pro / $99 / $19 add-on | Repo search | **Not found in UI code** | — | — |
| M&E on Growth | N/A | Not shown (M&E absent) | Growth must never show M&E entry without upgrade gate | N/A until built |

Bundled docs under `docs/contracts/` (`FRONTEND_ARCHITECTURE_SPEC.md` L598, L708–709; `ARTEFACTS_V1_LOCKED.md` L54) still say **20 Fit Scans** on Impact — treat as **doc drift** alongside code.

---

## 8. State Coverage

| State | Fit Scan (`/start`, detail) | Proposal | Dashboard | Billing | M&E (future) |
|-------|------------------------------|----------|-----------|---------|--------------|
| **Loading** | `LoadingSkeleton` — start L92+, detail L136 | new + detail | L214–216 | L142–144 | **Missing** |
| **Empty** | Invalid link / unavailable opportunity | Missing query context errors | Lists empty implicitly | Free plan chooser | **Missing** |
| **Error** | `ErrorDisplay`, fatal messages | `ErrorDisplay` | Per-section errors | load/action errors | **Missing** |
| **Quota exhausted (Free)** | `UpgradeWall` | `UpgradeWall` | QuotaOverview CTA | — | **Missing** |
| **Quota exhausted (Growth)** | `UpgradeNudge` | Similar patterns | Upgrade → Impact link | — | **Missing** |
| **Quota exhausted (Impact)** | `LimitReached` (reset date) | `LimitReached` | Reset notice only | Usage bars | **Missing** (need reports reset, no purchase) |
| **Upgrade to Impact (M&E gate)** | N/A | N/A | N/A | N/A | **Missing** |
| **Auth required** | Redirect via `/start` flow | `AuthGuard` | `AuthGuard` | `AuthGuard` | **Missing** |

**Reusable patterns for M&E:** `UpgradeWall`, `UpgradeNudge`, `LimitReached`, `QuotaGate`, `ErrorDisplay`, `LoadingSkeleton` — extend with new `ExhaustedResource` / action types or parallel components for `reports`.

---

## 9. API Client & Integration Readiness

### Structure

| Component | Location | Notes |
|-----------|----------|-------|
| **Central client** | `lib/api-client.ts` | `apiRequest<T>()`, `ApiClientError`, 401 → refresh → retry L164–168 |
| **Domain modules** | `lib/api/proposals.ts`, `lib/api/ngoProfile.ts`, `lib/profile-service.ts` | **No `lib/api/reports.ts`** |
| **Base URL** | `NEXT_PUBLIC_API_BASE_URL` — `api-client.ts` L38; `.env.example` L2 |
| **Auth header** | Bearer from in-memory access token via `configureApiClientAuthHandlers` L155–157 |
| **Error envelope** | Parses `error_code`, `message`, `details` L175–178 | Handles 429 generically L69–71 |
| **401 handling** | Refresh POST `/api/auth/refresh`; failure → login redirect L84–96, L171–173 |

### Readiness for M&E + new entitlements

| Capability | Ready? | Gap |
|------------|--------|-----|
| **`reports` block in entitlements** | **No** | Types in `QuotaOverview`, `billing/page`, `dashboard/page` only include `fit_scans` + `proposals` |
| **`GET /api/reports`** | **No client** | Add list fetch + typed response |
| **`GET /api/reports/{id}`** | **No client** | Detail + gates UI |
| **`GET /api/report-templates`** | **No client** | SCR 2 |
| **POST create / upload / job poll** | **No client** | Backend paths exist; frontend not wired |
| **403 upgrade-to-Impact for M&E** | **No handler** | Map `error_code` + `details.entitlement === "reports"` to upgrade UI |
| **Feature flag** | **No** | Need `NEXT_PUBLIC_ME_MODULE_ENABLED` to hide nav/routes when off |
| **File upload** | **No helper** | `apiRequest` is JSON-oriented; uploads need `FormData` + no JSON Content-Type |

**Assessment:** Client is **fit for extension** — same patterns as proposals. M&E requires new module file, entitlements type extension, FormData upload helper, and optional blob download helper (export).

---

## 10. Spec Mismatches (real frontend vs `FRONTEND_ARCHITECTURE_SPEC.md`)

| Area | Spec | Reality | Ahead / behind |
|------|------|---------|----------------|
| **Route map** | §2.1 pages listed | All pre-award routes implemented | **Aligned** |
| **`/reports`** | Not in spec page list | Not in code | **Aligned (both omit M&E)** |
| **Nav** | Sidebar dashboard, profile, billing | Matches `AppNav.tsx` | **Aligned** |
| **Impact fit scans** | Spec §6 copy: 20/month L708–709 | Code `plans.ts` L21: 20 | **Aligned with stale spec; both wrong vs canonical 10** |
| **QuotaOverview** | Spec: fit + proposal | Same — L129–131 | **Behind** target (needs reports) |
| **List endpoints** | Spec §8.3 / §9.3 | Dashboard validates response shapes strictly | **Ahead** (defensive STOP messages) |
| **M&E wireframes SCR 1–8** | Not in FRONTEND_ARCHITECTURE_SPEC | Not implemented | **Gap** — wireframes live in backend `ME_MODULE_WIREFRAMES_BRANDED.html` only |

---

## 11. Candidate Frontend Work-Package Inventory

*Unordered. No $19 add-on packages.*

1. **Open frontend as primary workspace** — Objective: Cursor workspace root = `ngoinfo-grantpilot-frontend`. Files: repo root. Dependencies: none.

2. **Fix Impact fit-scan copy 20→10** — Objective: align `PLAN_DETAILS`, `QuotaGate`, docs bundles. Files: `lib/plans.ts`, `components/shared/QuotaGate.tsx`, `LimitReached.tsx`, `UpgradeNudge.tsx`, `docs/contracts/*`. Dependencies: founder confirms canonical quota.

3. **Extend entitlements types + QuotaOverview** — Objective: add `reports` quota block; third bar on dashboard/billing. Files: `QuotaOverview.tsx`, `billing/page.tsx`, `dashboard/page.tsx`. Dependencies: backend `GET /api/me/entitlements` ships `reports`.

4. **Impact plan marketing bullets** — Objective: show **2 M&E reports/month**, priority support on Impact; explicitly **no M&E** on Growth cards. Files: `PlanCard.tsx`, `UpgradeWall.tsx`, `billing/page.tsx`. Dependencies: WP2.

5. **`NEXT_PUBLIC_ME_MODULE_ENABLED` + nav** — Objective: feature-flag Reports nav item. Files: `AppNav.tsx`, env example, layout. Dependencies: product flag decision.

6. **Reports route scaffold SCR 1** — Objective: `/reports` list + empty state + “New donor report”. Files: `app/(authenticated)/reports/page.tsx`, `components/reports/`. Dependencies: `GET /api/reports` backend.

7. **Impact-only upgrade gate component** — Objective: Free/Growth users hitting `/reports` see upgrade-to-Impact (not checkout for consumable). Files: new shared component; reports layout guard. Dependencies: backend 403 shape.

8. **Report create flow SCR 2–3** — Objective: template picker, period dates, optional `linked_proposal_id`, multi-file upload. Files: `reports/new/`, `lib/api/reports.ts`. Dependencies: template list + create + upload APIs.

9. **Pipeline progress SCR 4** — Objective: poll `GET /api/reports/{id}/job`. Files: job status component. Dependencies: backend job API path stability (note backend gate path drift).

10. **Human gates SCR 5–7** — Objective: KB review, gap answers, section review + critic flags. Files: gate pages/components. Dependencies: backend gate + detail endpoints.

11. **Export SCR 8** — Objective: download DOCX; Impact quota exhausted → reset message. Files: export button + blob download helper. Dependencies: export endpoint + `REPORT_EXPORT` entitlement.

12. **Path C landing** — Objective: marketing/deep link to `/reports` without `opportunity_id`. Files: optional `/reports/start` or root reports CTA copy. Dependencies: WP6.

13. **`lib/api/reports.ts` module** — Objective: typed wrappers for all §12 endpoints. Files: new API module. Dependencies: API contract lock.

14. **FormData upload helper** — Objective: extend API client for multipart document upload. Files: `api-client.ts` or `reports.ts`. Dependencies: none.

15. **Dashboard cohesion** — Objective: recent reports list alongside fit scans/proposals. Files: `dashboard/page.tsx`, new `ReportList.tsx`. Dependencies: WP6.

16. **Spec sync** — Objective: update `FRONTEND_ARCHITECTURE_SPEC.md` with `/reports` map, states, API table. Files: `docs/contracts/`. Dependencies: WP6–11 design lock.

---

## 12. What NOT To Touch Yet

### Plan 2 (quality)

- Fit Scan / proposal content quality, section prose, recommendation copy.
- Visual polish, typography refinement, accessibility audit.
- M&E gate UX microcopy beyond structural states.

### Plan 3 (security testing)

- Penetration testing, token storage migration review, CSP hardening.
- Do not “fix” refresh-token localStorage in this audit pass.

### V2 (reserved)

- **$19 one-off / pay-per-report M&E add-on** — no UI, no purchase flow, no metered copy.

### Explicit non-goals

- **IMPACT_PRO** third tier UI.
- Full admin/support dashboard for report jobs.
- Analytics platform / event taxonomy (only note gaps).

---

*End of Plan 1 Frontend Read-Only Audit.*
