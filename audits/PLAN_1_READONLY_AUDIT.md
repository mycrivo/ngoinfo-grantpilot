# Plan 1 Read-Only Audit Report

**Audit date:** 2026-05-30  
**Scope:** M&E module design/integration readiness vs canonical two-plan target (Growth $39, Impact $79 with 2 bundled M&E reports/month). Read-only; backend repo only.  
**Out of scope:** AI/factual/security quality (Plan 2/3); $19 one-off M&E add-on (V2).

---

## 0. Files Read / Files Missing

### Files read (canonical paths)

| File | Status |
|------|--------|
| `docs/artefacts/mvp_execution_plan_FINAL_2.md` | Read |
| `docs/artefacts/PRODUCT_NORTH_STAR.md` | Read |
| `docs/artefacts/MVP_SCOPE_LOCK.md` | Read |
| `docs/artefacts/FRONTEND_ARCHITECTURE_SPEC.md` | Read |
| `docs/artefacts/BRAND_AND_FRONTEND_SPEC.md` | Read (no M&E/pricing content) |
| `docs/artefacts/LAUNCH_JOURNEYS_SPEC.md` | Read (no M&E/Path C content) |
| `docs/artefacts/GUARDRAILS_RUNTIME_AND_SECURITY.md` | Read (partial — quota rules) |
| `docs/artefacts/API_CONTRACT.md` | Read (§4, §12) |
| `docs/artefacts/PRICING_AND_ENTITLEMENTS.md` | Read |
| `docs/artefacts/STRIPE_INTEGRATION_SPEC.md` | Read |
| `docs/artefacts/ENUM_REGISTRY.md` | Read (§3, §5.10) |
| `docs/artefacts/DB_FIELD_CONTRACT_USER_PLANS.md` | Located (aligned with code) |
| `docs/artefacts/DB_FIELD_CONTRACT_STRIPE_EVENTS.md` | Located |
| `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md` | Read |
| `docs/artefacts/me_module/ME_MODULE_PROJECT_PLAN.md` | Located |
| `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` | Read (D-010, D-044, D-045) |
| `docs/artefacts/me_module/ME_MODULE_INTERNAL_ARCHITECTURE.html` | Located |
| `docs/artefacts/me_module/ME_MODULE_WIREFRAMES_BRANDED.html` | Read (SCR 1–8) |
| `docs/artefacts/me_module/DB_FIELD_CONTRACT_REPORT_JOBS.md` | Located |
| `docs/artefacts/me_module/DB_FIELD_CONTRACT_DONOR_REPORTS.md` | Read (partial) |
| `docs/artefacts/me_module/DB_FIELD_CONTRACT_FUNDER_REPORT_TEMPLATES.md` | Located |
| `docs/artefacts/me_module/DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS.md` | Read (partial) |
| `docs/artefacts/DB_FIELD_CONTRACT_FIT_SCANS.md` | Located |
| `docs/artefacts/DB_FIELD_CONTRACT_FUNDING_OPPORTUNITY.md` | Located |

**Note:** Several artefacts also exist as duplicates under `M_E_Module/` (same filenames). Audit treated `docs/artefacts/` as canonical.

**Listed at repo root without prefix:** Not present at root; canonical copies found under `docs/artefacts/` or `docs/artefacts/me_module/`.

### Backend source read (integration verification)

| Area | Files |
|------|-------|
| M&E routes | `app/reports/router.py`, `app/reports/api/routes/lifecycle.py`, `gate1.py`, `gate2.py`, `gate3.py`, `export.py` |
| M&E models/services | `app/reports/models/donor_report.py`, `donor_report_lifecycle_service.py`, `export/docx_renderer.py` |
| Core entitlements | `app/services/quota_service.py`, `app/models/usage_ledger.py`, `app/schemas/entitlements.py`, `app/models/user_plan.py`, `app/api/routes/billing.py` |
| Proposal export | `app/services/export_service.py` |
| Mounting | `app/main.py` |

### Files listed but MISSING (exact names/paths)

| File | Status |
|------|--------|
| `7-large-grants-progress-report-template.docx` | **MISSING** |
| `proposal-genetrated-grantpilot.docx` | **MISSING** |
| GrantPilot frontend (`*.tsx` / `*.ts`) | **NOT IN WORKSPACE** — separate repo; runtime UI **UNVERIFIED** |

### DOCX example files

| File | Status |
|------|--------|
| `7-large-grants-progress-report-template.docx` | **MISSING / UNVERIFIED** |
| `proposal-genetrated-grantpilot.docx` | **MISSING / UNVERIFIED** (repo has `smoke_test_export.docx` — not audited as reference) |
| `6643d922_export_v2.docx` | **PRESENT** at `M_E_Module/gate_run/6643d922_export_v2.docx` (binary; export audit based primarily on renderer code + decision log) |

### Search-term summary (grouped)

| Term | Approx. hits | Notable locations |
|------|--------------|-------------------|
| **Impact Pro** | ~18 files, ~70+ line matches | `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md` L68–72, L274; `ME_MODULE_WIREFRAMES_BRANDED.html` L604; `ME_MODULE_DECISION_LOG.md` D-004; orientation/plan duplicates under `M_E_Module/` |
| **$99** | ~16 files | Same M&E docs; `ME_MODULE_COST_AND_TRACING_BRIEF.md` L73 |
| **99** (bare) | Very noisy (~100+) | Mostly dates, UUID fragments, unrelated numbers; pricing tier refs concentrated in M&E memory/orientation docs |
| **$19** | **0** | — |
| **add-on** | **0** (product sense) | Only unrelated "one-off insert/helper" in scripts |
| **one-off** | 2 | `ME_DB_NLCF_INSERT_2026-06-04.md`, `scripts/generate_gap_answer_keys.py` (ops helpers, not billing) |
| **metered / consumable / extra report / pay-per-report** | **0** | — |
| **20 Fit** | 4 | `docs/artefacts/MVP_SCOPE_LOCK.md` L31; `PRICING_AND_ENTITLEMENTS.md` L26; `FRONTEND_ARCHITECTURE_SPEC.md`; `CONFLICTS_RESOLVED.md` |
| **M&E_REPORT / ME_REPORT** | **0** | — |
| **REPORT_CREATE / REPORT_EXPORT** | Docs only (4–6 hits) | `ENUM_REGISTRY.md` L220–221; `API_CONTRACT.md` §12; **not in Python** |
| **REPORT** (noisy) | Many | Dominated by `donor_reports`, `report_jobs`, route paths; no product "REPORT" action in code |
| **funding_opportunity_id** | ~20 files | Core fit-scan/proposal paths only; **absent from M&E tables** |
| **proposal_id** | Core proposals + optional `linked_proposal_id` on M&E | `donor_report.py` L28–31 |
| **docxtpl** | ~25 refs, all docs | Decision/plan only; **not in `requirements.txt`** |
| **python-docx** | Code | `requirements.txt` L11; `export_service.py`, `docx_renderer.py` |
| **donor_reports** | Widespread | Models, migrations, M&E services |
| **report_jobs** | Widespread | Worker pipeline |
| **uploaded_documents** | M&E contracts + models | No plan gate in upload route |
| **funder_report_templates** | M&E models + contracts | No public list API in `app/` |

---

## 1. Executive Verdict

**Ready to START Plan 1 design/integration work?** **Yes, with pre-work** — not ready to ship an integrated product surface.

| Category | Verdict |
|----------|---------|
| **Can begin Plan 1** | Backend M&E pipeline, DB isolation, lifecycle/gates/export stubs, and wireframe targets exist. Work can start on contract reconciliation, entitlements Stage J, API surface completion, and frontend (separate repo). |
| **Not launch-ready** | No M&E quota/entitlement enforcement; API contract vs implemented routes diverge; frontend has zero M&E routes in spec/repo; pricing/docs still describe third tier / 20 fit scans / no M&E bundle on Impact. |
| **Founder-owned doc reconciliation** | Large: `ENUM_REGISTRY`, `API_CONTRACT` §12, `ME_MODULE_*` memory/wireframes, `PRICING_AND_ENTITLEMENTS`, `MVP_SCOPE_LOCK` Impact fit-scan count, D-004 Impact Pro decision — all conflict with canonical two-plan target. |
| **Genuine code/architecture blockers** | (1) M&E not gated to Impact + no `REPORT_CREATE` ledger; (2) entitlements payload lacks `reports`; (3) missing list/detail/template APIs; (4) gate route path mismatch vs lifecycle; (5) frontend M&E surface absent; (6) `IMPACT` fit-scan limit still 20 in code. |

**Isolation rule:** No violations found — M&E stays under `app/reports/`; core tables unchanged; single mount in `app/main.py` L214–217.

---

## 2. Contract Conflicts Found

| Conflict | File/location | Current value | Target value | Severity | Owner | Recommended action |
|----------|---------------|---------------|--------------|----------|-------|---------------------|
| Third tier **Impact Pro / IMPACT_PRO / $99** | `ENUM_REGISTRY.md` L104–110, L220; `API_CONTRACT.md` L1110, L1129–1131, L1168; `ME_MODULE_DECISION_LOG.md` D-004; `ME_MODULE_MASTER_MEMORY.md` L68–72, L274; wireframes L604 | Separate `IMPACT_PRO` plan, $99, M&E only on third tier | **Two paid plans only**; M&E on **Impact $79**; retire Impact Pro | **BLOCKER** (billing/API) | DOC-RECONCILIATION then CODE | Amend contracts + decision log; revert D-004; update §12 entitlement to `IMPACT`; no new Stripe price for third tier |
| **Impact fit scans 20/month** | `PRICING_AND_ENTITLEMENTS.md` L26; `MVP_SCOPE_LOCK.md` L31; `quota_service.py` L43–47 | 20 | **10** | **HIGH** | CODE + DOC | Change `PLAN_QUOTAS` + reconcile pricing docs |
| **No M&E in pricing doc** | `PRICING_AND_ENTITLEMENTS.md` (entire file) | Fit/proposal/export only; uploads disallowed all tiers | Impact: **2 M&E reports/month** bundled; Growth/Free: **no M&E**; Impact upload entitlement for M&E docs | **BLOCKER** | DOC-RECONCILIATION then CODE | Extend pricing + entitlements contract before Stage J code |
| **M&E quota action types documented, not implemented** | `ENUM_REGISTRY.md` L220–221; `usage_ledger.py` L11–17; `quota_service.py` L139–157 | No `REPORT_CREATE` / `REPORT_EXPORT` in Python enum or `get_entitlements` | Ledger types + 2/month on Impact + idempotent export | **BLOCKER** | CODE | Add action types, quota bucket, enforce on create/export |
| **Growth users can use M&E API today** | `lifecycle.py` L50–65; no plan check in `create_donor_report` | Auth only | Growth/Free → **403 + upgrade-to-Impact** at all M&E entry points | **BLOCKER** | CODE | Server-side entitlement middleware on `/api/reports*` |
| **Uploads "not allowed" vs M&E uploads** | `PRICING_AND_ENTITLEMENTS.md` L9, L21, L29 | Profile uploads blocked all tiers | M&E document upload allowed on **Impact** (not Growth) | **HIGH** | DOC-RECONCILIATION | Clarify M&E upload vs profile upload; gate upload route |
| **API §12 vs implemented routes** | `API_CONTRACT.md` §12.4–12.11 vs `app/reports/api/routes/` | Contract: list, detail, PATCH KB, GET/PATCH gap, POST generate, `/api/report-templates` | Parity with contract | **HIGH** | CODE (+ contract if paths frozen) | Implement missing routes or contract amendment |
| **Gate URL path drift** | `gate1.py` L22–24; `lifecycle.py` L50 | Gates: `/api/reports/donor-reports/{id}/...`; lifecycle: `/api/reports/{id}/...` | Single consistent prefix per `API_CONTRACT.md` | **HIGH** | CODE | Align paths before frontend integration |
| **Wireframes show IMPACT PRO tier** | `ME_MODULE_WIREFRAMES_BRANDED.html` L604 | "IMPACT PRO · Plan" badge | "Impact" + quota copy; upgrade gate for Growth | **MEDIUM** | DOC-RECONCILIATION | Rebrand wireframes to two-plan model |
| **PRODUCT_NORTH_STAR omits M&E** | `PRODUCT_NORTH_STAR.md` L26–32, L44–46 | Fit Scan → Proposal Export only | Include M&E as post-award wedge (Path C) | **LOW** | DOC-RECONCILIATION | Update north star when founder locks |
| **LAUNCH_JOURNEYS no Path C** | `LAUNCH_JOURNEYS_SPEC.md` | No M&E / won-anywhere journey | Path A/B/C convergence | **HIGH** | DOC-RECONCILIATION | Add M&E entry journeys |
| **FRONTEND_ARCHITECTURE no `/reports`** | `FRONTEND_ARCHITECTURE_SPEC.md` L772–793 | Dashboard: fit scans + proposals only | Unified nav + M&E routes SCR 1–8 | **BLOCKER** (UX) | DOC + separate frontend repo | Extend spec; implement in frontend repo |
| **funding_opportunity_id on M&E** | `donor_report.py` L10–32 | No FK — optional `linked_proposal_id` only | Standalone report creation | **None (aligned)** | — | Preserve; document in API examples |
| **$19 / metered / consumable M&E** | Repo search | **Not found** | V2 parked | **None** | — | No action |

---

## 3. Current GrantPilot UI State

**Evidence limit:** This workspace contains **no frontend source** (0 `*.tsx` files). Table reflects `FRONTEND_ARCHITECTURE_SPEC.md` + backend API only. **Deployed Railway frontend: UNVERIFIED.**

| Area | Current state | Gap | Recommended Plan 1 action |
|------|---------------|-----|---------------------------|
| **Route map** | `(authenticated)/dashboard`, `fit-scan/[id]`, `proposal/new`, `proposal/[id]`, `profile`, `billing/*` — `FRONTEND_ARCHITECTURE_SPEC.md` L782–793 | No `/reports/*` routes | Add reports section to spec; implement SCR 1–8 in frontend repo |
| **Navigation** | Sidebar: dashboard, profile, billing implied | M&E not in primary nav | Single product nav: Fit Scan · Proposals · **Reports** |
| **Dashboard quotas** | `QuotaOverview`: fit scans + proposals only — L801–803 | No M&E quota tile | Extend dashboard + `GET /api/me/entitlements` consumer for `reports` |
| **Fit Scan UI** | `/start` WordPress handoff, `/fit-scan/{id}` detail — L148–152, L374+ | Tied to `funding_opportunity_id`; no cross-link to optional M&E | Keep; add optional "Create report" CTA post-win (Impact only) — not required for Path C |
| **Proposal UI** | Section viewer, regenerate, export — L553–569 | Internal metadata in export (backend); no M&E link UX | Optional `linked_proposal_id` picker on report create (SCR 2) |
| **Billing / usage UI** | `/billing` plan + quota — L790–792 | Two-plan copy may still show 20 fits; no M&E bundle | Reconcile pricing display; exhausted states per plan |
| **Upgrade states** | Spec covers fit/proposal exhaustion — L336–347 | No **upgrade-to-Impact** gate for M&E entry | New empty state on `/reports` for Free/Growth |
| **M&E quota exhausted** | N/A | No UI pattern | Impact-only: next-reset message; **no purchase path** |
| **Loading / empty states** | Defined for fit/proposal flows | None for reports | Mirror patterns for SCR 3–4 job polling |

---

## 4. Current M&E UI State

**Wireframes:** `ME_MODULE_WIREFRAMES_BRANDED.html` defines SCR 1–8 (dashboard → funder choice → upload → agent work → Gate 1–3 → export).

| Area | Current state | Gap | Recommended Plan 1 action |
|------|---------------|-----|---------------------------|
| **SCR 1 Dashboard** | Wireframe: `/reports`, list + "New donor report" — L596–625 | **Not implemented** in frontend repo (absent from workspace) | Build list page calling `GET /api/reports` (API missing) |
| **SCR 2 Funder/template** | Wireframe L641–675 | No `GET /api/report-templates` in backend | Template list API + funder picker UI |
| **SCR 3 Upload** | Backend: `POST .../documents` — `lifecycle.py` L68–98 | No UI; no entitlement gate on upload | Upload component + Impact check |
| **SCR 4 Agent progress** | Backend: `GET .../job` — L123–148 | No watch UI | Poll job status + stage labels |
| **SCR 5 Gate 1** | Backend: `POST .../gate1/confirm` — `gate1.py` L22–45 | Path prefix mismatch; no GET KB edit UI per contract PATCH | KB review screen + aligned API |
| **SCR 6 Gate 2** | Backend: `POST .../gate2/gap-responses` — `gate2.py` L23–26 | No GET gap-check UI (`API_CONTRACT` §12.6) | Gap questionnaire UI |
| **SCR 7 Gate 3** | Backend: `gate3.py` (confirm route exists) | Section review + critic flags UI missing | Draft review + accept/edit |
| **SCR 8 Export** | Backend: `GET .../export` — `export.py` L21–45 | Download button only after gates; no in-app preview | Export CTA + quota messaging |
| **Tier badge** | Wireframe L604: "IMPACT PRO" | Wrong tier model | "Impact" + reports remaining |
| **Path C entry** | Copy in wireframe L607: "Won a grant — with us or anyone else" | No landing/journey in `LAUNCH_JOURNEYS_SPEC` | Marketing + `/reports` direct entry |
| **Growth gate** | Not in wireframes | Required | Full-page upgrade-to-Impact on `/reports` for non-Impact |

---

## 5. Pricing, Entitlements, Stripe Audit

| Component | Current state | Required target state | Risk | Recommended action |
|-----------|---------------|----------------------|------|---------------------|
| **Plan enum (DB)** | `FREE \| GROWTH \| IMPACT` — `user_plan.py` L13–15 | Same (no third tier) | Low | **Do not add IMPACT_PRO**; amend docs that require it |
| **Plan enum (docs)** | `IMPACT_PRO` in `ENUM_REGISTRY.md` L104 | M&E on `IMPACT` only | **HIGH** | Doc reconciliation |
| **Stripe checkout** | `GROWTH`, `IMPACT` only — `billing.py` L34 | Same | Low | No third price ID |
| **Impact fit-scan quota** | 20 — `quota_service.py` L44 | **10** | Medium | Code + doc fix |
| **M&E report quota** | **Not implemented** | 2/month on Impact, `BILLING_CYCLE` reset | **BLOCKER** | Extend `PlanQuota`, `get_entitlements`, `enforce_quota` |
| **Usage ledger actions** | `FIT_SCAN`, `PROPOSAL_CREATE`, `PROPOSAL_REGEN`, `DOCX_EXPORT` — `usage_ledger.py` L11–17 | Add **`REPORT_CREATE`**, **`REPORT_EXPORT`** (idempotent per report version) | **BLOCKER** | Enum + migration comment only (TEXT column) |
| **Entitlements response** | `fit_scans`, `proposals`, `proposal_regenerations` — `entitlements.py` L16–19 | Add **`reports`** (+ optional `report_exports`) | **BLOCKER** | Schema + `get_entitlements` |
| **M&E route enforcement** | None on `/api/reports*` | Impact + quota on create; Growth → upgrade error | **BLOCKER** | Dependency or service guard |
| **Exhausted handling** | Generic `QUOTA_EXCEEDED` for fit/proposal — `quota_service.py` L181–190 | Growth/Free: never reach M&E quota; Impact: reset message only | Medium | Distinct error codes/messages for UI |
| **Support labels** | Not in entitlements API | "Normal" (Growth), "Priority" (Impact) | Low | Marketing/copy in billing UI; optional metadata field |
| **Stripe webhooks** | Subscription cycle reset for fit/proposal — `STRIPE_INTEGRATION_SPEC.md` | Same cycle resets **reports** counter | Medium | No one-off SKUs; bundle only |
| **Upload entitlement** | Pricing: uploads disallowed — `PRICING_AND_ENTITLEMENTS.md` L21 | Impact M&E uploads allowed | Medium | Clarify in pricing doc |
| **Proposal DOCX export quota** | Uses `DOCX_EXPORT` ledger — `export_service.py` L52–57 | Unchanged for Plan 1 | Low | Keep separate from M&E export ledger |

---

## 6. DOCX Export Design Audit

### Proposal export

| Aspect | Finding |
|--------|---------|
| **Approach** | **python-docx from scratch** — `export_service.py` L73–74, `_build_docx_bytes` |
| **docxtpl** | Not used; not in `requirements.txt` |
| **Formatting weaknesses** | Cover exposes internal metadata (Proposal ID, Version, UTC timestamp) — L76–80; failed sections → **"To be completed manually"** — L96–97; assumptions in separate appendix — L99–109 |
| **Tables / footers / page numbers** | Basic headings only; no tables, footers, or page numbers |
| **Reference DOCX** | `proposal-genetrated-grantpilot.docx` **MISSING** |

### M&E export

| Aspect | Finding |
|--------|---------|
| **Approach** | **python-docx** via `docx_renderer.py`; `render_mode` `from_scratch` or `base_template` if file exists — L154–160, D-044 |
| **docxtpl (target)** | D-010 locks **docxtpl** long-run; D-044 shipped interim python-docx for Stage F gate |
| **Template location** | `resolve_docx_template_path` — L21–32; `funder_report_templates.docx_template_ref`; default `system/default.docx` often **missing on disk** → from_scratch |
| **Internal artefact leakage** | **Yes — structural UI issue:** `[Section not generated]`, `[Not generated: …]`, per-section **Assumptions** headings — L195–215 |
| **Hygiene** | D-045 terminology/citation strip at render layer — labels only |
| **Reference DOCX** | `6643d922_export_v2.docx` present; quality bar doc **MISSING** |

### Shared code?

| Question | Answer |
|----------|--------|
| Do proposal and M&E share export code? | **No** — core `export_service.py` vs `app/reports/export/docx_renderer.py` (isolation correct) |
| Should they share? | Share **style helpers** only if desired; keep **separate renderers** (funder templates vs proposal sections) |

### Recommended template architecture (prose, no code)

1. **Phase 1 (Plan 1):** Keep python-docx renderers; **stop leaking** internal placeholders into client DOCX — map `FAILED`/missing to funder-appropriate blank sections or omit with table skeletons from `funder_report_templates.report_sections_json`.
2. **Phase 2 (post–Plan 2 quality):** Introduce **docxtpl** per D-010 under `app/reports/templates/docx/{funder}/{template}.docx` with variables: `ngo_name`, `reporting_period`, `funder_name`, `sections[]` (heading, body_richtext, tables), `assumptions_appendix`, `evidence_appendix`, `action_plan`. Proposal export may adopt a **single GrantPilot proposal template** separately — do not merge with M&E funder templates.
3. **Content mapping:** Headings ← template section labels; tables ← `required_tables` + indicator actuals; callouts ← critic WARN blocks (Gate 3); assumptions/evidence ← appendices only when user accepted at Gate 3; never export agent trace or `[fact:…]` markers.
4. **Risk:** Changing export **design** before Plan 2 synthesis/critic quality work may churn templates twice — lock **structure** in Plan 1, defer **visual polish** until section quality stabilizes.

---

## 7. Integration Architecture Findings

| Layer | Current state | Gap / note |
|-------|---------------|------------|
| **Feature flag** | `ME_MODULE_ENABLED` gates router — `main.py` L214–217 | Frontend needs `NEXT_PUBLIC_ME_MODULE_ENABLED` (separate repo, UNVERIFIED) |
| **M&E independence** | No `funding_opportunity_id` on `donor_reports`; optional `linked_proposal_id` — `donor_report.py` L28–31; default template if none — `donor_report_lifecycle_service.py` L42–90 | **Aligned** with target |
| **Standalone create** | `POST /api/reports` with period dates only — `lifecycle.py` L50–65 | Works; funder template optional (defaults) |
| **Worker / jobs** | `POST /api/reports/{id}/job`, poll `GET .../job` | Pipeline runs in worker (not audited in depth); Gate 2 blocked on gap output size (operational, Plan 2) |
| **Human gates** | Gate 1–3 POST routes exist; server stamps in `knowledge_bank_json` | GET/PATCH gap flows incomplete vs contract |
| **Report history** | No `GET /api/reports` list | Dashboard/history blocked |
| **Report export** | `GET /api/reports/{id}/export`; no quota ledger | Add `REPORT_EXPORT` idempotency |
| **Template catalog** | DB `funder_report_templates`; no list endpoint | SCR 2 blocked |
| **Quota (M&E)** | Not enforced on create | Stage J blocker |
| **API contract** | §12 references `IMPACT_PRO`, full CRUD surface | Reconcile to `IMPACT` + implement missing endpoints |
| **Frontend** | Not in repo | All M&E UX in separate frontend repo |
| **Analytics** | No product event spec for M&E | **NOT FOUND** — add events for report create, gate confirm, export |
| **Admin/support** | Agent trace in `report_jobs.agent_trace_json` | No admin UI spec for support visibility |
| **Staging/prod** | M&E flag + worker scale documented in kill-switch docs | Parity UNVERIFIED without env access |

### Implemented vs `API_CONTRACT.md` §12 (summary)

| Endpoint (contract) | Implemented |
|---------------------|-------------|
| `GET /api/report-templates` | **No** |
| `POST /api/reports` | **Yes** |
| `POST /api/reports/{id}/documents` | **Yes** |
| `GET /api/reports/{id}/knowledge-bank` | **Yes** |
| `PATCH /api/reports/{id}/knowledge-bank` | **No** |
| `GET /api/reports/{id}/gap-check` | **No** |
| `PATCH /api/reports/{id}/gap-answers` | Partial (gate2 POST different path) |
| `POST /api/reports/{id}/generate` | **No** (job enqueue instead) |
| `GET /api/reports/{id}` | **No** |
| `GET /api/reports` | **No** |
| `PATCH /api/reports/{id}/sections/{key}` | **No** |
| `GET /api/reports/{id}/job` | **Yes** |
| `GET /api/reports/{id}/export` | **Yes** |

---

## 8. Candidate Work-Package Inventory

*Unordered. No $19 add-on packages.*

1. **Contract reconciliation (two-plan + Impact M&E bundle)** — Objective: align `ENUM_REGISTRY`, `API_CONTRACT` §12, `PRICING_AND_ENTITLEMENTS`, `ME_MODULE_MASTER_MEMORY`, wireframes, D-004 with canonical target. Files: `docs/artefacts/**`, `ME_MODULE_DECISION_LOG.md`. Dependencies: founder approval.

2. **Impact fit-scan quota 20→10** — Objective: code + docs match 10/month. Files: `quota_service.py`, pricing docs. Dependencies: none.

3. **M&E usage ledger + entitlements** — Objective: `REPORT_CREATE`/`REPORT_EXPORT`, `reports` block in entitlements, 2/month on Impact. Files: `usage_ledger.py`, `quota_service.py`, `entitlements.py`, tests. Dependencies: contract reconciliation.

4. **M&E entitlement guards** — Objective: block Free/Growth at all `/api/reports*` with upgrade payload; enforce quota on create. Files: `app/reports/api/dependencies` or lifecycle service. Dependencies: WP3.

5. **API surface completion** — Objective: list/detail reports, template list, gap-check GET, KB PATCH, path alignment for gates. Files: `app/reports/api/routes/*`, `API_CONTRACT.md` if amended. Dependencies: contract lock.

6. **Frontend M&E route scaffold** — Objective: SCR 1–8 routes, nav, feature flag. Files: separate frontend repo per `FRONTEND_ARCHITECTURE_SPEC`. Dependencies: WP5, entitlements shape.

7. **Unified dashboard quotas** — Objective: fit scans + proposals + M&E on dashboard/billing. Files: frontend components + entitlements consumer. Dependencies: WP3, WP6.

8. **Upgrade / exhausted states** — Objective: Growth→Impact gate on `/reports`; Impact reset message. Files: frontend + error contract. Dependencies: WP4.

9. **Launch journeys Path C** — Objective: won-anywhere M&E entry in `LAUNCH_JOURNEYS_SPEC` + landing copy. Files: journey docs, marketing. Dependencies: WP6.

10. **DOCX export structure hardening (Plan 1)** — Objective: remove internal placeholders from client export; optional base template path for NLCF/FCDO. Files: `docx_renderer.py`, template assets. Dependencies: none for minimal fix; docxtpl deferred.

11. **docxtpl template pipeline (later within Plan 1 if time)** — Objective: install docxtpl, funder `.docx` bases, variable contract. Files: `requirements.txt`, `app/reports/export/`, `funder_report_templates`. Dependencies: WP10, funder template assets.

12. **M&E analytics events** — Objective: server-side or frontend events for funnel metrics. Files: TBD spec + frontend. Dependencies: WP6.

13. **Support/admin read-only report inspect** — Objective: internal view of job stage, gates, trace. Files: admin route or script (out of user scope). Dependencies: none.

14. **Upload entitlement clarification** — Objective: Impact-only M&E uploads in pricing + enforcement. Files: pricing doc, upload route guard. Dependencies: WP4.

15. **FRONTEND_ARCHITECTURE_SPEC extension** — Objective: document `/reports/*`, API mapping, states. Files: `FRONTEND_ARCHITECTURE_SPEC.md`. Dependencies: WP1.

---

## 9. What NOT To Touch Yet

### Plan 2 (quality)

- Gap/compliance agent output size, JSON truncation, checklist verbosity (`GAP_AGENT_OUTPUT_DIAGNOSIS.md`).
- Synthesis section prose quality, critic accuracy, fact-safety thresholds.
- Knowledge-bank reconciliation conflict UX copy (beyond structural UI).
- Proposal AI section quality, Fit Scan scoring quality.
- Full funder-template visual parity with `7-large-grants-progress-report-template.docx` (missing reference).

### Plan 3 (security)

- Prompt-injection hardening review, upload malware scanning, secrets rotation.
- Penetration testing, OWASP pass on M&E upload surface.
- Production Stripe live-mode changes without staged rollout.

### V2 (explicitly out of scope)

- **$19 one-off / pay-per-report M&E add-on** — do not design, build, or document as in-scope.
- Consumable/metered report purchases, "extra report" SKUs.

### Isolation / thin-client (do not violate during Plan 1)

- No core imports of `app.reports`.
- No entitlement/Stripe logic in frontend beyond displaying API responses.
- No core table migrations for M&E.

---

*End of Plan 1 Read-Only Audit.*
