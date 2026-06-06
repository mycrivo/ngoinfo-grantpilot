# GrantPilot Reports — NGO-facing UI: implementation notes

**Companion to:** `ME_MODULE_REPORTS_NGO_UI.html`
**Status:** Design reference (medium-high fidelity). Not production code.
**Authority:** `BRAND_AND_FRONTEND_SPEC.md` (LOCKED v2.0) · `API_CONTRACT.md` §12 · `ME_MODULE_ARCHITECTURE_SPEC.md` · `ME_MODULE_MASTER_MEMORY.md`

---

## 1. What this is (and where it goes)

`ME_MODULE_REPORTS_NGO_UI.html` is the **customer-facing redesign** of the Donor Report
Writer journey. It takes the product flow from the `ME_MODULE_WIREFRAMES_V2.html` /
`ME_MODULE_WIREFRAMES_BRANDED.html` blueprints and re-expresses it as a calm NGO
reporting workspace — every internal/engineering term removed, brand tokens applied.

**It is a design artefact, not the shipping frontend.** The production UI is a **separate
Next.js repo** (`API_CONTRACT.md:1111` — *frontend `NEXT_PUBLIC_ME_MODULE_ENABLED`
(separate repo)*); this repository is the FastAPI backend. This file is the authoritative
visual + copy reference the Next.js team builds the `/reports` screens against, and it
lives beside the other M&E wireframe artefacts in `docs/artefacts/me_module/`.

The prototype **renders state only** — no business logic, entitlement checks, report-state
decisions, AI execution, secrets, or auth tokens. Interactions (selecting a figure,
choosing a funder, opening a section editor, removing an upload row) are purely
presentational.

---

## 2. Screen → route → API map

| # | Screen | Route | Reads / writes (`API_CONTRACT.md` §12 unless noted) |
|---|--------|-------|------------------------------------------------------|
| 0 | Reports home | `/reports` | `GET /api/reports` (§12.10) |
| 1 | Start report — organisation details | `/reports/new/about-you` | NGO-profile seed — **see gap in §5** |
| 2 | Confirm organisation profile | `/reports/new/confirm-profile` | `GET` / `PUT /api/ngo-profile` (§6) |
| 3 | Choose funder & reporting period | `/reports/new/funder` | `GET /api/report-templates` (§12.1) · `POST /api/reports` (§12.2) |
| 4 | Upload project documents | `/reports/{id}/upload` | `POST /api/reports/{id}/documents` (§12.3) |
| 5 | Reading documents | `/reports/{id}/reading` | `GET /api/reports/{id}/job` (§12.12) — poll for progress |
| 6 | Review project facts | `/reports/{id}/facts` | `GET` / `PATCH /api/reports/{id}/knowledge-bank` (§12.4–12.5) |
| 7 | Answer missing questions | `/reports/{id}/questions` | `GET /api/reports/{id}/gap-check` (§12.6) · `PATCH …/gap-answers` (§12.7) |
| 8 | Draft review | `/reports/{id}/review` | `GET /api/reports/{id}` (§12.9) · `PATCH …/sections/{key}` (§12.11) |
| 9 | Export — ready | `/reports/{id}/done` | `GET /api/reports/{id}` (§12.9) · `POST …/export` (§12.13) |

Section editing on Screen 8 is supported: `PATCH /api/reports/{id}/sections/{key}` (§12.11)
exists, so the **“Edit section” affordance is real** — the prototype shows the inline
editor for the flagged section. (The earlier V2 blueprint flagged this endpoint as missing;
it is now in the contract.)

---

## 3. Plain-language status labels (display map)

The backend exposes `status` and `current_gate` enums (`API_CONTRACT.md` §12.9/§12.10).
The UI shows **display-only** plain-language labels. No status logic lives in the frontend —
it renders the label for whatever state the API returns.

| Backend state | NGO-facing label (Reports home) |
|---------------|---------------------------------|
| `EXTRACTING` | **Reading documents** |
| `AWAITING_REVIEW` / `current_gate` ∈ {`gate1`,`gate3`} | **Needs your review** |
| `GENERATING` complete → content awaiting review | **Draft ready** |
| `COMPLETE` (not yet downloaded) | **Ready to download** |
| `COMPLETE` + first export downloaded | **Downloaded** |

Draft-section statuses on Screen 8 map from `content_json.sections[].generation_status`
(`GENERATED|FAILED|AWAITING_REVIEW|ACCEPTED`) + `critic_flags`:

| Section state | NGO-facing label |
|---------------|------------------|
| `ACCEPTED`, no open flags | **Checked** |
| open `BLOCK`/`WARN` flag, or figure mismatch | **Needs review** |
| `human_edited: true` | **Edited** |
| `FAILED` / no content | **Not provided** |

Accessibility rule honoured: **every status carries text + a shape/icon, never colour alone.**

---

## 4. Language & brand rules applied

- **DM Sans only** (no DM Mono) — `BRAND_AND_FRONTEND_SPEC.md` §2 + task design direction.
- **Navy** (`#1A1F71`) for all primary actions; **purple gradient** (`#5B2EFF→#8B5CFF`)
  reserved for the single upgrade accent (the quota state in the patterns appendix);
  **green/amber/red** for product statuses only.
- Logo loaded from the canonical URL (`BRAND_AND_FRONTEND_SPEC.md` §0.1), 40px header height.
- 8px spacing grid, 12px card radius, 8px button radius, 44px min button height, visible
  focus rings, 4.5:1 contrast targets.
- Banned internal vocabulary removed from the product surface. Replacements used:
  *file type, document reading, compare sources, **source check** (for the fact-safety
  step), confirmed project facts, review step, drafting* — and GrantPilot is named directly
  rather than “the engine”.
- No success/approval/probability claims; errors never blame the user; the person “stays
  the author”.

---

## 5. ⚠ Flagged gap — Screens 1–2 “Prepare my profile from a website URL”

**The one capability in this journey without a backing endpoint.** Screen 1’s primary
action (“Prepare my profile”) implies auto-drafting an organisation profile from a website
URL (and optional upload). **No such endpoint exists** in `API_CONTRACT.md` — §6 only
defines `GET/POST/PUT /api/ngo-profile` (manual create/edit) and `GET …/completeness`; the
deployed API (`openapi.json`) confirms the same.

**Implications for the build:**
- The **manual path is fully supported today** — Screen 1’s secondary CTA “I’ll enter
  details manually” → existing `/api/ngo-profile`; Screen 2 (“Confirm organisation
  profile”) maps to `GET`/`PUT /api/ngo-profile`.
- The **auto-draft path needs a new backend endpoint** before it can ship — e.g.
  `POST /api/ngo-profile/draft-from-source { website_url, document_id? }` returning a
  draft profile for the user to confirm. Until then, “Prepare my profile” should fall back
  to the manual form, or the two screens ship with the manual flow only.
- Nothing in the prototype mocks this behaviour — Screens 1–2 are rendered as design intent.

---

## 6. Verification checklist (task acceptance)

- [x] Reports nav appears in the authenticated app shell (Dashboard · Profile · Fit Scans · Proposals · **Reports** · Billing).
- [x] `/reports` renders **both** empty and populated states.
- [x] New-report journey renders all specified screens (0–9).
- [x] No banned internal terms in the rendered product UI (verified by scan; route names appear only in developer comments/notes).
- [x] Progress labels are **Upload · Read · Facts · Questions · Review · Download**.
- [x] Conflict review shows side-by-side sources + human decision actions (“Use 500 / Use 347 / Enter another figure”).
- [x] Missing questions allow **answer or skip**; skips noted as “not provided”.
- [x] Draft review surfaces the **source-check** issue in plain language (“says 500… your confirmed figure is 347”).
- [x] Export screen says **“Ready to download”**, never “Ready to submit”.
- [x] No `localStorage`/`sessionStorage`/cookie auth-token storage; no secrets.
- [x] Tokens, type, spacing, buttons follow `BRAND_AND_FRONTEND_SPEC.md`.
- [x] HTML parses cleanly (balanced tags); JS is null-guarded → no console errors.
- [ ] **Open:** Screens 1–2 auto-draft endpoint (see §5) — product decision needed.
