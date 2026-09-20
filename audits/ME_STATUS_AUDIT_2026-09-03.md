# M&E status audit — origin/main HEAD

Read-only audit at `origin/main`. Evidence pointers only. Verdicts: CONFIRMED / REFUTED / PARTIAL / CANNOT DETERMINE.

Scope: M&E (`app/reports/`) and Proposal Writer. Frontend lives in a separate repository (`mycrivo/grantpilot-frontend`); this backend repo is cited for API contracts only.

---

## SECTION 0 — Repo, CI, deployed reality

### 0.1 Main HEAD SHA and date. Every PR merged after PR #15

**Verdict:** CONFIRMED

**Pointer:** `git log -1 origin/main` → `f44426a2cb8cb3cdf4b6de91d37fccc8297b4b3e` (`2026-08-16 20:13:49 +0100`); `gh pr list --state merged --base main` (newest merged PR is `#15`).

**Evidence:** HEAD subject is `feat(p0): bundle export + scorecard emitter (D-083–D-085)`, the squash-merge of PR #15 (`mergedAt` `2026-08-16T19:13:49Z`). No later merged PR exists. Files in #15 under M&E: `app/reports/eval/bundle_export.py`, `app/reports/eval/scorecard.py`, plus harness scripts/tests/docs/CI. No proposal-module files (`app/services/proposal_service.py`, `app/ai/`, `app/api/routes/proposals.py`) appear in the #15 file list.

PRs merged *before* #15 (not after; listed only to pin the merge order): #14 (2026-08-08, golden pack + five-layer library), #13 (2026-07-27, D-078), #12 (2026-07-27, G1 hooks), #11 (2026-07-26, H0), #10 (2026-07-20, Gate 1 conflict integrity), #9 (2026-07-19, proposal timeout-degrade), #8 (2026-07-18, auth hygiene), #7 (2026-07-18, Gate 2 narrative elevation).

### 0.2 Branches with commits not on main touching M&E or proposal code

**Verdict:** PARTIAL

**Pointer:** `git branch -r --no-merged origin/main` plus `git log origin/main..<branch> -- app/reports app/ai app/services/proposal_service.py app/schemas/proposal.py app/api/routes/proposals.py` and two-dot `git diff origin/main <branch>` on the same paths.

**Evidence:** Three remote branches have unique commits (not on `main`, because those PRs were squash-merged) that touch M&E paths. None of them is *ahead* of `main` in file content:

| Branch | Last commit | Unique commits vs main | Two-dot vs `origin/main` on M&E/proposal paths |
|---|---|---|---|
| `origin/engine/p0-bundle-export` | 2026-08-16 20:10:18 +0100 — `fix(p0): D-084 cancel export corpus; land bundle integrity fixes` | 3 commits; paths `app/reports/eval/bundle_export.py`, `scorecard.py` | empty (content already on main via #15 squash) |
| `origin/engine/p0-harness` | 2026-08-08 09:05:30 +0100 — `test(p0): D-082 revert planted assertion-library CI failure` | 8 commits; `app/reports/eval/**` golden/assertion library | behind: 2 files / 665 deletions (`bundle_export.py` + `scorecard.py` exist on main, not on this branch) |
| `origin/feat/gate1-conflict-integrity` | 2026-07-19 17:20:15 +0100 — `docs(me): quote fix round 2 CI PASSED lines` | 7 commits; Gate 1 conflict-integrity files under `app/reports/` | behind: 15 files, 2089 deletions (later main work absent) |

Remaining unmerged remotes (`origin/claude/*`, `origin/docs/defer-dashboard-lists-mvp`, `origin/feat/frontend-bootstrap-design-system`, `origin/for-claude-code-review`) have unique commits that do **not** touch those M&E/proposal code paths (docs/audit/frontend-skeleton only). Whether any of those branches contain M&E *documentation* diffs was not fully enumerated.

### 0.3 Did the D-083 bundle export and scorecard run against dfd17248 happen?

**Verdict:** PARTIAL (discovery present; production scorecard absent)

**Pointer:** `docs/artefacts/me_module/audits/BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json` (+ `.md`); glob `**/*dfd17248*`; no `*scorecard*` artefacts besides library/CLI source.

**Evidence:** Discovery artefact `generated_at` `2026-08-08T09:21:52Z`, `report_id` `dfd17248-9b46-48d9-8bc6-5348eab44a1c`, `read_mode` `postgresql_readonly`, `purpose` states “No mapping, no scoring”. It records no git SHA of the originating report build and no five-layer scores. Companion markdown says “Do not author the production→ScoreableBundle mapping or the export/scorecard until the owner releases this gate”. Decision log D-083 (`docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` lines 92, 603–605) says the real-report scorecard run is owner-triggered and the builder does not produce it. No committed scorecard markdown/JSON with layer verdicts for this report_id exists in the repo. Five-layer scores: **absent**.

### 0.4 The scorer: exact invocation; model call; CI today

**Verdict:** CONFIRMED

**Pointer:** `scripts/audit/scorecard_emit.py` lines 21–48; `app/reports/eval/scorecard.py` `emit_scorecard` lines 41–49; `app/reports/eval/run_assertions.py` lines 19–30; `.github/workflows/smoke-test.yml` job `smoke` steps “P0 assertion library suite” and “P0 bundle export and scorecard suite” (lines 127–135).

**Evidence:** Exact owner invocation against an already-exported local bundle is `python scripts/audit/scorecard_emit.py --bundle <path> [--out …] [--json-out …]`. That CLI `json.loads` the file, builds `ScoreableBundle`, and calls `emit_scorecard` → `run_all_layers` (layers 1–5 in-process). Grep of `app/reports/eval/` finds no `openai` / `anthropic` / `prompt_runner` / HTTP client: the scorer makes **no model call**. CI does **not** run `scorecard_emit.py` or `bundle_export_run.py` against dfd17248. CI runs `pytest tests/test_p0_assertion_library.py` and `pytest tests/test_p0_bundle_export_scorecard.py` (constructed inputs only; workflow comment “constructed inputs only (D-083)”). The production-read CLI `scripts/audit/bundle_export_run.py` is owner-triggered (`--railway`) and is not a workflow step.

### 0.5 Hooks and guards: existence, commit/push invocation, fire evidence

**Verdict:** PARTIAL

**Pointer:** `.cursor/hooks.json`; `.claude/settings.json`; `.githooks/pre-commit`; `.github/workflows/smoke-test.yml` jobs `governance-guards` and `governance-tree-audit`; `scripts/governance/run_guards.py`; `.cursor/hooks/governance_guards.py` `evaluate_path_lines` (lines 562–564); `.cursor/hooks/isolation_veto.py`; `docs/artefacts/me_module/audits/G1_PLANTED_VIOLATION_PROOF_2026-07-26.md`; `tests/test_governance_guards.py`.

**Evidence:**

| Guard | Exists | Invoked on git commit | Invoked on push/PR | Fire evidence |
|---|---|---|---|---|
| Funder/fixture string (`funder_fixture` / `sealed_fixture`) | Yes — `check_funder_fixture_lines` in `governance_guards.py`; PreToolUse wrappers `.cursor/hooks/funder_fixture_guard.py` and `.claude/hooks/funder_fixture_guard.py` | Yes — `.githooks/pre-commit` execs `scripts/governance/run_guards.py --staged --layer pre-commit` (this checkout has `core.hooksPath=.githooks`) | Yes — job `governance-guards` runs `run_guards.py --range … --layer ci` (protected-file mode `blocking` on `pull_request`, `report` on push/schedule); funder/fixture remains blocking on all events per the job script | Planted-proof transcript: pre-commit exit 1 on `app/reports/gap/_g1_plant.py` token `FCDO`; CI job https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/30266529052/job/89978423265 conclusion failure, log excerpt `[funder_fixture] app/reports/gap/_g1_ci_plant.py`. Unit test `test_funder_string_on_engine_path_denied`. |
| Golden / protected-file | Yes — `check_protected_write`; PreToolUse `protected_file_guard.py` | Yes — same pre-commit `evaluate_added_map(..., check_protected=True)` | Yes on PR (blocking); on push/schedule **report-only** (D-078; `partition_ci_violations`) | Planted proof: unflagged `AGENTS.md` write exit 1; override path exit 0 logged to `.governance/override_log.jsonl`. Test `test_protected_file_requires_override`. |
| Harness-import | Yes — `check_harness_import_lines`; PreToolUse `harness_import_guard.py` | Yes — same `run_guards.py --staged` | Yes — blocking on all CI events | Planted proof: pre-commit exit 1 `app/reports/services/_g1_plant.py` import of `app.reports.eval`. |
| Secret write / secret scan | Yes — `check_secrets_lines`; PreToolUse `secret_write_guard.py`; Cursor `beforeShellExecution` matcher `git\s+commit` → `secret_scan.py`; Claude PreToolUse Bash → `secret_scan.py` | Secret *write* via staged-line scan in `run_guards.py`. Cursor `secret_scan.py` on `git commit` is editor-hook, not the git hook. | Secret line-scan in `governance-guards`. | Planted proof PreToolUse deny on planted `sk-` pattern in `docs/artefacts/me_module/audits/_planted_secret.md`. |
| Isolation veto (core must not import `app.reports`) | Yes — `.cursor/hooks/isolation_veto.py` / `.claude/hooks/isolation_veto.py` calling `check_isolation_violation` | **No** — `run_guards.py` / `evaluate_path_lines` do not call isolation. Isolation is PreToolUse-only. | **No** — not in `governance-guards`. | Planted-proof transcript does not include an isolation deny. `tests/test_governance_guards.py` has no isolation test. Whether PreToolUse isolation has ever denied a write in this checkout: **CANNOT DETERMINE**. |
| Migration parity | Yes — PostToolUse `migration_parity_check.py` | No | No | No commit/push fire evidence in the planted-proof pack. |
| Tree-wide funder scan | Yes — `scripts/governance/tree_audit.py` | No | Job `governance-tree-audit` on the same workflow, `continue-on-error: true` (report-only, never blocking) | Workflow writes `G1_TREE_AUDIT_CI.md` as an artifact; committed snapshot `docs/artefacts/me_module/audits/G1_TREE_AUDIT_2026-07-26.md`. |

Local git-hook installation is not automatic for every clone: `scripts/install_git_hooks.py` sets `core.hooksPath=.githooks`. This working tree has that config set. Whether every contributor machine has it: **CANNOT DETERMINE**. CI `governance-guards` is non-bypassable on GitHub events in the workflow file.

### 0.6 Deployed SHA on Railway versus main HEAD

**Verdict:** CONFIRMED (backend web + worker); frontend is a different repo

**Pointer:** `railway status`; `railway deployment list --json --service ngoinfo-grantpilot --limit 1`; same for `exemplary-encouragement`; `GET https://ngoinfo-grantpilot-production.up.railway.app/health`; `app/api/routes/health.py` lines 9–16; `app/reports/api/routes/health.py` lines 6–7.

**Evidence:** `origin/main` HEAD is `f44426a2cb8cb3cdf4b6de91d37fccc8297b4b3e`. Railway production web service `ngoinfo-grantpilot` latest SUCCESS deployment `ccb3ffea-3fd5-4d09-b176-33b2937f69df` (`createdAt` `2026-08-16T19:13:51.233Z`) has `meta.commitHash` `f44426a2cb8cb3cdf4b6de91d37fccc8297b4b3e` (equal to main HEAD). Worker service `exemplary-encouragement` latest SUCCESS `d3a63194-461e-474a-9db5-7410fcf779b7` (`createdAt` `2026-08-16T19:13:51.457Z`) has the same `commitHash`; `startCommand` is `python -m app.reports.worker`. Health JSON is `{"status":"ok","service":"grantpilot","version":"v1.0.0",…}` — `version` is `os.getenv("PROMPT_VERSION")`, not a git SHA (`app/api/routes/health.py`). Reports health returns `{"status":"ok","module":"reports"}` with no SHA. Frontend Railway service `grantpilot-frontend` latest SUCCESS (`createdAt` `2026-07-20T10:55:55.014Z`) is repo `mycrivo/grantpilot-frontend` commit `4577161cd8832a344d1ff0f8c5a3e25f4499c8eb`, not this backend SHA.

Both backend services use builder `RAILPACK` with `nixpacksConfigPath: null`.

### 0.7 Landed / not / partial

#### PDF crash fix (system library for Docling's PDF backend)

**Verdict:** PARTIAL

**Pointer:** `nixpacks.toml` lines 1–13 (`libxcb1`, `libxcb-render0`, `libxcb-shm0`, `libx11-6`, `libglib2.0-0`, `libgl1`, `tesseract-ocr`, `poppler-utils`); Railway deployment `serviceManifest.build.builder` = `RAILPACK`, `nixpacksConfigPath` = null (web and worker); `app/reports/orchestration/extract_isolation.py` `classify_intake_exception` lines 63–66; `tests/test_classify_isolation.py` line 39; `tests/test_p0_me_smoke.py` line 11; historical observation `docs/artefacts/me_module/audits/ME_MODULE_DYNAMIC_AUDIT_2026-06-08.md` lines 37–40.

**Evidence:** The repo declares the X11/render apt packages Nixpacks needed for Docling's `pypdfium` path. Production builds are Railpack, not Nixpacks, and the deployment manifest does not point at `nixpacks.toml`. No test or live log in this audit inspected `/usr/lib` of the running image for `libxcb.so.1`. Application code maps `DoclingIntakeError` (including a mocked `"libxcb.so.1 missing"`) to per-document **degrade**, not a whole-job crash. Whether the original missing-library crash is gone on the live worker: **CANNOT DETERMINE** from repo + Railway metadata alone.

#### Per-document extraction isolation

**Verdict:** CONFIRMED (landed in code + CI-tested)

**Pointer:** `app/reports/orchestration/classify_isolation.py`; `app/reports/orchestration/extract_isolation.py`; `app/reports/orchestration/pipeline.py` `_run_classify_stage` / `_run_extract_stage` (classify loop at lines 568–583); `tests/test_classify_isolation.py`; `tests/test_extract_isolation.py`; CI `smoke` step includes `tests/test_classify_isolation.py` (`.github/workflows/smoke-test.yml` line 125). `test_extract_isolation.py` is **not** named in that pytest invocation.

**Evidence:** Classify and extract stages iterate documents and catch hard-fail vs degrade. Unit tests exist for both. Classify isolation is in the blocking CI smoke list; extract isolation tests are present in the tree but not in the named CI file list on line 125.

#### Honest report status on partial failure

**Verdict:** CONFIRMED (landed in code)

**Pointer:** `app/reports/models/enums.py` `DonorReportStatus.DEGRADED`; `pipeline.py` lines 585–588 (classify degraded notes → `report.status = DEGRADED`); `app/reports/worker/job_failure.py` lines 56–59 (job fail: if report is `DRAFT`, set `DEGRADED`); `app/reports/services/report_synthesis_service.py` line 669; `app/reports/services/report_export_service.py` line 183.

**Evidence:** Partial classify degradation writes `DEGRADED` onto `donor_reports.status`. Terminal job failure promotes `DRAFT` → `DEGRADED`. Synthesis and export services also assign `DEGRADED`. Whether the NGO-facing UI surfaces that enum vs a mapped label is not in this backend repo (see 5.3). Discovery artefact for dfd17248 records report `status` `COMPLETE` (`BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json` `report_meta.status`), which is an observation of that run, not a counterexample to the code path.

#### Pre-create quota check refusing a third report before upload

**Verdict:** CONFIRMED (landed in code + unit test); CI inclusion PARTIAL

**Pointer:** `app/reports/services/donor_report_lifecycle_service.py` `create_donor_report` lines 78–98 (`enforce_report_create_quota` before `db.add(report)`); `app/services/quota_service.py` `PLAN_IMPACT` `reports=2` (lines 66–71) and `enforce_report_create_quota` (line 277); `tests/test_me_enforcement.py` `test_impact_create_rejected_when_quota_exhausted` lines 274–294 (POST `/api/reports` after two ledger rows → 429 `QUOTA_EXCEEDED`, `report_count == 0`).

**Evidence:** Quota is enforced on create, before any upload function runs. Impact plan limit is 2. The unit test asserts a third create is refused with no `DonorReport` row. `tests/test_me_enforcement.py` is **not** listed in `.github/workflows/smoke-test.yml` smoke pytest invocations.

---

## SECTION 1 — Template path

### 1.1 Where the pipeline obtains the template; create-flow questions

**Verdict:** PARTIAL (backend CONFIRMED; NGO-facing UI CANNOT DETERMINE)

**Pointer:** Table `funder_report_templates` (`app/reports/models/funder_report_template.py`); FK `donor_reports.funder_report_template_id`; create `_resolve_funder_template` (`donor_report_lifecycle_service.py` lines 57–75, 94–104); list `GET /api/report-templates` (`app/reports/api/routes/read.py` lines 58–76); `list_active_report_templates` (`report_read_service.py` lines 52–70); pipeline load (`pipeline.py` lines 256–266); synthesis (`report_synthesis_service.py` lines 591–609); `CreateDonorReportRequest` (`report_lifecycle.py` lines 12–16); `docs/artefacts/API_CONTRACT.md` §12.1–12.2.

**Evidence:** The report row stores a UUID FK. Create requires the client to send `funder_report_template_id` (plus period dates and optional `linked_proposal_id`). Selection is by that UUID, not by funder-name match and not a hardcoded live default. Inactive or missing UUID → `404 TEMPLATE_NOT_FOUND`. Sentinel `__default__` / `__lifecycle_default__` → `422`. Catalogue lists `is_active` rows excluding the sentinel, optionally filtered by `region`. Pipeline/gap/synthesis `session.get(FunderReportTemplate, report.funder_report_template_id)`; missing row → `StageFailure` / `STOP_TEMPLATE_NOT_FOUND`. Empty `report_sections_json` at synthesis → `STOP_NO_SECTIONS`. This backend repo has no Next.js create screen; Railway frontend is a different repo (`mycrivo/grantpilot-frontend`, deployed commit `4577161…` dated 2026-07-20). What labels the UI shows: **CANNOT DETERMINE** from this tree. API_CONTRACT.md §12.2 still says create is “not metered at this endpoint (D6)” while `create_donor_report` calls `enforce_report_create_quota` (disagreement recorded; not reconciled).

### 1.2 Downstream consumers of the template object and fields read

**Verdict:** CONFIRMED (backend). Frontend field reads: CANNOT DETERMINE.

**Pointer:** Consumers and fields as called at HEAD:

| Consumer | Path | Fields read |
|---|---|---|
| Classifier | `app/reports/agents/classifier.py` | **None** — no template import |
| Proposal / grant-terms / indicator extractors | `app/reports/agents/{proposal,grant_terms,indicator_data}_extractor.py` | **None** |
| Reconciler | `app/reports/agents/knowledge_bank_reconciler.py` | **None** (no `FunderReportTemplate` / `report_sections` reference) |
| Gap agent / gap services | `pipeline.py` 260–266; `gap_compliance_agent.py` 203–208, 463–469; `gap_compliance_service.py` 62–66; `post_draft_gaps.py` 101–107; `template_requirements.py`; `logframe_completeness.py` 52–54, 57–68; `requirement_metadata.py`; `section_visibility.py`; `proposal_failure_elevation.py` | `funder_name`, `template_name`, `report_sections_json` (section_key, label, required_indicators, required_tables including table_key/min_rows/data_source, owner, indicator_requirements, table_requirements, requirement_type_default, required, conditional_display, elevate_on_proposal_failure), `format_rules_json.logframe.enabled`, `terminology_map_json` (passed into the agent prompt payload) |
| Synthesis | `report_synthesis_service.py` 591–605; `report_inputs_builder.py` 99–123, 184–194, 225–231, 368–399; `ai/prompts/synthesis.py` 215–219, 243–269 | Full visible sections (`include_funder_owned=False`); `section_key`, `label`, `archetype`, `word_limit`, `tone`, `required_indicators`, `required_tables`, `fact_namespaces`, `source_section_labels`, `owner`; `format_rules_json.narrative_constraints`, `format_rules_json.forbidden_terms`; `terminology_map_json.canonical_to_funder`, `terminology_map_json.forbidden_terms`; `funder_name`, `template_name` |
| Critic (fact-safety) | `report_fact_safety_service.py` 155–163 | `report_sections_json` (section_key, plus the same routing fields `subset_facts_for_section` reads) |
| Renderer / export | `report_export_service.py` 83–112; `docx_renderer.py` 33–35, 171–237; `kb_table_renderer.py` 220–243 | `report_sections_json` (order, `section_key`, `label`, `required_tables` with `label`, `columns`, `data_source`); `format_rules_json.document_title`; `docx_template_ref`; `funder_name`, `template_name`; `terminology_map_json` is passed into `render_report_docx` but labels are **not** substituted (`docx_renderer.py` 216–218) |
| Orphan reaper | `orphan_reaper.py` 83–86 | `report_sections_json` |
| Frontend | not in this repo | list endpoint returns `id`, `funder_name`, `template_name`, `region`, `reporting_frequency`, `version` only (`read.py` 67–74) |

**Evidence:** Classifier/extractors/reconciler do not load the template row. Gap and synthesis load it from the FK. Empty `[]` sections fail synthesis (`STOP_NO_SECTIONS`). Critic reloads sections so fact visibility matches synthesis.

### 1.3 As-built schema: structural vs authored-knowledge; null behaviour

**Verdict:** PARTIAL (runtime fields CONFIRMED at HEAD; production JSON instances not queried)

**Pointer:** Model columns `funder_report_template.py` 18–31; section enumeration `template_requirements.py` 53–113; visibility `section_visibility.py` 8–18; metadata fallbacks `requirement_metadata.py` 10–61, 76–145; hints `requirement_satisfaction.py` `DATA_BACKED_HINTS` 22–41; synthesis routing `report_inputs_builder.py` 43–54, 99–123; archetype prompt map `ai/prompts/synthesis.py` `REPORT_ARCHETYPE_RULES` 74–120; logframe `logframe_completeness.py` 52–68; tables `kb_table_renderer.py` 237–243. Dated companion `docs/artefacts/me_module/FUNDER_TEMPLATE_SCHEMA_AS_BUILT.md` (extraction date 2026-06-08) describes the same column names; it is a document, not the runtime.

**Evidence — table columns (all DB-required except JSONB defaults `[]` / `{}`):** `funder_name`, `template_name`, `region`, `reporting_frequency`, `report_sections_json`, `format_rules_json`, `terminology_map_json`, `docx_template_ref`, `is_active`, `version`.

**Structural (shape/presentation) fields the engine reads:** section `section_key` (absent → section skipped, `template_requirements.py` 56–59; `section_visibility.py` 31–32); `label` (fallback `section_key`); `word_limit`; `tone`; `required` (default treated as true via `section.get("required", True)`); `conditional_display.enabled` / `.condition` (only exact string `report_type == 'final'` hides; any other condition shows); `required_tables[].table_key`, `.label`, `.columns`, `.min_rows` (min_rows &lt; 1 excluded from gap checklist); `format_rules_json.document_title`, `.narrative_constraints`, `.forbidden_terms`; `terminology_map_json.canonical_to_funder`, `.forbidden_terms`; `docx_template_ref` (missing file → renderer `from_scratch`, `docx_renderer.py` 171–177).

**Authored-knowledge fields the engine reads (requirement/routing/exclusions, not mere layout):**

| Field | If null / absent | Downstream break |
|---|---|---|
| `required_indicators` | Treated as `[]` (`template_requirements.py` 72) | No indicator checklist items for that section; `_indicator_match_tokens` empty |
| `required_tables` / `data_source` | Missing table_key skipped; `data_source` not in `{indicators,financials}` → honest-empty table (`kb_table_renderer.py` 237–243); logframe section resolver falls through to hardcoded `detailed_output_scoring` (`logframe_completeness.py` 57–68) | Gap/export/logframe attach to wrong section or empty tables |
| `owner`, `requirement_type_default`, `indicator_requirements`, `table_requirements` | Resolution falls through to hardcoded sets `FUNDER_SUPPLIED_INDICATORS`, `NARRATIVE_INDICATORS`, `FUNDER_OWNED_SECTIONS`, `FUNDER_SUPPLIED_TABLES` (`requirement_metadata.py` 10–61, 76–145) | Items mis-classified data vs narrative vs funder_supplied; Gate 2 checklist membership changes |
| `elevate_on_proposal_failure` on indicator_requirements | Default false (`proposal_failure_elevation.py` uses the flag) | Narrative elevation on `proceed_with_gap` does not fire |
| `archetype` | `archetype_rule_for(None)` generic rule (`synthesis.py` 243–245); if `fact_namespaces` key also absent, `_ARCHETYPE_FACT_ROOTS` fallback used (`report_inputs_builder.py` 117–122) | Fact routing and prompt structure change |
| `fact_namespaces` | Key **absent** → archetype fallback; key **present even if `[]`** → no archetype widening (`report_inputs_builder.py` 117–122) | Silent widening or narrowing of facts per section |
| `source_section_labels` | Empty → source-pin matching uses only `section_key` / other sections’ labels (`report_inputs_builder.py` 92–95, 258) | Cross-section pin may fail-safe to declared-needs |
| `format_rules_json.logframe.enabled` | `is_logframe_enabled` false (`logframe_completeness.py` 52–54) | No derived `logframe_row:*` gap items |
| Hint keys in `DATA_BACKED_HINTS` (engine, not template JSON) | Unknown `required_indicators` slug with no hints → `_hints_match` false (`requirement_satisfaction.py` 82–88, 105–109) | Data indicator never auto-satisfied from facts |

`DATA_BACKED_HINTS` keys at HEAD (verbatim): `actual_results`, `output_indicators`, `outcome_indicators`, `logframe_milestones`, `progress_against_expected_results`, `forecast_vs_actual_costs`, `forecast_vs_actual_spend`, `financial_delivery`, `cost_drivers`, `beneficiary_numbers`, `outcome_indicators_where_available`, `changes_made`, `review_summary_sheet`, `outcome_assessment`, `delivery_financial_performance`.

`evidence_rules` and `extensions`: no runtime reader found under `app/reports/` (as-built doc §2.1 also states evidence_rules unused). Production template JSON contents were not queried (rule: no production data).

### 1.4 Uploaded document as funder template / guidance; classifier types

**Verdict:** CONFIRMED (no template-from-upload path; types enumerated)

**Pointer:** `DocumentClassification` (`enums.py` 21–28); classifier allow-list `TEXT_CLASSIFICATIONS` and prompt (`classifier.py` 67–86); MIME short-circuit `classification_from_mime` (`document_intake.py` 35–42); extract skip set (`extract_isolation.py` 46–51, 276–277).

**Evidence:** No classification value is `funder_template`, `guidance`, or similar. LLM classifier may assign only `proposal`, `grant_letter`, `mou`, `indicator_data`, `other`. Photos (`image/*`) and decks (PowerPoint MIME) are assigned `photo` / `deck` from MIME before the LLM and are skipped at extract. No code path loads an upload into `funder_report_templates`.

### 1.5 Web and URL ingestion / Firecrawl / search

**Verdict:** CONFIRMED (absent from backend live paths)

**Pointer:** repo grep under `app/` for `Firecrawl`, `FIRECRAWL`, `web_search`, `tavily`, `serpapi`, `beautifulsoup`, `playwright`, `scrapy`, `crawl`; `httpx` uses: `app/integrations/openai_client.py`, `app/api/routes/auth.py` (Google userinfo), `app/services/email_service.py`.

**Evidence:** No Firecrawl client, no `FIRECRAWL_*` env var in `app/`. No scrape/search library in `app/`. `httpx` is the OpenAI HTTP client, OAuth userinfo, and email provider — not URL ingestion for reports. M&E pipeline intake is uploaded bytes via `DocumentStorageService.fetch_bytes`. Historical note in `DEPLOYMENT_STATE_2026-05-30.md` also recorded no `FIRECRAWL_*` under `app/` (document, not re-tested at deploy).

### 1.6 Docling tables vs flattened text; xlsx indicator degradation

**Verdict:** PARTIAL

**Pointer:** Docling text path `docling_adapter.py` 18–53 (`document.export_to_markdown()` only — no `tables` key returned). Structured `.docx` tables for indicator_data: `spreadsheet_input.py` `parse_docx_tables` 93–117 (`document.tables`, `table.export_to_dataframe`). Proving unit test: `tests/test_spreadsheet_input_adapter.py` `test_parse_docx_tables_via_docling_mock` (lines 141+; Docling `DocumentConverter` mocked). `.xlsx` path: `parse_xlsx_workbook` 120–146 (`openpyxl.load_workbook`, `data_only=True`) — Docling is not called. Router `parse_spreadsheet_from_path` 172–180: `.xlsx` / `.csv` / `.docx` only. Upload rejects `.xls` (`tests/test_upload_format_validation.py` 67–70). Unparseable: `extract_indicator_data_from_path` 692–698 catches `ValueError` (including `parse_docx_tables` “No tables found”) → `DEGRADED_EXTRACTION_UNPARSEABLE` without LLM; isolation `extract_isolation.py` 228–237 persists the same on any non-hard-fail intake exception.

**Evidence:** For classified `indicator_data`, `.docx` tables reach the extractor as a JSON grid of cells, not as the markdown blob from `extract_text_from_path`. The proving fixture in CI is a **mock** Docling table, not a live Docling conversion of a real .docx. `.xlsx` indicator intake is openpyxl at the adapter layer; comment at `spreadsheet_input.py` lines 3–4 (D-036) states Docling markdown is not used for indicator_data. A valid `.xlsx` parse does not itself degrade. Degradation observed in tests is: (a) non-spreadsheet `.docx` bytes → `ValueError` at **adapter** `parse_docx_tables` / `parse_spreadsheet_from_path`, **agent** never called (`test_unparseable_docx_from_path_returns_degraded_no_raise`); (b) `.xls` rejected at **upload validation**, never reaches Docling or the agent. Whether a corrupted `.xlsx` that raises `openpyxl` `InvalidFileException` (not a `ValueError`) degrades vs hard-fails depends on `classify_intake_exception` (`extract_isolation.py` 63–79: generic `Exception` → degrade unless classified systemic/RuntimeError/S3). No committed log of an xlsx-specific production degrade for dfd17248 (discovery `indicator_actuals` empty is a persisted-shape observation, not a layer diagnosis).

---

## SECTION 2 — Gate 1 and conflicts

### 2.1 Gate 1 resolution options as implemented in API and frontend

**Verdict:** PARTIAL (API CONFIRMED; frontend screens CANNOT DETERMINE from this repo)

**Pointer:** `app/reports/schemas/knowledge_bank_patch.py` 10–23; `app/reports/services/knowledge_bank_patch_service.py` `materialize_conflict_resolution` 85–155; `app/reports/api/routes/gate1.py`; `app/reports/schemas/gate1_confirmation.py`; `docs/artefacts/API_CONTRACT.md` §12.4–12.5a; `app/reports/knowledge/confirmed_kb.py` `is_fact_citable` 34–40; `KnowledgeBankConflict.values` (`knowledge_bank_reconciliation_v1.py` 58–64). Frontend: not in this repository; Railway `grantpilot-frontend` commit `4577161cd8832a344d1ff0f8c5a3e25f4499c8eb` (2026-07-20) message mentions “explicit-entry for ambiguous values” (deploy metadata, not source).

**Evidence:** The backend exposes no named resolution enum (`keep_both`, `choose_a`, `both_are_true`). Wire options are:

1. **PATCH** `/api/reports/{id}/knowledge-bank` `conflict_resolutions[]`: one `fact_key` + one concrete `resolved_value` (null/blank → 422 `KB_CONFLICT_RESOLUTION_VALUE_REQUIRED`). If `resolved_value` equals a `conflict.values[].value`, that candidate’s value/unit/source/provenance is copied onto `facts[fact_key]`. If it matches none, the fact is overwritten with the new value, `source_document_id` `owner-attested`, label “Owner attestation (Gate 1)”. `conflict.resolved_value` / `resolved_at` are set. The fact is `confirmed` / `confirmed_by_user`. The `conflicts[].values` array is **not** deleted.
2. **PATCH** `facts{}`: overwrite `facts[key].value` and optional `confirmed`.
3. **POST** `.../gate1/promote`: snapshot-checked promotion of unverified facts without setting `gate1_confirmed_at`.
4. **POST** `.../gate1/confirm`: persist full `knowledge_bank_json`; `validate_gate1_knowledge_bank` requires every conflict to have `resolved_value` not None (`knowledge_bank_reconciliation_v1.py` 148–152).

**Retain both values?** Conflict candidate rows remain in `conflicts[].values`. D-060 sibling facts may keep the other figure under a related key with `provenance_only_for` set; those siblings are **not citable** (`confirmed_kb.py` 37–40). There is no API that leaves two citable values on the same `fact_key`. Golden-pack `resolution_type: both_are_true_different_facts` exists only in harness fixtures (`RECONCILIATION.md`, `l2_assertions.py`), not in the Gate 1 PATCH schema. Frontend option labels and whether the UI offers “keep both” as a third button: **CANNOT DETERMINE** without the frontend source.

### 2.2 Reconciler conflict rule, target/milestone/actual distinction, key convention

**Verdict:** PARTIAL

**Pointer:** Reconciler prompt `knowledge_bank_reconciler.py` `_SYSTEM_PROMPT_BASE` 128–145 (same `fact_key` + same semantic quantity; zero numeric tolerance; different questions → two keys, not a conflict). Candidate `field_path`s: `reconciliation/input_builder.py` `_flatten_proposal` 206–223 (`indicators.{indicator_key}.target` only) and `_flatten_indicator_data` 307–315 (`indicators.{row_id}.target` and `.actual`). Proposal schema still has `baseline` / `milestone` / `target` (`proposal_extraction_v1.py` 100–106) but flatten does not emit baseline or milestone candidates. Facet collapse: `synthesis_output_hygiene.py` `_map_facet_token` 120–127 (`target`, `ar1target`, `milestonetarget`, `milestone` → one `"target"` facet). ID regex: `logframe_completeness.py` `normalize_indicator_id` 12–34 and `synthesis_output_hygiene.py` `_extract_indicator_id` 109–117 (both `opN_N` and `opN.N` normalize to `opN_N`). Prompt example: `ai/prompts/synthesis.py` 184–185 (`indicators.op1_1.ar1_actual` / `ar1_target`). Gap copy: `gap_question_copy.py` 114–119 (underscore → dotted uppercase display). Proposal extractor instruction: `proposal_extractor.py` 131 (`op1_1_girls_reenrolled` snake_case). Gap agent prompt: `gap_compliance_agent.py` 84 (`OP2.3` in questions).

**Evidence:** Conflict detection at E1 is **LLM-assigned `fact_key` identity**, not a deterministic Python equality over ontology slots. Deterministic candidate paths distinguish only **`.target` vs `.actual`** (plus notes/disaggregation). Proposal **endline vs period milestone vs baseline** are extracted onto `ExtractedIndicator` fields but **not** flattened into separate `field_path`s, so they are not separate candidate slots for the reconciler. Hygiene treats milestone tokens as the same facet as target. Therefore the **current key shape does not distinguish** endline target, period milestone, and achieved value as three comparable slots; achieved is the `.actual` / `ar1_actual` facet; the two target-like names collapse.

**Live indicator key convention:** dotted namespace `indicators.<id>.<facet>` is the candidate and citation shape. The `<id>` token is **underscored `opN_N`** in flatten (`row_id` / `indicator_key`) and in the synthesis JSON example (`op1_1`). Dotted `OP1.1` / `OP2.3` appears in NGO-facing question copy and in a gap-agent instruction, not as the persisted candidate `field_path`. Both regexes are accepted when parsing ids. Which `row_id` the indicator extractor actually writes for a given spreadsheet is model output plus extractor mapping — not a second hardcoded convention in flatten.

### 2.3 Synthesis comparator for “achieved against target”

**Verdict:** PARTIAL (instruction unspecified; example names `ar1_target`)

**Pointer:** `app/reports/ai/prompts/synthesis.py` lines 8–11 (“measured against targets”; “Explain variance against targets where the knowledge bank supplies both target and actual”); example `source_refs` lines 183–185 (`fact:indicators.op1_1.ar1_actual` and `fact:indicators.op1_1.ar1_target`); table fill families `kb_table_renderer.py` 31–46 (`ar1_actual` vs a single target family including `ar1_milestone_target`, `proposal_target`, `target`). No `synthesis_claim_binding.py` symbol selects endline vs milestone.

**Evidence:** The synthesis system prompt does not name endline, period milestone, or AR1. The only concrete pairing in that prompt file is `ar1_actual` against `ar1_target`. Export tables treat several target-named facets as one fill family. Which fact the model actually binds on a given run is not recorded in the dfd17248 discovery artefact (no per-section fact lists in that JSON’s purpose). Unspecified in code; example implies `ar1_target`.

---

## SECTION 3 — Gaps

### 3.1 Gap agent inputs; hint map

**Verdict:** CONFIRMED

**Pointer:** `run_gap_compliance` (`gap_compliance_agent.py` 452–472, 195–221); `TemplateRequirement` (`template_requirements.py` 20–30); `enumerate_template_requirements`; `DATA_BACKED_HINTS` (`requirement_satisfaction.py` 22–41) used by `_hints_match` 82–88 and `_data_indicator_satisfied` 105–107; wrapper `satisfaction.py` 21–51. Duplicate dict in `scripts/audit/analyze_run.py` is not on the pipeline path.

**Evidence:** Template side is `report_sections_json` turned into `TemplateRequirement` records (`item_key`, `section_key`, `section_label`, `required_item_type`, `required_item_ref`, `severity`, `owner`, `requirement_type`), plus derived `logframe_row:*` items when `format_rules_json.logframe.enabled`. Bank side passed into the agent payload is `schema_version`, `facts`, `conflicts`, `unreadable_sources`, `gap_answers`, `gate1_confirmed_at`. The hint map **is still consulted** for data-indicator auto-satisfaction. Verbatim keys: `actual_results`, `output_indicators`, `outcome_indicators`, `logframe_milestones`, `progress_against_expected_results`, `forecast_vs_actual_costs`, `forecast_vs_actual_spend`, `financial_delivery`, `cost_drivers`, `beneficiary_numbers`, `outcome_indicators_where_available`, `changes_made`, `review_summary_sheet`, `outcome_assessment`, `delivery_financial_performance`. Hint values are substring needles (`ar1_actual`, `indicators.`, `.note`, …). Pipeline may skip the LLM (`use_llm` false → deterministic output only, lines 498–514). Draft-first path (`pipeline.py` 271–314) uses `run_post_draft_gap_analysis` instead of `run_gap_compliance`.

### 3.2 Satisfaction logic: implementations and disagreement

**Verdict:** CONFIRMED (one matcher, two `purpose` modes that can disagree)

**Pointer:** `evaluate_requirement_satisfaction` (`requirement_satisfaction.py` 133–177); wrappers `satisfaction.py` `is_requirement_satisfied` / `unsatisfied_requirements` (default `purpose="gate"`); Gate 2 checklist time: `deterministic_gaps.py` 10, `unsatisfied_requirements`; disclosure/caveats: `remit_disclosure.py` `_requirement_present` 75–82 (`purpose="synthesis"`); synthesis sufficiency: `report_inputs_builder.py` 336–341 (`purpose="synthesis"`).

**Evidence:** There are not two independent algorithms. `satisfaction.py` delegates to `evaluate_requirement_satisfaction`. Call sites differ by `purpose`. With `purpose="gate"` (default), a **narrative** indicator returns `satisfied=True` even when no citable facts exist (`requirement_satisfaction.py` 175–176: `if requirement.required_item_type == "indicator" and purpose != "synthesis": return SatisfactionResult(satisfied=True)`). With `purpose="synthesis"`, that shortcut is skipped, so the same item can be unsatisfied for disclosure/synthesis. Skipped gap-answers count as resolved for `purpose="gate"` (`_gap_answer_satisfies_requirement` 143–148) but not for `purpose="synthesis"` (requires `disposition == answered`). Funder-owned / `funder_supplied` items are auto-satisfied in both modes (line 159–160). Table presence in remit_disclosure can additionally short-circuit via namespace facts before calling the matcher (lines 71–74).

### 3.3 Where NGO-facing question text is formed; keys; comparator

**Verdict:** CONFIRMED (backend). Frontend rendering: CANNOT DETERMINE.

**Pointer:** `build_gap_question` / `build_logframe_indicator_question` (`gap_question_copy.py` 114–138); `deterministic_gaps._default_question` 15–16; logframe items `logframe_completeness.py` `_default_question` 195–202 and `_default_rationale` 205–214; post-draft `post_draft_gaps.py` 40, 61, 81; GET mapping `gap_check_service.py` 83–103 (`prompt` copies `question`).

**Evidence:** Checklist questions are deterministic English from `section_label` + a clause map keyed by `required_item_ref`, or `humanize_ref` (underscores → spaces) when the slug is unknown — the slug’s words can therefore appear in the question. Logframe questions rewrite `op2_3` → `OP2.3` in the question string; they do **not** embed `item_key`. Rationale for missing actuals quotes `entry.proposal_target_value` (from proposal-sourced `.target` facts, `logframe_completeness.py` 147–152) and `entry.indicator_id.upper()` (underscore form, e.g. `OP2_3`) in `_default_rationale`. The question asks for “actual result … during this reporting period” / “Annual Review actual” against “the proposal target” in the rationale — not named as endline vs milestone. GET `/gap-check` also returns `item_key`, `owner`, `requirement_type`, `suggested_action` as JSON fields (those are keys/enums on the wire; whether the UI displays them is not in this repo).

### 3.4 Gap-answers contract: wire, DB, docs

**Verdict:** PARTIAL (canonical POST agrees with field-contract + schemas; GET extra fields; PATCH vs docs disagree)

**Pointer:** Wire POST: `Gate2GapAnswersRequest` (`gate2_gap_answers.py` 14–40); persist `_persisted_answer` (`gate2_gap_answer_service.py` 60–88) into `knowledge_bank_json.gap_answers`; GET `GapCheckResponse` (`gap_check.py` 13–35); PATCH `PatchGapAnswersRequest` 38–46; routes `gate2.py` 25–75; `docs/artefacts/me_module/GATE2_GAP_ANSWERS_FIELD_CONTRACT.md`; `docs/artefacts/API_CONTRACT.md` §12.6–12.7a.

**Evidence:** Canonical POST `/knowledge-bank/gate2/gap-responses` request is `responses: { item_key: { disposition, answer_text?, skip_reason? } }`. Persisted answered row: `disposition`, `answer_text`, `skip_reason=null`, `responded_at`, `provenance.{source,excerpt}`, `source_label`, `source_document_id=null`. Skipped: `skip_reason` in `{not_applicable, cannot_provide}`, `provenance=null`. That matches `GATE2_GAP_ANSWERS_FIELD_CONTRACT.md` and `Gate2GapAnswerPersisted`. GET `/gap-check` returns `missing_items[].prompt` (API_CONTRACT §12.6) **and** additional fields `question`, `rationale`, `owner`, `requirement_type`, `suggested_action`, `confirm_existing_excerpt` not listed in §12.6. `PATCH /api/reports/{id}/gap-answers` **is implemented** (`gate2.py` 40–57). API_CONTRACT.md line 1478 and GATE2 field-contract lines 70–71 still say that PATCH is “PROVISIONAL — not implemented”. Frontend agreement: **CANNOT DETERMINE**.

---

## SECTION 4 — Writer

### 4.1 Per-section synthesis payload (D-046 trim); dfd17248 fact counts

**Verdict:** CONFIRMED (routing rule). Fact counts for dfd17248: CANNOT DETERMINE.

**Pointer:** D-046 text `ME_MODULE_DECISION_LOG.md` line 55; implementation `subset_facts_for_section` / `_fact_namespace_patterns` (`report_inputs_builder.py` 1–11, 99–123, 241–253); `build_report_inputs_for_section` 357–376; discovery artefact `BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json` (shape/redaction only; `generation_summary` keys `accepted`, `awaiting_review`, `critic_blocks`, `failed`, `generated`, `total_sections`, `warnings` — no per-section fact cardinalities).

**Evidence:** Each F1 call is built per template section. Facts with `source_section` are pinned to that section only. Other facts match `fact_namespaces` + `required_tables.data_source` + `required_indicators` tokens, plus shared roots `{grant, reporting, objectives}`. If `fact_namespaces` is omitted, `_ARCHETYPE_FACT_ROOTS` widens the set. Gap answers are similarly filtered (`filter_citable_gap_answers` then section subset). The dfd17248 discovery file redacts free text and does not record how many facts were passed into each section prompt. No run bundle with per-section input traces for that id is committed.

### 4.2 Contamination at HEAD vs G1 worklist of 14 files

**Verdict:** CONFIRMED (hits enumerated). Exhaustive “beyond worklist” scan: PARTIAL (engine `app/reports/` grep for `FCDO`/`NLCF`; prompts not fully read for coaching without tokens).

**Pointer:** Worklist `docs/artefacts/me_module/audits/G1_DECONTAMINATION_WORKLIST_2026-07-26.md` (14 files). HEAD grep of those paths:

| File | Hit still present? | Pointer |
|---|---|---|
| `app/reports/agents/gap_compliance_agent.py` | **yes** (related; original `logframe_row_template_form` string not found) | line 84 example `OP2.3` in engine prompt |
| `app/reports/agents/grant_terms_extractor.py` | **yes** | line 85 dated period example in extractor rules |
| `app/reports/agents/indicator_data_extractor.py` | **yes** | lines 646–647 funder name in comment |
| `app/reports/agents/proposal_extractor.py` | **yes** | lines 110, 118 expected counts |
| `app/reports/ai/prompts/synthesis.py` | **yes** | lines 182–185 JSON example (worklist sample sentence + `indicators.op1_1.*` keys) |
| `app/reports/extraction/spreadsheet_input.py` | **yes** | lines 225–226 funder name in comment; live token tuple is `("section",)` at 229 |
| `app/reports/gap/gap_question_copy.py` | **yes** | line 115 docstring “FCDO-style” |
| `app/reports/gap/logframe_completeness.py` | **yes** | line 68 fallback heading `Detailed Output Scoring` |
| `app/reports/gap/requirement_metadata.py` | **yes** | line 21 slug `FCDO_management_actions` |
| `app/reports/gap/requirement_satisfaction.py` | **yes** | line 27 hint key `progress_against_expected_results` |
| `app/reports/schemas/indicator_data_extraction_v1.py` | **yes** | lines 78, 85 funder name in comments |
| `app/reports/schemas/proposal_extraction_v1.py` | **yes** | line 4 module docstring funder name |
| `app/reports/services/report_inputs_builder.py` | **yes** | lines 118, 261 comments `e.g. FCDO` |
| `app/reports/services/synthesis_citation_emission.py` | **yes** | line 28 `OP2.1-style` |

**Beyond the worklist (engine paths, not `app/reports/eval/`):** `proposal_extractor.py` 110–118 also asserts expected objective and indicator **counts** (named enemy in AGENTS.md). `gap_compliance_agent.py` 84 names a dotted OP id. Harness/eval files (`eval/gates.py`, `eval/output_rubric.py`, `eval/fixtures.py`, golden pack loader) contain funder names and expected counts; those paths are harness, not the 14-file engine worklist. A full prompt-coaching read without blocklist tokens was not completed.

### 4.3 Tables: binding vs writer-emitted rows

**Verdict:** CONFIRMED

**Pointer:** `kb_table_renderer.py` 1–17, 220–243; `docx_renderer.py` 220–238; synthesis user prompt 157–161 (caveats on `required_tables`, no row-emission schema); `content_json_v1` section content is `text` / `claims` / `assumptions` — no `table_rows` field.

**Evidence:** Export tables are filled by `table_rows_for_definition` from KB facts when `data_source` is `indicators` or `financials`. Empty binding: one honest-empty row of `"not provided"` cells (`kb_table_renderer.py` 16–17, 218, 241–243); `docx_renderer.py` 236–238 may append an honest-empty caveat. `data_source` other than those two also gets a single honest-empty row. The writer has no structured channel to emit table rows; the renderer does not read prose tables into `required_tables`. Whether the model pastes a markdown grid into `generated_content.text` is unconstrained by schema (prose is a string).

### 4.4 Cover metadata: reporting period and organisation name

**Verdict:** CONFIRMED

**Pointer:** `report_export_service.py` 98–113; `docx_renderer.py` 185–192; `build_report_inputs_for_section` NGO payload `report_inputs_builder.py` 197–211 (`get_profile` → `organization_name`).

**Evidence:** Cover reporting period is `donor_reports.reporting_period_start` / `reporting_period_end` via `.isoformat()` (date fields, not the knowledge bank). Cover organisation name is `NGOProfile.organization_name` for `report.user_id`, else the literal `Organisation`. Funder line is `template.funder_name`. Synthesis prose may also receive `organization_name` inside `report_inputs` NGO block; that is profile, not bank. Bank facts are not the cover period source.

### 4.5 Prompts on the synthesis path; verbatim-echo risk

**Verdict:** CONFIRMED

**Pointer:** `app/reports/ai/prompts/synthesis.py`: `REPORT_SYNTHESIS_SYSTEM_PROMPT` 5–52; `REPORT_ARCHETYPE_RULES` 74–120; `REPORT_SYNTHESIS_USER_PROMPT_TEMPLATE` 126–199; `_tone_and_voice_block` 202–226; `_linked_proposal_context_block` 229–240; `build_synthesis_user_prompt` 252–270. Call site `report_synthesis_service.py` 143–147. JSON example 176–198. Cardinal rule 13–15 (specifics from facts/gap_answers). Cover dates: `report_export_service.py` 109–110 `.isoformat()`.

**Evidence:** F1 uses one system prompt, one user template (injecting JSON `report_inputs` + full `section` object + tone + linked-proposal block + archetype rule). Purpose: draft one section’s JSON (`claims`, `text`, `assumptions`). Instruction that can cause source-format echo: the model must copy numbers/dates/names from KB fact values (system prompt 13–15; user task 144–145); there is no instruction to reformat dates. The user prompt embeds the entire `report_inputs` JSON, so ISO timestamps or fact keys present there are in the model context. The few-shot JSON block includes dotted `fact:` keys (lines 183–185). Cover period is ISO `YYYY-MM-DD` from the ORM date, independent of the writer. No prompt says “copy ISO” or “copy identifiers into prose”; identifiers are banned in NGO-facing text (system prompt 25–32).

### 4.6 Resume/idempotency (D-047); concurrency, timeout, retry as deployed

**Verdict:** CONFIRMED in code. Live env overrides: PARTIAL.

**Pointer:** D-047 `ME_MODULE_DECISION_LOG.md` line 56; `section_needs_synthesis` `content_json_v1.py` 155–177; `merge_synthesis_sections` / `merge_content_json_after_synthesis` 180–216; concurrency `get_synthesis_max_concurrency` `report_synthesis_service.py` 56, 71–74 and `Settings.ME_SYNTHESIS_MAX_CONCURRENCY` default 2 (`config.py` 61); OpenAI client `httpx.Client(timeout=90.0)` (`openai_client.py` 34), `_MAX_RETRIES = 1` (line 15), timeout retryable only when `feature == "report_synthesis"` (186–188); parse retry `MAX_SYNTHESIS_PARSE_ATTEMPTS = 2` (`report_synthesis_service.py` 63); worker `JOB_WALL_CLOCK_CAP_SECONDS` default `ME_WORKER_JOB_TIMEOUT_SECONDS` or 3600 (`job_timeout.py` 18); lease `ME_WORKER_LEASE_SECONDS` default 120, `ME_WORKER_REQUEUE_MAX` default 1 (`job_lease.py` 19–20). Railway variables for web and worker (`exemplary-encouragement`): `ME_SYNTHESIS_MAX_CONCURRENCY`, `ME_WORKER_JOB_TIMEOUT_SECONDS`, `ME_WORKER_LEASE_SECONDS`, `ME_WORKER_REQUEUE_MAX` **unset** (not in `railway variables --json` key set). Set: `ME_MODULE_ENABLED=true`, `ME_CLASSIFIER_MODEL=haiku`, `OPENAI_MODEL_PRIMARY=gpt-5.4`, `OPENAI_MODEL_FALLBACK=gpt-5.4-mini`, `PROMPT_VERSION=v1.0.0`.

**Evidence:** Resume skips `GENERATED`/`AWAITING_REVIEW`/`ACCEPTED` with non-empty text, skips `human_edited` and `ACCEPTED`, retries `FAILED` and empty text, and bounds `synthesis_parse_failure` to two cycles. Merge walks template order and preserves sibling `content_json` keys. That matches D-047. Deployed concurrency/timeout/retry therefore follow **code defaults** (2, 90s HTTP, one transport retry for synthesis, 3600s job cap) because those env keys are absent on both Railway services. Critique park/resume (`critique_resume_service.py`, `POST .../job/resume-critique`) is a separate Gate 3 seam, not F1 idempotency.

---

## SECTION 5 — Checker and Gate 3

### 5.1 Deployed checker mechanism; tokenisation; severity; download block

**Verdict:** CONFIRMED (backend). Frontend download gating: CANNOT DETERMINE.

**Pointer:** Orchestration F2 `report_fact_safety_service.py` 31–34, 58–70; numeric pass `numeric_fact_verifier.py` 1–5, 19–27, 90–105, 181–228 (claims-primary; `_NUMBER_RE` / `_CURRENCY_RE` on claim `value_tokens` and prose backstop `extract_significant_numbers`); qualitative pass `fact_safety_critic.py` `_QUALITATIVE_SYSTEM_PROMPT` 42–72 (model judgement of names/places; numbers deferred); flag schema `fact_safety_critic_v1.py` 41, 51 (default severity `BLOCK`); Gate 3 `gate3_confirmation_service.py` 84–150 (`severity == "BLOCK"` and not `accepted` → 422 `GATE3_UNACCEPTED_BLOCKS`); export generate `report_export_service.py` 71 (`require_gate3_confirmed`); download `export.py` 21–45 / `fetch_export_bytes` 194–208 (no critic re-check; 404 if no `content_json.export.storage_ref`).

**Evidence:** The live checker is a **mixture**: deterministic numeric/date/money matching of tokens against cited KB values (not a typed quantity ontology), plus a **model** qualitative critic. Prose is tokenised with `\b(\d[\d,]*(?:\.\d+)?)\b` (minimum two digits). Flags use `BLOCK` or `WARN` from the qualitative JSON; numeric flags are always `BLOCK`. Unaccepted `BLOCK` flags prevent **Gate 3 confirm**, which prevents the **worker export stage** from running. **GET download** only requires an already-stored artefact plus Impact plan + ownership — it does not re-evaluate flags. Whether the UI hides the download button: **CANNOT DETERMINE**.

### 5.2 Semantic / meaning-level checker on main or any branch

**Verdict:** PARTIAL

**Pointer:** Qualitative F2 (`fact_safety_critic.py` 42–56) is model judgement of “faithful paraphrase” of qualitative specifics — not a separate named meaning-level checker. D-085 (`ME_MODULE_DECISION_LOG.md` line 94, narrative 611): “Nothing in the system currently verifies that the delivered document matches the confirmed ledger. Recorded as a Phase 2 Checker concern. Not acted on.” Eval `faithfulness_check.py` is harness-side. Unmerged branches with unique M&E *code* (0.2) are squash ancestors **behind** main, not carriers of a newer checker.

**Evidence:** No module on `origin/main` is named a semantic/meaning-level checker of the delivered DOCX vs the ledger. The qualitative critic is the closest live meaning pass, and it scores **section prose in `content_json`**, not the rendered file. Exhaustive search of every remote branch’s extra commits for a new checker: not completed; the three M&E-touching unmerged branches are not ahead of main.

### 5.3 Raw engine vocabulary reaching the user (API surfaces; UI mapping unknown)

**Verdict:** PARTIAL (API returns unmapped strings; screens not in this repo)

**Pointer:**

| Surface | Unmapped field | Pointer |
|---|---|---|
| List/detail | `status` (`DRAFT`/`DEGRADED`/`COMPLETE`/…) | `report_read.py` 16, 39; `report_read_service.py` 98, 135 |
| List/detail | `current_gate` (`gate1`/`gate2`/`gate3`/`none`) | `report_gate_state.py` 8–22; `report_read.py` 19 |
| List/detail | `latest_job_status`, `latest_job_stage` (`queued`/`classify`/…) | `report_read.py` 20–21 |
| Documents | `classification`, `extraction_status` | `report_lifecycle.py` 39–40 |
| Knowledge bank GET | full `facts`/`conflicts` objects including `verification_status`, `conflict_type`, `fact_key`, `provenance_only_for` | `KnowledgeBankResponse` `report_lifecycle.py` 77–85 |
| Gap-check GET | `item_key`, `owner`, `requirement_type`, `suggested_action` | `gap_check.py` 13–25; `gap_check_service.py` 90–102 |
| Gate 2 remaining | `item_key`, `required_item_type`, `required_item_ref` | `gate2_gap_answers.py` 58–64 |
| Gate 2 skip | `cannot_provide` / `not_applicable` | `gate2_gap_answers.py` 11 |
| Gate 3 / content | `generation_status`, `critic_flags[].severity` (`BLOCK`/`WARN`) | `content_json_v1.py`; review routes |
| Export filename | slugged `funder_name`/`template_name` | `docx_renderer.py` 277–289 |

**Evidence:** These strings are serialized on the backend responses without an NGO-copy mapper in this repo. `ngo_text_redaction.redact_internal_identifiers` applies to **export prose**, not to JSON field names. Whether Gate 1/2/3 screens display them raw: **CANNOT DETERMINE**.

---

## SECTION 6 — Export

### 6.1 Renderer: order, headings, tables, docxtpl

**Verdict:** CONFIRMED

**Pointer:** `docx_renderer.py` `render_donor_report_docx` 171–274 (loop `template_sections` 209–218; heading from `label` or `section_key`); tables 220–238 via `kb_table_renderer`; markdown tables in section prose `_render_section_body` 112–128 / `_parse_markdown_table_block` 79–89; `python-docx` `Document` import line 11; `resolve_docx_template_path` 33–44 (`base_template` vs `from_scratch` 171–177); `tests/test_docx_structural_hardening.py` `test_docxtpl_not_installed` 248–250.

**Evidence:** Section order and headings come from the funder template JSON, not from `content_json` order. Declared tables are KB-filled. Writer markdown pipe-tables in prose are also rendered as Word tables. `docxtpl` is **not installed** (import raises); the live path is `python-docx`. `docx_template_ref` is used only as a **base .docx file** if present on disk, not as a Jinja docxtpl template.

### 6.2 Export endpoint metering / entitlement

**Verdict:** PARTIAL (GET matches “no export quota”; POST in contract is absent; Impact plan still required)

**Pointer:** Live download `GET /api/reports/{id}/export` (`export.py`); gated by `require_impact_plan` (`router.py` 16–19). No `enforce_quota` / `REPORT_EXPORT` on that GET. Generate path `report_export_service.py` 14, 71 calls `charge_report_on_first_complete` (REPORT_CREATE at first COMPLETE, not an export meter). API_CONTRACT.md §12.13 describes **POST** `/api/reports/{id}/export` as unmetered; **no POST handler exists** under `app/reports/` (only GET). Worker export stage writes the artefact after Gate 3.

**Evidence:** Re-download is unmetered at the ledger. Entitlement: Impact plan (403 `UPGRADE_REQUIRED`) plus ownership. Decision “none” on export metering holds for GET; the contract’s POST endpoint is not implemented.

---

## SECTION 7 — Proposal Writer

### 7.1 Most recent smoke/integration evidence; files changed since

**Verdict:** PARTIAL

**Pointer:** Committed smoke write-up `docs/audits/prelaunch_smoke_report.md` dated **2026-02-24**, backend SHA `8197616` (not a 22/22 tally). `scripts/smoke_test.py` last commit `53c0bd9` 2026-02-24. GitHub Actions workflow `Smoke Test` on `main` latest success `2026-09-04T09:49:04Z`, `headSha` `f44426a2cb8cb3cdf4b6de91d37fccc8297b4b3e` (includes `python scripts/smoke_test.py` when `github.event_name != pull_request`). Document claim “22/22” appears in `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md` line 399 without a run date/SHA. Proposal-path commits since 2026-03-01: `app/ai`, `app/api/routes/proposals.py`, `app/schemas/proposal.py`, `app/services/proposal_service.py` — latest `87510f6` 2026-05-30 (fit-scan/prompt version); last proposal-generation-focused `03a5e07` 2026-04-01; cluster of GP-P02 fixes 2026-03-23–31 including `9de4491` “make model selection env-driven”.

**Evidence:** A 22/22 March result is **not** present as a dated artefact at HEAD. CI currently reports **success** of the smoke workflow at main HEAD; this audit did not open that job log to count Track A/B steps. Proposal writer files **have** changed since March 2026 (list above).

### 7.2 Model configuration environment-driven; same client?

**Verdict:** CONFIRMED (env-driven in both; **not** the same client)

**Pointer:** Proposal / fit-scan: `app/ai/prompt_runner.py` 85–86 and `app/ai/fit_scan_executor.py` 249–250 use `settings.OPENAI_MODEL_PRIMARY` / `OPENAI_MODEL_FALLBACK` via `OpenAIClient` (`app/integrations/openai_client.py`). M&E synthesis: same OpenAI settings (`report_synthesis_service.py` 143–144). M&E agents: `ME_CLASSIFIER_MODEL` (classifier, proposal extractor, grant terms, indicator data; default `haiku`); `ME_RECONCILER_MODEL` (default `claude-sonnet-4-6`); `ME_GAP_COMPLIANCE_MODEL`; `ME_FACT_SAFETY_CRITIC_MODEL`; timeouts `ME_CLASSIFIER_TIMEOUT_SECONDS`, `ME_RECONCILER_TIMEOUT_SECONDS`, `ME_GAP_COMPLIANCE_TIMEOUT_SECONDS`, `ME_FACT_SAFETY_CRITIC_TIMEOUT_SECONDS`; `ME_GAP_COMPLIANCE_USE_LLM`; `ANTHROPIC_API_KEY` (`claude_sdk_env.py`). Deployed (Railway web+worker): `OPENAI_MODEL_PRIMARY=gpt-5.4`, `OPENAI_MODEL_FALLBACK=gpt-5.4-mini`, `ME_CLASSIFIER_MODEL=haiku`. `ME_RECONCILER_MODEL` unset (code default).

**Evidence:** Proposal path is OpenAI Chat Completions. M&E extract/reconcile/critic path is Claude Agent SDK with separate env names. Synthesis shares the OpenAI client with Proposal Writer.

---

## SECTION 8 — Close

### 8.1 Cannot-determine list

| Item | What would settle it |
|---|---|
| NGO-facing Gate 1/2/3 / create-flow UI copy and whether enums are mapped | Frontend source at `mycrivo/grantpilot-frontend` (deployed SHA `4577161…`) or a recorded screen walk |
| Whether live Railpack images contain `libxcb.so.1` | Read-only inspect of worker container libraries, or a PDF classify log after f44426a |
| Five-layer scores for dfd17248 | Owner-run `scorecard_emit.py` on an exported bundle committed or retained outside this audit’s write ban |
| Per-section F1 fact counts for dfd17248 | Unredacted `agent_trace` / report_inputs dump for that run |
| Isolation-veto PreToolUse ever denied a write | A planted-proof transcript or hook log (none in G1 pack) |
| `core.hooksPath` on every contributor clone | Machine survey; CI does not need it |
| Extract-isolation tests in CI | They exist but are absent from `smoke-test.yml` line 125 — whether another job runs them: no |
| Corrupted `.xlsx` → degrade vs hard-fail | A test raising `openpyxl.InvalidFileException` through `load_spreadsheet_json` |
| Frontend “keep both” control | Frontend Gate 1 source |
| Exact 22/22 smoke step count on a dated SHA after March 2026 | Job log of `scripts/smoke_test.py` with printed step list, or a new artefact |
| Meaning-level checker on remotes other than the three squash-ancestor M&E branches | `git grep` across all `origin/claude/*` unique commits |
| Live `ME_SYNTHESIS_MAX_CONCURRENCY` / worker timeout if set outside `railway variables` | Those keys were absent from both services’ variable JSON |
| Production template JSON inner fields | DB read (forbidden in this audit) |

### 8.2 Docs-vs-code contradictions

1. `API_CONTRACT.md` §12.2: create “not metered”; code `create_donor_report` calls `enforce_report_create_quota` before insert.
2. `API_CONTRACT.md` §12.7 and `GATE2_GAP_ANSWERS_FIELD_CONTRACT.md`: PATCH `/gap-answers` “not implemented”; `gate2.py` implements PATCH.
3. `API_CONTRACT.md` §12.13: POST `/api/reports/{id}/export`; code has GET only; generation is the worker export stage.
4. `API_CONTRACT.md` §12.6 gap-check JSON omits `question`/`owner`/`requirement_type`/`suggested_action`; `GapCheckMissingItemResponse` includes them.
5. `nixpacks.toml` apt libs for Docling PDF; Railway builder is `RAILPACK` with `nixpacksConfigPath` null.
6. `FUNDER_TEMPLATE_SCHEMA_AS_BUILT.md` (2026-06-08) describes engine behaviour; HEAD adds `fact_namespaces` routing and still contains hardcoded `FCDO_management_actions` / `NARRATIVE_INDICATORS` fallbacks the constitution forbids in engine code.
7. D-046 decision text: concurrency 5→2 and 90s timeout; Railway has no `ME_SYNTHESIS_MAX_CONCURRENCY` override (default 2 matches); 90s is OpenAI HTTP timeout in code, not `ME_WORKER_JOB_TIMEOUT_SECONDS` (3600 default).
8. MASTER_MEMORY “22/22 smoke green” vs no dated 22/22 artefact at HEAD; latest committed smoke report is 2026-02-24 at SHA `8197616`.
9. Discovery markdown (2026-08-08) still says do not author export/scorecard until owner gate; D-083 later accepted mapping; scorecard **run** against dfd17248 still absent.
10. Constitution / AGENTS.md: no funder names or expected counts in engine prompts; HEAD `proposal_extractor.py` and `synthesis.py` example plus `requirement_metadata.py` slug still violate that as code (worklist 4.2).

### 8.3 Stop

Last completed section: **8**. Audit file: `audits/ME_STATUS_AUDIT_2026-09-03.md`. HEAD audited: `f44426a2cb8cb3cdf4b6de91d37fccc8297b4b3e` (`origin/main`, also Railway web + worker). No other files modified. No pipeline, worker, model, DB write, or audits-directory write except this file.
