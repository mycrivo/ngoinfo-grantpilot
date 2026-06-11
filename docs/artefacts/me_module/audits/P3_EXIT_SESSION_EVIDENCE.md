# P3 exit session evidence — Phase B full chain (2026-06-11)

**Authority:** Owner exec + guard resolution logged in [`ME_MODULE_DECISION_LOG.md`](../ME_MODULE_DECISION_LOG.md).  
**Final HEAD (pre-push):** see §Push / CI below.

---

## B2a · Purge

**Command:** `python scripts/audit/b2_phase_exec.py --purge`  
**Exit code:** `0`

**Stdout (verbatim):**

```json
{
  "purge_dump": "docs\\artefacts\\me_module\\audits\\snapshots\\b2a_purge_dump_20260611T155247Z.json",
  "scope_count": 41,
  "deleted_counts": {
    "uploaded_documents": 110,
    "report_jobs": 36,
    "donor_reports": 41
  },
  "r2_delete_failures": [],
  "remaining_reports_on_template": 0,
  "remaining_jobs_on_template": 0
}
```

Guard: 41/41 pass (includes `probe-upload2@test.org`, `probe-upload3@test.org` per amended decision).  
usage_ledger: untouched in B2a.

---

## B2a-2 · Probe account deletion

**Command:** `python scripts/audit/b2_phase_exec.py --delete-probes`  
**Exit code:** `0`

**Stdout (verbatim):**

```json
{
  "probe_dump": "docs\\artefacts\\me_module\\audits\\snapshots\\b2a2_probe_account_dump_20260611T155321Z.json",
  "deleted_counts": {
    "users": 2
  },
  "r2_delete_failures": [],
  "remaining_probe_users": []
}
```

Scoped emails: `probe-upload2@test.org`, `probe-upload3@test.org` only.

---

## B2b · Template replace

**Source:** `tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json` (SHA256 `c151a4348ab5008fccedab7013d76a1102b6b6e1b9e468d3da46756788c9db2b`)

**Command:** `python scripts/audit/b2_phase_exec.py --replace`  
**Exit code:** `0`

**Stdout (verbatim):**

```json
{
  "replace_source": "tests\\fixtures\\templates\\fcdo_55f891ac_post_deletion_v1.2.0.json",
  "affected_rows": 1,
  "read_back": {
    "section_count": 6,
    "strict_v120_tagged": 30,
    "strict_v120_total": 30,
    "kill_list_refs_remaining": [],
    "kill_sections_remaining": []
  },
  "version_before": 1,
  "version_after": 2,
  "rollback_snapshot_sha256": "aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0"
}
```

Rollback script armed; not executed.

---

## B3 · Live walks

**Account:** `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` (`AUDIT_EMAIL`, `PLAN=IMPACT`)

| Run | Template | Report ID | Walk exit | Verdict | Export (committed copy) |
|-----|----------|-----------|-----------|---------|-------------------------|
| `p3_b3_fcdo` | FCDO complete docset (default 3 files) | `7cdcc3a8-e15e-449b-991c-b79d99c918ec` | 0 | `completed` | [`snapshots/p3_b3_export_fcdo_7cdcc3a8.docx`](snapshots/p3_b3_export_fcdo_7cdcc3a8.docx) |
| `p3_b3_nlcf` | NLCF pin docset (proposal + award + monitoring) | `df7450dc-5d63-4461-98fc-9f09dea44a70` | 0 | `completed` | [`snapshots/p3_b3_export_nlcf_df7450dc.docx`](snapshots/p3_b3_export_nlcf_df7450dc.docx) |

Full walk logs (gitignored): `dynamic_run/p3_b3_fcdo_walk.log`, `dynamic_run/p3_b3_nlcf_walk.log`.

### FCDO — `phase2_owner_validation.py --fcdo-complete`

**Command:** `--report-id 7cdcc3a8-e15e-449b-991c-b79d99c918ec --fcdo-complete`  
**Exit code:** `2`

**Stderr (verbatim):**

```text
FAIL: FCDO complete gap set mismatch expected=['logframe_row:op2_3', 'logframe_row:op4_2'] actual=[]
FAIL: open_items_count 0 != expected 2
```

**Stdout (verbatim):**

```json
{
  "open_items_count": 0,
  "readiness_basis": "ngo_data",
  "readiness_message": "All required data items are on file.",
  "missing_count": 0,
  "required_item_refs": [],
  "funder_side_leaks": [],
  "missing_items": []
}
```

**Gap-stage snapshot (at Gate 2 boundary):** [`snapshots/p3_b3_gap_stage_7cdcc3a8.json`](snapshots/p3_b3_gap_stage_7cdcc3a8.json) — `open_items_count: 2`, refs `{logframe_row:op2_3, logframe_row:op4_2}`. Walk log: `GATE2 gaps=2 answered=0 skipped=2`.

### NLCF — regression pin evidence

**`offline_replay.py --nlcf-pin` exit code:** `0` — pin status `matches_observed_e7fa9bee`, 18-ref set exact.

**Walk artifact replay:** `offline_replay.py walk_p3_b3_nlcf_df7450dc.json` exit code `0`, `"passed": true`.

**`phase2_owner_validation.py` (post-complete gap-check) exit code:** `0`

```json
{
  "open_items_count": 0,
  "readiness_basis": "ngo_data",
  "readiness_message": "All required data items are on file.",
  "missing_count": 0,
  "required_item_refs": [],
  "funder_side_leaks": []
}
```

**Gap-stage snapshot:** [`snapshots/p3_b3_gap_stage_df7450dc.json`](snapshots/p3_b3_gap_stage_df7450dc.json) — 18 gaps at Gate 2 boundary (pin-class ref set).

---

## Stage traces · ledger

[`snapshots/p3_b3_ledger_traces.json`](snapshots/p3_b3_ledger_traces.json)

| Report | `requeue_count` | `degraded_pass_through_sum` | `REPORT_CREATE` idempotency key |
|--------|----------------:|------------------------------:|----------------------------------|
| FCDO `7cdcc3a8…` | 0 | 0 | `report:create:7cdcc3a8-e15e-449b-991c-b79d99c918ec` |
| NLCF `df7450dc…` | 0 | 0 | `report:create:df7450dc-5d63-4461-98fc-9f09dea44a70` |

Both reports `status: COMPLETE`. One `REPORT_CREATE` ledger row per report at first export complete.

FCDO agent trace gap stage: `open_items_count: 2`, `degraded: false`. Template version at export: `2`.

---

## Reporting debt closure (prior + this package)

| Run ID | Workflow | headSha | conclusion |
|--------|----------|---------|------------|
| [27348215767](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215767) | Smoke Test | `e29c89e` | success |
| [27348215676](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215676) | P3 Offline Replay | `e29c89e` | success |
| [27350651156](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651156) | Smoke Test | `300b430` | success |
| [27350651106](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651106) | P3 Offline Replay | `300b430` | success |
| [27355737608](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27355737608) | P3 Offline Replay | `e06673b` | success |

**This package CI runs:** inserted after push (see §Push / CI).

### Offline replay committed input paths

| Entry point | Reads |
|-------------|-------|
| `python scripts/audit/offline_replay.py --fixture` | `tests/fixtures/synthesis/clean_faithfulness_fixture.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` |
| `python scripts/audit/offline_replay.py --nlcf-pin` | `tests/fixtures/gap/keys/nlcf_regression_pin_e7fa9bee.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` |

### R4 forbidden-ref provenance

| Ref | Owner-adjudicated in P2? | Evidence |
|-----|--------------------------|----------|
| `outcome_indicators` | No | Literal-forbidden regression pin; absent from FCDO complete-docset probe expected set |
| `progress_against_expected_results` | No | Same; incomplete-docset key only |

---

## Push / CI

Commits in this package: `f1a4c6e`, `0868920`, `9ec90de`, plus B2/B3/B4 completion commits on push.

**FINAL STOP** — Owner reads [`p3_b3_export_fcdo_7cdcc3a8.docx`](snapshots/p3_b3_export_fcdo_7cdcc3a8.docx) and [`p3_b3_export_nlcf_df7450dc.docx`](snapshots/p3_b3_export_nlcf_df7450dc.docx) against knowledge bank and declares Phase 3 closed.
