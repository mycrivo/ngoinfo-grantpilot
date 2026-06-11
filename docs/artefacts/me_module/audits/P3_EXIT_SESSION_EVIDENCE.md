# P3 exit session evidence — Phase B exec (2026-06-11)

**Authority:** Owner exec decision 2026-06-11 (logged in [`ME_MODULE_DECISION_LOG.md`](../ME_MODULE_DECISION_LOG.md) §Phase B exec).  
**Session commit (prep only):** `f1a4c6e` — post-deletion template + B2 scripts; **no prod template mutation executed**.

---

## Stop condition — B2a guard (before any delete)

**Command:**

```text
python scripts/audit/b2_phase_exec.py --purge
```

**Exit code:** `1`

**Stdout (verbatim):**

```json
{
  "stop": "unknown_account_in_purge_scope",
  "rows": [
    {
      "report_id": "c7c86452-89a6-4039-9284-963113d9bf3a",
      "status": "DRAFT",
      "user_id": "3b9323eb-adca-4352-b9aa-36f8c52d1651",
      "created_at": "2026-06-09 05:43:03.792151+00:00",
      "email": "probe-upload2@test.org",
      "job_count": 0,
      "doc_count": 0
    },
    {
      "report_id": "922d464d-3109-465d-81e7-453e2a413048",
      "status": "DRAFT",
      "user_id": "9d8f98de-3a85-4853-8d49-a8c9106413b8",
      "created_at": "2026-06-09 05:43:51.802270+00:00",
      "email": "probe-upload3@test.org",
      "job_count": 0,
      "doc_count": 1
    }
  ]
}
```

**Scope probe (read-only, post-guard):**

| Metric | Value |
|--------|------:|
| Total `donor_reports` on template `55f891ac` | 41 |
| Rows passing guard (audit-mint `@grantpilot-test.org` or `pranabksingh@gmail.com`) | 39 |
| Rows blocked | 2 (`probe-upload2@test.org`, `probe-upload3@test.org`) |

**Effect:** Zero rows deleted; no pre-delete dump written; usage_ledger untouched; R2 purge not invoked.

**B2b / B3 / B4:** Not executed (sequential stop after B2a guard).

---

## B2b prerequisite — committed post-state file (ready, not applied)

**Source:** `tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json`  
**Builder:** `python scripts/audit/build_fcdo_post_deletion_template.py`

**Build stdout (verbatim):**

```json
{
  "artifact": "tests\\fixtures\\templates\\fcdo_55f891ac_post_deletion_v1.2.0.json",
  "section_count": 6,
  "section_keys": [
    "evidence_and_evaluation",
    "performance_and_conclusions",
    "programme_management_delivery_commercial_financial",
    "recommendations_and_actions",
    "risk_and_safeguarding",
    "summary_and_overview"
  ],
  "tag_stats": {
    "total_indicators": 25,
    "total_tables": 5,
    "tagged_indicators": 25,
    "tagged_tables": 5,
    "tagged_requirements": 30,
    "total_requirements": 30
  },
  "strict_v120_tagged": 30,
  "strict_v120_total": 30,
  "kill_list_refs_remaining": [],
  "kill_sections_remaining": [],
  "checksum_sha256": "c151a4348ab5008fccedab7013d76a1102b6b6e1b9e468d3da46756788c9db2b"
}
```

**Builder exit code:** `0`

**Rollback snapshot (ready, not executed):** `docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json` — SHA256 `aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0` (CI proof run [27355737608](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27355737608)).

---

## B3 designated account (not run)

| Field | Value |
|-------|-------|
| Account | `audit-p0_fcdo_pdf_full-1780984679@grantpilot-test.org` |
| FCDO docset | Default complete (`full_walk.py` DEFAULT_DOCSETS fcdo: proposal + award + logframe xlsx) |
| NLCF docset | Default pin docset (proposal + award + monitoring) |

`full_walk.py` supports `AUDIT_EMAIL` env for fixed mint (added @ `f1a4c6e`).

---

## Reporting debt closure (prior CI runs)

| Run ID | Workflow | headSha | status | conclusion |
|--------|----------|---------|--------|------------|
| [27348215767](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215767) | Smoke Test | `e29c89e` | completed | success |
| [27348215676](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27348215676) | P3 Offline Replay | `e29c89e` | completed | success |
| [27350651156](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651156) | Smoke Test | `300b430` | completed | success |
| [27350651106](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27350651106) | P3 Offline Replay | `300b430` | completed | success |
| [27355737608](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27355737608) | P3 Offline Replay | `e06673b` | completed | success |

**This session:** No new CI run kicked (B2a stopped before prod mutation; push of `f1a4c6e` pending owner).

---

## Offline replay committed input paths

| Entry point | Reads (repo-relative) |
|-------------|-------------------------|
| `python scripts/audit/offline_replay.py --fixture` | `tests/fixtures/synthesis/clean_faithfulness_fixture.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` |
| `python scripts/audit/offline_replay.py --nlcf-pin` | `tests/fixtures/gap/keys/nlcf_regression_pin_e7fa9bee.json`; `docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json` |

---

## R4 forbidden-ref provenance (retained)

| Ref | Owner-adjudicated in P2 table? | In literal-forbidden? | Evidence |
|-----|-------------------------------|----------------------|----------|
| `outcome_indicators` | No | Yes | Complete-docset probe emits zero gaps for this ref; literal-forbidden regression pin — see [`P3_B1_RESTAGE_PACK.md`](P3_B1_RESTAGE_PACK.md) §R4 |
| `progress_against_expected_results` | No | Yes | Same pattern; incomplete-docset key only |

---

## Not captured (blocked by B2a stop)

- Live FCDO / NLCF walks (B3)
- `phase2_owner_validation.py --fcdo-complete` stdout
- Gap-stage JSON, rendered exports, ledger `REPORT_CREATE` rows, stage traces
- Post-mutation prod template read-back

---

## Owner unblock options (facts only)

1. Remove or reassign the two `probe-upload*@test.org` reports off template `55f891ac`, then re-run `b2_phase_exec.py --purge`.
2. Owner amends guard to include an explicit allow-list for those probe accounts (requires decision log row).

**FINAL STOP** — Phase 3 closure declaration withheld pending successful B2a→B4 chain.
