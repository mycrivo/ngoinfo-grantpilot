# P2-CORRECTIONS — Part 1 findings

**Date:** 2026-06-09  
**Scope:** Read-only confirmation before P2-CORRECTIONS build  
**STOP gate:** Not triggered — proceed to Part 2.

---

## 1. Gate-1 fact-confirmation UI

### Components (live frontend: `ngoinfo-grantpilot-frontend`)

| Role | Path |
|------|------|
| Page | `app/(authenticated)/reports/[id]/facts/page.tsx` |
| Shell | `components/reports/gate1/Gate1ReviewFacts.tsx` |
| Layout VM | `lib/knowledge-bank-gate1-layout.ts` |
| Fact rows | `Gate1FactGridRow.tsx`, `Gate1IndicatorTable.tsx`, `Gate1FinancialTable.tsx` |
| Conflicts | `Gate1ConflictPanel.tsx`, `Gate1ClientConflictPanel.tsx` |
| Footer | `Gate1StickyFooter.tsx` |
| API client | `lib/api/reports.ts` — `getKnowledgeBank`, `patchKnowledgeBank`, `confirmGate1` |

### Flat vs grouped

- **API / storage:** flat `facts` map on `knowledge_bank_json`.
- **UI:** section-grouped (programme summary, indicators table, financials, objectives, reporting, other) via `buildGate1LayoutView()`.
- **Not cluster-confirmable:** no per-cluster batch promote wired in UI before P2-CORRECTIONS.

### Rubber-stamp behaviour (pre-correction)

`facts/page.tsx` calls `confirmGate1({ knowledge_bank_json: payload })` with the full KB — a single global confirm. No `promoteGate1` client call.

### Unverified / degraded visibility (pre-correction)

`Gate1FactGridRow` shows a `confirmed` badge only; `verification_status: unverified` is not visually distinct.

### Batch promotion API (backend — exists)

**Endpoint:** `POST /api/reports/{donor_report_id}/knowledge-bank/gate1/promote`  
**Handler:** `app/reports/api/routes/gate1.py` → `promote_gate1_facts`  
**Schema:** `app/reports/schemas/gate1_confirmation.py`

**Request shape:**

```json
{
  "promote_fact_keys": [
    {
      "fact_key": "string (required)",
      "confirmed_value_snapshot": "<any — must match current fact.value>"
    }
  ],
  "cluster_id": "string | null (observability only)"
}
```

- Does **not** set `gate1_confirmed_at`.
- Promotes only `unverified` facts after per-fact snapshot validation.
- Confirm endpoint (`POST .../gate1/confirm`) accepts the same optional `promote_fact_keys` batch before stamping Gate 1.

**Tests:** `tests/test_p1_fence_eval.py` — `test_cluster_batch_promotion_makes_facts_citable`.

---

## 2. Template state (Phase 2 build vs prod `55f891ac`)

| Location | Phase 2 build modified? | Funder-owned rows still present? |
|----------|-------------------------|----------------------------------|
| **Prod DB** `55f891ac-bb8b-4137-bc42-6de8ff935064` | **No** — repo/test artefacts only; prod row inserted manually (`ME_DB_LIVE_VERIFICATION_2026-06-04.md`). | **Yes** — prod row predates P2-1 `owner` / `indicator_requirements` unless owner updated manually. |
| `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` | **Yes** — P2-1 tags (`owner`, `indicator_requirements`, `table_requirements`). | **Yes** — rows retained; runtime filter excludes from NGO checklist. |
| `docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` | Conditional visibility fix only; no funder tags. | N/A |
| `tests/worker_validation_seed.py` | Generic empty template; unchanged. | No |
| `tests/test_orchestrator_gate1.py` `_apply_fcdo_template_to_report` | Overlays repo FCDO JSON in tests. | Inherits repo tags |

### Enumerated funder-owned refs (FCDO)

**Sections (default owner funder):** `detailed_output_scoring`, `value_for_money`

**Indicators (funder_supplied or funder owner):** `output_scores`, `impact_weightings`, `risk_ratings`, `economy`, `efficiency`, `effectiveness`, `equity`, `commercial_improvement_where_relevant`, `FCDO_management_actions`

**Tables:** `output_score_table`, `vfm_measures`

**Runtime defense:** `app/reports/gap/requirement_metadata.py` — `is_ngo_checklist_item()` excludes funder-owned / funder_supplied from Gate 2 checklist.

---

## 3. Render-path dependency (COMPLETE reports)

| Path | Reads from | Template-dependent? |
|------|------------|---------------------|
| In-app view (`GET /api/reports/{id}`) | `donor_reports.content_json` | **No** for prose |
| Download export (`GET .../export`) | `content_json.export.storage_ref` blob | **No** |
| Stage H re-export | `docx_renderer` merges **current** `template.report_sections_json` + `content_json.sections` | **Yes** on re-export only |

**Code:** `app/reports/services/report_export_service.py`, `app/reports/export/docx_renderer.py`, `app/reports/services/report_read_service.py`.

**Implication for funder-row deletion:** Existing COMPLETE reports keep stored prose and DOCX; deletion affects **future re-exports** and new runs using the updated template row.

---

## 4. Readiness — compute, persist, render (pre-correction)

| Stage | Location |
|-------|----------|
| Compute | `app/reports/gap/deterministic_gaps.py`, `post_draft_gaps.py`, `gap_compliance_agent.py` |
| Persist | `donor_reports.gap_analysis_json` via `envelope_to_gap_analysis_json` |
| API | `GET /api/reports/{id}/gap-check` — `gap_check_service.py` |
| Frontend | `Gate2AnswerQuestions.tsx` — percentage bar + `readiness_label` |
| Contract | `docs/artefacts/API_CONTRACT.md` §12.6 — `readiness_score` 0–100 |

**P2-CORRECTIONS replaces percentage with `open_items_count`.**

---

## 5. Fixture and validator (pre-correction)

### `tests/test_gap_compliance_agent.py`

- `test_fcdo_complete_deterministic_gap_count_at_most_three`: `len(gaps) <= 3`, `readiness_score >= 95`
- `test_fcdo_complete_has_no_funder_side_gaps`: zero funder-side gap refs
- `_build_complete_fcdo_kb`: synthetic logframe actual injection + supplemental fact backfill (**anti-pattern — replaced by distillation**)

### `tests/fixtures/gap/keys/fcdo_complete_answer_key.json`

```json
"expected_missing": [],
"max_gaps": 0
```

### `scripts/audit/phase2_owner_validation.py`

Prints `readiness_score`, `missing_count`, `funder_side_leaks`; fails only on funder leaks.

---

## 6. Ground truth — walk `3347590c` (FCDO BridgeLight clean run)

**Source:** `docs/artefacts/me_module/audits/dynamic_run/walk_fcdo_full_3347590c.json`  
**Report ID:** `3347590c-5b4f-4443-8a3d-a5ae455932e2`  
**KB slice:** `snapshots.after_gap.report.knowledge_bank_json`

- Gate-1 confirmed (`gate1_confirmed_at` set), `gap_answers: {}`
- 74 facts; proposal targets for OP2.3 / OP4.2 present; **no** `indicators.OP2.3.ar1_actual` / `indicators.OP4.2.ar1_actual`
- Pre-Phase-2 E3 surfaced 46 gaps (narrative + funder + matcher noise). **P2-ADJUDICATION CI exact set (distilled 3347590c KB):** `{logframe_row:op2_3, logframe_row:op4_2}` only — see `P2_GAP_SET_ADJUDICATION.md` and `fcdo_complete_3347590c_expected_gaps.json`.

**Fixture policy:** Distil KB from this walk — do not hand-author or backfill to satisfy assertions.

---

## 7. Owner sequencing (Correction D)

**The owner executes production funder-row deletion on template `55f891ac` before the Phase 2 phase-gate validation walk** (FCDO + NLCF live runs). CI/fixture tests guard regressions; owner walk validates prod template + live gap counts.

**Rollback requires a mandatory fresh pre-deletion snapshot** of the live `55f891ac` row (not `me_capture/230290ce/template.json`). See `P2_FUNDER_ROW_DELETION_PROPOSAL.md`.
