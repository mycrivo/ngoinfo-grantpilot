# P3 Phase exit — owner session pack

**Plan:** Phase 3 — Durable and Excellent (Plan v2)  
**Status:** STOP — owner session required before prod mutations or live validation walks  
**Baseline after Phase 3:** (record commit SHA + CI run ID after push)

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
| P3-1..6 | _pending_ | smoke-test + p3-offline-replay on push |

---

## 6. STOP conditions respected

- No prod `55f891ac` mutation by agent  
- No live walks dispatched by agent (`p0-audit-walk.yml` remains workflow_dispatch only)  
- NLCF eval gates await owner ratification (CP-2 proposal only)

**Next:** Owner session — snapshot, JSONB replace, FCDO + NLCF validation walks, NLCF golden ratification.
