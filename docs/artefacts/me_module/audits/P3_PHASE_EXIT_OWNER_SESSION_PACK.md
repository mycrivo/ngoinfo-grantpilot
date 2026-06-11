# P3 Phase exit — owner session pack

**Plan:** Phase 3 — Durable and Excellent (Plan v2)  
**Status:** Phase B **B1 complete** — STOP for `GO MUTATION` (B2/B3/B4 pending)  
**Baseline after Phase 3:** `6ff999a` (hold-clearance) + Phase B commits pending push

---

## 1. Pre-snapshot for prod template `55f891ac`

**Template ID:** `55f891ac-bb8b-4137-bc42-6de8ff935064` (FCDO Annual Review)

Before any prod JSONB replace, owner MUST export the live row:

```sql
SELECT id, funder_name, template_name, version, is_active,
       report_sections_json, format_rules_json, terminology_map_json,
       docx_template_ref, created_at, updated_at
FROM funder_report_templates
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';
```

Save to:

`docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_phase3_exit_YYYY-MM-DD.json`

Reference: [`P2_FUNDER_ROW_DELETION_PROPOSAL.md`](P2_FUNDER_ROW_DELETION_PROPOSAL.md)

---

## 2. JSONB-replace script (owner executes)

**Do not run from agent.** Owner applies cleaned template from repo artefact after review:

- Source: [`tests/fixtures/templates/fcdo_owner_tagged.json`](../../tests/fixtures/templates/fcdo_owner_tagged.json) or [`docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`](../../docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json) (verify parity before apply)

```sql
-- OWNER ONLY — after pre-snapshot saved
UPDATE funder_report_templates
SET
  report_sections_json = :report_sections_json::jsonb,
  format_rules_json = COALESCE(:format_rules_json::jsonb, format_rules_json),
  terminology_map_json = COALESCE(:terminology_map_json::jsonb, terminology_map_json),
  version = version + 1,
  updated_at = now()
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';
```

Bind parameters from verified snapshot diff vs repo tagged instance. Full kill-list: [`P2_FUNDER_ROW_DELETION_PROPOSAL.md`](P2_FUNDER_ROW_DELETION_PROPOSAL.md).

---

## 3. Validation commands (owner session)

### FCDO complete gap set

After one live FCDO export-complete walk (workflow_dispatch `p0-audit-walk.yml` or manual):

```powershell
$env:PYTHONPATH="."
python scripts/audit/phase2_owner_validation.py --report-id <UUID> --fcdo-complete
```

**Expected:** gap refs exactly `{logframe_row:op2_3, logframe_row:op4_2}`; zero funder-side leaks.

### NLCF

```powershell
python scripts/audit/phase2_owner_validation.py --report-id <NLCF_UUID>
```

Review against [`P3_1_NLCF_GOLDEN_PROPOSAL.md`](P3_1_NLCF_GOLDEN_PROPOSAL.md) after owner ratifies NLCF golden set.

### Offline CI gates (no live API)

```powershell
pytest tests/test_p3_eval_harness.py -q
python scripts/audit/offline_replay.py --fixture
```

---

## 4. Phase 3 package summary

| Package | Report | Key deliverable |
|---------|--------|-----------------|
| P3-0 | [`P3_0_BASELINE_AUDIT.md`](P3_0_BASELINE_AUDIT.md) | P2-CORRECTIONS closure `ab66dd9` |
| P3-1 | [`P3_1_PACKAGE_REPORT.md`](P3_1_PACKAGE_REPORT.md) | 7 FCDO gates + offline replay |
| P3-2 | [`P3_2_EXTRACT_HANG_DIAGNOSIS.md`](P3_2_EXTRACT_HANG_DIAGNOSIS.md) | Heartbeat/lease/requeue migration |
| P3-3 | [`P3_3_PACKAGE_REPORT.md`](P3_3_PACKAGE_REPORT.md) | DYN-10 closed; `estimated: true` markers |
| P3-4 | [`P3_4_PACKAGE_REPORT.md`](P3_4_PACKAGE_REPORT.md) | Proposal context, humaniser detect, tone |
| P3-5 | [`P3_5_PACKAGE_REPORT.md`](P3_5_PACKAGE_REPORT.md) | API contract + gap-answers doc |
| P3-6 | [`P3_6_PACKAGE_REPORT.md`](P3_6_PACKAGE_REPORT.md) | R2 delete order, ledger index, advisory lock |

---

## 5. CI run IDs (fill after push)

| Package | Run ID | Notes |
|---------|--------|-------|
| P3-0 | 27341189633 | Closure smoke @ `ab66dd9` |
| P3-1..6 | 27342062753 (smoke), 27342064122 (offline-replay) | @ `bd72572` |

---

## 6. STOP conditions respected

- No prod `55f891ac` mutation by agent  
- No live walks dispatched by agent (`p0-audit-walk.yml` remains workflow_dispatch only)  
- NLCF eval gates await owner ratification (CP-2 proposal only)

**Next:** Owner session — snapshot, JSONB replace, FCDO + NLCF validation walks, NLCF golden ratification.

---

## 7. B1 addenda (recorded pre-session — no action)

### Template pinning vs live reference

**Fact (schema):** `donor_reports` has single template FK column `funder_report_template_id` only — no JSONB snapshot of template at report creation (`information_schema` probe 2026-06-11).

**Implication for B1:** In-flight reports **live-reference** the `funder_report_templates` row. JSONB replace on `55f891ac` affects all 16 in-flight FCDO-template reports immediately on next engine read — strand risk per [`P2_FUNDER_ROW_DELETION_PROPOSAL.md`](P2_FUNDER_ROW_DELETION_PROPOSAL.md) scoping applies to each non-terminal job stage.

### DEGRADED in-flight origin (7 rows, FCDO template `55f891ac`)

| Report ID | Created (UTC) | User email | Job stage |
|-----------|---------------|------------|-----------|
| `f162ae64-2be2-4f7a-a8b5-de979b582bd0` | 2026-06-09 12:50:40 | `audit-p0_degraded_pdf-1781009439@grantpilot-test.org` | gap |
| `1f617f76-ab03-453b-9731-8c148b7d4a95` | 2026-06-09 11:57:50 | `audit-p0_degraded_pdf-1781006269@grantpilot-test.org` | gap |
| `c1e33557-eb88-4826-bf11-80f72042d0c6` | 2026-06-09 08:50:22 | `audit-p0_degraded_pdf-1780995021@grantpilot-test.org` | gap |
| `982834f6-4032-4ed6-b6a4-f5f75080536b` | 2026-06-09 08:07:21 | `audit-p0_degraded_pdf-1780992440@grantpilot-test.org` | gap |
| `9606f25a-4b34-4fb6-8261-67d220d968fb` | 2026-06-09 05:58:01 | `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` | synthesise |
| `fcd8131c-eb7a-446d-8741-2368218ebdff` | 2026-06-09 05:52:33 | `audit-p0_degraded_pdf-1780984351@grantpilot-test.org` | gap |
| `230290ce-d28a-4138-ae08-901cf1ad69c0` | 2026-06-08 13:30:07 | `pranabksingh@gmail.com` | critique |

**Fact:** 6/7 DEGRADED rows are audit test accounts (`@grantpilot-test.org`); 1/7 is real user email. All non-terminal (`awaiting_human`).

---

## 8. Phase B progress (owner GO 2026-06-11)

| Step | Status | Artefact |
|------|--------|----------|
| R1 RED cleanup | Done | distill → committed fixture; `_probe_leak.py` removed |
| NLCF regression pin | Active in CI | `nlcf_regression_pin_e7fa9bee.json`, `G-nlcf-gap-regression-pin` |
| H5 fence note | Ratified | `ME_MODULE_DECISION_LOG.md` 2026-06-11 entry |
| B1 snapshot + staging | Done | [`P3_B1_MUTATION_STAGING.md`](P3_B1_MUTATION_STAGING.md) |
| B2 mutation | **Awaiting `GO MUTATION`** | — |
| B3 live walks | Pending B2 | Test account: `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` |
| B4 evidence bundle | Pending B3 | — |
