# A-00 Contract Reset Changelog

**Work package:** A-00 — controlled governance/spec reconciliation  
**Date:** 2026-06-06  
**Mode:** DRY_RUN = false (edits applied)  
**Scope:** Backend canonical docs only (`docs/artefacts/`, `docs/artefacts/me_module/`). No code. No frontend mirror. No git commit.

---

## Summary

Ten governance files updated to the **two-plan canonical target** (Growth $39, Impact $79 with 2 bundled M&E reports/mo). Plan enum locked to `FREE | GROWTH | IMPACT`. §12 aligned to job-model + `/api/reports/{id}/...` path prefix. Decision log appended D-048–D-050; D-004/D-005 annotated superseded.

**STOP for founder:** Review via `git diff` before A-01/A-02/A-03.

---

## Per-file changes

### 1. `docs/artefacts/PRICING_AND_ENTITLEMENTS.md`

| Edit | Before → After |
|------|----------------|
| Free plan | Added M&E not available; clarified profile uploads |
| Growth plan | Added M&E not available, normal support; clarified profile uploads |
| Impact Fit Scans | **20 / month → 10 / month** |
| Impact plan | Added 2 M&E reports/mo, M&E document uploads, priority support |
| Quota enforcement | Added **M&E report quota exhausted** block (Free/Growth upgrade gate; Impact reset, no purchase) |
| Upload clarification | New section: profile uploads vs M&E report-source uploads (Impact only) |
| Quota accounting | Added M&E report decrement rule |
| Quota reset | Added reports counter resets with billing cycle |

### 2. `docs/artefacts/ENUM_REGISTRY.md`

| Edit | Before → After |
|------|----------------|
| §4.1 Plan names | Removed `IMPACT_PRO`; rules now two-plan + M&E on IMPACT (D-048) |
| §5.10 reports quota | `IMPACT_PRO` → **IMPACT** |
| §3.3 | **No change** — already listed `REPORT_CREATE` / `REPORT_EXPORT` |

### 3. `docs/artefacts/MVP_SCOPE_LOCK.md`

| Edit | Before → After |
|------|----------------|
| In scope | Added **M&E Donor Report Writer** |
| Impact Fit Scans | **20 → 10** |
| Impact plan | Added **2 M&E reports per month** |
| Growth uploads | Clarified profile-only; M&E uploads Impact-only |

### 4. `docs/artefacts/API_CONTRACT.md`

| Edit | Before → After |
|------|----------------|
| §4 entitlements | Added **`reports`** and **`report_exports`** blocks + limit notes |
| §10.2 | Extended entitlement enum with `reports` \| `report_exports` |
| §10.3 | **New** `403 UPGRADE_REQUIRED` envelope |
| §12 header | `IMPACT_PRO` → **IMPACT**; added path prefix + independence + job model notes |
| §12.0 | Removed IMPACT_PRO future billing refs |
| §12.1, 12.2 auth | `IMPACT_PRO` → **IMPACT** |
| §12.5, 12.6, 12.7, 12.11 | Marked **PROVISIONAL — Track B** |
| §12.5a, 12.7a, 12.8a | **New** canonical POST gate routes (path-aligned) |
| §12.8 | **Removed** `POST .../generate`; **replaced** with `POST /api/reports/{id}/job` |
| §12.14 | Added `UPGRADE_REQUIRED` row |
| Changelog footer | IMPACT_PRO ref → IMPACT bundled entitlements |

### 5. `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md`

| Edit | Before → After |
|------|----------------|
| §4 GTM | Third tier language → Impact bundled capability; $39–99 → Growth/Impact pricing |
| §5 Tier & pricing | **Rewritten** to two-plan table; removed Impact Pro, consolidate-later, dual-capability tier |
| §5 cost ceiling | Reframed to Impact $79 / 2 reports; **flagged** founder margin vs $49.50/$99 assumption |
| §6 in scope | Impact Pro billing tier → Impact M&E entitlement |
| §10 Stage J/K | Impact Pro → **Impact** M&E live |
| §18 artefact refs | Impact Pro wireframe badge → **Impact** |

### 6. `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md`

| Edit | Before → After |
|------|----------------|
| D-004, D-005 | Prefixed **SUPERSEDED by D-048 —** (rows preserved) |
| New rows | **D-048** two-plan model; **D-049** Fit Scans 20→10; **D-050** Plan 1 DOCX scope |
| O-004 | `STRIPE_PRICE_ID_IMPACT_PRO` → **`STRIPE_PRICE_ID_IMPACT`** |
| Revisions table | Added D-048 supersedes D-004/D-005 |
| D-010, D-020 | **Untouched** |

### 7. `docs/artefacts/me_module/ME_MODULE_WIREFRAMES_BRANDED.html`

| Edit | Before → After |
|------|----------------|
| SCR 1 tier badge | `IMPACT PRO · Plan` → **`Impact · Plan · Reports remaining: 1 / 2`** |

### 8. `docs/artefacts/PRODUCT_NORTH_STAR.md`

| Edit | Before → After |
|------|----------------|
| Core Solution | Added post-award M&E / donor-ready reporting line |
| North Star Metric | **Untouched** — flagged for founder (see below) |

### 9. `docs/artefacts/LAUNCH_JOURNEYS_SPEC.md`

| Edit | Before → After |
|------|----------------|
| J8 Path C | **New** journey at definition level (won-anywhere M&E, upgrade gate, gates, export) |
| Paths A/B | **Unchanged** |

### 10. `docs/artefacts/FRONTEND_ARCHITECTURE_SPEC.md`

| Edit | Before → After |
|------|----------------|
| Billing mockup | 20 Fit Scans → **10**; added 2 M&E reports/mo on Impact upgrade card |
| Quota messaging table | 20 scans copy → **10**; Growth upsell mentions M&E |
| §2.1 page map | One-line note: **`/reports` UI spec pending Track B** |
| `/reports` routes | **Not added** (per brief) |

---

## Verification pass

Search across `docs/artefacts/` and `docs/artefacts/me_module/` for drift terms:

| Term | Result in **A-00 edited files** | Remaining elsewhere (out of A-00 scope) |
|------|--------------------------------|----------------------------------------|
| Impact Pro / IMPACT_PRO / $99 | **Intentional only** in D-004/D-005 superseded rows + D-048 text + master memory margin note | `ME_MODULE_ARCHITECTURE_SPEC.md`, `ME_MODULE_INTERNAL_ARCHITECTURE.html`, `ME_MODULE_PROJECT_PLAN.md`, `ME_MODULE_ORIENTATION_REPORT.md`, `REPO_MAP_ME_MODULE.md`, `ME_MODULE_KILL_SWITCH.md`, `DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS.md`, `WORKSTREAM_T2_*.md` (historical/T2 note) |
| 20 Fit / 20 fit scans | **Zero** in edited files | `ARTEFACTS_V1_LOCKED.md` L54 (not in A-00 list) |
| $19 / add-on / metered / consumable / pay-per-report | **Zero** | — |

### New content confirmed present

| Check | Location |
|-------|----------|
| PRICING M&E + Impact 10 fits | `PRICING_AND_ENTITLEMENTS.md` |
| API §4 `reports` / `report_exports` | `API_CONTRACT.md` §4 |
| API §10.3 `UPGRADE_REQUIRED` | `API_CONTRACT.md` §10.3 |
| ENUM IMPACT-only M&E quota | `ENUM_REGISTRY.md` §4.1, §5.10 |
| REPORT_CREATE / REPORT_EXPORT | `ENUM_REGISTRY.md` §3.3 (pre-existing) |
| D-048–D-050 + D-004/D-005 superseded | `ME_MODULE_DECISION_LOG.md` |
| Path C J8 | `LAUNCH_JOURNEYS_SPEC.md` |
| Wireframe Impact badge | `ME_MODULE_WIREFRAMES_BRANDED.html` |
| North star M&E line | `PRODUCT_NORTH_STAR.md` |

---

## FLAGGED FOR FOUNDER

1. **Margin / cost ceiling** — Master memory retains founder note: prior ~$49.50/report revenue assumption was at $99 tier; bundled 2 reports @ $79 needs margin confirmation (D-048). No new numbers invented.

2. **North Star Metric** — Still "Fit Scan → Proposal Export within 14 days" only. Post-award M&E added to Core Solution but **not** to North Star. Decide whether to add a Path C activation metric.

3. **Out-of-scope doc drift** — Files not in A-00 list still reference Impact Pro / IMPACT_PRO / $99 / 20 fits. Recommend a follow-up **A-00b** or fold into A-01 doc hygiene:
   - `ME_MODULE_ARCHITECTURE_SPEC.md`
   - `ME_MODULE_INTERNAL_ARCHITECTURE.html`
   - `ME_MODULE_PROJECT_PLAN.md`
   - `ME_MODULE_ORIENTATION_REPORT.md`
   - `REPO_MAP_ME_MODULE.md`
   - `ME_MODULE_KILL_SWITCH.md`
   - `DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS.md`
   - `ARTEFACTS_V1_LOCKED.md`

4. **Code vs contract** — A-00 is docs-only. Known gaps for A-01/A-02/A-03: `quota_service.py` Impact fit scans still 20; no `REPORT_CREATE` in Python enum; gate paths still use `donor-reports` segment; §12 export verb (GET implemented vs POST in older §12.13 text — not changed in A-00).

5. **Frontend mirror** — `ngoinfo-grantpilot-frontend/docs/contracts/` not updated (Track B separate task).

---

## STOP

A-00 complete. **Do not commit** until founder reviews diff. **Do not proceed** to A-01/A-02/A-03 until approved.
