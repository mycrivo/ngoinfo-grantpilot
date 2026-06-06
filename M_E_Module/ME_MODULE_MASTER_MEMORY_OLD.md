# GrantPilot M&E Module — Master Memory Document

> **Purpose of this file.** A single, self-contained source of truth for the GrantPilot M&E (Donor Report Writer) module. It exists so the project can be re-initiated in a fresh chat without losing context, and so it can be uploaded to Cursor as build context. If you are an AI reading this in a new session: this document supersedes any partial memory; treat it as authoritative. Everything below is **decided and locked** unless explicitly marked OPEN.
>
> **Last consolidated:** 2026-05-31 · **Module status:** Stages A–E **built and deployed to production**; orchestrator spine **built and proven end-to-end on real FCDO data through the Gate 1 halt**. Next work: E3 (gap/compliance) → Gate 2. See §18 for precise current state.
>
> **⚠ Runtime reality note for any AI reading this:** the agent runtime is **MIXED**, not uniformly Claude Agent SDK. D1 classifier, E1 reconciler, and E3 gap-agent run on the **direct Anthropic Messages API**; D2/D3/D4 extractors run on the **Claude Agent SDK** (subprocess). The orchestrator is **plain Python dispatch logic, not an LLM agent**. Gates are **orchestrator state-machine halts** (`report_jobs.status=awaiting_human` + a stage cursor + re-enqueue on human confirm), **not** "Agent SDK hooks." The **Claude Code build path is retired** — **Cursor builds everything**; `.cursor/hooks/` are the live enforcement layer, the old `.claude/hooks/` + `CLAUDE.md` are vestigial. Where older sections below still say otherwise, this note and §7/§8/§18 are authoritative.

---

## 0. HOW TO USE THIS FILE

- **Re-initiating a chat:** paste or attach this file and say "continue the M&E build from the project memory file." The assistant should resume at the current state (see §18): Stages A–E built and deployed, orchestrator spine proven to the Gate 1 halt, next work is E3 → Gate 2.
- **Working rhythm:** Claude (strategy/specs/prompts/review) → Pranab (decides, runs prompts, reports back) → **Cursor (executes — sole code-writing tool; the Claude Code build path is retired)** → repeat. One outcome-driven prompt at a time.
- **Cardinal principle:** spec → code, never code → retroactive spec. This file and the contract docs are truth; code obeys them.
- **The hard-won lesson:** a prior project (ReqAgent) broke during updates due to no guardrails and weak specs. Every discipline here exists to prevent that: spec-first, staged pipelines, isolation, deterministic enforcement, human gates.

---

## 1. WHO & WHY

**Founder:** Pranab — Principal Director, Data & AI at Accenture (EMEA); solo founder of GrantPilot + NGOInfo, lean budget, building part-time. Builds on a **personal Windows laptop** (no corporate execution-policy restrictions).

**Products:**
- **GrantPilot** (grantpilot.ngoinfo.org) — AI grant-proposal generation for NGOs. Live/production.
- **NGOInfo** (ngoinfo.org) — WordPress content/marketing site; discovery layer. On Hostinger.

**Target users:** US international-development NGOs, Indian grassroots organisations, UK charities.

**Existing GrantPilot pricing:** Free (1 fit scan, 1 proposal lifetime), Growth ($39/mo), Impact ($79/mo).
> *Note: the live Free tier pricing card has a duplicate "1 proposal draft (lifetime)" line — fix when convenient.*

**Working model with Claude:** Claude acts as strategic CTO/CMO co-founder — strategy, specs, and outcome-driven prompts; never pseudocode or implementation-heavy instructions. Claude specifies *what*; **Cursor writes *how*** (Cursor is the sole code-writing tool; the Claude Code build path is retired). (The one exception: hook scripts, where the script *is* the spec.)

---

## 2. THE M&E MODULE IN ONE PARAGRAPH

A post-award reporting product. A charity that has won a grant — through GrantPilot or anywhere else — uploads the messy reality they already have (winning proposal, funder grant letter/MoU, indicator spreadsheet, activity photos, a deck). A team of bounded AI agents reads and organises that material, reconciles it into a single human-confirmed picture of the project, checks it against the specific funder's reporting requirements, asks only for what's genuinely missing, then writes a funder-ready narrative report and exports it as a formatted Word document. The human confirms facts at every gate; agents do the labour, not the judgement.

**North Star / positioning:** *"GrantPilot helps you win the grant. Then it helps you keep the funder."*

---

## 3. WHY IT EXISTS (validated market pain)

- UK charities spend an estimated **15.8M hours/year** on grant monitoring reports (~£204M staff time); average report ~**40 hours**.
- A mid-size NGO runs several grants → **8–20 funder reports/year**, each in a different format.
- Reporting staff are rarely trained M&E professionals — programme staff with reporting bolted on. **79%** cite restricted staff time as the main M&E barrier; only **8%** have dedicated M&E staff.
- **The gap:** every existing tool stops at dashboards (DevResults, DHIS2, TolaData, ActivityInfo) or generic insight (Sopact). **Nobody writes the funder-formatted narrative report.** That is the blue ocean.
- **Competitive vacuum, UK specifically:** existing UK tools (Plinth, Lamplight, Upshot, Makerble) are CRMs/case-management with reporting bolted on. Plinth's "Pippin" generates impact reports but is locked inside a full platform. eSuivi describes the exact model (one data source → funder-specific templates) but isn't dominant. No standalone, affordable, funder-aware AI donor-report writer exists.

---

## 4. STRATEGY & GO-TO-MARKET (decided)

- **New paid tier**, not a feature bolt-on. Serves a customer whose immediate need is **not** proposal writing.
- **Acquisition wedge:** the report is the cheaper, more urgent, more frequent entry product. NGOs who won *elsewhere* arrive in deadline pain, hand over their full org profile + funder relationship + indicators, and become natural pre-award (proposal) customers next cycle. The landing message: *"Won a grant — with us or anyone — and dreading the report? Upload what you've got."*
- **GTM sequencing:**
  1. **UK + selected EU bilateral donors first** (Months 1–6). The US pre-award market is saturated (Instrumentl, Grantable, etc.); UK/EU post-award is underserved.
  2. **India second** (Months 4–8), leveraging the CSR-mandate compliance market (~$3.2B/yr deployed).
  3. **US last** (Months 8–12), entering as the *post-award specialist*, not another grant-writer.
- **NGOInfo v2** launches **after** the M&E module — stronger complete-lifecycle narrative; v2 content targets post-award search intent (reporting guides, indicator frameworks) as a new organic channel.
- **Why UK-first (CMO rationale):** US pre-award is a bloodbath; UK/EU buyers feel underserved by US-centric tools; UK's ~207K charities is a dominable market where content marketing on NGOInfo can cut through; $39–99/mo pricing is well-positioned vs UK incumbents.

---

## 5. TIER & PRICING (LOCKED)

- **New third tier: "Impact Pro" — $99/mo.** Everything in Impact **plus 2 M&E reports/month**.
- **Long-run intent:** consolidate to two paid plans (retire or reprice the $79 Impact tier) a couple of months post-launch, based on market acceptance.
- **Name rationale:** "Impact Pro" reads as the natural step above "Impact," implies "everything in Impact plus more," and collapses cleanly into a two-tier ladder later. Marketing positioning line carries the story ("win the grant, keep the funder").
- **Cost ceiling:** per-report model cost must stay well inside per-report revenue (~$49.50 at 2 reports/mo) with margin. `agent_trace_json` provides per-run cost accounting.

---

## 6. SCOPE

### In scope (launch)
Document upload + agentic extraction; knowledge-bank reconciliation with human confirmation; funder-aware gap check; narrative generation; fact-safety critic; funder-formatted DOCX export; **10 report templates** (8 funder-specific + 2 generic fallbacks); the Impact Pro billing tier.

### The 10 launch templates
| # | Template | Region |
|---|----------|--------|
| 1 | NLCF End-of-Grant Report | UK |
| 2 | NLCF Annual Progress Update | UK |
| 3 | FCDO Annual Review | UK |
| 4 | Comic Relief End-of-Grant Report | UK |
| 5 | USAID Quarterly Performance Report | US |
| 6 | USAID Annual Performance Report | US |
| 7 | ECHO Single Form — Interim | EU |
| 8 | ECHO Single Form — Final | EU |
| 9 | Generic Institutional Donor Report | Universal fallback |
| 10 | Generic CSR Project Report | India fallback |

### Non-goals (STOP-and-flag if a build prompt drifts here)
Field data **collection** (KoboToolbox/ODK do this free — we ingest, not collect); dashboards/visualisation; full logframe/ToC management as a live system; real-time monitoring; multi-user approval workflows; **autonomous agent action without human gates** (Level 3); Railway per-session sandboxes (in-app job queue is the launch execution model); building any document parser, agent framework, or Word engine from scratch (all reused).

---

## 7. ARCHITECTURE

### 7.1 Stance
- **Level 2 agentic with human-in-the-loop gates.** Bounded specialist agents coordinated by an orchestrator; agents reason, call tools, hand off — but every fact entering the report is human-confirmed. **Not Level 3** (open-ended autonomy): in a compliance product, an unsupervised agent inventing a beneficiary number is a funding-clawback event.
- **Reuse the proposal stack (~70%).** Report service mirrors `proposal_service`; input adapter mirrors `build_prompt_inputs`; section synthesis reuses archetypes + humaniser; billing/auth/quota inherited.
- **Backend is the single source of truth.** All reasoning, entitlements, AI live server-side. Frontend renders + calls the API.
- **Reuse the plumbing, build the brain.** 4 of 5 layers are assembled from existing packages; only Layer 3 (the domain brain) is built from scratch — that's the moat.

### 7.2 The five layers
```
L5 Connectors/ingestion ...... n8n (template ingestion, optional Drive/Gmail pull)        REUSE (deferred, post-revenue)
L4 Assembly & export ......... docxtpl + funder .docx templates                           REUSE engine / BUILD templates (Stage H, not started)
L3 M&E DOMAIN BRAIN .......... Orchestrator (BUILT, plain Python) · Reconciler · Gap/      BUILT (the moat)
                               compliance · Synthesis (pending) · Fact-safety critic
                               (pending) · funder template logic
L2 Agent runtime ............. MIXED — direct Anthropic Messages API (D1/E1/E3) +          REUSE / BUILT agents
                               Claude Agent SDK subprocess (D2/D3/D4). NOT uniformly SDK.
L1 Document extraction ....... Docling: PDF/DOCX/XLSX/PPTX/images → clean structured text  REUSE
   Execution model: in-app background job queue (Railway worker) + object storage (Railway Buckets),
   behind a real run_pipeline() → orchestrated walk. (NOT Railway sandboxes, NOT Agent-SDK hooks.)
```

> **Runtime correction vs original design:** the original plan assumed all agents would run on the Claude Agent SDK. Reality (and the decision log) is **mixed**: D1/E1/E3 migrated to the direct Anthropic Messages API (in-process HTTP); D2/D3/D4 remain on the Agent SDK (which shells out to the `claude` CLI as a subprocess). A **uniform dispatch wrapper** (`app/reports/orchestration/dispatch.py`) normalizes both calling conventions plus a wall-clock timeout so any hang/crash/degraded-return surfaces as a clean "stage failed, persist trace, stop" — never a hung worker. **Decision: D2–D4 stay on the SDK; not migrated pre-emptively** (deploy-first — fix against a real failure if the subprocess pattern breaks under load).

### 7.3 The agent roster (Layer 3) — build status & actual runtime
Each agent has one narrow, individually-testable job. Built and validated one at a time. **Runtime is mixed** (see §7.2). Build status as of 2026-05-31:

| Agent | Single responsibility | Runtime (actual) | Status |
|-------|----------------------|------------------|--------|
| **Orchestrator** | Inventory uploads, dispatch agents via the dispatch wrapper, hold state via `report_jobs`, halt at gates | **Plain Python** (not an LLM agent) | **BUILT** — spine proven classify→extract→reconcile→Gate 1 halt on real data |
| **Document classifier (D1)** | Label each upload (proposal/grant_letter/mou/indicator_data/photo/deck/other) | **Messages API** | **BUILT & proven** |
| **Proposal extractor (D2)** | Objectives, activities, original indicators+targets from the winning proposal | **Agent SDK (subprocess)** | **BUILT & proven** |
| **Grant-terms extractor (D3)** | Reporting obligations, deadline, period, budget, funder from award letter/MoU | **Agent SDK (subprocess)** | **BUILT & proven** |
| **Tabular/indicator extractor (D4)** | Actuals-vs-targets, beneficiary counts, disaggregation, financials from Excel/CSV | **Agent SDK (subprocess)** | **BUILT & proven** — **NOTE: accepts spreadsheet input only (.xlsx/.csv); rejects .docx tables** (see lessons log §8b) |
| **Vision agent (D5)** | Caption/interpret photos and image-only PDFs as evidence | Cheap multimodal API | **DEFERRED to Phase 2** (not in MVP) |
| **Knowledge-bank reconciler (E1)** | Merge extractions into one picture; **surface conflicts** (don't silently average) | **Messages API** | **BUILT & proven** — produced clean 31-fact bank on real FCDO set, zero conflicts, correct provenance |
| **Gap/compliance agent (E3)** | Compare knowledge bank vs funder template; readiness score + funder-aware questions | **Messages API** | **BUILT (agent + service) but NOT wired into orchestrator** — next work |
| **Synthesis agents** | Write each section (one per section); reuse archetypes + humaniser | gpt-5.4 (humaniser reuse) | **NOT STARTED** (Stage F) |
| **Fact-safety critic** | Check every specific claim (number/name/date) vs sources; block/flag mismatches | TBD (strong model) | **NOT STARTED** (Stage F) |

### 7.4 The pipeline (gates marked)
```
1 INTAKE     pick grant + funder template, upload documents
2 CLASSIFY   classifier labels each doc → routes to extractors            [agent]
3 EXTRACT    specialist extractors + vision run concurrently (bg job)     [agents]
4 RECONCILE  reconciler merges; surfaces conflicts                        [agent]
  ══ GATE 1 ══  HUMAN: confirm/correct facts; resolve conflicts
5 GAP CHECK  gap agent scores readiness vs funder template                [agent]
  ══ GATE 2 ══  HUMAN: answer only genuinely-missing items (free text)
6 SYNTHESISE synthesis agents write sections concurrently                 [agents]
7 CRITIQUE   fact-safety critic checks claims vs sources; flags           [agent]
  ══ GATE 3 ══  HUMAN: review per-section, accept flags, edit
8 EXPORT     docxtpl renders funder-formatted .docx from confirmed content
```
Gates are **orchestrator state-machine halts enforced server-side** — **not** Agent SDK hooks. The orchestrator halts a job by setting `report_jobs.status = awaiting_human` with the `stage` cursor parked at the gate; the pipeline cannot advance until the human confirmation route stamps the gate (e.g. `gate1_confirmed_at`) and **re-enqueues** the job (`status → queued`) for the worker to re-claim and continue. Gate 1 (after reconcile) is built and proven; Gate 2 (after gap/E3) has its confirmation route but **no re-enqueue/resume trigger yet** — that is part of the next build.

### 7.5 Execution model (LOCKED)
**In-app background job queue + object storage. Not Railway sandboxes.** The workload is our own code over customer-supplied (not adversarial) documents; per-session container isolation defends a risk we don't have and adds operational burden a solo founder must run. The genuine need (long-running multimodal work that can't block a sync request) is met by an async job runner + small concurrency cap + `report_jobs` state table + object storage.
**Forward-compatibility:** the runner sits behind a clean `run_pipeline(report_id)` interface so the backend can later swap to Railway sandboxes (or any worker fabric) without touching agents.

---

## 8. TECH & TOOL STACK (LOCKED)

### Build tools
| Tool | Role | Model |
|------|------|-------|
| **Cursor** | **All code** — conventional backend AND the agent layer (orchestrator, agents, dispatch, gate logic, trace plumbing). Sole code-writing tool. | **GPT Codex, High compute** |
| **Claude** (chat) | Strategy, specs, prompts, architectural decisions, quality review | — |
| **ChatGPT (Enterprise/Copilot)** | Pranab's personal/Accenture writing + humaniser. Not a build tool here. | — |

**Build-tool decision (superseded):** the original plan split work between Cursor (conventional backend) and Claude Code (agent layer on the Agent SDK). **That split is retired.** Cursor builds everything; the `.cursor/hooks/` + `.cursor/rules/` are the live enforcement layer. The old `.claude/hooks/` + `CLAUDE.md` are vestigial (cleanup parked, not urgent).

### Runtime & hosting (all on Railway except marketing)
| Component | Where | Notes |
|-----------|-------|-------|
| FastAPI backend (incl. all agent code) | Railway (existing) | Agents are library-powered Python objects *inside* this app — not a separate service/SaaS |
| Background job worker | Railway (worker process / 2nd service from same image) | Runs the async pipeline behind `run_pipeline`. Runtime kill switch = scale worker to 0 |
| PostgreSQL | Railway (existing) | + 4 new tables; holds `knowledge_bank_json`, `agent_trace_json`, job state |
| Object storage (uploads) | **Railway Buckets** (S3-compatible) | The one new infra primitive. Alt: Cloudflare R2 if decoupling later |
| n8n | Railway (existing self-hosted) | Template-ingestion pipeline + optional Drive/Gmail pull. Plumbing only |
| WordPress / NGOInfo.org | **Hostinger** (existing) | Marketing only. **The app does not spread onto Hostinger.** |

### Reused open-source / external (the plumbing — not built)
| Package/service | Layer | Replaces building | Licence |
|-----------------|-------|-------------------|---------|
| **Docling** (IBM) | 1 | All PDF/DOCX/XLSX/PPTX/image/OCR parsing | MIT |
| **OpenDataLoader-PDF** | 1 (privacy tier) | Local-only parsing + prompt-injection protection (future) | OSS |
| **Claude Agent SDK** (Python) | 2 | Agent loop, subagents, hooks, context mgmt, MCP | Anthropic |
| **docxtpl** | 4 | Word-XML generation (design templates in Word + Jinja2 tags) | LGPL |
| **n8n** | 5 | Workflow/orchestration plumbing for ingestion | fair-code |
| Cheap multimodal vision API | model | Photo/image interpretation | external |
| OpenAI `gpt-5.4` | model | Section synthesis (humaniser reuse) | external |
| Claude (strong+cheap) | model | Coordinator/critic/reconciler/gap (strong); classifier/extractors (cheap) | external |

**Reference-only (studied, not adopted):** `wshobson/agents`, `claude-agent-sdk` GitHub topic, orchestrator examples (Multiclaude/Agent Teams) — patterns only; their autonomy-first defaults are the wrong posture for compliance.

**Build accelerators (not product components):** **Railway Agent** (DevOps copilot — provision services, diagnose deploys). **OpenClaw/Hermes-style installed agents — DECLINED** (autonomy-first, incompatible with human-gated design).

**Where the agents reside (one line):** your own Python code inside the FastAPI backend, executed by the **Railway background worker** — D1/E1/E3 calling the Anthropic **Messages API** in-process, D2/D3/D4 spawning the **Claude Agent SDK** (`claude` CLI) as a subprocess — coordinated by a **plain-Python orchestrator**, reading/writing documents in Railway Buckets and state in Railway Postgres. Not a separate service, not SaaS, not Hostinger, not n8n, not Railway sandboxes, not Agent-SDK hooks.

---

## 8b. DEPLOYMENT LESSONS LOG (real failures from production bring-up, 2026-05-31)

These are real environment failures surfaced by deploying and running — none were predictable from code review, all validate the **deploy-first-then-fix** principle. Recorded so they are not re-hit.

1. **Railway env-var edits don't apply until redeploy.** `TEST_MODE=true` shown in the dashboard returned `TEST_MODE_DISABLED` at runtime because the value was staged, not applied. Dashboard presence ≠ runtime presence. (Same class as: `ANTHROPIC_API_KEY` is **not validated at boot** — a missing key fails silently mid-run, not at startup.)
2. **A cloned Railway service runs the parent's start command by default.** The worker service was cloned from the API service and silently ran the web server, so no process consumed `report_jobs`. Fix: set the worker service's **start command** explicitly to `python -m app.reports.worker`.
3. **Worker entrypoint must register the full ORM model surface before its first query.** `python -m app.reports.worker` imported only the reports models, so SQLAlchemy could not resolve `DonorReport → User` and every poll cycle crashed (`failed to locate a name 'User'`). The web path didn't hit this because `app.main` imports everything. Fix: a shared bootstrap that imports `app.models` + `app.reports.models` before the poll loop. **Lesson: the two process entrypoints (web vs worker) have different import graphs — the worker must explicitly load what the web app loads transitively.**
4. **D4 (indicator extractor) accepts spreadsheet input only.** A logframe uploaded as `.docx` (Word table) was correctly classified `indicator_data`, routed to D4, and rejected with `Unsupported spreadsheet format: .docx`. Every component behaved correctly; the mismatch is test-data packaging. **Open product question (logged, not yet decided): real NGOs often submit logframes as Word tables — decide whether to widen D4's intake to accept `.docx`-embedded tables.**
5. **Queued-forever job ≠ one diagnosis.** A job stuck `queued` with `started_at=NULL` can mean "no worker," "worker crashing on boot," or "worker crashing pre-claim" — the `report_jobs` table alone cannot distinguish them. **Always pull the worker logs.**

**Carried-forward (assumed-good, not yet proven in prod):** the Gate 1 **resume** path (re-enqueue → re-claim → advance) passed in CI and the forward walk is proven, but the resume round-trip was not separately verified in production by deliberate choice; its first prod exercise will be the E3 build's run.

**Carried-forward (housekeeping, pre-launch):** turn `TEST_MODE` **off** in prod before launch and keep the `/api/auth/test-mode/mint` endpoint on the kill-before-launch list (it can mint a token for any email while on). Worker is at **1 replica** (correct for now — keeps the un-cross-process-tested `SKIP LOCKED` claim safe).

---

## 9. TOOLING CAPABILITIES & HOW WE EXPLOIT THEM

> **Note:** this section is preserved from the original planning. The **Cursor** capabilities (Composer/Codex, `.cursor/hooks/`, `.cursor/rules/`) remain live and load-bearing. The **Claude Code** capabilities (`.claude/hooks/`, subagents) are **retired** — kept here only for historical context; the live enforcement layer is `.cursor/hooks/`.

The 2026 versions of all three tools shipped enforcement layers that turn governance from *advice the model might follow* into *rules the system enforces* — directly attacking the ReqAgent failure mode.

- **Cursor Composer 2.5** (May 18 2026): frontier-parity coding at ~1/10 cost (~$0.50/task); retrained for long-horizon reliability with fewer mid-task hallucinations of completed steps. Default for conventional backend.
- **Cursor Hooks** (`.cursor/hooks/`): scripts wired to editor events — `onPreEdit` (can **veto** an edit), `onPostEdit`, `onPreCommit`, `onApprove`. Canonical use: block edits to protected paths unless flagged.
- **Claude Code Hooks** (`.claude/hooks/`): deterministic code that **cannot hallucinate**. Fire at lifecycle points — `UserPromptSubmit` (block/modify prompt), `PreToolUse` (primary security checkpoint), `Stop`/`SubagentStop`. Runaway-loop protection: a turn ends after 8 consecutive stop-hook blocks.
- **Claude Code subagents**: isolated context windows; the field-consensus pattern is "strong planner + clear subagent boundaries + tool-specific permissions + test feedback + human review at checkpoints" — i.e. exactly our roster.
- **Railway**: PR Environments (ephemeral per-PR), **Focused PR Environments** (only deploy services touched by the PR — fits our monolith+worker), Config-as-Code (TOML/JSON: cron, healthchecks, scaling), one-click rollback, volumes, cron. **Caveat:** independent reports of recurring Railway outages in late-2025/2026 — keep kill-switch/rollback tight and the `run_pipeline` seam swappable.

**The three-layer build defence (the "learn from the past" upgrade):**
1. **Deterministic enforcement (hooks, not prose):** the must-not-violate rules become code. Isolation boundary (core never imports M&E) → `onPreEdit`/`PreToolUse` veto. Migration column-name parity → `PostToolUse` check. Secret scan → `onPreCommit`. These can't be forgotten or reasoned around.
2. **Model intelligence where it pays:** Composer 2.5 for conventional backend; Opus-class Claude Code for architecture/agents; cheap subagents for extraction.
3. **Human review at checkpoints:** Plan Mode before big changes; PR environments to see each change running before merge; the three product gates.

> Hooks are written in **Python** (not bash/PowerShell) so they run identically on the Windows laptop and Railway's Linux containers; account for Windows path/line-ending differences.

---

## 10. ISOLATION & KILL SWITCH (modular monolith)

**Four rules make the module killable:**
1. **One-way dependency.** M&E may import core; **core must NEVER import M&E.** (The cardinal rule — enforced by hook.)
2. **One mounting seam.** Entire M&E API attaches via a single router-include; frontend hidden behind a single feature flag.
3. **Separate data, FKs inward only.** The 4 M&E tables may FK *to* core; no core table FKs back to M&E; no core migration alters a core table for M&E.
4. **Separate runtime process.** The agent pipeline runs in the background worker, not the main API path.

**Three independent kill switches:**
- **Code:** un-mount the router + flag off the UI → GrantPilot unaffected.
- **Runtime:** scale the worker to 0 → proposal product never notices.
- **Data:** drop the 4 M&E tables → core schema intact.

**Decision:** **modular monolith** (same repo, isolated folder) over a separate service — operational simplicity for a solo founder; isolation rules + hooks do the separation work.

---

## 11. PROJECT PLAN — STAGES & PROVENANCE

> **Build status (2026-05-31):** Stages **A–E COMPLETE and deployed**. Orchestrator (Stage G) **spine BUILT and proven** to the Gate 1 halt — note this was deliberately built early as a thin slice (see §18), out of the original A→…→F→G order, to surface integration risk; the Stage F quality gate is **preserved and moved**, not skipped (it applies when synthesis is wired). Stages **F, H, I, J, K, L NOT STARTED**. D5 vision **deferred to Phase 2**.

**Provenance tags:** EXISTING (extend/reuse) · REUSE (external OSS/service) · BUILD (our IP) · DECISION (locked choice).
**Three ordering principles:** isolation before code · spec before build · validate before automate/polish.

### Stage A — Governance & isolation scaffold *(no product code)*
Produces the soft layer (`.cursor/rules/`: global, isolation, backend, agents, scope-fence; `CLAUDE.md`) **and** the hard layer (`.cursor/hooks/` + `.claude/hooks/`: isolation veto, migration-parity, secret-scan), plus `REPO_MAP_ME_MODULE.md`, `ME_MODULE_KILL_SWITCH.md`, `ME_MODULE_DECISION_LOG.md` (seeded). Drop the architecture spec + wireframes into the repo.
**Exit gate:** rules, repo map, kill-switch doc, and hooks agree on one boundary and one seam. If the kill-switch doc can't be written cleanly, isolation isn't done.

### Stage B — Phase 0 specification lock *(no product code)*
4 field contracts (`donor_reports`, `funder_report_templates`, `uploaded_documents`, `report_jobs`); `FUNDER_TEMPLATE_SCHEMA.md`; **NLCF + FCDO reference templates** expressed in the schema (the stress test — simple + complex extremes); `REPORT_INPUTS_FIELD_MAPPING.md`; `API_CONTRACT.md` additions; just-in-time additions to prompts library, pricing/entitlements, guardrails, env vars, dependencies, dev setup.
**Exit gate:** both extreme templates fit the schema with zero gaps; every synthesis input mapped; no existing contract altered. **Requires Workstream T2.**

### Stage C — Foundations & proven kill switch *(first code)*
Module skeleton (isolated `reports/` package, single router seam, frontend flag); migrations + models for 4 tables (column-name parity enforced; FKs inward only); object storage wiring (Railway Buckets); background worker + `run_pipeline` interface; Docling extraction adapter.
**Exit gate — kill-switch rehearsal on the empty module:** (a) un-mount + flag off leaves GrantPilot working, (b) worker→0 affects nothing, (c) drop 4 tables leaves core schema intact. **Do not proceed until all three pass.**

### Stage D — Extraction agents *(Cursor; one at a time)* ✅ COMPLETE (D5 deferred)
Classifier → proposal extractor → grant-terms extractor → tabular/indicator extractor → ~~vision agent~~. Each with its own test harness on real sample documents before the next. **D1–D4 built and proven; D5 vision deferred to Phase 2.** Runtime: D1 Messages API, D2–D4 Agent SDK subprocess.

### Stage E — The brain (reconciliation + gaps + gates 1–2) ◐ MOSTLY COMPLETE
Knowledge-bank reconciler (surfaces conflicts) → Gate 1 (confirm facts, server-enforced) → gap/compliance agent → Gate 2 (fill only gaps, server-enforced). **E1 + Gate 1 built, wired into orchestrator, and proven on real data. E3 + Gate 2 exist as agent/service/route but are NOT yet wired into the orchestrator (Gate 2 also lacks a re-enqueue/resume trigger) — this is the next build.**

### Stage F — Generation + critic + THE QUALITY GATE
Synthesis agents (reuse archetypes/humaniser, gpt-5.4) → fact-safety critic → Gate 3 (review/edit).
**QUALITY GATE (the plan's hinge):** reports must be **funder-grade on hand-confirmed data** — graded vs humaniser rules, no hallucinated specifics, critic catches planted errors. **No UX polish, no orchestrator, no more templates until this passes.**

### Stage G — Orchestrator ◐ SPINE BUILT (out of original order — deliberate)
Wire all agents into one coordinated pipeline with the gate halts + full `agent_trace` logging. **Built as a thin slice EARLY** (classify→extract→reconcile→Gate 1 halt + resume), ahead of the original "after Stage F" position, to surface integration unknowns on real infrastructure rather than in theory. The orchestrator is **plain Python dispatch** (not an LLM agent) with a uniform dispatch wrapper over the mixed runtime. **The Stage F quality gate is preserved and moved:** synthesis must still pass fact-safety + Gate 3 before any generated report is exported — building the spine early earns the right to reorder, not to skip the gate.

### Stage H — Export
docxtpl render engine (idempotent from stored content) + the 10 funder `.docx` templates (NLCF + FCDO first). Hand-built, not via n8n.

### Stage I — Frontend journey
The 8 screens (dashboard → template → upload → watch → Gate 1 → Gate 2 → Gate 3 → export), behind the feature flag, calling the API only, no business logic. (See §13 for screen detail.)

### Stage J — Billing & entitlements
Impact Pro tier ($99), 2 reports/mo quota, regeneration limits, idempotent Stripe webhooks, correct plan claims in JWT.

### Stage K — Testing & launch readiness
Smoke tracks (health / authenticated report journey / auth boundaries); J1→J2 on 3 templates (NLCF, FCDO, one generic); lifecycle emails ("report ready", "report due") via existing `email_service`; production hardening + **live kill-switch rehearsal on the full module**.
**Launch gate:** smoke green + J1→J2 passing on 3 templates + kill switches confirmed → flag on → Impact Pro live.

### Stage L — Post-launch (validate-then-automate)
n8n funder-template ingestion pipeline (Firecrawl → extract → human review → POST); extraction refinement against real customer documents; templates 11+ by demonstrated demand; NGOInfo v2 with the lifecycle story + post-award content.

### Critical path
```
A → B → C → D → E → F → ◆QUALITY GATE◆ → {G, H} → I → J → K → L
Workstream T runs parallel from Stage A; T2 gates Stage B.
```
**Hard gates that stop the build:** end of A (isolation coherent) · end of B (templates fit schema; +T2) · end of C (3 kill switches proven empty) · end of F (reports funder-grade — *the hinge*) · end of K (smoke green + kill switches re-proven full).

---

## 11b. WORKSTREAM T — Template sourcing (parallel, starts Stage A)

> **Template population mechanism (DECISION, 2026-05-31):** funder M&E requirements are entered **manually into the `funder_report_templates` DB table** (`report_sections_json`, etc.). There is no seed script or ingestion *feature* to build for launch — Pranab populates funder templates by hand. The n8n + Firecrawl ingestion pipeline (Stage L) remains the **deferred, post-revenue** automation for scaling templates 11+. **Cursor must never build a template loader/seeder** — the table is populated operationally. (Note: reports created without a `funder_report_template_id` fall back to an empty `__default__` template, against which the gap agent has nothing to check — so meaningful E3 testing requires a real funder template row to exist first.)

Funder templates are **assembled**, not possessed. Sourcing ladder: (1) public funder docs, (2) FundsforNGOs Premium (already paid), (3) **real grantee reports** (richest source + moat), (4) n8n pipeline (scales 11+ post-launch only).

| # | Template | Primary public source | Grantee report needed? |
|---|----------|----------------------|------------------------|
| 1 | NLCF End-of-Grant | NLCF grant-holder reporting guidance | Helpful |
| 2 | NLCF Annual Progress | NLCF "tell us how it's going" guidance | Helpful |
| 3 | FCDO Annual Review | **DevTracker** — real published annual reviews + logframes, downloadable; FCDO PrOF + smart guides | No — public examples abundant |
| 4 | Comic Relief End-of-Grant | Funded-partner reporting template (grantee pages) | Helpful |
| 5 | USAID Quarterly | Public ADS guidance, PMP/IPTT toolkits | Helpful (exact tables) |
| 6 | USAID Annual | Same ADS/PMP guidance | Helpful (exact tables) |
| 7 | ECHO Single Form Interim | **Published** Single Form + EU guidelines | No — fully public |
| 8 | ECHO Single Form Final | Same | No — fully public |
| 9 | Generic Institutional | Synthesised from patterns across 3–8 | No |
| 10 | Generic CSR | Indian CSR norms; FundsforNGOs + CSR portals | Helpful (India specifics) |

**Steps:** T1 grantee outreach (**start immediately — longest lead time**) · T2 NLCF+FCDO dossiers (feeds Stage B) · T3 dossiers for the other 8 (feeds Stage H) · T4 gather grantee reports where flagged · T5 hand-author templates in schema.
**Reframe:** absence of a ready-made template library = absence of a competitor. You assemble the bank; that assembly *is* the moat.

---

## 12. DATA MODEL (new tables; field contracts locked in Stage B)

**`funder_report_templates`** — post-award equivalent of `requirements_json`
`id, created_at, updated_at, funder_name, template_name, region, reporting_frequency (end_of_grant|annual|quarterly|interim|final), report_sections JSONB, format_rules JSONB, terminology_map JSONB, docx_template_ref, is_active, version`

**`donor_reports`** — post-award equivalent of `proposals`
`id, user_id, created_at, updated_at, funder_report_template_id FK, linked_proposal_id FK (nullable — set if won via GrantPilot), reporting_period_start, reporting_period_end, status (DRAFT|EXTRACTING|AWAITING_REVIEW|GENERATING|DEGRADED|COMPLETE), knowledge_bank_json JSONB, indicator_actuals_json JSONB, content_json JSONB, version`

**`uploaded_documents`** — the ingestion surface
`id, donor_report_id FK, user_id, storage_ref, original_filename, mime_type, size_bytes, classification (proposal|grant_letter|mou|indicator_data|photo|deck|other), extracted_json JSONB, extraction_status, created_at`

**`report_jobs`** — async pipeline state
`id, donor_report_id FK, stage (classify|extract|reconcile|gap|synthesise|critique|export), status (queued|running|awaiting_human|failed|done), agent_trace_json JSONB, error, started_at, finished_at`

**Partial-success rule (inherited):** if some sections succeed and others fail, persist as `DEGRADED` with per-section status — never lose completed work.
**FK rule:** all FKs point inward to core. No core table FKs to these.

---

## 13. API SURFACE (outcome-level; envelopes locked in Stage B)
Authenticated + entitlement-gated:
- `POST /api/reports` — create (funder template required, grant link optional)
- `POST /api/reports/{id}/documents` — upload → classification + extraction job
- `GET /api/reports/{id}/knowledge-bank` — reconciled picture + conflicts (Gate 1)
- `PATCH /api/reports/{id}/knowledge-bank` — human confirmations/corrections
- `GET /api/reports/{id}/gap-check` — readiness score + missing items (Gate 2)
- `PATCH /api/reports/{id}/gap-answers` — free-text answers
- `POST /api/reports/{id}/generate` — synthesis + critic
- `GET /api/reports/{id}` — full state + per-section status + critic flags (Gate 3)
- `PATCH /api/reports/{id}/sections/{key}` — human edit/accept
- `POST /api/reports/{id}/export` — funder-formatted DOCX (idempotent)
- `GET /api/reports/{id}/job` — async pipeline status (drives "watch it work" UI)
- `GET /api/report-templates` — list funder templates

---

## 14. THE 8 FRONTEND SCREENS (from the wireframe blueprint)
1. **Dashboard** — "Won a grant — with us or anyone else? Generate the funder report." In-progress reports show their current gate.
2. **Choose grant + funder template** — funder choice loads the whole template config (sections, word limits, required tables, terminology, tone).
3. **Upload** — drag the mess (PDF/Word/Excel/PPT/images) or pull from Drive/Gmail; classifier tags each file as it lands.
4. **Watch the agents work** — live per-agent progress in the background job; visible cost meter reflecting the cheap/strong model split.
5. **Gate 1 — confirm facts** — reconciler surfaces extracted values + conflicts ("proposal 500 vs sheet 450"); human resolves. Server-enforced.
6. **Gate 2 — fill only gaps** — readiness score + funder-aware questions for genuinely-missing items only. Kills blank-page friction.
7. **Gate 3 — review with critic** — per-section status; critic flags claims mismatched to sources; human edits/accepts; human stays the author.
8. **Export** — funder-formatted DOCX; re-export idempotent; "duplicate for next period" turns the saved knowledge bank into recurring revenue.

**Colour language:** teal = agent working autonomously; plum = human gate (pipeline halts, server-enforced); orange = primary action.

---

## 15. SECURITY & GUARDRAILS
- **Fact-safety critic is mandatory.** No specific claim reaches export without being checkable against a source document or a human gap-answer.
- **Prompt-injection fence.** Uploaded document text is **data, never instructions**; extraction agents treat it as content; the orchestrator never executes embedded instructions. (OpenDataLoader injection protection available for privacy tier.)
- **Human gates enforced server-side**, not just in UI — pipeline can't advance without recorded confirmation.
- **Data sensitivity.** Beneficiary data may be present; object storage scoped per user; documents purgeable; local-extraction (OpenDataLoader) path as privacy tier.
- **Inherited hardening:** strict CORS to browser origin; no test endpoints in prod; single-instance rate-limiting honoured; secrets server-side only; correct plan claims in JWT.
- **Agent containment:** explicit STOP conditions, timeouts, bounded toolset per agent; `agent_trace_json` makes every run inspectable + cost-accountable.
- **Deterministic enforcement (hooks):** isolation veto, migration-parity, secret-scan run as code, not model instruction.

---

## 16. KEY PRINCIPLES & WORKING PREFERENCES (carried from all prior work)
- **Spec-first, then code.** Lock specs before building; `API_CONTRACT.md` is source of truth; changelog/decision-log entries for governance decisions.
- **Backend is source of truth** during contract drift — frontend adapts to backend, never reverse.
- **Validate with paying users before building automation** (applied to own products: content pipeline + n8n deferred to post-revenue).
- **Deploy-first, then fix (added 2026-05-31).** Real environment failures reveal problems theoretical analysis misses. Ship the thin slice, let the environment surface the real failures, fix against them — rather than pre-engineering against imagined ones. Validated repeatedly during M&E bring-up (see §8b): every real blocker was an environment/data issue no code review would have caught. **Corollary — executable guards beat documented guards:** a regression test that reproduces a real failure (e.g. the worker mapper-init test) is worth more than a best-practices doc.
- **Uniform dispatch over a mixed substrate (added 2026-05-31).** When agents run on different calling conventions (Messages API vs SDK subprocess), normalize them behind one dispatch wrapper so every stage outcome is either success-with-persisted-output or clean-stage-failure-with-trace — never a hung worker. The orchestrator owns its transaction; each stage commits output + cursor as one atomic, resumable checkpoint.
- **Diagnose before fixing.** Structured diagnosis precedes any patch.
- **Revenue before elegance.** Ship what works by the date; polish post-launch.
- **Monolithic autonomous flows fail** (ReqAgent) → staged, inspectable pipelines with human gates.
- **AI writing quality:** structural rules beat cosmetic cleanup; humaniser V3 (13-point self-check); controlled uncertainty as a rule; hard vs contextual banned-word split; fact-safety guardrail on named specifics to prevent hallucination.
- **Cursor prompt discipline:** outcome-driven only — specify *what*, never *how* (no code/pseudocode); tight scope fences; explicit STOP conditions; single task per prompt; read-only audit before any change prompt; framework-based prompts (contract lock, scope fence, canonical spec, idempotency spec, non-goals, acceptance tests).
- **Decision style:** strategic, decisive; quick binary calls when presented options; shipping over perfection.

### Existing GrantPilot tech context (for reference)
Next.js frontend + FastAPI/Python backend on Railway (GitHub CI/CD); PostgreSQL; OpenAI Chat Completions (`gpt-5.4`, env `OPENAI_MODEL_PRIMARY`, `response_format: json_object`); ThreadPoolExecutor for concurrent section generation; Resend (`support@ngoinfo.org`) for email; Stripe (hosted checkout + portal); Google OAuth + magic link; GTM/GA4 cross-domain. Core engine production-ready (22/22 smoke checks green). Humaniser framework governs both GrantPilot generation and Pranab's Accenture writing.
**M&E runtime additions (live):** Railway **worker service** (separate service from the same image, start command `python -m app.reports.worker`, 1 replica) polling `report_jobs`; **Railway Buckets** (`ME_DOCUMENTS_S3_*`) for uploads; **Anthropic Messages API** (`ANTHROPIC_API_KEY`, not boot-validated) for D1/E1/E3; **Claude Agent SDK** subprocess for D2–D4; `ME_MODULE_ENABLED=true` mounts `/api/reports*`. Backend `origin/main` on `mycrivo/ngoinfo-grantpilot`.
**Key existing spec docs:** `API_CONTRACT.md`, `OPENAI_PROMPTS_LIBRARY.md`, `FUNDING_OPPORTUNITY_GOLDEN_RULES.md`, `ENV_VARS_REFERENCE.md`, `GUARDRAILS_RUNTIME_AND_SECURITY.md`, `PROMPT_INPUTS_FIELD_MAPPING.md`, plus DB field contracts.

---

## 17. OPEN ITEMS (everything else is LOCKED)
- **Synthesis model final call:** start on `gpt-5.4` (humaniser reuse); re-evaluate a cheaper class once synthesis is built, before launch — benchmark in Stage F. *(Still open — Stage F not started.)*
- **Vision API vendor:** **DEFERRED to Phase 2** — D5 vision is out of MVP scope; vendor choice not needed until then.
- **Object storage:** **RESOLVED** — Railway Buckets in use (`ME_DOCUMENTS_S3_*`), live in production.
- **D4 `.docx`-table intake:** **OPEN** — decide whether to widen the indicator extractor to accept tabular data embedded in Word docs (real NGOs submit logframes this way). See §8b.4.
- **Gate 1 resume verified in prod:** **OPEN** — proven in CI, not separately verified in production by choice; first prod exercise = E3 build run. See §8b.
- **Privacy tier (OpenDataLoader):** post-launch consideration, not in MVP.

---

## 18. CURRENT STATUS & NEXT ACTION

- **Status (2026-05-31):** Stages **A–E built and deployed to production** on Railway (`ME_MODULE_ENABLED=true`, worker live). The **orchestrator spine is built and proven end-to-end on real FCDO data**: a real report ran create → upload (3 docs) → classify (D1) → extract (D2/D3/D4) → reconcile (E1) → halted at **Gate 1** (`status=awaiting_human, stage=gap`) with a clean **31-fact knowledge bank**, zero conflicts, correct provenance. The mixed-substrate dispatch (Messages API + SDK subprocess) and the pause-persist halt are validated in the real environment.
- **What's built:** D1–D4 extractors, E1 reconciler, E3 gap-agent (agent + service, **not orchestrator-wired**), Gate 1 (full: confirm + re-enqueue), Gate 2 (route + service only, **no resume trigger**), the orchestrator walk to Gate 1, the uniform dispatch wrapper, the report-lifecycle HTTP routes (`POST /api/reports`, `/documents`, `/job`, `GET /job`, `/knowledge-bank`), the hardened worker (atomic claim, wall-clock backstop, fail-safe transitions, ORM bootstrap).
- **Immediate next action: wire E3 (gap/compliance) + Gate 2 into the orchestrator.** A read-only seam audit (`E3_GAP_GATE2_SEAM_AUDIT_2026-05-31.md`) is complete. The build must: bring E3 into the dispatch wrapper (and normalize E3's bare `asyncio.TimeoutError` leak), replace the gap-boundary park with a real gap stage that runs E3 → persists `gap_analysis_json` → halts at Gate 2, and add a Gate 2 re-enqueue/resume trigger (mirror of Gate 1).
- **Prerequisite for meaningful E3 testing:** a **real funder template** (e.g. FCDO) must be **manually populated** in `funder_report_templates` (see §11b decision) — the empty `__default__` template gives E3 nothing to check gaps against. A fresh report created against that template is the test vehicle (the existing test report is linked to the empty default).
- **Carried-forward items:** Gate 1 resume unverified-in-prod (§8b); D4 `.docx` intake undecided (§17); `TEST_MODE` to be turned off pre-launch (§8b). 
- **After E3/Gate 2:** Stage F (synthesis + critic + Gate 3, the quality-gate hinge) → export (H) → frontend (I) → billing (J) → launch (K).

### Companion artefacts (also in the project)
- `ME_MODULE_ARCHITECTURE_SPEC.md` — full architecture spec. **⚠ Contains stale "Claude Agent SDK runtime" / "gates as hooks" framing — code is source of truth; this memory file's §7–§8 supersede it. Cleanup parked, not urgent.**
- `ME_MODULE_WIREFRAMES.html` / `ME_MODULE_WIREFRAMES_BRANDED.html` — the 8-screen visual blueprint.
- `ME_MODULE_PROJECT_PLAN.md` — the sequenced plan (updated 2026-05-31 to mark A–E done and the orchestrator-early reordering).
- `ME_MODULE_DECISION_LOG.md` — the decision log (most authoritative for individual locked decisions).
- `ORCHESTRATOR_SEAM_AUDIT_2026-05-30.md`, `E3_GAP_GATE2_SEAM_AUDIT_2026-05-31.md` — read-only seam audits backing the orchestrator and next build.

---

*End of master memory document. To resume: attach this file and say "continue the M&E build from the project memory file." The assistant resumes at §18 — next work is wiring E3 + Gate 2 into the orchestrator, after a real FCDO funder template is manually populated.*
