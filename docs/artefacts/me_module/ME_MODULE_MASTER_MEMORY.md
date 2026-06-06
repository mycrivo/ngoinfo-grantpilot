# GrantPilot M&E Module — Master Memory Document

> **Purpose of this file.** A single, self-contained source of truth for the GrantPilot M&E (Donor Report Writer) module. It exists so the project can be re-initiated in a fresh chat without losing context, and so it can be uploaded to Cursor/Claude Code as build context. If you are an AI reading this in a new session: this document supersedes any partial memory; treat it as authoritative. Everything below is **decided and locked** unless explicitly marked OPEN.
>
> **Last consolidated:** 2026-06-04 · **Module status:** Stages A–E complete and proven in prod; F1/F2/Gate 3 built and orchestrator-wired; Stage H export built early; Stage F quality gate in progress on test report `6643d922`

---

## 0. HOW TO USE THIS FILE

- **Re-initiating a chat:** paste or attach this file and say "continue the M&E build from the project memory file." The assistant should resume at the current stage (see §12 Status).
- **Working rhythm:** Claude (strategy/specs/prompts/review) → Pranab (decides, runs prompts, reports back) → Cursor or Claude Code (executes) → repeat. One outcome-driven prompt at a time.
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

**Working model with Claude:** Claude acts as strategic CTO/CMO co-founder — strategy, specs, and outcome-driven prompts; never pseudocode or implementation-heavy instructions. Claude specifies *what*; Cursor/Claude Code write *how*. (The one exception: hook scripts, where the script *is* the spec.)

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

- **New paid capability on Impact**, not a feature bolt-on to Growth. Serves customers whose immediate need may be **post-award reporting**, not proposal writing.
- **Acquisition wedge:** the report is the cheaper, more urgent, more frequent entry product. NGOs who won *elsewhere* arrive in deadline pain, hand over their full org profile + funder relationship + indicators, and become natural pre-award (proposal) customers next cycle. The landing message: *"Won a grant — with us or anyone — and dreading the report? Upload what you've got."*
- **GTM sequencing:**
  1. **UK + selected EU bilateral donors first** (Months 1–6). The US pre-award market is saturated (Instrumentl, Grantable, etc.); UK/EU post-award is underserved.
  2. **India second** (Months 4–8), leveraging the CSR-mandate compliance market (~$3.2B/yr deployed).
  3. **US last** (Months 8–12), entering as the *post-award specialist*, not another grant-writer.
- **NGOInfo v2** launches **after** the M&E module — stronger complete-lifecycle narrative; v2 content targets post-award search intent (reporting guides, indicator frameworks) as a new organic channel.
- **New paid capability on Impact**, not a separate third tier. M&E is bundled on **Impact ($79/mo)** with 2 reports/month.
- **Why UK-first (CMO rationale):** US pre-award is a bloodbath; UK/EU buyers feel underserved by US-centric tools; UK's ~207K charities is a dominable market where content marketing on NGOInfo can cut through; **Growth $39 / Impact $79** pricing is well-positioned vs UK incumbents.

---

## 5. TIER & PRICING (LOCKED)

**Two paid plans only:** FREE | **Growth ($39/mo)** | **Impact ($79/mo)**. Plan enum stays `FREE | GROWTH | IMPACT` — no third tier.

| Plan | Pre-award | Post-award (M&E) |
|------|-----------|------------------|
| **Growth** | 10 Fit Scans/mo, 3 Proposals/mo, DOCX export, normal support | **No M&E** — upgrade-to-Impact gate at any M&E entry |
| **Impact** | 10 Fit Scans/mo, 5 Proposals/mo, DOCX export, priority support | **2 M&E reports/mo** (bundled subscription quota) |

- **Cost ceiling:** per-report model cost must stay inside bundled margin on Impact (2 reports/mo at $79). `agent_trace_json` provides per-run cost accounting. *(Founder: confirm margin vs prior ~$49.50/report assumption at $99 tier — see D-048.)*
- **Impact carries both products:** proposal credits (pre-award) **and** 2 M&E reports/mo (post-award) under one `IMPACT` plan claim. A user can enter purely for M&E (**Path C** — won a grant anywhere, never used NGOInfo or written a proposal) and still has proposal credits when they next need to bid.
- **Three entry paths:** (A) via NGOInfo.org WordPress discovery → proposal; (B) direct to GrantPilot for proposals; (C) **direct to the M&E door** in reporting-deadline pain, no NGOInfo/proposal history required. M&E does **not** require `funding_opportunity_id`; `linked_proposal_id` is optional only. All three converge on the same shared core.

---

## 6. SCOPE

### In scope (launch)
Document upload + agentic extraction; knowledge-bank reconciliation with human confirmation; funder-aware gap check; narrative generation; fact-safety critic; funder-formatted DOCX export; **10 report templates** (8 funder-specific + 2 generic fallbacks); **Impact plan M&E entitlement** (2 reports/mo).

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
L5 Connectors/ingestion ...... n8n (template ingestion, optional Drive/Gmail pull)        REUSE
L4 Assembly & export ......... docxtpl + 10 hand-designed funder .docx templates          REUSE engine / BUILD templates
L3 M&E DOMAIN BRAIN .......... Orchestrator · Reconciler · Gap/compliance · Synthesis ·    BUILD (the moat)
                               Fact-safety critic · funder template logic
L2 Agent runtime ............. Claude Agent SDK: agent loop, subagents, hooks (=gates)     REUSE SDK / BUILD agents
L1 Document extraction ....... Docling: PDF/DOCX/XLSX/PPTX/images → clean structured text  REUSE
   Execution model: in-app background job queue + object storage (NOT Railway sandboxes), behind swappable run_pipeline()
```

### 7.3 The agent roster (Layer 3, on Claude Agent SDK)
Each agent has one narrow, individually-testable job. Built and validated one at a time *before* the orchestrator is wired over them.

| Agent | Single responsibility | Model class |
|-------|----------------------|-------------|
| **Orchestrator** | Inventory uploads, dispatch agents, hold state, decide readiness, route to gates | Strong (Opus-class) |
| **Document classifier** | Label each upload (proposal/grant letter/MoU/indicator data/photo/deck); SDK `max_turns=2` (second turn required for structured-output JSON — ratified D-030) | Cheap |
| **Proposal extractor** | Objectives, activities, original indicators+targets from the winning proposal | Cheap–mid |
| **Grant-terms extractor** | Reporting obligations, deadline, period, budget, funder from award letter/MoU | Cheap–mid |
| **Tabular/indicator extractor** | Actuals-vs-targets, beneficiary counts, disaggregation, financials from Excel/CSV | Cheap–mid |
| **Vision agent** | Caption/interpret photos and image-only PDFs as evidence | Cheap multimodal API |
| **Knowledge-bank reconciler** | Merge extractions into one picture; **surface conflicts** (don't silently average) | Strong |
| **Gap/compliance agent** | Compare knowledge bank vs funder template; readiness score + funder-aware questions | Strong |
| **Synthesis agents** | Write each section (one per section); reuse archetypes + humaniser | gpt-5.4 (humaniser reuse) |
| **Fact-safety critic** | Check every specific claim (number/name/date) vs sources; block/flag mismatches | Strong |

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
Gates are **Agent SDK hooks** — pause points enforced **server-side** (the pipeline cannot advance past a gate without a recorded human confirmation).

### 7.5 Execution model (LOCKED)
**In-app background job queue + object storage. Not Railway sandboxes.** The workload is our own code over customer-supplied (not adversarial) documents; per-session container isolation defends a risk we don't have and adds operational burden a solo founder must run. The genuine need (long-running multimodal work that can't block a sync request) is met by an async job runner + small concurrency cap + `report_jobs` state table + object storage.
**Forward-compatibility:** the runner sits behind a clean `run_pipeline(report_id)` interface so the backend can later swap to Railway sandboxes (or any worker fabric) without touching agents.

---

## 8. TECH & TOOL STACK (LOCKED)

### Build tools
| Tool | Role | Model |
|------|------|-------|
| **Cursor** | Conventional backend: services, models, migrations, endpoints, docxtpl layer | **Composer 2.5** (frontier-parity at ~1/10 cost; strong long-horizon reliability) |
| **Claude Code** | The **agent layer** specifically: orchestrator, agents, gate hooks, trace plumbing (reference impl of the Claude Agent SDK we build on) | **Opus-class** for architecture/agents; cheap subagents for bounded work |
| **Claude** (chat) | Strategy, specs, prompts, quality review | — |
| **ChatGPT (Enterprise/Copilot)** | Pranab's personal/Accenture writing + humaniser. Not a build tool here. | — |

**Split rule:** Cursor builds conventional backend; Claude Code builds the agent layer. Both already available.

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

**Where the agents reside (one line):** your own Python code, built on the Claude Agent SDK, inside the FastAPI backend process on Railway, executed by the background worker, talking to model APIs over the network, reading/writing documents in Railway Buckets and state in Railway Postgres. Not a separate service, not SaaS, not Hostinger, not n8n, not Railway sandboxes.

---

## 9. LATEST TOOLING CAPABILITIES & HOW WE EXPLOIT THEM

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

### Stage D — Extraction agents *(Claude Code; one at a time)*
Classifier → proposal extractor → grant-terms extractor → tabular/indicator extractor → vision agent. Each with its own test harness on real sample documents before the next.

### Stage E — The brain (reconciliation + gaps + gates 1–2)
Knowledge-bank reconciler (surfaces conflicts) → Gate 1 (confirm facts, server-enforced) → gap/compliance agent → Gate 2 (fill only gaps, server-enforced).

### Stage F — Generation + critic + THE QUALITY GATE
Synthesis agents (reuse archetypes/humaniser, gpt-5.4) → fact-safety critic → Gate 3 (review/edit).
**QUALITY GATE (the plan's hinge):** reports must be **funder-grade on hand-confirmed data** — graded vs humaniser rules, no hallucinated specifics, critic catches planted errors. Active focus (2026-06-04): close the gate on a real end-to-end `.docx` after resumable F1 converges to 8/8 — not citation-BLOCK count tuning.

### Stage G — Orchestrator
Wire all agents into one coordinated pipeline with the 3 gate hooks + full `agent_trace` logging. Built only after every agent is individually proven.
*(Note: orchestrator was wired early for E/F validation walks; see decision log and §18.)*

### Stage H — Export
**Built ahead of plan order (2026-06):** `report_export_service` + `docx_renderer` (`render_mode: from_scratch` via python-docx) and `GET /api/reports/{id}/export` — constructed so the Stage F gate produces a real artefact at the end (a stubbed export would make the gate meaningless). Long-run intent unchanged: docxtpl + hand-built funder `.docx` templates when base templates are supplied (NLCF + FCDO first).

### Stage I — Frontend journey
The 8 screens (dashboard → template → upload → watch → Gate 1 → Gate 2 → Gate 3 → export), behind the feature flag, calling the API only, no business logic. (See §13 for screen detail.)

### Stage J — Billing & entitlements
**Impact** plan ($79): 2 M&E reports/mo bundled quota (`REPORT_CREATE` / `REPORT_EXPORT`), idempotent Stripe webhooks, correct plan claims in JWT. Free/Growth → `403 UPGRADE_REQUIRED` on M&E entry.

### Stage K — Testing & launch readiness
Smoke tracks (health / authenticated report journey / auth boundaries); J1→J2 on 3 templates (NLCF, FCDO, one generic); lifecycle emails ("report ready", "report due") via existing `email_service`; production hardening + **live kill-switch rehearsal on the full module**.
**Launch gate:** smoke green + J1→J2 passing on 3 templates + kill switches confirmed → flag on → **Impact M&E live**.

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
`id, user_id, created_at, updated_at, funder_report_template_id FK, linked_proposal_id FK (nullable — set if won via GrantPilot), reporting_period_start, reporting_period_end, status (DRAFT|EXTRACTING|AWAITING_REVIEW|GENERATING|DEGRADED|COMPLETE), knowledge_bank_json JSONB, gap_analysis_json JSONB, indicator_actuals_json JSONB, content_json JSONB, version`

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
- **Diagnose before fixing.** Structured diagnosis precedes any patch.
- **Revenue before elegance.** Ship what works by the date; polish post-launch.
- **Monolithic autonomous flows fail** (ReqAgent) → staged, inspectable pipelines with human gates.
- **AI writing quality:** structural rules beat cosmetic cleanup; humaniser V3 (13-point self-check); controlled uncertainty as a rule; hard vs contextual banned-word split; fact-safety guardrail on named specifics to prevent hallucination.
- **Cursor/Claude Code prompt discipline:** outcome-driven only — specify *what*, never *how*; tight scope fences; explicit STOP conditions; single task per prompt; framework-based prompts (contract lock, scope fence, canonical spec, idempotency spec, non-goals, acceptance tests).
- **Decision style:** strategic, decisive; quick binary calls when presented options; shipping over perfection.

### Session learnings (2026-06-04 — Stage F gate + F1 reliability)
- **When the failing element keeps rotating across attempts, the structure is wrong, not the element.** Stop turning knobs (timeout, concurrency, retry) and fix the architecture. Atomic all-or-nothing pipelines fail exponentially; resumability is the fix, not tuning.
- **"Contracts from imagined data" recurs in disguise** — this session it was the renderer transforming prose it assumed it understood, and tests asserting against a fictional KB namespace. Cure: bind every transform/contract to the real artefact (the reconciler KB namespace captured from a prod report; `content_json` compared before/after render).
- **Reading the actual rendered `.docx` against the knowledge bank is the only real gate for "funder-grade + zero hallucination."** The citation-BLOCK count was a red herring — the document proved the engine never had a hallucination problem.
- **Validate at the layer you changed:** a renderer fix needs a re-render; a resume fix needs a convergence run — not a full pipeline walk, and not unit tests alone (which mock OpenAI and cannot prove live behaviour).
- **Resume lowers token cost** (regenerate only failures, never re-roll good sections) while trading for more passes — counterintuitive but real.

### Existing GrantPilot tech context (for reference)
Next.js frontend + FastAPI/Python backend on Railway (GitHub CI/CD); PostgreSQL; OpenAI Chat Completions (`gpt-5.4`, env `OPENAI_MODEL_PRIMARY`, `response_format: json_object`); ThreadPoolExecutor for concurrent section generation; Resend (`support@ngoinfo.org`) for email; Stripe (hosted checkout + portal); Google OAuth + magic link; GTM/GA4 cross-domain. Core engine production-ready (22/22 smoke checks green). Humaniser framework governs both GrantPilot generation and Pranab's Accenture writing.
**Key existing spec docs:** `API_CONTRACT.md`, `OPENAI_PROMPTS_LIBRARY.md`, `FUNDING_OPPORTUNITY_GOLDEN_RULES.md`, `ENV_VARS_REFERENCE.md`, `GUARDRAILS_RUNTIME_AND_SECURITY.md`, `PROMPT_INPUTS_FIELD_MAPPING.md`, plus DB field contracts.

---

## 17. OPEN ITEMS (everything else is LOCKED)
- **Synthesis model final call:** start on `gpt-5.4` (humaniser reuse); **re-evaluate switching to a cheaper class once built, before launch** — benchmark in Stage F.
- **Vision API vendor:** "cheap multimodal API" locked as the approach; specific vendor to pick at Stage D — **D5 deferred Phase 2**.
- **Object storage final:** **RESOLVED** — Railway Buckets (`ME_DOCUMENTS_S3_*`) live in production.
- **Privacy tier (OpenDataLoader):** post-launch consideration, not in the 10-template MVP.

**Deferred (intent locked — see decision log 2026-06-04):** `report_type` persistence + generalised conditional evaluator; per-report template-version pin; pgcrypto scratch-Postgres harness (precondition before the **next** migration); D2–D4 substrate convergence (V2 brief). `FUNDER_REPORTING_ROLE_TAXONOMY.md` still grounds the R1 canonical schema.

**Pre-launch (post–Stage F gate):** Gate 3 section-review PATCH API (currently confirm-only; tests use accept-all); E3 gap-agent JSON flake needs a retry path.

**Launch list (unchanged):** WordPress CTAs; ~20 funding opportunities seeded; Stripe live mode; full J1→J2 smoke test; D4 `.docx` graceful-degradation fix.

---

## 18. CURRENT STATUS & NEXT ACTION

### Platform & schema (2026-06-04)
- **DB schema is LOCKED** and verified against production. Both launch funder templates are live in Railway Postgres: **FCDO** (`55f891ac`) and **NLCF** (manually inserted this session). Field contracts, API §12.9, and this memory were synced to deployed code — `gap_analysis_json` documented with its flattened shape (no nested `structured` wrapper); `agent_trace_json` is a `stages{}` map not `runs[]`; Alembic head **0015**, deployed.

### Stages built
- **Stages A–E:** complete and proven in production (unchanged from May 2026 walks).
- **Stage F (F1 synthesis, F2 fact-safety critic, Gate 3):** built and orchestrator-wired through the Gate 3 halt. F1 uses per-section OpenAI synthesis + citation emission/hygiene; F2 critic persists flags into `content_json`; Gate 3 confirm path exists (section PATCH API still missing — see §17).
- **Stage H (export):** built **ahead of plan order** — FCDO `.docx` via `from_scratch` python-docx render + `GET /api/reports/{id}/export` + R2 persist, so the Stage F quality gate is testable end-to-end.

### Stage F quality-gate journey — test report `6643d922` (FCDO/BridgeLight, 72-fact confirmed KB, gates 1+2 confirmed)
- First gate run produced a **real `.docx`** and proved the engine **does not fabricate** — every specific traced to the bank; the model showed strong restraint (declined to invent a programme title; refused to judge an indicator with no target).
- Surfaced **two mechanical defects, not a hallucination problem:**
  1. **Terminology corruption** — root-caused to the export **render** layer: `canonical_to_funder` applied as blind find-replace across body prose (e.g. `"risk"` → `"Risk rating / assumptions / controls"`) and template schema keys stripped from prose (deleting words like `"milestone"`). **Fixed:** terminology on labels only; schema-key prose-strip removed; whole-marker citation removal. F1/hygiene unchanged — stored prose was always clean. Confirmed by re-render of `6643d922`.
  2. **Failed sections (C `detailed_output_scoring`, D `value_for_money`)** — root-caused to OpenAI **90s timeout** under parallel load with the **full 72-fact KB** in every section call. Deeper cause: synthesis was **atomic** — every run regenerated all 8 sections and overwrote `content_json`, so one transient failure (timeout or 502) sank the whole report; success required a lucky simultaneous 8/8 (probability ≈ p⁸). Across three runs the failing section **rotated** (C/D → E → A/B) — signature of a structural problem, not a section problem.

### F1 reliability fixes shipped (2026-06-04 session; deploy `a6b430c` on Railway)
1. **Per-section KB payload trim** — each section gets only the facts/gaps it needs plus shared programme/grant/reporting context.
2. **Synthesis-only timeout retry** — one retry on transport timeout (`feature=report_synthesis` only).
3. **Concurrency reduced 5→2** — `ME_SYNTHESIS_MAX_CONCURRENCY`, default 2.
4. **Structural fix — resumable/idempotent synthesis** — generates only incomplete sections (missing / `FAILED` / empty text); **merges** into `content_json` preserving `GENERATED` / `ACCEPTED` / `human_edited` sections and sibling keys (`export`, gate stamps) byte-for-byte; sets `DEGRADED` on partial failure, clears to `DRAFT` on full completion. `test_idempotent_overwrite` inverted to assert resume. **90s timeout not raised.** Per-section incremental commit explicitly **not** taken (Session thread-safety cost not justified).
- **Convergence proof (2026-06-04):** on `6643d922`, baseline 6/8 + 2 failed → **one pass** regenerated only A+B (~30k input tokens vs ~110k for a full 8-section pass); all assertions held (monotonic, preservation, selection).

### To close Stage F
1. ~~Confirm resumable synthesis converges to 8/8 on `6643d922`~~ — **done** (convergence run 2026-06-04).
2. **Walk forward:** F2 critic → Gate 3 → render on `6643d922`.
3. **Human read** of the eight-section report against the KB — that read closes Stage F.

### Immediate next action
Execute the Stage F walk-forward on `6643d922` (F2 → Gate 3 accept-all for validation → export → human KB-grade read). Do not treat citation-BLOCK count as the quality gate.

### Companion artefacts (also in the project)
- `ME_MODULE_ARCHITECTURE_SPEC.md` — the full architecture spec (this file summarises it).
- `ME_MODULE_INTERNAL_ARCHITECTURE.html` — **internal** build diagram: entry paths, Impact bundled tier, shared core, agent pipeline, data model, kill switch. For build context, not customer-facing.
- `ME_MODULE_WIREFRAMES_BRANDED.html` — **canonical** customer-facing wireframe (NGOInfo-branded, 8 screens; tier badge reads "Impact"). Supersedes the earlier schematic `ME_MODULE_WIREFRAMES.html`.
- `ME_MODULE_PROJECT_PLAN.md` — the full sequenced plan (this file summarises it).
- `ME_COMPLIANCE_MARKET_RESEARCH.md` — the market research backing the strategy.
- `ME_AGENTIC_REUSE_MAP.md` — the detailed build-vs-reuse map.

---

*End of master memory document. To resume: attach this file and say "continue the M&E build from the project memory file." The assistant resumes at §18 — **Stage F quality gate: walk forward F2 → Gate 3 → export on `6643d922`, then human KB-grade read.**"
