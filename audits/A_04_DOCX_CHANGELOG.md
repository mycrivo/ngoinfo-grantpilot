# A-04 — DOCX Structural Hardening Changelog

**Work package:** A-04 (proposal + M&E export presentation chrome only)  
**Date:** 2026-06-06  
**Status:** Complete — **STOP for human git-diff + sample-document review. Not committed. Not deployed.**

---

## Step 1 — Findings

### Renderer files (exact paths)

| Document | Renderer module | Orchestration | Engine |
|----------|-----------------|---------------|--------|
| **Proposal export** | `app/services/proposal_docx_renderer.py` (`build_proposal_docx_bytes`) | `app/services/export_service.py` | python-docx from scratch |
| **M&E report export** | `app/reports/export/docx_renderer.py` (`render_donor_report_docx`) | `app/reports/services/report_export_service.py` | python-docx from scratch (optional base `.docx` if `docx_template_ref` exists on disk) |

**docxtpl:** Not installed (`requirements.txt` has `python-docx==1.1.2` only; repo-wide grep finds no `docxtpl`).

### Brand basis (print adaptation)

Source: `docs/artefacts/me_module/NGOINFO_BRAND_GUIDELINES.md` §3–4, `docs/artefacts/BRAND_AND_FRONTEND_SPEC.md` §1–2.

| Token | Spec value | A-04 print choice |
|-------|------------|-------------------|
| Primary navy | `#1A1F71` | Title + Heading 1/2/3 colour |
| Body text | `#1F2937` / `#374151` | Normal style `#1F2937` |
| Muted meta | `#64748B` | Cover subtitles + footer |
| Font | DM Sans (web) | **Calibri 11pt** body / scaled headings — **FLAG:** Word may not have DM Sans embedded; Calibri chosen as conservative print fallback |

### Before → after emission behaviour

**Proposal (before):**
- Cover: opportunity title (Heading 0), `NGO:`, `Generated At (UTC):` ISO timestamp, `Proposal ID:`, `Version:` — **internal metadata leak**
- Sections: Heading 1 from `label`; non-`GENERATED` → `"To be completed manually"`
- Assumptions: structured `content.assumptions[]` per section → end `"Assumptions Appendix"` (deduped bullets)

**Proposal (after):**
- Branded title block: NGO name, `Grant Proposal — [Funder]`, human date (`6 June 2026` format)
- Sections: Heading 1 only; empty/non-generated sections leave heading with **no placeholder prose**
- Assumptions: consolidated `"Assumptions & Caveats"` appendix via shared helper
- Footer: org name + `"Grant Proposal"` + Page X of Y fields

**M&E (before):**
- Cover: template document title (Heading 0), `Funder:`, `Reporting period:` — no NGO name
- Missing section → `"[Section not generated]"`; failed → `"[Not generated: …]"`
- Assumptions: inline per section under Heading 3 `"Assumptions"`
- Body: internal citation tokens stripped (pre-existing); markdown tables rendered (pre-existing)

**M&E (after):**
- Branded title block: NGO name (from `NGOProfile`), `Donor Report — [Funder]`, reporting period, human date
- Suppressed `[Section not generated]` / `[Not generated: …]` — heading only
- Assumptions: collected from structured `content.assumptions[]` → single end appendix (inline Heading 3 scaffolding removed)
- Footer + page numbers via shared helper

### Assumptions gate

**Decision: STRUCTURED field** — both proposal and M&E store assumptions in `content.assumptions[]` per section (see `app/reports/schemas/content_json_v1.py`). Consolidation into one end-of-document appendix **implemented** for both renderers.

**Inline prose limitation (FLAG):** Section body text may still mention assumptions in narrative (e.g. fixture line *"Assumption on focal teacher availability was partially realised."* in `risk_and_safeguarding`). A-04 does **not** parse or relocate inline prose — Plan 2 if needed.

### Page numbers gate

**Decision: CLEAN** — footer uses standard python-docx `OxmlElement` PAGE + NUMPAGES field codes (documented community pattern; not raw file hacking). Renders as `"Page X of Y"` in footer on all sections.

---

## Files changed

| File | Change |
|------|--------|
| `app/core/docx_presentation.py` | **NEW** — shared house style, title block, footer/page fields, assumptions appendix, artifact helpers |
| `app/services/proposal_docx_renderer.py` | **NEW** — proposal render logic extracted from export service |
| `app/services/export_service.py` | Delegates to `build_proposal_docx_bytes`; cover metadata removed from output |
| `app/reports/export/docx_renderer.py` | Branded cover, suppress placeholders, consolidate assumptions, shared style/footer |
| `app/reports/services/report_export_service.py` | Resolves `NGOProfile.organization_name`; passes `ngo_name` + `generated_at` to renderer |
| `tests/test_docx_structural_hardening.py` | **NEW** — A-04 acceptance assertions |
| `tests/test_report_export_service.py` | Seeds `NGOProfile` for export path |
| `tests/worker_validation_seed.py` | Adds `ngo_profiles` table to in-memory SQLite |
| `scripts/generate_a04_sample_docx.py` | **NEW** — sample generator for founder review |

**Isolation:** `app/core/docx_presentation.py` has zero M&E imports. Core does not import `app.reports/`. M&E imports core only.

---

## Sample documents (founder review)

| File | Description |
|------|-------------|
| `audits/A_04_SAMPLE_proposal.docx` | BridgeLight proposal — 3 sections, assumptions appendix, missing section heading-only |
| `audits/A_04_SAMPLE_me_report.docx` | FCDO fixture content — full template order, assumptions appendix |

Regenerate: `python scripts/generate_a04_sample_docx.py`

---

## Test results

```
python -m pytest tests/test_docx_structural_hardening.py tests/test_docx_renderer.py tests/test_report_export_service.py -q
19 passed in 7.21s
```

| Suite | Result |
|-------|--------|
| `tests/test_docx_structural_hardening.py` | 12 passed (A-04 acceptance) |
| `tests/test_docx_renderer.py` | 3 passed (content/terminology regression) |
| `tests/test_report_export_service.py` | 4 passed (export persist + download route) |

Export route behaviour, content-type, filename, and quota interaction **unchanged**.

---

## FLAGGED FOR FOUNDER

1. **Font:** Calibri used for Word compatibility; brand spec prefers DM Sans for web. Confirm print font choice or embed DM Sans in a future template pass (D-010).
2. **Inline assumptions prose:** Structured `assumptions[]` consolidated; narrative mentions of assumptions in section body text remain inline (not extracted). Plan 2 if relocation required.
3. **Tables:** M&E renderer still emits markdown pipe tables as Word tables (pre-existing). A-04 scope fence — no table work done; flagged for follow-on.
4. **Base template path:** When `docx_template_ref` file exists on disk, renderer opens it then applies chrome on top. FCDO fixture uses `from_scratch` in tests (template file absent). Confirm behaviour when real funder `.docx` bases arrive (D-010).
5. **Proposal empty sections:** Removed `"To be completed manually"` placeholder (not in suppress list but violates "never author replacement prose"). Sections now heading-only when not `GENERATED`.
6. **House-style accent:** No logo image in title block (python-docx text-only chrome). Logo embedding deferred to template-engine track.

---

## Non-goals confirmed untouched

- No docxtpl install or template-engine migration
- No section content rewrite, completion, or reordering
- No export route / quota / entitlement changes
- No pipeline, agents, orchestrator, or frontend changes
- No new dependencies
