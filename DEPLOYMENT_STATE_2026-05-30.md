# Deployment State Reconciliation — 2026-05-30

**Audit type:** Read-only deployment-state reconciliation (not a structural re-audit).  
**Prior report:** `BUILD_STATUS_2026-05-27.md` — structural snapshot; referenced below where state has changed.  
**Repository:** `c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot` (backend).  
**Evidence date:** Git/filesystem inspection 2026-05-30 (commands via `cmd /c`).  
**HEAD / origin/main tip:** `f26e477` (`fix(deploy): disable mise Python GitHub attestation check for 3.11.8`).

---

## Delta from 2026-05-27 structural audit

| Topic | 2026-05-27 (`BUILD_STATUS_2026-05-27.md`) | 2026-05-30 (this report) |
|-------|---------------------------------------------|---------------------------|
| Local vs `origin/main` | **1 commit ahead**, dirty M&E tree mostly **untracked** | **In sync**; M&E **implementation committed** |
| E1 commit `7c1a666` | Present locally | **On `origin/main`** (ancestor confirmed) |
| M&E agents / migrations | Mostly working-tree only | **Tracked** on `origin/main` (0014, 0015, `app/reports/*`) |
| E2/E3/E4 | Absent | **Present in code** (gate routes, gap agent, services) — worker still stub |
| Fit Scan prompt | v1.0.1 runtime | **v1.1.0** on `origin/main` (`87510f6`) |
| Railway build | Not covered | **`mise.toml`** attestation fix on `origin/main` (`f26e477`) |

---

## 1. Working tree vs committed

**Command:** `git status -sb`

```
## main...origin/main
 M smoke_test_export.docx
?? .claude/
?? .cursor/
?? BUILD_STATUS_2026-05-27.md
?? CLAUDE.md
?? ME_MODULE_STATUS_REPORT.md
?? M_E_Module/
?? status_till_e4.md
```

**Command:** `git status -u --porcelain` (full untracked enumeration)

### Modified (tracked, unstaged)

| Path | Notes |
|------|--------|
| `smoke_test_export.docx` | Binary export artifact; unrelated to deploy code |

### Untracked — editor / agent tooling (not deployed)

| Path |
|------|
| `.claude/hooks/isolation_veto.py` |
| `.claude/hooks/migration_parity_check.py` |
| `.claude/hooks/secret_scan.py` |
| `.claude/settings.json` |
| `.cursor/hooks.json` |
| `.cursor/hooks/isolation_veto.py` |
| `.cursor/hooks/me_module_hooks.py` |
| `.cursor/hooks/migration_parity_check.py` |
| `.cursor/hooks/secret_scan.py` |
| `.cursor/plans/m&e_module_orientation_1fd3437f.plan.md` |
| `.cursor/rules/00-global.mdc` |
| `.cursor/rules/10-isolation.mdc` |
| `.cursor/rules/20-backend.mdc` |
| `.cursor/rules/30-agents.mdc` |
| `.cursor/rules/40-scope-fence.mdc` |
| `CLAUDE.md` |

### Untracked — status / audit markdown (not deployed)

| Path |
|------|
| `BUILD_STATUS_2026-05-27.md` |
| `ME_MODULE_STATUS_REPORT.md` |
| `status_till_e4.md` |

### Untracked — `M_E_Module/` spec mirror (not application code)

| Path |
|------|
| `M_E_Module/ME_MODULE_ARCHITECTURE_SPEC.md` |
| `M_E_Module/ME_MODULE_INTERNAL_ARCHITECTURE.html` |
| `M_E_Module/ME_MODULE_MASTER_MEMORY.md` |
| `M_E_Module/ME_MODULE_ORIENTATION_REPORT.md` |
| `M_E_Module/ME_MODULE_PROJECT_PLAN.md` |
| `M_E_Module/ME_MODULE_WIREFRAMES_BRANDED.html` |
| `M_E_Module/NGOINFO_BRAND_GUIDELINES.md` |
| `M_E_Module/WORKSTREAM_T2_NLCF_FCDO_REFERENCE_TEMPLATES.md` |
| `M_E_Module/Sample_docs/FCDO_Test_Set/01_FCDO_BridgeLight_Winning_Proposal.docx` |
| `M_E_Module/Sample_docs/FCDO_Test_Set/02_FCDO_BridgeLight_Award_Letter.docx` |
| `M_E_Module/Sample_docs/FCDO_Test_Set/03_FCDO_BridgeLight_Logframe_Data_Table.docx` |
| `M_E_Module/Sample_docs/FCDO_Test_Set/04_FCDO_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx` |
| `M_E_Module/Sample_docs/NLCF_Test_Set/01_NLCF_Southbank_Application_Proposal.docx` |
| `M_E_Module/Sample_docs/NLCF_Test_Set/02_NLCF_Southbank_Award_Letter.docx` |
| `M_E_Module/Sample_docs/NLCF_Test_Set/03_NLCF_Southbank_Monitoring_and_Spend_Table.docx` |
| `M_E_Module/Sample_docs/NLCF_Test_Set/04_NLCF_Answer_Key_DO_NOT_INCLUDE_IN_DOCUMENTS.docx` |

### M&E **implementation** code — committed, not in working-tree delta

**Fact:** `git ls-files app/reports/` returns **53 paths** including agents, worker, docling adapter, models, storage service, gate routes, and services.  
**Fact:** `git ls-files alembic/versions/` includes `0014_me_module_tables.py` and `0015_donor_reports_gap_analysis_json.py`.

Unlike `BUILD_STATUS_2026-05-27.md`, **no M&E Python implementation exists only in the working tree today.** A destructive `git clean -fdx` would **not** remove `app/reports/` or M&E migrations from disk (they are committed).

**Would be lost on destructive clean (untracked only):** all `??` paths above plus uncommitted changes to `smoke_test_export.docx`.

**Grouped M&E items the 2026-05-27 audit listed as untracked — current state:**

| Component | 2026-05-27 | 2026-05-30 |
|-----------|------------|------------|
| Agents (`app/reports/agents/*.py`) | Untracked | **Committed** |
| Worker (`app/reports/worker/`) | Untracked | **Committed** |
| Docling adapter | Untracked | **Committed** (`app/reports/extraction/docling_adapter.py`) |
| Models | Untracked | **Committed** (`app/reports/models/`) |
| Storage service | Untracked | **Committed** (`document_storage_service.py`) |
| Migration 0014 | Untracked | **Committed** |
| Gates (HTTP) | Absent | **Committed** (`gate1.py`, `gate2.py`) |
| Tests | Present mixed | **Committed** under `tests/` (not re-enumerated here) |
| `M_E_Module/` specs/samples | Untracked | **Still untracked** (mirror only) |

---

## 2. Local vs origin

| Check | Command | Result |
|-------|---------|--------|
| Current branch | `git branch --show-current` | `main` |
| Local-only commits | `git log origin/main..HEAD --oneline` | **(empty)** |
| Origin-only commits | `git log HEAD..origin/main --oneline` | **(empty)** |
| E1 checkpoint `7c1a666` | `git merge-base --is-ancestor 7c1a666 origin/main` | **On `origin/main`** |
| | `git log -1 --oneline 7c1a666` | `7c1a666 E1 reconciler: Agent SDK→Messages API migration + corroboration + conflict-validity; gate 4/4 green on Sonnet (attempt_count=1, ~117s)` |

**Push gap (one sentence):** Local `main` and `origin/main` both point at **`f26e477`** — there is **no unpushed backend commit** as of this audit.

**Recent `origin/main` history (fact):**

```
f26e477 fix(deploy): disable mise Python GitHub attestation check for 3.11.8
87510f6 feat(fit-scan): plain-English GP-F02 output and bump prompt version to 1.1.0
3141bd5 fix(me-module): shorten 0015 alembic revision id to fit version_num(32)
ff1ee5c feat(me-module): Stage E2/E3/E4 + D1 Messages API migration
5ea7579 M&E checkpoint: Stage C infra + D1–D4 extractors + worker scaffold + storage + migration 0014
7c1a666 E1 reconciler: Agent SDK→Messages API migration + corroboration + conflict-validity
```

### Frontend (separate repo — informational)

Nested at `ngoinfo-grantpilot-frontend/` (excluded from backend git via `.git/info/exclude`; own remote `mycrivo/grantpilot-frontend`).

| Check | Result |
|-------|--------|
| `git status -sb` | `main...origin/main` — **in sync** |
| Fit Scan label commit | `7492f8e` on `origin/main` (pushed prior to this audit) |
| Uncommitted | Line-ending-only noise on proposal UI files (`proposal/[id]`, `proposal/new`, `SectionContent`, `SectionNav`) — **no diff content** in Fit Scan paths |

---

## 3. Migration state

**Directory:** `alembic/versions/` — **15 files**, all **tracked**.

| File | `revision` id | Length | `down_revision` |
|------|---------------|--------|-----------------|
| `0001_initial.py` | `0001_initial` | 12 | `None` |
| `0002_auth_tables.py` | `0002_auth_tables` | 15 | `0001_initial` |
| `0003_ngo_profiles.py` | `0003_ngo_profiles` | 16 | `0002_auth_tables` |
| `0004_funding_defaults.py` | `0004_funding_defaults` | 21 | `0003_ngo_profiles` |
| `0005_commercial_spine.py` | `0005_commercial_spine` | 20 | `0004_funding_defaults` |
| `0006_fit_scans.py` | `0006_fit_scans` | 13 | `0005_commercial_spine` |
| `0007_schema_alignment.py` | `0007_schema_alignment` | 20 | `0006_fit_scans` |
| `0008_oauth_exchange_codes.py` | `0008_oauth_exchange_codes` | 24 | `0007_schema_alignment` |
| `0009_stripe_events.py` | `0009_stripe_events` | 17 | `0008_oauth_exchange_codes` |
| `0010_email_canon_unique.py` | `0010_email_canon_unique` | 22 | `0009_stripe_events` |
| `0011_proposals.py` | `0011_proposals` | 14 | `0010_email_canon_unique` |
| `0012_email_events_login.py` | `0012_email_events_login` | 22 | `0011_proposals` |
| `0013_ngo_profiles_knowledge_bank.py` | `0013_ngo_profiles_knowledge_bank` | **32** | `0012_email_events_login` |
| `0014_me_module_tables.py` | `0014_me_module_tables` | 21 | `0013_ngo_profiles_knowledge_bank` |
| `0015_donor_reports_gap_analysis_json.py` | `0015_gap_analysis_json` | 22 | `0014_me_module_tables` |

**Latest head:** `0015_gap_analysis_json`  
**Chain:** linear `0001_initial` → … → `0014_me_module_tables` → `0015_gap_analysis_json`

**Migration 0014 (M&E tables):** **tracked and on `origin/main`** — not working-tree-only.

**Revision id length check (Railway `alembic_version.version_num` ≤ 32):** All **15** revision strings are **≤ 32 characters**. Longest is `0013_ngo_profiles_knowledge_bank` at **exactly 32**. `0015` was shortened in commit `3141bd5` (filename still descriptive; revision id is `0015_gap_analysis_json`).

**Release hook (fact):** `Procfile` line `release: alembic upgrade head` — a deploy runs migrations through head **`0015_gap_analysis_json`** if release phase executes successfully.

---

## 4. What a deploy of `origin/main` would ship

**Reasoning scope:** Committed code on `origin/main` at `f26e477` + `Procfile` process definitions. **Not** speculating about Railway service wiring beyond what the repo declares.

### Procfile (`Procfile`)

| Process | Command | Ships on deploy if Railway provisions it |
|---------|---------|------------------------------------------|
| `release` | `alembic upgrade head` | Runs once per deploy (if release phase enabled) |
| `web` | `bash scripts/start.sh` | Primary API |
| `worker` | `python -m app.reports.worker` | M&E background worker |

### Would ship (committed on `origin/main`)

- **GrantPilot core:** auth, billing, entitlements, NGO profile, fit-scans (**GP-F02 v1.1.0**), proposals, funding-opportunity read API.
- **Build fix:** `mise.toml` (`python.github_attestations = false`) for `runtime.txt` → `python-3.11.8`.
- **M&E module code (flag-gated):** full `app/reports/` tree — D1–D4 extractors, E1 reconciler, E3 gap agent, gate1/gate2 HTTP routes, docling adapter, S3 storage service, schemas/services, worker scaffold.
- **M&E DB migrations:** 0014 + 0015 (applied if release succeeds).

### Would **not** ship

- Untracked paths in §1 (`M_E_Module/` mirror, `.cursor/`, status markdown, etc.).
- Uncommitted `smoke_test_export.docx` changes.
- Frontend app (separate repo `grantpilot-frontend`; not in this git tree).

### `run_pipeline` — **stub** (fact)

`app/reports/worker/run_pipeline.py` docstring: *"Stage C no-op stub"*. It sets `ReportJob` to `RUNNING` then `DONE` without calling agents. **A deploy ships this stub**, not an orchestrated agent pipeline.

### `ME_MODULE_ENABLED` default (fact)

`app/core/config.py`: `ME_MODULE_ENABLED: bool = False`. **Default deploy behavior:** M&E router **not mounted** unless env sets `true`. Gate routes exist in code but are inactive when flag is off (`app/main.py` lines 214–217).

### Correction vs 2026-05-27

The 2026-05-27 report stated untracked M&E would **not** ship. **That is no longer true** — committed M&E **would** ship, but remains **runtime-disabled** by default and **non-functional end-to-end** while `run_pipeline` is a stub.

---

## 5. Runtime substrate per M&E agent file

Inspection: lazy imports inside agent run functions (`from anthropic import AsyncAnthropic` vs `from claude_agent_sdk import …`).

| File | Agent | Runtime API | vs 2026-05-27 finding |
|------|-------|-------------|------------------------|
| `app/reports/agents/classifier.py` | D1 document classifier | **Anthropic Messages API** (`AsyncAnthropic`) | **Corrected** — was Agent SDK on 2026-05-27; migrated in `ff1ee5c` |
| `app/reports/agents/proposal_extractor.py` | D2 proposal extractor | **Claude Agent SDK** (`claude_agent_sdk`) | Unchanged |
| `app/reports/agents/grant_terms_extractor.py` | D3 grant-terms extractor | **Claude Agent SDK** | Unchanged |
| `app/reports/agents/indicator_data_extractor.py` | D4 indicator/tabular extractor | **Claude Agent SDK** | Unchanged |
| `app/reports/agents/knowledge_bank_reconciler.py` | E1 reconciler | **Anthropic Messages API** (`AsyncAnthropic`) | Confirmed |
| `app/reports/agents/gap_compliance_agent.py` | E3 gap/compliance | **Anthropic Messages API** (`AsyncAnthropic`) | **New** since 2026-05-27 (agent absent then) |
| `app/reports/agents/claude_sdk_env.py` | (helper, not an agent) | Passes `ANTHROPIC_API_KEY` into SDK subprocess env | — |

**Summary correction:** **E1, E3, and D1** use **Messages API**; **D2–D4** use **Agent SDK**. The 2026-05-27 blanket “D1–D4 on Agent SDK” statement is **out of date**.

---

## 6. Env var inventory for deploy

**Sources:** `app/core/config.py` (`Settings` + `validate_config()`), `docs/artefacts/ENV_VARS_REFERENCE.md`.  
**Rule:** Names and default presence only — **no secret values**.

### Core / auth (required at startup — no safe default in `Settings`)

| Variable | Code default | Startup validated |
|----------|--------------|-------------------|
| `APP_ENV` | none | yes (must be dev/staging/prod) |
| `APP_NAME` | none | yes |
| `APP_BASE_URL` | none | yes |
| `CORS_ALLOWED_ORIGINS` | none | yes |
| `LOG_LEVEL` | none | yes |
| `DATABASE_URL` | none | yes |
| `AUTH_JWT_SIGNING_KEY` | none | yes |
| `AUTH_ACCESS_TOKEN_TTL_MIN` | none | yes (>0) |
| `AUTH_REFRESH_TOKEN_TTL_DAYS` | none | yes (>0) |
| `AUTH_MAGIC_LINK_TTL_MIN` | none | yes (>0) |
| `AUTH_RATE_LIMIT_ENABLED` | none | yes (bool field, no default) |
| `AUTH_ALLOWED_REDIRECT_URLS` | none | yes |
| `GOOGLE_OAUTH_CLIENT_ID` | none | yes |
| `GOOGLE_OAUTH_CLIENT_SECRET` | none | yes |
| `GOOGLE_OAUTH_REDIRECT_URI` | none | yes |

| Variable | Code default | Notes |
|----------|--------------|-------|
| `AUTH_POST_LOGIN_REDIRECT_URL` | `https://grantpilot.ngoinfo.org/auth/callback` | has default |
| `GOOGLE_OAUTH_SCOPES` | `None` | optional |

### Email (required at startup)

| Variable | Code default |
|----------|--------------|
| `EMAIL_PROVIDER` | none (must be `resend`) |
| `EMAIL_FROM_NAME` | none |
| `EMAIL_FROM_ADDRESS` | none |
| `EMAIL_API_KEY` | none |
| `EMAIL_BASE_URL` | `https://grantpilot.ngoinfo.org` |
| `EMAIL_SUPPRESS_SENDING` | `False` |

### OpenAI — proposal / fit-scan engine (required at startup)

| Variable | Code default |
|----------|--------------|
| `OPENAI_API_KEY` | none |
| `PROMPT_VERSION` | none |
| `OPENAI_MODEL_PRIMARY` | `gpt-5.4` |
| `OPENAI_MODEL_FALLBACK` | `gpt-5.4-mini` |

### Stripe (required at startup)

| Variable | Code default |
|----------|--------------|
| `STRIPE_MODE` | none (`test` or `live`) |
| `STRIPE_SECRET_KEY` | none |
| `STRIPE_WEBHOOK_SECRET` | none |
| `STRIPE_CHECKOUT_SUCCESS_URL` | none |
| `STRIPE_CHECKOUT_CANCEL_URL` | none |
| `STRIPE_PRICE_ID_GROWTH` | none |
| `STRIPE_PRICE_ID_IMPACT` | none |
| `STRIPE_PORTAL_RETURN_URL` | `None` (optional) |

### M&E — feature flag and storage

| Variable | Code default | When required |
|----------|--------------|---------------|
| `ME_MODULE_ENABLED` | `False` | always settable; `true` mounts `/api/reports*` |
| `ME_DOCUMENTS_S3_ENDPOINT` | `""` | **required non-empty if** `ME_MODULE_ENABLED=true` |
| `ME_DOCUMENTS_S3_ACCESS_KEY` | `""` | same |
| `ME_DOCUMENTS_S3_SECRET` | `""` | same |
| `ME_DOCUMENTS_S3_BUCKET` | `""` | same |

### Anthropic — M&E agents (runtime, not in `Settings`)

| Variable | In `validate_config()` | Code default | Notes |
|----------|------------------------|--------------|-------|
| `ANTHROPIC_API_KEY` | **no** | read via `os.getenv` in agents / `claude_sdk_env.py` | App **boots without it**; M&E agent calls fail at runtime if missing |

### M&E optional tuning (runtime defaults in agent code)

| Variable | Default if unset |
|----------|----------------|
| `ME_CLASSIFIER_MODEL` | `haiku` |
| `ME_CLASSIFIER_TIMEOUT_SECONDS` | `60` (classifier) / `90` (extractors) |
| `ME_RECONCILER_MODEL` | `claude-sonnet-4-6` |
| `ME_RECONCILER_TIMEOUT_SECONDS` | `180` |
| `ME_GAP_COMPLIANCE_MODEL` | falls back to `ME_RECONCILER_MODEL` then `claude-sonnet-4-6` |
| `ME_GAP_COMPLIANCE_TIMEOUT_SECONDS` | `180` |

### Test mode (conditional)

| Variable | Code default |
|----------|--------------|
| `TEST_MODE` | `False` |
| `TEST_MODE_SECRET` | `None` — **required ≥32 chars if** `TEST_MODE=true` |

### FIRECRAWL

**Fact:** No `FIRECRAWL_*` references under `app/` (repo search 2026-05-30). **Not present in deploy config.**

### Frontend (separate Railway service)

| Variable | Required per docs |
|----------|-------------------|
| `NEXT_PUBLIC_API_BASE_URL` | yes |

---

## 7. Railway-observable open questions

**Cannot verify from code.** Each item: **REQUIRES DASHBOARD CONFIRMATION** — what the human checks.

| # | Question | Human checks |
|---|----------|--------------|
| 1 | Is **`origin/main` (`f26e477`) actually deployed** on the backend service? | Railway → backend service → **Deployments** tab: latest deployment commit SHA matches `f26e477` (or newer); status **Success**. |
| 2 | Did the **`mise.toml` build fix** succeed? | Same deployment → **Build logs**: no `mise ERROR Failed to install core:python@3.11.8` / attestation errors. |
| 3 | Did **`release: alembic upgrade head`** apply **0015**? | Deploy logs for release phase; or Postgres → `SELECT version_num FROM alembic_version;` expects **`0015_gap_analysis_json`**. |
| 4 | Is the **worker process provisioned**? | Railway → service → **Processes**: `worker` exists; not scaled to 0 if M&E jobs expected. |
| 5 | Is worker **scaled > 0**? | Worker replica count / instance settings. |
| 6 | Are **`ME_DOCUMENTS_S3_*`** credentials set? | Variables tab — only relevant if `ME_MODULE_ENABLED=true`. |
| 7 | **`ME_MODULE_ENABLED` in production** | Variables tab — `true` or `false` (code default is `false`). |
| 8 | **`STRIPE_MODE`** test vs live | Variables → `STRIPE_MODE`; cross-check `STRIPE_SECRET_KEY` prefix (`sk_test_` vs `sk_live_`). |
| 9 | **`funding_opportunities` row count** | Postgres query or admin tooling — table non-empty for fit-scan/proposal flows. |
| 10 | **`ANTHROPIC_API_KEY` set** for M&E | Variables tab — required for agent execution; not validated at app boot. |
| 11 | **Docling system dependencies** in Railway build | Build logs after deploy: `docling>=2.0.0` install succeeds; no missing OS libs at runtime when extraction invoked. |
| 12 | **Frontend deploy** (`grantpilot-frontend` `7492f8e`) | Separate Railway service → deployment SHA; Fit Scan UI shows human labels not raw enums. |

---

## Deployment readiness

### In our control via git (backend)

| Status | Item |
|--------|------|
| **Done** | Backend `main` pushed to `origin/main` — no local-only commits. |
| **Done** | M&E implementation, migrations 0014/0015, Fit Scan 1.1.0, `mise.toml` fix are on origin. |
| **Optional** | Commit or discard `smoke_test_export.docx` local edit (does not block deploy). |
| **Optional** | Track or ignore `M_E_Module/` mirror separately from canonical `docs/artefacts/me_module/` (spec hygiene only). |
| **Not done (product)** | Replace `run_pipeline` stub with real orchestration before M&E is production-ready. |
| **Not done (product)** | Gate 3, synthesis, critic, docxtpl export, orchestrator (per `BUILD_STATUS_2026-05-27.md` stage map — still largely absent). |

### Requires Railway dashboard / ops (not git)

1. **Confirm deploy landed** — backend at `f26e477+`, build green, migrations at head.  
2. **Confirm env vars** — especially `DATABASE_URL`, auth, Stripe, OpenAI, email; plus `ANTHROPIC_API_KEY` if exercising M&E agents.  
3. **Set `ME_MODULE_ENABLED`** deliberately — default off; enabling requires all four `ME_DOCUMENTS_S3_*` vars.  
4. **Provision worker** if background M&E jobs are intended — code ships worker entrypoint but stub completes jobs without agent work.  
5. **Verify frontend service** separately (`grantpilot-frontend` repo).  
6. **Validate Docling** on first document upload in staging — OS dependency risk not provable from repo alone.

### Plain-language bottom line

**Git is caught up:** pushing again would not change what Railway *can* pull. Whether production **runs** that code depends on Railway having successfully built **`f26e477`** (after the Python/mise fix) and promoted it. **GrantPilot core** (fit-scan, proposals, billing) should deploy as usual when env is complete. **M&E** code is on the branch but is **off by default**, **worker is a stub**, and **needs dashboard secrets + worker scaling + Docling validation** before it is operationally real — even though the code and migrations are no longer “local only.”

---

*End of report. No files modified except this document.*
