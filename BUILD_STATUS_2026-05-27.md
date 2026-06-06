# BUILD STATUS REPORT — 2026-05-27

**Audit type:** Read-only point-in-time snapshot.  
**Repository:** `c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot`  
**Report path:** `BUILD_STATUS_2026-05-27.md` (repo root — filename specified in audit brief; `docs/` exists but this report uses the mandated root filename).  
**Evidence date:** Git and filesystem inspection on 2026-05-27 (commands run via `cmd /c` per audit environment note).

---

## TL;DR

| Area | Readiness (facts only) | Primary evidence |
|------|------------------------|----------------|
| **GrantPilot Core (revenue / J1–J2)** | **Partial** — backend billing, auth, fit-scan, and proposal APIs are implemented in this repo; funding-opportunity population and live Stripe mode are not verifiable from code alone; frontend app is not in this repository. | `app/api/routes/*`, `app/services/billing_service.py`, `docs/artefacts/ENV_VARS_REFERENCE.md` |
| **M&E module (Stages A–L)** | **Partial** — Stage D extractors + E1 reconciler exist in code (much untracked); E2–I largely absent; worker/report_jobs/storage scaffolding present but pipeline is a stub; no M&E business HTTP routes beyond health. | `app/reports/`, `alembic/versions/0014_me_module_tables.py`, `app/main.py`, `Procfile` |
| **E1 reconciler checkpoint** | **Present (committed slice)** — Messages API in `knowledge_bank_reconciler.py`; gate + graders present; live gate green state claimed by operator (not re-run in this audit). | `git show 7c1a666`, `scripts/knowledge_bank_reconciler_gate.py` |
| **Deployment / git** | **Local checkpoint only** — `main` ahead of `origin/main` by 1 commit; working tree dirty; Railway `web` + `worker` defined in `Procfile` but M&E worker pipeline not wired to agents. | `git status -sb`, `Procfile` |

---

## A. GrantPilot Core — acquire and bill a customer today?

### A.1 Stripe

| Question | Finding | Evidence |
|----------|---------|----------|
| Live vs test mode (config) | Mode is selected by required env var `STRIPE_MODE`, validated to `test` or `live` only. **Which mode is active in production is UNKNOWN** — depends on Railway/dashboard secrets, not committed values. | `app/core/config.py` (`STRIPE_MODE`, `_VALID_STRIPE_MODES`), `docs/artefacts/ENV_VARS_REFERENCE.md` §G |
| Secret key shape | Docs specify `STRIPE_SECRET_KEY` example `sk_test_...`; no `.env` committed. **Prefix of deployed key UNKNOWN.** | `docs/artefacts/ENV_VARS_REFERENCE.md` §G |
| Webhook wired? | **Yes (code).** `POST /api/billing/webhook` persists events and calls `handle_stripe_event`. OpenAPI/public path list includes webhook. | `app/api/routes/billing.py` (`billing_webhook`), `app/main.py` (path `/api/billing/webhook`) |
| Checkout / portal | **Yes (code).** `POST /api/billing/checkout`, `GET /api/billing/portal`. | `app/api/routes/billing.py` |
| Stripe SDK usage | `stripe` package in requirements; `billing_service` sets `stripe.api_key` from settings. | `requirements.txt`, `app/services/billing_service.py` |

### A.2 Funding opportunities

| Question | Finding | Evidence |
|----------|---------|----------|
| Schema / model | **Present.** Table `funding_opportunities` created in migration; SQLAlchemy model exists. | `alembic/versions/0001_initial.py`, `app/models/funding_opportunity.py` |
| Seed mechanism in repo | **No seed script or fixture JSON found** (search: `seed`, `INSERT INTO funding` under `alembic/`, `scripts/`). Migrations create empty tables only. | Repo search (2026-05-27) |
| Row count in DB | **UNKNOWN — requires human/dashboard confirmation** (no DB connection run in this audit). | — |
| HTTP API | `GET /api/funding-opportunities/{id}` (read single opportunity). | `app/api/routes/funding_opportunities.py` |

### A.3 J1 → J2 user journey (signup → fit scan → proposal)

**Backend endpoints present in this repo (confirmed by inspection):**

| Step | Endpoint / flow | Auth | Evidence |
|------|-----------------|------|----------|
| Signup / session | Google OAuth (`/api/auth/google/start`, callback), magic link (`/api/auth/magic-link/*`), token refresh | Yes | `app/api/routes/auth.py` |
| Fit scan (J1) | `POST /api/fit-scans` | Requires `get_current_user` | `app/api/routes/fit_scans.py`, `app/services/fit_scan_service.py` |
| Proposal (J2) | `POST /api/proposals`, pre-flight, regenerate, export | Requires auth on routes | `app/api/routes/proposals.py` |
| Entitlements | `GET /api/me/entitlements` | Yes | `app/api/routes/entitlements.py` |
| NGO profile | `GET/POST/PUT /api/ngo-profile` | Yes | `app/api/routes/ngo_profile.py` |

**Frontend routes in this repository:** **None found** (no `frontend/` tree; `docs/artefacts/ENV_VARS_REFERENCE.md` references separate Railway service `grantpilot-web` Next.js).

**End-to-end wiring (browser):** **UNKNOWN — requires human/dashboard confirmation** for deployed `grantpilot-web` routes (`/start`, `/login`, fit-scan UI, proposal UI). Spec defines journeys in `docs/artefacts/LAUNCH_JOURNEYS_SPEC.md` (J1–J7).

**Inferred gap (labeled inference):** Backend chain exists; full J1→J2 UX cannot be confirmed from this repo alone without the frontend service.

### A.4 WordPress → GrantPilot CTAs

| Finding | Evidence |
|---------|----------|
| **Spec only in this repo** — deep link `https://grantpilot.ngoinfo.org/start?opportunity_id={id}&source=wp`, JWT state token design. | `docs/artefacts/WORDPRESS_TO_GRANTPILOT_INTEGRATION.md` |
| **No WordPress theme/plugin code** in repository. | Repo layout |
| **Backend `/start` route** — not found under `app/` (only `/api/auth/google/start`). | `grep` in `app/` |
| **WP CTA live on ngoinfo.org** | **UNKNOWN — requires human/dashboard confirmation** |

---

## B. M&E module vs Stage A–L plan

**Module code locations (confirmed):**

- Primary implementation: `app/reports/` (agents, schemas, services, worker, models).
- Parallel spec copies (untracked): `M_E_Module/` (HTML/MD specs + sample `.docx`).
- Canonical specs (many tracked under `docs/artefacts/me_module/`).

**Feature flag:** `ME_MODULE_ENABLED` default `false`; when `true`, mounts `app.reports.router` only. | `app/core/config.py`, `app/main.py` lines 214–217 |

### Stage map (present / partial / absent)

| Plan item | Status | Evidence |
|-----------|--------|----------|
| **D1 Classifier** | **Present** (untracked in working tree) | `app/reports/agents/classifier.py`, `scripts/live_classifier_run.py`, `tests/test_classifier_agent.py` |
| **D2 Proposal extractor** | **Present** (untracked) | `app/reports/agents/proposal_extractor.py`, gates/tests under `tests/fixtures/proposal_extractor/` |
| **D3 Grant-terms extractor** | **Present** (untracked) | `app/reports/agents/grant_terms_extractor.py` |
| **D4 Tabular/indicator extractor** | **Present** (untracked) | `app/reports/agents/indicator_data_extractor.py`, `app/reports/extraction/spreadsheet_input.py` |
| **D5 Vision agent** | **Absent** | No `vision` agent file under `app/reports/agents/` (glob: 7 agent files only) |
| **E1 Knowledge-bank reconciler** | **Present** (committed in `7c1a666`) | `app/reports/agents/knowledge_bank_reconciler.py`, `scripts/knowledge_bank_reconciler_gate.py`, `tests/reconciliation_grading.py` |
| **E2 Gate 1 (server-enforced)** | **Absent** | No gate-1 API; `knowledge_bank_reconciliation_service.py` states it does not set `gate1_confirmed_at` |
| **E3 Gap/compliance agent** | **Absent** | No agent module in `app/reports/agents/` |
| **E4 Gate 2** | **Absent** | No route/service found |
| **F1 Synthesis agents** | **Absent** (M&E) | No `app/reports` synthesis agent; core proposal generation uses OpenAI in `app/ai/` (separate product) |
| **F2 Fact-safety critic** | **Absent** | — |
| **F3 Gate 3** | **Absent** | — |
| **G1 Orchestrator + gate hooks** | **Absent** | No orchestrator agent; `run_pipeline` is explicit stub | `app/reports/worker/run_pipeline.py` |
| **H1 docxtpl export (M&E reports)** | **Absent** | No docxtpl usage under `app/reports/` |
| **H2 Funder .docx templates** | **Partial (assets only)** | Sample `.docx` in `M_E_Module/Sample_docs/`; template JSON in `docs/artefacts/me_module/TEMPLATE_INSTANCE_*.json` |
| **I1 Eight frontend screens** | **Absent in this repo** | Spec/wireframes in `docs/artefacts/me_module/ME_MODULE_WIREFRAMES_BRANDED.html`; no M&E UI code here |

**Stage C infrastructure (partial):**

| Component | Status | Evidence |
|-----------|--------|----------|
| DB tables migration | **Present** (untracked migration file) | `alembic/versions/0014_me_module_tables.py` (`donor_reports`, `uploaded_documents`, `report_jobs`, `funder_report_templates`, …) |
| `report_jobs` model | **Present** (untracked) | `app/reports/models/report_job.py`, enums include stages `classify`, `extract`, `reconcile`, `gap`, `synthesise`, `critique`, `export` | `app/reports/models/enums.py` |
| Object storage | **Present** (untracked service) | `app/reports/services/document_storage_service.py` (boto3 S3-compatible; requires `ME_DOCUMENTS_S3_*`) |
| Worker process | **Present** (config + stub logic) | `Procfile` `worker: python -m app.reports.worker`, `app/reports/worker/job_runner.py`, `run_pipeline.py` stub marks jobs DONE without calling agents |
| Docling adapter | **Present** (untracked) | `app/reports/extraction/docling_adapter.py`, `docling_content_guard.py` |

### M&E HTTP routes

| Route | Behavior | Evidence |
|-------|----------|----------|
| `GET /api/reports/health` | Returns `{"status":"ok","module":"reports"}` when `ME_MODULE_ENABLED=true` | `app/reports/api/routes/health.py`, `app/reports/router.py` |

**No other M&E report/donor-report/reconcile/upload routes found** under `app/reports/api/`.

**`reconcile_and_persist`:** Service exists; **not referenced from any HTTP route** in `app/` (grep 2026-05-27). Invocation today: tests, gate script (`reconcile_from_fixture`), potential future worker — **not sync HTTP**.

**Sync vs async (confirmed):** No M&E agent is invoked inside a FastAPI request handler except the health check. Extractors/reconciler are async Python functions called from scripts/tests/services; background path is **intended** via `report_jobs` + worker but **pipeline stub only**.

---

## C. Knowledge-bank reconciler (E1) — verified from code

| Question | Finding | Evidence |
|----------|---------|----------|
| Model invocation | **Direct Anthropic Messages API** — `AsyncAnthropic.messages.create`, `temperature=0`, no `claude_agent_sdk` import in this file. | `app/reports/agents/knowledge_bank_reconciler.py` (`_call_anthropic_messages`, `from anthropic import AsyncAnthropic`) |
| Default model id | `ME_RECONCILER_MODEL` default `claude-sonnet-4-6` in code. | Same file (`DEFAULT_MODEL`) |
| Env doc drift | `ENV_VARS_REFERENCE.md` still documents default `opus` for `ME_RECONCILER_MODEL`. | `docs/artefacts/ENV_VARS_REFERENCE.md` §J (not edited in this audit) |
| Standalone gate script | **Present** (committed) | `scripts/knowledge_bank_reconciler_gate.py` |
| Graders | **Present** — case1–4 + `assert_no_spurious_conflicts` + global checks | `tests/reconciliation_grading.py` |
| Vestigial CLI check | **Yes** — `_require_claude_cli()` requires `claude` on PATH; docstring still mentions CLI. | `scripts/knowledge_bank_reconciler_gate.py` lines 11–12, 69–72, 291–292 |
| Gate pass criteria (current) | Invariant grading on every run; byte fingerprint observability only (D-041). | Gate script docstring + `STABILITY_POLICY`; `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` D-041 |
| Committed green artefacts | Recorded KB + wall times + drift-debug payloads in commit `7c1a666`. | `git show 7c1a666` file list, `tests/fixtures/reconciler/recorded/` |

**Operator-reported live gate (not re-executed in this audit):** 4/4 invariant pass, `attempt_count=1`, wall ~113–119s on Sonnet — **confirmed only by user statement; UNKNOWN in this audit run** (no API key execution).

---

## D. Agent-layer substrate — post–Agent SDK

### What the code runs on (by agent)

| Agent | Runtime pattern | Evidence |
|-------|-----------------|----------|
| `knowledge_bank_reconciler` | **Anthropic Python SDK** (`anthropic>=0.42.0`) | `app/reports/agents/knowledge_bank_reconciler.py`, `requirements.txt` |
| `classifier` | **Claude Agent SDK** (`claude_agent_sdk.query`, `ClaudeAgentOptions`, `ResultMessage`) | `app/reports/agents/classifier.py` |
| `proposal_extractor` | **Claude Agent SDK** | `app/reports/agents/proposal_extractor.py` |
| `grant_terms_extractor` | **Claude Agent SDK** | `app/reports/agents/grant_terms_extractor.py` |
| `indicator_data_extractor` | **Claude Agent SDK** | `app/reports/agents/indicator_data_extractor.py` |
| Subprocess env helper | `merge_claude_subprocess_env` for SDK agents | `app/reports/agents/claude_sdk_env.py` (untracked) |

**Consistency:** **Partial only** — E1 migrated to Messages API; D-stage extractors still use Agent SDK CLI subprocess pattern.

**Core GrantPilot proposal engine (non–M&E):** OpenAI Chat Completions via `app/integrations/openai_client.py` / `app/ai/` — separate from M&E agent layer.

### Spec ↔ code drift (Agent SDK references in specs — record only)

| Document | Drift summary | Evidence |
|----------|---------------|----------|
| `docs/artefacts/me_module/ME_MODULE_ARCHITECTURE_SPEC.md` | States Layer 2 = Claude Agent SDK for all agents, hooks = gates | §B3, technology table |
| `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md` | Same Agent SDK roster/runtime | §7.2–7.3 |
| `docs/artefacts/me_module/ME_MODULE_PROJECT_PLAN.md` | D1/G1 "BUILD on REUSE Agent SDK" | Stage D, G tables |
| `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` | D-009, D-028, D-029 lock Agent SDK; D-040 still mentions `opus`/SDK-style reconciler | Decision rows |
| `docs/artefacts/ENV_VARS_REFERENCE.md` | §J describes reconciler via Agent SDK subprocess | §J `ANTHROPIC_API_KEY` note |
| `M_E_Module/ME_MODULE_*.md/html` | Duplicate copies of same SDK-centric narrative | Untracked `M_E_Module/` |
| `docs/artefacts/me_module/ME_MODULE_WIREFRAMES_BRANDED.html` | UI copy: "Claude Agent SDK" runtime | HTML line ~529 (grep) |

**Code-aligned spec updates:** D-041, D-042, D-043 in `ME_MODULE_DECISION_LOG.md` partially reflect gate/reconciler evolution; architecture/master docs not updated in committed tree.

---

## E. Deployment state

### E.1 Git (2026-05-27, `cmd /c git …`)

| Item | Value |
|------|--------|
| Branch | `main` |
| Latest commit | `7c1a666` — `E1 reconciler: Agent SDK→Messages API migration + corroboration + conflict-validity; gate 4/4 green on Sonnet (attempt_count=1, ~117s)` |
| Remote | `origin` → `https://github.com/mycrivo/ngoinfo-grantpilot.git` |
| vs `origin/main` | **Ahead by 1 commit** (E1 checkpoint); **not pushed** per operator workflow |
| Working tree | **Dirty** — modified: `Procfile`, `alembic/env.py`, `app/core/config.py`, `app/main.py`, several `docs/artefacts/*`, `smoke_test_export.docx`; large untracked M&E tree (D1–D4 agents, worker, migration `0014`, gates, tests, `M_E_Module/`, `.cursor/`, `.claude/`, etc.) |

### E.2 Railway / worker configuration in repo

| Item | Finding | Evidence |
|------|---------|----------|
| Release phase | `alembic upgrade head` | `Procfile` line `release:` |
| Web service | `uvicorn app.main:app` via `scripts/start.sh` | `Procfile` `web:`, `scripts/start.sh` |
| Worker service | **Defined:** `worker: python -m app.reports.worker` | `Procfile` |
| Worker behavior | Polls `report_jobs` QUEUED; calls `run_pipeline` **stub** (no agent dispatch) | `app/reports/worker/job_runner.py`, `run_pipeline.py` |
| M&E local-only? | **No — config exists for Railway dual process**, but most M&E code is **uncommitted**; only E1 slice is in `7c1a666`. | Git status + `Procfile` |

**Production deploy state (Railway build, env vars, worker scaled):** **UNKNOWN — requires human/dashboard confirmation.**

---

## OPEN QUESTIONS — requires human confirmation

1. **Stripe live vs test in production** — `STRIPE_MODE` and `STRIPE_SECRET_KEY` values on Railway (dashboard only).
2. **Stripe account activation** (live payments enabled, webhook endpoint registered and delivering).
3. **`funding_opportunities` row count** and how opportunities are loaded (CMS, manual SQL, external ETL — not defined in repo).
4. **Frontend (`grantpilot-web`) routes** for J1 `/start`, login, fit-scan, proposal — separate service not in this repo.
5. **WordPress CTAs** live on NGOInfo.org pointing to GrantPilot deep links.
6. **Whether `7c1a666` and/or unstaged M&E work has been pushed** to GitHub / deployed to Railway (git shows local ahead 1; deploy UNKNOWN).
7. **Railway worker process** — provisioned, scaled, bucket credentials set (`ME_DOCUMENTS_S3_*`).
8. **E1 live gate re-run** on current dirty tree (operator reported green; not re-run in audit).
9. **Production `ME_MODULE_ENABLED`** and whether `/api/reports/health` is exposed.
10. **Anthropic billing / model availability** for Sonnet reconciler in deployed environment.

---

*End of report. No repository files were modified except this document.*
