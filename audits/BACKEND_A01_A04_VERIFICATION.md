# Backend A-01 → A-04 Verification Audit

**Auditor role:** Senior backend QA (read-only)  
**Date:** 2026-06-06  
**Repo commit audited:** `74b0a91` on `main` (post-deploy push)  
**Scope:** A-01 entitlements, A-02 enforcement, A-03 read APIs, A-04 DOCX hardening only  

---

## 0. Files Read / Tests Run / Method

### Changelogs & samples read
- `audits/A_01_ENTITLEMENTS_CHANGELOG.md`
- `audits/A_02_ENFORCEMENT_CHANGELOG.md`
- `audits/A_03_READ_APIS_CHANGELOG.md`
- `audits/A_04_DOCX_CHANGELOG.md`
- `audits/A_04_SAMPLE_proposal.docx`, `audits/A_04_SAMPLE_me_report.docx` (parsed with python-docx)

### Contracts read
- `docs/artefacts/API_CONTRACT.md` — §4, §10.2, §10.3, §12.0, §12.1, §12.9, §12.10
- `docs/artefacts/ENUM_REGISTRY.md` — §3.3, §5.10
- `docs/artefacts/PRICING_AND_ENTITLEMENTS.md`

### Implementation inspected (representative)
| Area | Files |
|------|-------|
| A-01 | `app/services/quota_service.py`, `app/schemas/entitlements.py`, `app/models/usage_ledger.py`, `app/api/routes/entitlements.py`, `tests/test_quota_service.py` |
| A-02 | `app/reports/api/dependencies/plan_gate.py`, `app/reports/router.py`, `app/reports/services/donor_report_lifecycle_service.py`, `tests/test_me_enforcement.py` |
| A-03 | `app/reports/api/routes/read.py`, `app/reports/services/report_read_service.py`, `app/reports/services/report_access.py`, `app/reports/schemas/report_read.py`, gate route files, `tests/test_report_read_routes.py` |
| A-04 | `app/core/docx_presentation.py`, `app/services/proposal_docx_renderer.py`, `app/reports/export/docx_renderer.py`, `app/reports/services/report_export_service.py`, `tests/test_docx_structural_hardening.py` |
| Cross-cut | `app/main.py` (exception handler), `requirements.txt`, `alembic/versions/*`, `git diff af80363..74b0a91` |

### Method
- Line-numbered source reads and `rg` pattern searches
- Sample DOCX parsed programmatically (python-docx; footer PAGE/NUMPAGES verified in OOXML)
- **No source, contract, test, or config edits**
- Test execution only (read-only)

### Tests run (unmodified suite)
```text
# Full backend
pytest tests/ -q
→ 285 passed, 5 failed, 0 skipped, 1 warning (38.36s)

# A-01–A-04 target union
pytest tests/test_quota_service.py tests/test_me_enforcement.py \
  tests/test_report_read_routes.py tests/test_docx_structural_hardening.py \
  tests/test_docx_renderer.py tests/test_report_export_service.py \
  tests/test_report_lifecycle_routes.py tests/test_gate1_confirmation.py \
  tests/test_gate2_gap_answers.py -q
→ 70 passed (12.17s)
```

Full-run output saved incidentally to `audits/_pytest_full_run.txt` during audit execution.

---

## 1. Executive Verdict

### **READY-WITH-MINOR-FIXES** for frontend (B-series)

**Basis:** A-01–A-04 acceptance logic is implemented and **70/70 package-target tests pass**. Entitlements shape, 403/429 error contracts, read endpoints, path alignment, owner-scoping, and DOCX structural hardening match the locked contracts in code. **The full backend suite is not green** (5 pre-existing failures unrelated to A packages). Several founder-flagged semantics (report_exports display, current_gate heuristic, inline assumption prose, Calibri vs DM Sans) are documented and acceptable for B-series binding with UI caveats.

| Category | Items |
|----------|-------|
| **Genuine blockers** | None in A-01–A-04 contract surface |
| **Non-blocking but should track** | Full-suite red (5 tests); stale prod walk scripts; `report_exports` display vs enforcement; changelogs stale (“not committed”) vs deployed `74b0a91` |
| **Cosmetic / Plan 2+** | Print font choice; inline assumption narrative; M&E markdown tables in export; no logo in title block |

---

## 2. Per-Package Findings

### A-01 — Entitlements / accounting

| Check | Expected | Actual (file:line) | Result | Sev |
|-------|----------|-------------------|--------|-----|
| Impact `fit_scans` = 10 | 10, not 20 | `PLAN_QUOTAS[IMPACT].fit_scans=10` — `app/services/quota_service.py:65` | PASS | — |
| Growth `fit_scans` = 10 | 10 | `quota_service.py:58` | PASS | — |
| Free `fit_scans` = 1 | 1 | `quota_service.py:51` | PASS | — |
| Proposals unchanged | Free 1 / Growth 3 / Impact 5 | `quota_service.py:52,59,66` | PASS | — |
| `reports` allowance | Impact 2 BILLING_CYCLE; Growth/Free 0 | `quota_service.py:53,60,67` | PASS | — |
| `REPORT_CREATE` / `REPORT_EXPORT` in ledger enum | Both present, TEXT column | `app/models/usage_ledger.py:18-19,35-40` | PASS | — |
| Invalid action_type rejected | App validation error | `quota_service.py:335-342`; `tests/test_quota_service.py` | PASS | — |
| GET `/api/me/entitlements` shape | `reports` + `report_exports` blocks | `app/schemas/entitlements.py:16-21`; `entitlements.py:12-17` | PASS | — |
| `reports.used` from `REPORT_CREATE` rows | Current billing window | `quota_service.py:248-250,273-277` | PASS | — |
| `remaining` floored at 0 | `max(limit-used,0)` | `quota_service.py:129` | PASS | — |
| Billing-cycle reset | Window-based, no counter table | A-01 changelog mechanism; `_usage_count` `quota_service.py:108-123` | PASS | — |
| No other quota numbers changed | Only Impact fit_scans 20→10 | Grep: no `fit_scans=20` in codebase; proposals/regen unchanged | PASS | — |
| No Alembic migration for action types | TEXT + app validation | Latest M&E migration `0015`; no new revision in A commit range | PASS | — |
| `report_exports.limit` semantics | Contract §4 block present | `limit=quota.reports` (2 on Impact); `REPORT_EXPORT` idempotency-only — `quota_service.py:32-36,279-283` | PASS (flagged) | LOW |

### A-02 — Enforcement / gating

| Check | Expected | Actual (file:line) | Result | Sev |
|-------|----------|-------------------|--------|-----|
| Single Impact gate on M&E router | One dependency on gated sub-router | `app/reports/router.py:15-22` | PASS | — |
| Health ungated | Outside `gated_router` | `router.py:13` | PASS | — |
| FREE/GROWTH → 403 exact body | §10.3 shape | `plan_gate.py:27-35`; tested `tests/test_me_enforcement.py:126-134` | PASS | — |
| IMPACT passes gate | 200 on create/upload | `test_me_enforcement.py:185-207` | PASS | — |
| Quota exhausted → 429 exact body | §10.2 reports snapshot, no upgrade field | `_raise_report_quota_exceeded` `quota_service.py:190-203`; handler maps to 429 `main.py:95-96`; `test_me_enforcement.py:227-248` | PASS | — |
| Atomic create + `REPORT_CREATE` | Single transaction | `donor_report_lifecycle_service.py:114-143` | PASS | — |
| Decrement on CREATE only | Not upload/generate/export | Upload gated only; export test `test_me_enforcement.py:364-387` | PASS | — |
| No double-spend at remaining=1 | 429 on 2nd create; 1 report row | `test_me_enforcement.py:252-288` | PASS | — |
| Rollback on late exhaustion | No orphan report/ledger | `test_me_enforcement.py:291-328,331-361` | PASS | — |
| No reservation/refund system | Decrement-at-create only | No refund code in lifecycle/quota | PASS | — |
| Row lock on REPORT_CREATE | FOR UPDATE | `_lock_user_plan_row` `quota_service.py:206-209`; used in `record_usage` `357-358` | PASS | — |
| No route path changes | A-02 scope | No new paths in A-02 files | PASS | — |

### A-03 — Read APIs / paths / ownership

| Check | Expected | Actual (file:line) | Result | Sev |
|-------|----------|-------------------|--------|-----|
| GET `/api/reports` list | Owner-scoped, `?limit` default 10 max 50 | `read.py:31-43` | PASS | — |
| Empty list → 200 `[]` | `{reports:[]}` | `test_report_read_routes.py` (passing) | PASS | — |
| GET `/api/reports/{id}` detail | Top-level detail shape | `read.py:46-55`; `report_read.py:28-45` | PASS | — |
| GET `/api/report-templates` | Catalogue + optional region | `read.py:58-77` | PASS | — |
| List = summary only (no JSONB) | §12.10 fields | `report_read_service.py:62-74` | PASS | — |
| Gate paths canonical | `/api/reports/{id}/…` | `gate1.py:22-23`, `gate2.py:24`, `gate3.py:19-20` | PASS | — |
| Old `donor-reports` gone | 404 on old paths | `test_report_read_routes.py:264+` (passing) | PASS | — |
| Read routes inherit A-02 gate | On `gated_router` | `router.py:16-17` | PASS | — |
| Owner 404 uniform | Missing + foreign → 404 | `report_access.py:19-25` | PASS | — |
| No provisional PATCH/GET gate-edit | Not built | No `@router.patch` under `app/reports/` | PASS | — |
| No sync POST `…/generate` | Not built | No `/generate` route in `app/reports/api/routes/` | PASS | — |
| Gate handler logic unchanged | Paths + ownership only | Gate services delegate to `get_owned_donor_report`; confirm logic retained | PASS | — |
| `current_gate` derivation | From KB/gap stamps | `report_gate_state.py:8-22` | PASS (heuristic flagged) | LOW |
| Prod walk scripts updated | Canonical paths | **Still use `donor-reports`** — e.g. `scripts/fcdo_d4_f1_fresh_prod_walk.py:424` | FAIL | MEDIUM |

### A-04 — DOCX hardening

| Check | Expected | Actual (file:line) | Result | Sev |
|-------|----------|-------------------|--------|-----|
| No `[Section not generated]` / `[Not generated` | Absent in samples | Parsed samples + `docx_renderer.py:222-226` | PASS | — |
| No internal ID/version/UTC on cover | Stripped | `proposal_docx_renderer.py:29-34`; M&E `docx_renderer.py:176-185` | PASS | — |
| Branded title block | NGO + doc title + human date | `app/core/docx_presentation.py:86-118`; samples contain org name + titles | PASS | — |
| Word Heading styles | No literal `#` in headings | Samples: all headings `Heading 1/2`; `strip_markdown_heading_prefix` `docx_presentation.py:44-46` | PASS | — |
| Footer + page fields | Footer present; PAGE/NUMPAGES in OOXML | `docx_presentation.py:149-201`; samples `page_fields: True` | PASS | — |
| Assumptions appendix (structured) | Single `"Assumptions & Caveats"` | `add_assumptions_appendix` `docx_presentation.py:204-212`; both samples | PASS | — |
| Inline assumption prose | Flagged, not extracted | Pre-existing body text unchanged; A-04 changelog flag honoured | PASS (flagged) | LOW |
| python-docx only; no docxtpl | No new dep | `requirements.txt:11`; repo grep: no docxtpl | PASS | — |
| Shared helper in CORE | No M&E in core | `app/core/docx_presentation.py`; core grep: no `app.reports` imports | PASS | — |
| Export route unchanged | Same path, content-type, filename | `export.py:21-44`; `DOCX_CONTENT_TYPE` unchanged | PASS | — |
| Content preserved verbatim | Known snippets in output | Proposal: *"BridgeLight will re-enrol…"*; M&E: *"The programme made steady progress…"* in samples | PASS | — |
| No new tables added (A-04) | Scope fence | M&E `_add_word_table` pre-existing `docx_renderer.py:94-96`; not added in A-04 | PASS (pre-existing tables remain) | LOW |

---

## 3. Anti-Bent-Ruler & Scope-Fence Findings

### Anti-bent-ruler
| Finding | Evidence | Severity |
|---------|----------|----------|
| No `xfail` / `skip` markers in A test files | `rg` across `tests/**`: no matches | Clean |
| No loosened quota assertions (e.g. `allowed=` → weak checks) | `test_quota_service.py:77-87` uses canonical `limit=` shape | Legitimate target change |
| Impact fit_scans 20→10 asserted explicitly | `test_plan_quotas_impact_fit_scans_ten` `test_quota_service.py:113-117` | Legitimate target change |
| Non-owner 403 → 404 | `test_report_lifecycle_routes.py`, `test_report_read_routes.py` | Legitimate A-03 contract alignment |
| No “delete content to pass artifact tests” pattern | A-04 tests assert known body snippets **present** `test_docx_structural_hardening.py` | Clean |

### Scope fences (A-01–A-04 code changes)
| Fence | Status | Evidence |
|-------|--------|----------|
| M&E pipeline / agents / orchestrator | **Honoured** | `git diff af80363..74b0a91 -- app/reports/agents app/reports/orchestration app/reports/worker` → empty |
| Core proposal prompts / proposal_service logic | **Honoured** | No diff in `app/ai/prompts/proposal.py`; `export_service.py` delegates render only |
| Frontend repo | **Not touched** | Backend repo only |
| Alembic new migration in A packages | **Honoured** | No migration added in A commit range |
| docxtpl / funder templates | **Honoured** | Not installed; no template engine |

### Out-of-scope repo noise (not A package logic, but present in `74b0a91`)
The deploy commit bundled **158 files** including diagnostic logs, `M_E_Module/` duplicates, throwaway scripts, and editor hooks — beyond A-01–A-04 backend deliverables. This does not break B-series binding but increases repo noise and review surface (**MEDIUM hygiene**, not a contract defect).

---

## 4. Contract Conformance (code vs §4 / §10 / §12 / ENUM / PRICING)

| Topic | Contract | Code | Alignment |
|-------|----------|------|-----------|
| Plan quotas | PRICING: Impact 10 fit_scans, 2 reports/mo | `PLAN_QUOTAS` | ✅ |
| Entitlements §4 blocks | `reports`, `report_exports` | `EntitlementsPayload` + `get_entitlements()` | ✅ |
| §10.3 UPGRADE_REQUIRED | Exact JSON | `plan_gate.py:27-35` | ✅ |
| §10.2 QUOTA_EXCEEDED (reports) | 429 + entitlement snapshot | `quota_service.py:190-203` + `main.py:95-96` | ✅ |
| §12 list/detail/templates | Shapes + paths | `read.py`, `report_read.py`, `report_read_service.py` | ✅ |
| §12 gate paths | `/api/reports/{id}/knowledge-bank/gateN/…` | gate route modules | ✅ |
| ENUM §3.3 action types | Six TEXT values | `usage_ledger.py:14-19` | ✅ |
| ENUM §5.10 mapping | REPORT_CREATE → reports; REPORT_EXPORT idempotent | Enforced vs idempotency split in `quota_service.py:23-36` | ✅ |
| `report_exports.used` | §4 shows block; §5.10 idempotent audit | **No `REPORT_EXPORT` ledger writes on M&E export route** — `used` stays 0 in practice | ⚠️ Display-only; flagged A-01/A-02 |
| §12.10 list errors | Doc lists 401·500 | IMPACT gate returns 403 for Free/Growth — consistent with §12.0 + §10.3 | ✅ (§12.10 error list understates 403) |

**Silent divergence:** None material for B-series API binding. The `report_exports` block is the main semantic ambiguity (already flagged in A-01 changelog).

---

## 5. Test Run Result

| Metric | Value |
|--------|-------|
| **Full suite** | 285 passed, **5 failed**, 0 skipped, 1 warning |
| **A-01–A-04 target union** | **70 passed**, 0 failed |
| **Green without modification by auditor** | **No** (full suite) / **Yes** (A-package target union) |

### Failing tests (full suite — not modified)

| Test | Failure | Relation to A-01–A-04 |
|------|---------|-------------------------|
| `tests/test_auth_account_linking.py::test_google_then_magic_link_links_same_user` | `AttributeError: 'tuple' object has no attribute 'id'` | Pre-existing auth regression |
| `tests/test_auth_account_linking.py::test_magic_link_then_google_links_same_user` | Same | Pre-existing auth regression |
| `tests/test_gate1_confirmation.py::test_gate1_confirm_endpoint_404_when_module_disabled` | `SimpleNamespace` missing `AUTH_ACCESS_TOKEN_TTL_MIN` | Test/settings fixture fragility |
| `tests/test_me_module_worker.py::test_outcome_1_concurrent_claim_only_one_wins` | SQLite concurrent claim assertion | Pre-existing worker/SQLite limitation |
| `tests/test_me_module_worker.py::test_worker_startup_path_registers_mappers_before_claim` | Subprocess expects mapper error; gets missing table | Pre-existing worker test drift |

**Note:** A-02/A-03 changelogs correctly recorded these as pre-existing. They were **not** introduced by A packages.

---

## 6. Changelog Claim vs Reality

| Claim (changelog) | Reality at `74b0a91` | Verdict |
|-------------------|----------------------|---------|
| A-01: Impact fit_scans 10, reports 2, no migration | Matches `quota_service.py` | ✅ Supported |
| A-01: Full suite “pre-existing failures only” | Still 5 failures; none in A target tests | ✅ Supported |
| A-02: 37-pass target suite | 70-pass union includes all A-02 tests | ✅ Supported |
| A-02: No route path changes | True at A-02 time; A-03 later added reads | ✅ Supported in sequence |
| A-03: Gate paths aligned; old paths 404 | Code + tests confirm | ✅ Supported |
| A-03: Prod walk scripts **not** updated | Still stale (`scripts/*prod_walk*.py`) | ✅ Claim accurate — **debt remains** |
| A-04: 19-pass export/DOCX tests | Included in 70-pass union | ✅ Supported |
| A-04: Assumptions structured → appendix | Implemented; inline prose flagged | ✅ Supported |
| A-04: Page numbers via clean PAGE fields | OOXML fields present in samples | ✅ Supported |
| All four: “Not committed. Not deployed.” | **Contradicted** — `74b0a91` pushed to `origin/main` | ⚠️ Changelog status stale (process, not code) |
| A-01: “Full suite green” in acceptance table | Marked ⚠️ pre-existing; full suite still red | ✅ Honest in changelog; still true |

---

## 7. Defect List for Founder Decision

Ordered by severity. **No fixes applied in this audit.**

| # | Severity | What | Where | Why it matters | Suggested owner |
|---|----------|------|-------|----------------|-----------------|
| 1 | **MEDIUM** | Full backend suite not green (5 failures) | See §5 | CI/deploy confidence; unrelated to M&E but blocks “all green” claim | Pre-A hygiene package (auth + worker tests) |
| 2 | **MEDIUM** | Prod/dev walk scripts still call `/api/reports/donor-reports/…` | `scripts/fcdo_d4_f1_fresh_prod_walk.py:424+` (13+ files) | Next manual prod walk will 404 on gates | Script maintenance (ops; not B-series) |
| 3 | **LOW** | `report_exports` entitlements block shows `limit=2` but export never writes `REPORT_EXPORT` ledger rows | `quota_service.py:279-283`; no writes in `report_export_service.py` | Frontend may misread “2 exports/month” vs audit-only idempotency | Founder decision / A-01 follow-up or B-series UI copy |
| 4 | **LOW** | `current_gate` derived from KB stamps, not live `report_jobs.awaiting_human` | `report_gate_state.py:8-22` | Dashboard gate badge may lag actual pipeline halt | B-series UI (document) or future read-API enhancement |
| 5 | **LOW** | Inline assumption **prose** remains in section bodies | M&E sample fixture content; A-04 flag | Transparency OK; not consolidated | Plan 2 if relocation required |
| 6 | **LOW** | Deploy commit `74b0a91` includes large non-backend artefacts (logs, duplicate docs, hooks) | Git history | Review noise; not runtime defect | Repo hygiene / `.gitignore` curation |
| 7 | **LOW** | Changelog headers still say “not committed” | All four A changelogs | Process/documentation drift | Update changelog status lines |

**Not defects (explicit boundaries):** AI/content quality (Plan 2); adversarial security (Plan 3); pre-existing M&E markdown table rendering in export.

---

## 8. Frontend-Readiness Statement

### Can Track B bind against this backend?

**Yes — with caveats.**

| Surface | Stable & correct for B-series? | Caveats |
|---------|-------------------------------|---------|
| `GET /api/me/entitlements` (`reports`, `report_exports`) | **Yes** | Treat `report_exports` as informational until write path exists; gate CTAs on `reports.remaining` |
| `403 UPGRADE_REQUIRED` on M&E | **Yes** | Exact body verified; all gated routes including new reads |
| `429 QUOTA_EXCEEDED` on report create | **Yes** | Exact §10.2 snapshot; decrement-at-create semantics |
| `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/report-templates` | **Yes** | Shapes match §12; owner 404 uniform |
| Gate confirm paths | **Yes** | Use `/api/reports/{id}/knowledge-bank/gateN/…` — **not** `donor-reports` |
| Job polling / lifecycle POSTs | **Yes** | Unchanged paths under `/api/reports/{id}/…` |
| Export download | **Yes** | Unchanged; DOCX now client-clean (A-04) |
| `current_gate` on list/detail | **Usable** | Heuristic — may not match live job stage exactly |

**Recommendation:** Proceed with B-series against `main` @ `74b0a91`. Triage the 5 full-suite failures in parallel (not blocking M&E UI scaffolding). Document `report_exports` and `current_gate` semantics in frontend types/copy.

---

*End of audit. Single deliverable file only; no code changes made.*
