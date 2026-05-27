# M&E Module — Master Project Plan

**Module:** GrantPilot Donor Report Writer (tier: **Impact Pro**, $99/mo)
**Structure:** Modular monolith — isolated folder in the existing repo, one removable seam
**Document type:** Sequenced build plan — what to do, what it comes from, why it sits where it does
**Companions:** `ME_MODULE_ARCHITECTURE_SPEC.md` (the what/why), `ME_MODULE_WIREFRAMES.html` (the visual target)

---

## How to read this plan

The plan runs in **stages A→L**. Stages A–B are governance and specification with **no product code**. Stage C lays foundations and proves the kill switch *before any agent exists*. Stages D–K build the module. Stage L is post-launch.

Three principles drive the ordering:

1. **Isolation before code.** The governance and isolation scaffold (Stage A) exists before anything it must govern. The kill switch is proven on an empty module (Stage C) before the module has anything worth killing — because if you can't unplug it empty, you can't unplug it full.
2. **Spec before build.** Every contract is locked (Stage B) before the code it governs is written. This is the discipline that the ReqAgent failure taught.
3. **Validate before automate / before polish.** The engine must produce funder-grade reports on hand-confirmed data (quality gate after Stage F) before any UX investment, and before the orchestrator wires everything together. Effort follows proven value, not hope.

### Provenance legend — "what comes from where"

| Tag | Meaning |
|-----|---------|
| **EXISTING** | Already in the repo / infra; we extend or reuse, don't rebuild |
| **REUSE** | External open-source package or service pulled in (Docling, Agent SDK, docxtpl, n8n) |
| **BUILD** | Written from scratch — our IP, no equivalent exists |
| **DECISION** | A locked choice (recorded in the decision log) |

### Who does what

| Actor | Role |
|-------|------|
| **Pranab** | Scope/product decisions, runs prompts, reports back, final calls |
| **Claude** (this workspace) | Specs, contracts, governance files, Cursor/Claude Code prompts, quality review |
| **Cursor** | Conventional backend code (services, models, migrations, endpoints, docxtpl layer) |
| **Claude Code** | The agent layer specifically (orchestrator, agents, gates, trace) |

---

## STAGE A — Governance & isolation scaffold
*No product code. This is the fence everything else is built inside.*

**Why first:** these files govern every later prompt and *define* the isolation that makes the module killable. They must exist before Cursor writes anything, or there is nothing constraining it.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| A1 | `.cursor/rules/` set (global, isolation, backend, agents, scope-fence) | BUILD | Claude | Auto-loaded rules that constrain every prompt. The isolation rule (M&E imports core, never reverse) is the cardinal one. |
| A2 | `REPO_MAP_ME_MODULE.md` | BUILD | Claude | Tells Cursor exactly where the module lives and what it may touch — stops M&E code scattering through the existing tree. |
| A3 | `ME_MODULE_KILL_SWITCH.md` | BUILD | Claude | The three kill procedures (un-mount + UI flag, worker→0, drop 4 tables). Writing it now forces the isolation to be real. |
| A4 | `ME_MODULE_DECISION_LOG.md` (seeded with locked decisions) | BUILD | Claude | One legible record of every deliberate choice; Cursor appends here rather than pivoting silently. |
| A5 | Drop `ARCHITECTURE_SPEC` + `WIREFRAMES` into repo | EXISTING | Pranab | The reference the rules point at. |

**Exit gate:** the rules, repo map, and kill-switch doc agree on one boundary and one seam. If the kill-switch doc can't be written cleanly, the isolation design isn't done — fix it here, not later.

---

## STAGE B — Phase 0 specification lock
*No product code. The contracts become truth; code obeys them.*

**Why here:** nothing can be built correctly until the data shapes, the funder template schema, and the API surface are fixed. Locking them now prevents the contract-drift class of failure.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| B1 | 4 field contracts: `donor_reports`, `funder_report_templates`, `uploaded_documents`, `report_jobs` | BUILD | Claude | Column-level truth for the new tables; FKs point inward to core only. |
| B2 | `FUNDER_TEMPLATE_SCHEMA.md` | BUILD | Claude | The JSONB shape: sections, archetypes, word limits, required tables, terminology, tone. The heart of the funder-aware engine. |
| B3 | NLCF + FCDO reference templates expressed in the schema | BUILD | Claude | **Schema stress test.** NLCF (simple) and FCDO (complex/RAG/VfM) are the two extremes; if both fit with zero gaps, the schema holds. |
| B4 | `REPORT_INPUTS_FIELD_MAPPING.md` | BUILD (mirrors EXISTING `PROMPT_INPUTS_FIELD_MAPPING.md`) | Claude | How NGO profile + template + confirmed knowledge bank assemble into the synthesis inputs. |
| B5 | `API_CONTRACT.md` — M&E additions | EXISTING (extend) | Claude | The endpoints from spec Part E, in a clearly-marked M&E section. |
| B6 | Just-in-time additions: `OPENAI_PROMPTS_LIBRARY` (report archetypes), `PRICING_AND_ENTITLEMENTS` (Impact Pro), `GUARDRAILS_RUNTIME_AND_SECURITY` (critic mandate, injection fence, worker kill switch), `ENV_VARS_REFERENCE` (storage/vision/SDK vars), `DEPENDENCIES_ME_MODULE`, `DEV_ENVIRONMENT_SETUP` (worker locally) | EXISTING (extend) + BUILD | Claude | Extend existing canon as each is needed; named, not valued, for secrets. |

**Exit gate:** both reference templates fit the schema with no gaps; every synthesis input has a mapped source; the API additions don't alter any existing contract.

---

## STAGE C — Foundations & the proven kill switch
*First code. Prove isolation on an empty module before adding intelligence.*

**Why here:** lay the rails (module skeleton, data, storage, worker, extraction adapter) and confirm all three kill switches work while the module is still empty and harmless.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| C1 | Module skeleton: isolated `reports/` package, single router-include seam, frontend feature flag | BUILD | Cursor | The seam that makes it pluggable. One line mounts it; one flag shows it. |
| C2 | Migrations + models for the 4 tables (column-name parity enforced) | BUILD | Cursor | The bug class that crashed the last build is killed at the first migration. FKs inward only — no core table altered. |
| C3 | Object storage wiring | REUSE (Railway Buckets) | Cursor | The one new infra primitive; uploads land here, scoped per user. |
| C4 | Background worker + `run_pipeline(report_id)` interface | BUILD (on EXISTING Railway) | Cursor | The runtime kill switch (worker→0) and the swappable execution seam for any future backend. |
| C5 | Docling extraction adapter (thin wrapper) | REUSE (Docling) | Cursor | Layer 1 done by import, not authorship. Returns clean structured text to the agents. |

**Exit gate — the kill-switch rehearsal:** with the empty module mounted, confirm (a) un-mounting the router + flagging off the UI leaves GrantPilot fully working, (b) scaling the worker to zero affects nothing in the proposal product, (c) dropping the 4 tables leaves the core schema intact. **Do not proceed until all three pass.**

---

## STAGE D — Extraction agents
*Built one at a time, each tested in isolation. Claude Code's domain.*

**Why here:** the foundations exist; now teach the module to read documents. One agent at a time with its own test harness against real sample documents — the staged-pipeline discipline, never a monolithic flow.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| D1 | Document classifier agent | BUILD (on REUSE Agent SDK) | Claude Code | Labels each upload, routes to the right extractor. Cheap model. |
| D2 | Proposal extractor agent | BUILD | Claude Code | Objectives, activities, original indicators/targets from the winning proposal. |
| D3 | Grant-terms extractor agent | BUILD | Claude Code | Reporting obligations, deadline, period, budget, funder from the award letter/MoU. |
| D4 | Tabular/indicator extractor agent | BUILD | Claude Code | Actuals-vs-targets, beneficiary counts, disaggregation, financials from Excel/CSV. |
| D5 | Vision agent | BUILD (on REUSE cheap multimodal API) | Claude Code | Captions/interprets photos and image-only PDFs as evidence. |

**Exit gate:** each agent passes its own test harness on real sample documents before the next is built.

---

## STAGE E — The brain (reconciliation + gaps + first two gates)

**Why here:** raw extractions are useless until merged into one confirmed picture and checked against the funder's requirements. This is where the moat starts.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| E1 | Knowledge-bank reconciler agent (surfaces conflicts) | BUILD | Claude Code | Merges extractions; flags contradictions ("proposal 500 vs sheet 450") instead of silently averaging. |
| E2 | Gate 1 — confirm facts (server-enforced) | BUILD | Cursor | Pipeline cannot advance without recorded human confirmation. The truth-ownership gate. |
| E3 | Gap/compliance agent | BUILD | Claude Code | Holds funder template against knowledge bank; produces readiness score + funder-aware missing-item questions. |
| E4 | Gate 2 — fill only the gaps (server-enforced) | BUILD | Cursor | Asks only for what's genuinely missing — the intake-friction killer. |

---

## STAGE F — Generation + critic + the quality gate

**Why here:** with confirmed, complete inputs, write the report and check it. This stage ends in the most important gate in the whole plan.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| F1 | Synthesis agents (per section) | BUILD (reuse EXISTING archetypes/humaniser, `gpt-5.4`) | Claude Code + Cursor | Writes each section; reuses the humaniser rules (challenges + adaptation, no glossy spin). |
| F2 | Fact-safety critic agent | BUILD | Claude Code | Checks every specific claim back against sources; flags mismatches. Mandatory, non-negotiable. |
| F3 | Gate 3 — review per section, accept flags, edit | BUILD | Cursor | Human stays the author. |

**QUALITY GATE (the plan's hinge):** reports must be **funder-grade on hand-confirmed data** — graded against the humaniser rules, no hallucinated specifics, critic catching planted errors. **No UX polish, no orchestrator, no further templates until this passes.** If quality isn't here, nothing downstream matters.

---

## STAGE G — Orchestrator

**Why here:** only now, with every agent individually proven, wire them into one coordinated pipeline. Building the orchestrator earlier would mean coordinating agents that don't yet work.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| G1 | Orchestrator agent + 3 gate hooks + full `agent_trace` logging | BUILD (on REUSE Agent SDK) | Claude Code | Dispatches agents, holds state, enforces gates, records every run for inspectability + cost accounting. |

---

## STAGE H — Export

**Why here:** the content exists and is confirmed; render it to the funder's format.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| H1 | docxtpl render engine for reports | REUSE (docxtpl) | Cursor | Word-XML generation by library, not authorship. Idempotent from stored content. |
| H2 | 10 funder `.docx` templates (NLCF + FCDO first, then the rest) | BUILD | Pranab + Claude | Hand-designed in Word. Not via n8n (that's post-launch automation). |

---

## STAGE I — Frontend journey

**Why here:** backend proven end-to-end; now build the 8-screen experience, entirely behind the feature flag so it ships dark until ready.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| I1 | The 8 screens (dashboard → template → upload → watch → Gate 1 → Gate 2 → Gate 3 → export) | BUILD (EXISTING Next.js patterns) | Cursor | Renders the wireframes; calls the API only; no business logic. Behind the flag = a code kill switch. |

---

## STAGE J — Billing & entitlements

**Why here:** the product works; now make it purchasable and gated.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| J1 | Impact Pro tier ($99), 2 reports/mo quota, regeneration limits, idempotent webhooks | EXISTING (extend Stripe) | Cursor | Reuses the proposal billing lifecycle; correct plan claims in JWT. |

---

## STAGE K — Testing & launch readiness

**Why here:** prove the whole thing green, including a live kill-switch rehearsal, before exposing the tier.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| K1 | Smoke tracks (health / authenticated report journey / auth boundaries) | EXISTING (extend) | Cursor | Define the green count up front (e.g. 20/20). |
| K2 | J1→J2 journey on 3 templates (NLCF, FCDO, one generic) | BUILD | Pranab + Claude | The end-to-end proof. |
| K3 | Lifecycle emails ("report ready", "report due") | EXISTING (extend `email_service`) | Cursor | Idempotent, suppressible, logged. |
| K4 | Production hardening + **live kill-switch rehearsal** | EXISTING (extend) | Cursor + Pranab | CORS, no test endpoints, rate limiting; re-run the three kill switches on the full module. |

**Launch gate:** smoke green, J1→J2 passing on 3 templates, kill switches confirmed on the full module. Flag on → Impact Pro live.

---

## WORKSTREAM T — Template sourcing (parallel track, starts in Stage A)

*Runs alongside the build, not after it. The funder templates are not something you possess — they are assembled from public sources, sharpened with real grantee reports, and scaled later by automation. This track has a longer lead time than the code (relationships take weeks), so it starts at Stage A and feeds Stage B and Stage H.*

**The sourcing ladder (in priority order):**
1. **Public funder documentation** — author the first draft of every template from what funders publish themselves.
2. **FundsforNGOs Premium** — already paid for; mine it for reporting guidance and sample reports before buying anything new.
3. **Real grantee reports** — the richest source and the moat. A past submitted report reveals the true format. The product itself becomes the collection mechanism over time; early on, ask friendly NGOs directly.
4. **n8n ingestion pipeline (Stage L)** — scales templates 11+ *after* launch. Not how the first 10 are made.

**Per-funder source map (the 10 launch templates):**

| # | Template | Primary public source | Grantee report needed? |
|---|----------|----------------------|------------------------|
| 1 | NLCF End-of-Grant | NLCF grant-holder reporting guidance (website) | Helpful, not essential |
| 2 | NLCF Annual Progress | NLCF "tell us how it's going" guidance | Helpful, not essential |
| 3 | FCDO Annual Review | **DevTracker** — real published annual reviews + logframes, downloadable (JSON/docs); FCDO PrOF + smart guides | No — public examples are abundant |
| 4 | Comic Relief End-of-Grant | Comic Relief funded-partner reporting template (grantee pages) | Helpful |
| 5 | USAID Quarterly Performance | Public ADS guidance, PMP/IPTT partner toolkits | Helpful for exact table layout |
| 6 | USAID Annual Performance | Same ADS/PMP public guidance | Helpful for exact table layout |
| 7 | ECHO Single Form — Interim | **Published, standardised** Single Form + official EU guidelines | No — fully public |
| 8 | ECHO Single Form — Final | Same published Single Form guidance | No — fully public |
| 9 | Generic Institutional Donor | Synthesised from common patterns across 3–8 | No |
| 10 | Generic CSR Project Report | Indian CSR reporting norms; FundsforNGOs + CSR portal guidance | Helpful for India specifics |

**Read of the map:** FCDO (#3) and both ECHO forms (#7, #8) are fully sourceable from public material — which is exactly why FCDO + NLCF are the schema-stress-test pair in Stage B (one public-rich, one grantee-helped). The USAID tables (#5, #6) and Comic Relief (#4) are public in structure but sharper with one real grantee report. India generic (#10) benefits most from a real CSR report.

**Workstream steps:**

| Step | Produces | From | Who | Timing |
|------|----------|------|-----|--------|
| T1 | Outreach to warmest NGO contacts / pilot charities for a past report submitted to any of the 10 funders ("show me yours, I'll build your template free") | BUILD (relationships) | Pranab | **Start at Stage A** — longest lead time |
| T2 | Public-source dossier for NLCF + FCDO (the two reference templates) | EXISTING public docs + DevTracker | Pranab + Claude | Feeds Stage B (B3) |
| T3 | Public-source dossiers for the remaining 8 | Public docs + FundsforNGOs | Pranab + Claude | Feeds Stage H (H2), staggered |
| T4 | Grantee reports gathered where the map flags "helpful/essential" | BUILD (relationships) | Pranab | Ongoing through Stages B–H |
| T5 | Hand-authored templates in the schema (NLCF + FCDO first, then 8) | BUILD | Claude + Pranab | B3 then H2 |

**Dependency:** T2 must complete before Stage B can author the reference templates; T3/T5 feed Stage H. The whole workstream is the input supply chain for the funder-template IP — without it, Stage B and Stage H have nothing real to encode.

**The reframe:** the absence of a ready-made template library is the same fact as the absence of a competitor. You assemble the bank — you don't find it — and that assembly *is* the moat.

---

## STAGE L — Post-launch (validate-then-automate)

**Why last:** these are investments justified only by real customers and real documents.

| Step | Produces | From | Who | Why here |
|------|----------|------|-----|----------|
| L1 | n8n funder-template ingestion pipeline (Firecrawl → extract → human review → POST) | REUSE (n8n) | Pranab + Claude | Scales templates 11+ once the first 10 prove demand. |
| L2 | Extraction refinement against real customer documents | BUILD | Claude Code | Tune on real mess, not guessed mess. |
| L3 | Templates 11+ by demonstrated demand | BUILD | Pranab + Claude | Customer-led, not speculative. |
| L4 | NGOInfo v2 with the lifecycle story + post-award content | EXISTING (Hostinger/WordPress) | Pranab + Claude | The second acquisition channel; launches after the module exists to point at. |

---

## The critical path (what blocks what)

```
A (governance) ─► B (spec lock) ─► C (foundations + kill-switch rehearsal)
                                          │
                                          ▼
                                   D (extraction agents, one by one)
                                          │
                                          ▼
                                   E (reconcile + gaps + gates 1–2)
                                          │
                                          ▼
                                   F (synthesis + critic + gate 3)
                                          │
                                     ◆ QUALITY GATE ◆   ← nothing past here until reports are funder-grade
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                   G (orchestrator)  H (export+templates)  (H2 templates can run parallel)
                          └───────────────┼───────────────┘
                                          ▼
                                   I (frontend) ─► J (billing) ─► K (test + launch)
                                          │
                                          ▼
                                   L (post-launch: n8n, refinement, v2)
```

**Hard gates that stop the build (in order):**
1. **End of A** — isolation boundary coherent; kill-switch doc writable.
2. **End of B** — both extreme templates fit the schema; no contract drift. *(Requires Workstream T2 complete — the NLCF + FCDO source dossiers.)*
3. **End of C** — three kill switches proven on the empty module.
4. **End of F** — reports funder-grade on hand-confirmed data. *The hinge.*
5. **End of K** — smoke green + kill switches re-proven on the full module.

**Parallel input supply:** Workstream T (template sourcing) runs from Stage A onward and feeds Stage B (T2) and Stage H (T3/T5). It is the supply chain for the funder-template IP — start T1 (grantee outreach) immediately, as it has the longest lead time of anything in the plan.

---

## What this plan deliberately protects

- **The proposal product** — one-way dependency, single seam, separate worker, separate tables. GrantPilot keeps running whatever happens to M&E.
- **The launch** — if M&E delays or misbehaves, it's flagged off and worker-zeroed; the proposal product and its launch are untouched.
- **You** — reuse at four of five layers; you author only the moat. The staged build means a failure is contained to one agent, not the system.
- **Legibility** — the decision log and agent traces mean future-you (or a future hire) can read how and why it was built.

---

*On approval of this plan, Stage A drafting begins: the `.cursor/rules/` set first, then `REPO_MAP` + `KILL_SWITCH`, then the Stage B contracts. In parallel, Workstream T begins immediately with T1 — reaching out to friendly NGOs for a past funder report — since it carries the longest lead time in the whole plan.*
