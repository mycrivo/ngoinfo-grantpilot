# GrantPilot M&E Module — Architecture & Project Specification

**Module:** Donor Report Writer (working name: *GrantPilot Reports*)
**Document type:** Canonical architecture spec — source of truth for the build
**Status:** v1 DRAFT for review
**North Star:** *"GrantPilot helps you win the grant. Then it helps you keep the funder."*

**Roles:** Pranab — product/scope decisions · Claude — specs + Cursor prompts · Cursor — code execution
**Working rule:** spec → code, never code → retroactive spec. This document is the spec. Build prompts are generated against it, one outcome-driven prompt at a time.

---

## PART A — WHAT WE ARE BUILDING

### A1. The product in one paragraph

A post-award reporting product. A charity that has won a grant — through GrantPilot or anywhere else — uploads the messy reality they already have (the winning proposal, the funder's grant letter or MoU, an indicator spreadsheet, activity photos, a steering-committee deck). A team of bounded AI agents reads and organises that material, reconciles it into a single confirmed picture of the project, checks it against the specific funder's reporting requirements, asks the charity only for what's genuinely missing, then writes a funder-ready narrative report and exports it as a formatted Word document. The human confirms the facts at every gate; the agents do the labour, not the judgement.

### A2. Why it exists (the validated pain)

UK charities collectively spend an estimated 15.8 million hours a year on grant monitoring reports — roughly £204m in staff time — with the average report taking around 40 hours. A mid-size NGO running several grants produces 8–20 funder reports a year, each in a different format. The people doing this are rarely trained M&E professionals; they are programme staff with reporting bolted on. Every existing tool stops at dashboards (DevResults, DHIS2, TolaData) or generic insight (Sopact). **Nobody writes the actual funder-formatted narrative report.** That is the gap this module fills.

### A3. Strategic position (decided, summarised)

- **New paid tier on the site**, not a feature bolt-on. It serves a customer whose immediate need is *not* proposal writing.
- **Acquisition wedge:** the report is the cheaper, more urgent, more frequent entry product. NGOs who won elsewhere arrive in deadline pain, hand us their full org profile + funder relationship + indicators in the process, and become natural pre-award customers next cycle.
- **GTM:** UK + selected EU bilateral donors first; India second; US last (as the post-award specialist, not another grant-writer).
- **NGOInfo v2** launches *after* this module, with a complete grant-lifecycle story and post-award content (reporting guides, indicator frameworks) as a new organic channel.

### A4. Scope

**In scope (launch):** document upload + agentic extraction; knowledge-bank reconciliation with human confirmation; funder-aware gap check; narrative generation; fact-safety critic; funder-formatted DOCX export; 10 report templates (8 funder-specific + 2 generic fallbacks); a new billing tier.

**The 10 launch templates**

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

**Out of scope / non-goals (STOP-and-flag if a build prompt drifts here):**
field data *collection* (KoboToolbox/ODK already do this free — we ingest, not collect); dashboards or data visualisation; full logframe/Theory-of-Change management as a live system; real-time monitoring; multi-user approval workflows; autonomous agent action without human gates; Railway per-session sandboxes (the in-app job queue is the launch execution model); building any document parser, agent framework, or Word engine from scratch (all reused — see Part C).

---

## PART B — SYSTEM ARCHITECTURE

### B1. Architectural stance

- **Level 2 agentic with human-in-the-loop gates.** Bounded specialist agents coordinated by an orchestrator. Agents reason, call tools, and hand off — but every fact that enters the report is human-confirmed. Not Level 3 (open-ended autonomy): in a compliance context, an unsupervised agent that invents a beneficiary number is a funding-clawback event, not a bug.
- **Reuse the proposal stack where it fits (~70%).** The report service mirrors `proposal_service`; the input adapter mirrors `build_prompt_inputs`; section synthesis reuses the archetype + humaniser approach; billing/auth/quota patterns are inherited.
- **Backend is the single source of truth.** All reasoning, entitlements, and AI live server-side. The frontend renders and calls the API.
- **Reuse the plumbing, build the brain.** Document extraction, the agent runtime, and DOCX rendering are solved open-source problems. The funder-aware reasoning, knowledge-bank reconciliation, and fact-safety critic have no open-source equivalent — that is the moat, and the only part built from scratch.

### B2. The five layers

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — Connectors & ingestion plumbing                        │
│  n8n: funder-template ingestion, optional Drive/Gmail pull        │  REUSE
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4 — Report assembly & export                               │
│  docxtpl + 10 hand-designed funder .docx templates                │  REUSE engine / BUILD templates
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3 — M&E DOMAIN BRAIN  ◀── the moat, built from scratch     │
│  Orchestrator · Knowledge-bank reconciler · Gap/compliance ·      │  BUILD
│  Synthesis · Fact-safety critic · funder template logic           │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2 — Agent runtime                                          │
│  Claude Agent SDK: agent loop, subagents, hooks (= human gates)   │  REUSE SDK / BUILD agents
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1 — Document ingestion & extraction                        │
│  Docling: PDF/DOCX/XLSX/PPTX/images → clean structured text       │  REUSE
└─────────────────────────────────────────────────────────────────┘
        ▲ runs on ▼
┌─────────────────────────────────────────────────────────────────┐
│  EXECUTION MODEL — in-app background job queue + object storage    │
│  FastAPI + jobs table + small concurrency cap (NOT Railway sandbox)│
└─────────────────────────────────────────────────────────────────┘
```

### B3. The agent roster (Layer 3, on the Claude Agent SDK)

Each agent has one narrow, individually testable job. They are built and validated one at a time before the orchestrator is wired over the top — the staged-pipeline discipline that prevents a ReqAgent repeat.

| Agent | Single responsibility | Model class |
|-------|----------------------|-------------|
| **Orchestrator** | Inventory uploads, decide which agents to dispatch, hold state, decide when enough information exists, route to the right human gate | Strong (coordinator) |
| **Document classifier** | Label each upload: proposal / grant letter / MoU / indicator data / photo / deck | Cheap |
| **Proposal extractor** | Pull objectives, planned activities, original indicators + targets from the winning proposal | Cheap–mid |
| **Grant-terms extractor** | Pull reporting obligations, deadline, reporting period, budget, funder, special conditions from the award letter/MoU | Cheap–mid |
| **Tabular/indicator extractor** | Pull actuals-vs-targets, beneficiary counts, disaggregation, financials from Excel/CSV | Cheap–mid |
| **Vision agent** | Caption/interpret photos and image-only PDFs as evidence | Vision model (local VLM or cheap multimodal) |
| **Knowledge-bank reconciler** | Merge all extractions into one project picture; flag conflicts ("proposal says target 500, sheet says 450") | Strong |
| **Gap / compliance agent** | Compare the knowledge bank against the chosen funder template; produce the readiness score + funder-aware questions for what's missing | Strong |
| **Synthesis agents** | Write each report section (one invocation per section), reusing archetypes + humaniser rules | Mid (your existing OpenAI prompt path is viable here) |
| **Fact-safety critic** | Check every specific claim (number, name, date) in generated sections back against source documents; block/flag mismatches | Strong |

### B4. The pipeline, stage by stage (gates marked)

```
1. INTAKE          User picks the grant + funder template, uploads documents
        │
2. CLASSIFY        Classifier labels each document → routes to extractors
        │
3. EXTRACT         Specialist extractors + vision agent run concurrently (background job)
        │
4. RECONCILE       Knowledge-bank reconciler merges; surfaces conflicts
        │
   ╔═══ GATE 1 ═══╗  HUMAN: confirm/correct extracted facts; resolve conflicts
        │
5. GAP CHECK       Gap/compliance agent scores readiness against funder template
        │
   ╔═══ GATE 2 ═══╗  HUMAN: answer only the genuinely missing items (free text)
        │
6. SYNTHESISE      Synthesis agents write each section concurrently
        │
7. CRITIQUE        Fact-safety critic checks claims vs sources; flags suspects
        │
   ╔═══ GATE 3 ═══╗  HUMAN: review per-section, accept critic flags, edit
        │
8. EXPORT          docxtpl renders the funder-formatted .docx from confirmed content
```

The three gates are implemented as Agent SDK **hooks** — pause points where the pipeline halts and waits for human confirmation before continuing. This is what makes "fully agentic" safe: agents do the full workload, humans own the truth.

### B5. Execution model (decided)

**In-app background job queue + object storage. Not Railway sandboxes.** Rationale: the workload is our own code over customer-supplied (not adversarial) documents; per-session container isolation defends a risk we don't have and adds a proxy + GraphQL provisioning + session lifecycle that a solo founder must then operate. The genuine need — long-running multimodal work that can't block a synchronous request — is fully met by an async job runner with a small concurrency cap, a `report_jobs` state table, and object storage for uploads.

**Forward-compatibility requirement:** the job runner sits behind a clean `run_pipeline(report_id)` interface so the execution backend can later be swapped to Railway sandboxes (or any worker fabric) without touching the agents, if real concurrency demands it post-revenue.

**Railway Agent** (the dashboard DevOps copilot) is used only as a *build accelerator* — provisioning services, diagnosing failed deploys, opening fix PRs. It is not a product component. **OpenClaw / Hermes-style installed agents are explicitly declined** — their autonomy-first posture is incompatible with the human-gated, compliance-grade design.

---

## PART C — TECHNOLOGY & TOOLS (consolidated reuse map)

| Layer | Component | Decision | Tool | Licence | Notes |
|-------|-----------|----------|------|---------|-------|
| 1 | Document extraction | **REUSE** | **Docling** (IBM) | MIT | One converter for PDF/DOCX/XLSX/PPTX/HTML/images incl. OCR. Pure-Python-friendly. |
| 1 | Privacy-tier extraction (optional) | Reuse if needed | OpenDataLoader-PDF | OSS | 100% local, prompt-injection protection, bounding boxes. The "documents never leave our environment" selling point. |
| 2 | Agent runtime | **REUSE** | **Claude Agent SDK** (Python) | Anthropic | Agent loop, subagents, hooks (= gates), MCP. Note: from 15 Jun 2026 SDK usage on subscription plans draws a separate Agent SDK credit — plan cost accordingly. |
| 3 | M&E domain brain | **BUILD** | — | our IP | Orchestrator, reconciler, gap/compliance, critic, funder logic. No OSS equivalent exists. |
| 4 | DOCX rendering | **REUSE** | **docxtpl** (python-docx-template) | LGPL | Design each funder layout *in Word*, drop Jinja2 tags, render from a context dict. Far better than raw python-docx for fixed funder formats. |
| 4 | Report templates | **BUILD** | docxtpl `.docx` files | our IP | 10 hand-designed funder layouts. |
| 5 | Connectors / ingestion | **REUSE** | **n8n** (self-hosted, already on Railway) | fair-code | Funder-template ingestion pipeline (Firecrawl → extract → human review → POST). Optional Drive/Gmail document pull. Called as plumbing by the orchestrator — never the orchestrator itself. |
| — | Data platform integration | Far-future only | DHIS2 (export target) | BSD-3 | Not a launch component. |

### C1. Multi-provider model strategy (cost control)

The known multi-agent tax is ~15× the tokens of a single agent; pairing a strong coordinator with cheap subagents recovers most quality at a fraction of the cost (Anthropic's own figure: ~87% vs ~75% for coordinator-alone). Applied here:

- **Strong model** (coordinator/critic/reconciler/gap): the small number of high-judgement agents. Claude class.
- **Cheap model** (classifier + extractors): the high-volume, low-judgement labour. Cheap Claude/OpenAI class.
- **Vision — LOCKED:** a **cheap multimodal API** for photo/image interpretation (not the local Granite VLM at launch — lower setup burden; revisit local/private vision if a privacy tier demands it).
- **Synthesis — LOCKED for build:** stay on the existing OpenAI `gpt-5.4` path to reuse the humaniser library directly. **Re-evaluate switching synthesis to a cheaper class once the product is built and before launch**, benchmarked on real reports.

**Per-report cost ceiling — LOCKED against the tier price.** The new third tier is **$99/mo** (see C2/Part H) and includes 2 M&E reports per month. A report touching ~10 documents costs materially more than a proposal (~$1.25 ceiling today); the per-report cost must stay well inside the per-report revenue (~$49.50 at 2 reports/mo) with margin. `agent_trace_json` provides per-run cost accounting to monitor this.

### C2. Full tech & tool stack — what we build with, where it runs, what we reuse

**Guiding objective:** reuse existing infrastructure (Railway, Claude, Claude Code, Cursor, ChatGPT, n8n) first; add only what is genuinely missing. Of the five architectural layers, four are assembled from existing open-source packages; only Layer 3 (the domain brain) is written from scratch.

**Build tools (what we author code with)**

| Tool | Role for this module | Status |
|------|----------------------|--------|
| **Cursor** (GPT Codex, high compute) | Primary build tool for conventional backend: services, models, migrations, endpoints, the docxtpl assembly layer. Unchanged from the proposal build. | Existing |
| **Claude Code** | Build tool **specifically for the agent layer** — orchestrator, the specialist agents, gate hooks, agent-trace plumbing. Chosen because the agent work is multi-file/agentic and Claude Code is the reference implementation of the Claude Agent SDK we build on (learn the SDK through the tool that embodies it). | Existing access |
| **Claude** (this workspace) | Strategy, specs, Cursor/Claude Code prompts, quality review. CTO/CMO co-founder role. | Existing |
| **ChatGPT (Enterprise/Copilot)** | Pranab's personal/Accenture writing + humaniser work. Not a build tool for this module. | Existing |

**Split rule:** Cursor builds the conventional backend; Claude Code builds the agent layer. Both already available — no new spend.

**Runtime & hosting (where it runs)**

| Component | Where it runs | Notes |
|-----------|---------------|-------|
| FastAPI backend (incl. all agent code) | **Railway** (existing service) | Agents are library-powered Python objects inside this app — not a separate service or SaaS. |
| Background job worker | **Railway** (worker process / second service from same image) | Runs the async pipeline behind the swappable `run_pipeline(report_id)` interface. The lighter alternative to Railway sandboxes. |
| PostgreSQL | **Railway** (existing) | Adds the 4 new tables; holds `knowledge_bank_json`, `agent_trace_json`, job state. |
| Object storage (uploaded documents) | **Railway Buckets** (S3-compatible) | The one new infra primitive. Keeps storage on-platform/one bill. Alt: Cloudflare R2 if decoupling is wanted later. |
| n8n | **Railway** (existing self-hosted) | Funder-template ingestion pipeline + optional Drive/Gmail document pull. Operational plumbing only. |
| WordPress / NGOInfo.org | **Hostinger** (existing) | Marketing surface only. **The application does not spread onto Hostinger.** Clean separation: Hostinger = marketing site; Railway = the entire GrantPilot app including M&E. |

**Reused open-source / external components (the plumbing — not built)**

| Package / service | Layer | What it replaces building | Licence/type |
|-------------------|-------|---------------------------|--------------|
| **Docling** (IBM) | 1 — extraction | All PDF/DOCX/XLSX/PPTX/image/OCR parsing. A Python dependency in backend + worker. | MIT |
| **OpenDataLoader-PDF** | 1 — extraction (privacy tier) | Local-only parsing + prompt-injection protection. Built only when the privacy tier is offered. | OSS |
| **Claude Agent SDK** (Python) | 2 — runtime | The agent loop, subagents, hooks (= gates), context mgmt, MCP. We author agents *on top*; we don't build the runtime. | Anthropic pkg |
| **docxtpl** | 4 — export | Word-XML generation. Templates designed in Word with Jinja2 tags; rendered from a dict. | LGPL |
| **n8n** | 5 — connectors | Workflow/orchestration plumbing for ingestion. Already self-hosted. | fair-code |
| Cheap multimodal vision API | model | Photo/image interpretation (locked choice). | external API |
| OpenAI `gpt-5.4` | model | Section synthesis (locked for build; reuses humaniser library). | external API |
| Claude (strong + cheap) | model | Coordinator/critic/reconciler/gap (strong) and classifier/extractors (cheap). | external API |

**Reference-only (studied, not adopted):** `wshobson/agents`, `claude-agent-sdk` GitHub topic, orchestrator examples (Multiclaude/Agent Teams). Patterns only — their autonomy-first defaults are the wrong posture for a compliance product.

**Build accelerators (help us ship, not product components):** **Railway Agent** (dashboard DevOps copilot) for provisioning the new worker/storage services and diagnosing failed deploys. **OpenClaw / Hermes-style installed agents — explicitly declined** (autonomy-first, incompatible with human-gated design).

**Net new spend introduced by this module:** object storage (Railway Buckets — small), incremental model-API spend (the multi-agent token cost, controlled by the cheap/strong split and the cost meter), and the Claude Agent SDK credit line (separate from chat usage on subscription plans from 15 Jun 2026). Everything else reuses infrastructure already paid for.

**Where the agents reside (one-line answer):** the agents are your own Python code, built on the Claude Agent SDK, living inside the FastAPI backend process on Railway, executed by the background job worker, talking to model APIs over the network and reading/writing documents in Railway Buckets and state in Railway Postgres. Not a separate service, not SaaS, not Hostinger, not n8n, not Railway sandboxes.

---

## PART D — DATA MODEL

New tables (post-award equivalents of the proposal-side model). Field-level contracts to be locked in Sprint 0, mirroring existing `DB_FIELD_CONTRACT_*` docs.

**`funder_report_templates`** — the post-award equivalent of `requirements_json`
- `id`, `created_at`, `updated_at`
- `funder_name`, `template_name`, `region`
- `reporting_frequency` (enum: end_of_grant / annual / quarterly / interim / final)
- `report_sections_json` (JSONB) — ordered array; each: section key, archetype, word limit, required tables, required indicators, tone
- `format_rules_json` (JSONB) — funder-specific structure (e.g. FCDO RAG ratings, ECHO Single Form blocks)
- `terminology_map_json` (JSONB) — e.g. outputs/outcomes/impact vs results/outcomes
- `docx_template_ref` — pointer to the docxtpl `.docx` file
- `is_active`, `version`

**`donor_reports`** — the post-award equivalent of `proposals`
- `id`, `user_id`, `created_at`, `updated_at`
- `funder_report_template_id` (FK)
- `linked_proposal_id` (nullable FK — set when the grant was won via GrantPilot)
- `reporting_period_start`, `reporting_period_end`
- `status` (enum: DRAFT / EXTRACTING / AWAITING_REVIEW / GENERATING / DEGRADED / COMPLETE)
- `knowledge_bank_json` (JSONB) — the reconciled, human-confirmed project picture
- `indicator_actuals_json` (JSONB) — targets vs actuals, disaggregation, financials
- `content_json` (JSONB) — generated per-section content + per-section generation_status
- `version`

**`uploaded_documents`** — the new ingestion surface
- `id`, `donor_report_id` (FK), `user_id`
- `storage_ref` (object storage key), `original_filename`, `mime_type`, `size_bytes`
- `classification` (enum: proposal / grant_letter / mou / indicator_data / photo / deck / other)
- `extracted_json` (JSONB) — this document's structured extraction
- `extraction_status`, `created_at`

**`report_jobs`** — execution state for the async pipeline
- `id`, `donor_report_id` (FK)
- `stage` (enum: classify / extract / reconcile / gap / synthesise / critique / export)
- `status` (enum: queued / running / awaiting_human / failed / done)
- `agent_trace_json` (JSONB) — per-agent inputs/outputs for inspectability + cost tracking
- `error`, `started_at`, `finished_at`

**Partial-success rule (inherited):** if some sections generate and others fail, persist the report as `DEGRADED` with per-section status — never lose completed work.

---

## PART E — API SURFACE (outcome-level, not implementation)

All under the authenticated, entitlement-gated namespace. Request/response envelopes and error contracts to be specified in `API_CONTRACT.md` additions during Sprint 0.

- `POST /api/reports` — create a report (grant link optional, funder template required)
- `POST /api/reports/{id}/documents` — upload one or more documents → returns classification + extraction job
- `GET  /api/reports/{id}/knowledge-bank` — the reconciled picture + flagged conflicts (Gate 1)
- `PATCH /api/reports/{id}/knowledge-bank` — human confirmations/corrections
- `GET  /api/reports/{id}/gap-check` — readiness score + funder-aware missing items (Gate 2)
- `PATCH /api/reports/{id}/gap-answers` — free-text answers to missing items
- `POST /api/reports/{id}/generate` — run synthesis + critic
- `GET  /api/reports/{id}` — full state incl. per-section status + critic flags (Gate 3)
- `PATCH /api/reports/{id}/sections/{key}` — human edit/accept a section
- `POST /api/reports/{id}/export` — render funder-formatted DOCX (idempotent from `content_json`)
- `GET  /api/reports/{id}/job` — async pipeline status (drives the "watch it work" UI)
- `GET  /api/report-templates` — list available funder templates

---

## PART F — SECURITY & GUARDRAILS

- **Fact-safety critic is mandatory and non-negotiable.** No specific claim reaches export without being checkable against a source document or a human-entered gap answer. This is the single most important guardrail in a compliance product.
- **Prompt-injection surface.** Uploaded documents are untrusted *content*, not instructions. Extraction agents must treat document text as data; the orchestrator must never execute instructions embedded in an uploaded file. (OpenDataLoader's built-in injection protection is a mitigation if adopted.)
- **Human gates are enforced server-side**, not just in the UI — the pipeline cannot advance past a gate without a recorded human confirmation.
- **Data sensitivity.** Beneficiary data may be present in uploads. Object storage access scoped per user; documents purgeable on request; the local-extraction (OpenDataLoader) path available as a privacy tier.
- **Inherited hardening:** strict CORS to the browser origin, no test endpoints in prod, single-instance rate-limiting honoured, secrets server-side only, correct plan claims in JWT.
- **Agent containment:** every agent has explicit STOP conditions, timeouts, and a bounded toolset; `agent_trace_json` makes every run inspectable (and is the basis for cost accounting).

---

## PART G — BUILD SEQUENCE (agent-by-agent, staged)

Mirrors the locked working rhythm: one outcome-driven Cursor prompt at a time, validate, then next. Critical principle: **build and test each agent in isolation before wiring the orchestrator.** The quality gate after the engine is proven on hand-entered data (as in the earlier sprint plan) still applies — UX investment follows proven report quality.

**Phase 0 — Spec lock (no code).** Field contracts, funder template schema, report-inputs mapping, API additions, NLCF + FCDO reference templates expressed in the schema. Exit: both extreme templates fit the schema with zero gaps.

**Phase 1 — Foundations.** Data model + migrations (enforce model/migration column-name parity — the bug class that crashed the last build). Object storage wired. `report_jobs` runner behind the swappable `run_pipeline` interface. Docling integrated as the extraction adapter.

**Phase 2 — Extraction agents (one at a time).** Classifier → proposal extractor → grant-terms extractor → tabular extractor → vision agent. Each with its own test harness against real sample documents before the next.

**Phase 3 — The brain.** Knowledge-bank reconciler (with conflict surfacing) → Gate 1 → gap/compliance agent → Gate 2.

**Phase 4 — Generation + critic.** Synthesis agents (reuse archetypes/humaniser) → fact-safety critic → Gate 3. **Quality gate:** reports must be funder-grade on hand-confirmed data before UX polish.

**Phase 5 — Orchestrator.** Wire the agents into the coordinated pipeline with the three hooks/gates and full `agent_trace` logging.

**Phase 6 — Export.** docxtpl engine + the 10 funder `.docx` templates (NLCF + FCDO first, then the rest; hand-built, not via n8n).

**Phase 7 — Frontend journey.** The screens in Part I, end to end.

**Phase 8 — Billing & entitlements.** New tier, quota, regeneration limits; Stripe lifecycle with idempotent webhooks.

**Phase 9 — Testing & launch.** Smoke tracks (health / authenticated report journey / auth boundaries); J1→J2 on 3 templates; lifecycle emails ("report ready", "report due"); production hardening pass.

**Phase 10 — Post-launch.** n8n funder-template ingestion pipeline; document-assisted extraction refinements against real customer documents; templates 11+ by demonstrated demand; NGOInfo v2 with the lifecycle story.

---

## PART H — RISKS & OPEN DECISIONS

**Top risks**

| Risk | Mitigation |
|------|-----------|
| Hallucinated facts in a compliance document | Mandatory fact-safety critic + server-enforced human gates |
| Intake friction (where M&E tools die) | Document-assisted extraction removes the blank-page problem; ask only for true gaps; save/resume |
| Per-report cost vs tier price | Multi-provider split; cost ceiling set before launch; `agent_trace` cost accounting |
| Multi-agent failure modes (loops, mis-routing) | Bounded agents, STOP conditions, timeouts, staged build, full trace logging |
| Funder format accuracy | Hand-author templates against real funder guidance; NLCF + FCDO extremes first |
| Scope creep into an M&E platform | Part A4 non-goals; STOP-and-flag discipline |
| Solo-founder operational load | Lighter in-app job queue over Railway sandboxes; reuse over build at every layer |

**Decisions — now LOCKED (resolved 2026-05)**
1. **Tier & price — LOCKED.** New **third tier at $99/mo**, named **"Impact Pro"** — everything in Impact plus **2 M&E reports/month**. Long-run intent: consolidate to two paid plans (retire or reprice the $79 tier) a couple of months post-launch based on market acceptance. Sets the per-report cost-ceiling target (well inside ~$49.50/report revenue).
2. **Extraction engine — LOCKED.** Docling as default; OpenDataLoader-PDF as the future privacy tier.
3. **Synthesis model — LOCKED for build.** OpenAI `gpt-5.4` (direct humaniser reuse); re-evaluate switching to a cheaper class once built and before launch.
4. **Vision — LOCKED.** Cheap multimodal API (not local Granite VLM at launch).

**Naming note:** "Impact Pro" reads as the natural step above "Impact," implies "everything in Impact plus more," and collapses cleanly into a two-tier ladder ("Impact" + "Impact Pro") when the $79 tier is retired/repriced. Marketing positioning line carries the story: *"win the grant, keep the funder."*

---

*End of spec v1. Companion artefact: `ME_MODULE_WIREFRAMES` (visual screens). On approval, Phase 0 spec docs are generated against this document.*
