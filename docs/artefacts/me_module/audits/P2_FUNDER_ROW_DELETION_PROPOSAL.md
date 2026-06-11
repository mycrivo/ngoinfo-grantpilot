# P2 — Funder-row deletion proposal (FCDO template)

**Status:** Proposal only — no agent or CI execution against production DB.  
**Template:** `55f891ac-bb8b-4137-bc42-6de8ff935064` (Foreign, Commonwealth & Development Office — FCDO Annual Review)

---

## Owner sequencing (mandatory)

```text
1. Capture fresh pre-deletion snapshot of live 55f891ac row
2. Owner replaces prod template JSONB with cleaned, fully-tagged repo version (single operation)
3. Owner runs Phase 2 phase-gate validation walk (FCDO + NLCF live runs)
```

CI/distilled fixtures guard code regressions; the owner walk validates prod template state and live gap counts **after** the replace.

---

## Pre-deletion snapshot (rollback source)

Before any JSONB mutation:

1. Export the full live row for `55f891ac-bb8b-4137-bc42-6de8ff935064`, including at minimum:
   - `report_sections_json`
   - `format_rules_json`
   - `terminology_map_json`
   - `version`, `funder_name`, `template_name`, `region`, `reporting_frequency`, `is_active`
2. Save as a dated artefact, e.g.  
   `docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_deletion_YYYY-MM-DD.json`
3. **Rollback restores from this snapshot only** — do **not** use `me_capture/230290ce/template.json` or other stale captures.

---

## Enumerated funder-owned refs (remove from template definition)

### Sections (default owner `funder`)

| `section_key` |
|---------------|
| `detailed_output_scoring` |
| `value_for_money` |

### Indicators (`funder_supplied` or funder owner)

| `required_item_ref` |
|---------------------|
| `output_scores` |
| `impact_weightings` |
| `risk_ratings` |
| `economy` |
| `efficiency` |
| `effectiveness` |
| `equity` |
| `commercial_improvement_where_relevant` |
| `FCDO_management_actions` |

### Tables

| `table_key` | Section | Notes |
|-------------|---------|-------|
| `output_score_table` | `detailed_output_scoring` | Funder output scoring |
| `vfm_measures` | `value_for_money` | Funder VfM measures |
| **`review_summary_sheet`** | **`summary_and_overview`** | **P2-ADJUDICATION:** funder scoring + review-team columns; `owner: funder`, `requirement_type: funder_supplied` in repo |

**Scope fence:** Remove funder-owned **template definition** rows only. Do not touch NGO report rows (`donor_reports`), stored `content_json`, or export blobs.

**Retained with narrative typing (not on kill list):** `outcome_assessment` — NGO prose synthesized from objectives + indicator actuals (`requirement_type: narrative`).

---

## Render-path pre-check (COMPLETE reports)

| Path | Template-dependent? |
|------|---------------------|
| In-app view (`content_json` prose) | No |
| Download export (stored DOCX blob) | No |
| Stage H re-export (merge current template + `content_json`) | Yes — structure/headings follow **current** template |

Existing COMPLETE reports keep stored prose and DOCX. Replace affects **future re-exports** and **new runs** using the updated template row.

---

## Per-location operations

### Production DB (owner-executed) — full JSONB replace

Target: `funder_report_templates.id = '55f891ac-bb8b-4137-bc42-6de8ff935064'`.

**Why replace, not row-deletion alone:** Prod row predates schema v1.2.0 tags (`owner`, `indicator_requirements`, `table_requirements`, `table_requirements` for `review_summary_sheet` / `outcome_assessment`). The typed matcher reads these tags; patching tags and removing funder rows must happen together.

**Single operation (owner validates in staging first):**

1. Capture mandatory fresh pre-deletion snapshot (above).
2. Build **cleaned payload** from repo [`TEMPLATE_INSTANCE_FCDO.json`](../TEMPLATE_INSTANCE_FCDO.json):
   - All v1.2.0 typing applied (including adjudication `table_requirements`).
   - Funder-owned sections/indicators/tables **removed** from `report_sections_json` per kill list (including `review_summary_sheet` table definition from section A if removing funder table row entirely, or retain section with table removed — owner choice aligned to cleaned repo shape).
3. One `UPDATE`:

```sql
UPDATE funder_report_templates
SET
  report_sections_json = :cleaned_sections,
  format_rules_json = :format_rules,
  terminology_map_json = :terminology,
  version = version + 1,
  updated_at = now()
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';
```

**Do not** run Alembic or seed reload against prod for this change.

### Repo artefact

[`TEMPLATE_INSTANCE_FCDO.json`](../TEMPLATE_INSTANCE_FCDO.json) — source of truth for cleaned + tagged payload until owner confirms post-replace prod shape.

### Test overlays

[`tests/test_orchestrator_gate1.py`](../../../tests/test_orchestrator_gate1.py) `_apply_fcdo_template_to_report` — inherits repo JSON; no separate prod touch.

---

## Defense-in-depth (retain after replace)

Keep in codebase even after funder rows are removed from prod template:

- Schema fields: `owner`, `requirement_type`, `indicator_requirements`, `table_requirements`
- Runtime filter: `is_ngo_checklist_item()` / `requirement_metadata.py` — excludes funder-owned items from NGO Gate 2 checklist

---

## Draft decision-log entry (AMBER)

**Title:** Replace prod FCDO template `55f891ac` with cleaned tagged JSONB  
**Risk:** AMBER — live template replace; mitigated by mandatory pre-deletion snapshot and render-path audit (stored artefacts unaffected).  
**Rollback:** Restore full row from dated pre-deletion snapshot file.  
**Validation:** Owner phase-gate walk (FCDO + NLCF) after replace; `phase2_owner_validation.py --fcdo-complete` expects `{logframe_row:op2_3, logframe_row:op4_2}` on BridgeLight-equivalent run.

---

## Cross-references

- [`P2_GAP_SET_ADJUDICATION.md`](P2_GAP_SET_ADJUDICATION.md) — gap-set verdicts + failure provenance
- [`P2_CORRECTIONS_FINDINGS.md`](P2_CORRECTIONS_FINDINGS.md) §7 — owner sequencing
- [`ME_DB_LIVE_VERIFICATION_2026-06-04.md`](../../../ME_DB_LIVE_VERIFICATION_2026-06-04.md) — prod FCDO row verification
