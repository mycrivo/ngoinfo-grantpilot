# M&E Module — Done vs Planned Status Report

**Audience:** CTO review  
**Date:** 2026-05-25  
**Module:** GrantPilot Donor Report Writer (Impact Pro tier)  
**Plan reference:** `docs/artefacts/me_module/ME_MODULE_PROJECT_PLAN.md` (Stages A→L)  
**Decision log:** `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` (D-001 through D-030)

---

## Executive summary

| Metric | Value |
|--------|--------|
| **Overall build progress** | **~25%** of product stages (A–C complete; D partially complete; E–K not started; L post-launch) |
| **Current position** | **Stage D in progress** — classifier built and validated; extractors, upload flow, and pipeline wiring not started |
| **Revenue engine (core GrantPilot)** | **Protected** — 22/22 E2E smoke green against **production**; M&E module dormant (`ME_MODULE_ENABLED=false`) |
| **Kill switch** | **Proven** on empty module (Stage C exit gate) |
| **Launch readiness** | **Not ready** — no end-to-end report journey, no orchestrator, no export, no billing tier live |

The build is on plan through Stage C and is executing Stage D with the correct discipline: spec-first, isolation-first, one agent at a time, validate before wiring.

---

## Stage scorecard (planned vs done)

| Stage | Planned scope | Status | Exit gate |
|-------|---------------|--------|-----------|
| **A** — Governance & isolation | Rules, repo map, kill switch, decision log seed, wireframes/spec drop | **COMPLETE** | Isolation coherent across rules + kill-switch doc |
| **B** — Spec lock | Field contracts, funder schema v1.1.0, NLCF/FCDO instances, API §12, ENUM_REGISTRY | **COMPLETE** | B-validation passed (D-024); templates fit schema |
| **C** — Foundations | `app/reports/` skeleton, migration 0014, storage, worker stub, Docling adapter, kill-switch rehearsal | **COMPLETE** | Three kill switches rehearsed (D-026) |
| **D** — Extraction agents | Classifier + 4 extractors + vision; each isolated-tested | **IN PROGRESS (~20%)** | Classifier only — see D detail below |
| **E** — Reconciler + gaps + Gates 1–2 | Reconciler, gap agent, server-enforced gates | **NOT STARTED** | — |
| **F** — Synthesis + critic + Gate 3 | Section writers, fact-safety critic, quality gate | **NOT STARTED** | Funder-grade on hand-confirmed data |
| **G** — Orchestrator | Pipeline coordinator + trace logging | **NOT STARTED** | All agents proven first |
| **H** — Export | docxtpl engine + 10 funder Word templates | **NOT STARTED** | — |
| **I** — Frontend | 8-screen journey (separate repo) | **NOT STARTED** | Behind feature flag |
| **J** — Billing | Impact Pro $99/mo, quotas, Stripe | **NOT STARTED** | O-004 open |
| **K** — Launch readiness | M&E smoke, J1→J2 on 3 templates, kill-switch re-proven | **NOT STARTED** | Launch gate |
| **L** — Post-launch | n8n ingestion, extraction tuning, templates 11+ | **NOT STARTED** | Post-revenue |

**Parallel workstream T (template sourcing):** T2 (NLCF + FCDO dossiers) **done** for schema stress test; T1 grantee outreach and T3/T5 remaining templates **ongoing / not complete**.

---

## Stage D detail (current work)

| Step | Planned deliverable | Status | Evidence |
|------|---------------------|--------|----------|
| **D1** Document classifier | Bounded agent on Claude Agent SDK; text-types-only contract | **DONE** | `app/reports/agents/classifier.py`; D-028, D-030 |
| **D2** Proposal extractor | — | **NOT STARTED** | — |
| **D3** Grant-terms extractor | — | **NOT STARTED** | — |
| **D4** Tabular/indicator extractor | — | **NOT STARTED** | — |
| **D5** Vision agent | Cheap multimodal API (vendor TBD O-001) | **NOT STARTED** | — |
| Upload / storage endpoint | Wire Docling + S3 intake | **NOT STARTED** | Storage service exists; no upload API |
| `run_pipeline` wiring | Orchestrated classify→extract | **NOT STARTED** | Worker stub only (`run_pipeline` no-op) |

### Classifier validation summary (D1 exit criteria)

| Check | Result |
|-------|--------|
| Unit tests (mocked SDK path) | **12/12 pass** |
| Live local run (4 fixtures, real SDK) | **PASS** — all four labels correct; `max_turns=2` required (D-030) |
| Live Railway worker run (2b) | **DEFERRED** — not yet executed |
| Migration-parity + isolation-veto hooks | **GREEN** |
| Env governance (`ANTHROPIC_API_KEY`, `ME_CLASSIFIER_MODEL`) | **Registered** in `ENV_VARS_REFERENCE.md` §J |

### Classifier contract updates (locked)

- **Text-types only:** `proposal | grant_letter | mou | indicator_data | other`
- **Upstream routing:** `photo` / `deck` by mime-type at upload (not classifier)
- **Over-large input:** truncate-then-classify (not reject)
- **Uniform SDK:** all Claude-reasoning agents on `claude-agent-sdk` at launch (CTO decision; synthesis stays gpt-5.4, vision stays multimodal API)

---

## Core platform & dependency baseline (cross-cutting)

| Item | Status | Notes |
|------|--------|-------|
| **claude-agent-sdk in requirements.txt** | **Installed** | `fastapi>=0.115`, `uvicorn>=0.30`, `httpx>=0.27` (D-029) |
| **22/22 core smoke (production)** | **PASS** | Validated production API contract; not the bumped local server process |
| **22/22 smoke (local bumped server)** | **BLOCKED** | **4/22** — no local PostgreSQL; boot on bumped stack OK; DB routes return 500 |
| **Deploy bumped stack to Railway** | **NOT DONE** | Production may still run pre-bump FastAPI until next deploy |
| **Four fragile core pytest tests** | **Still failing** | Stale mocks/tests — pre-existing, not dependency-related |

**CTO implication:** D-029 ratifies installability and production contract stability. A **deploy** plus optional **local Postgres smoke** are still needed to prove the bumped stack **as the serving process**.

---

## What exists in the repo today

### Built (M&E)

- `app/reports/` package: router, health, 4 SQLAlchemy models, migration `0014_me_module_tables.py`
- `document_storage_service.py` (Railway Buckets / `ME_DOCUMENTS_S3_*`)
- `docling_adapter.py` (standalone; not wired to upload flow)
- `worker/` stub (`run_pipeline` no-op)
- `agents/classifier.py` + tests + `scripts/live_classifier_run.py`
- Governance: `.cursor/rules/`, hooks (isolation veto, migration parity, secret scan), `CLAUDE.md` agent layer

### Not built (M&E)

- Extractors D2–D5, reconciler, gap, critic, orchestrator
- Upload API, report CRUD API (beyond health), gates, synthesis, export
- Frontend screens, Impact Pro billing, M&E-specific smoke tracks

---

## Locked CTO decisions (since build start)

| ID | Decision | Impact |
|----|----------|--------|
| D-009 / uniform SDK | All Claude-reasoning agents use `claude-agent-sdk` | No second Anthropic direct path for cheap agents |
| D-025 | `ME_DOCUMENTS_S3_*` env prefix | Module-scoped storage kill switch |
| D-029 | FastAPI/uvicorn/httpx bump for SDK | Core smoke green on production; local serving stack TBD |
| D-030 | Classifier `max_turns=2` | Structured JSON needs second turn; monitor extractors |

---

## Open items & blockers

| ID / topic | Severity | Owner action |
|------------|----------|--------------|
| **Local Postgres for bump validation** | Medium | Stand up dev DB + `alembic upgrade head` + re-run smoke with `BASE_URL=http://127.0.0.1:8000` |
| **Deploy bumped requirements to Railway** | Medium | Align serving process with D-029 assumptions |
| **Railway worker live classifier (2b)** | Medium | Ratify SDK subprocess on worker before extractors |
| **O-001 Vision API vendor** | Low (blocks D5) | Pick vendor before vision agent |
| **O-004 Stripe Impact Pro price** | Low (blocks J) | `STRIPE_PRICE_ID_IMPACT_PRO` |
| **Upload endpoint** | High (blocks real D testing) | Next infrastructure step after D1 closure |
| **Workstream T grantee reports** | Medium | Long-lead; feeds template quality for H2 |

---

## Recommended next steps (sequenced)

1. **Close D governance** — CTO review of this report; confirm D1 complete.
2. **Deploy bumped core stack** to Railway (no M&E flag on) — re-run 22/22 smoke post-deploy.
3. **Optional:** Local Postgres + full 22/22 against `127.0.0.1` on bumped venv.
4. **Railway worker live classifier** — one fixture, confirm SDK subprocess.
5. **D2 proposal extractor** — same pattern as classifier (isolated harness, live run, decision-log if bounds change).
6. **Upload endpoint** — mime-type routing (photo/deck upstream); then wire Docling + classifier.

---

## Risk register (concise)

| Risk | Mitigation in place |
|------|---------------------|
| M&E breaks core proposal product | One-way imports, single mount seam, kill switch proven, module off by default |
| Contract drift | Stage B lock + migration parity hook |
| Agent runaway / injection | Level 2 gates, bounded tools, injection fence, `max_turns` caps |
| SDK dependency fragility | D-029; tripwire: revert to smaller SDK footprint if conflicts recur |
| False confidence from smoke | Production smoke ≠ bumped server — track deploy + local DB smoke separately |

---

## Appendix — Decision log entries (M&E build)

| ID | Date | Summary |
|----|------|---------|
| D-021–D-024 | 2026-05-24 | Stage B structure + NLCF/FCDO validation |
| D-025–D-026 | 2026-05-24 | Storage env vars + Stage C complete |
| D-027 | 2026-05-24 | CLAUDE.md agent governance |
| D-028 | 2026-05-24 | Classifier agent (D1) |
| D-029 | 2026-05-25 | Dependency baseline + production smoke |
| D-030 | 2026-05-25 | Classifier max_turns 1→2 |

---

*Report generated from repo state and `ME_MODULE_DECISION_LOG.md`. For drill-down: `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md`, `ME_MODULE_PROJECT_PLAN.md`.*
