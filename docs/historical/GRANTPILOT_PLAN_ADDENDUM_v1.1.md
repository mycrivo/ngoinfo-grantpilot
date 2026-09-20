# GrantPilot Completion Plan — Addendum v1.1
**Closes four gaps in v1.0: the wireframing workflow, concrete agent roles, Human Writing Instructions coverage, and the build-vs-borrow inventory — plus the Grantable teardown recommendations mapped to phases.**
**2026-07-25. Reads with GRANTPILOT_COMPLETION_PLAN_v1.0.md; supersedes nothing.**

---

## 1. The wireframing workflow — exact steps

Rule R4 said "mockups before build." This is the machinery. We already hold the assets to do this well: the branded M&E wireframes HTML, the brand guidelines, and the frontend spec. The process per screen set:

**Step 1 — Screen inventory and journey map** (Claude drafts, Pranab approves). Which screens exist or change, in journey order, per module. Phase 1 design track: the six M&E screens. Phase 3 design track: the org-profile flow (~4 screens), the Fit Scan Decision Brief page, and Proposal workspace refinements.

**Step 2 — State ledger per screen** (Claude drafts). Every state a screen can be in, written in NGO language: default, waiting (with the real measured durations, not spinners-forever), degraded, error, empty, over-quota, and the interaction states (conflict resolution, flag review). This is where the last build failed — screens were designed for the happy path and the in-between states leaked engine vocabulary.

**Step 3 — Branded HTML mockups** (Claude produces). One HTML file per screen set, every state rendered, built on the existing brand system. These are review artifacts, not code to ship.

**Step 4 — NGO-shoes walk on the mockups** (Pranab + Claude, before any build). The same walk discipline we used on the live screens, applied before the cost is sunk. Findings amend the mockups, not a backlog.

**Step 5 — Approval.** The approved mockup file becomes the acceptance artifact named inside the build package spec. "Matches the mockup, all states" is an EARS-checkable criterion.

**Step 6 — Implementation.** Cursor builds with Design Mode against the mockup — Design Mode accelerates faithful implementation of an approved design; it is never used to improvise one. Bugbot `/review` pre-push as usual.

**Step 7 — Post-build walk.** Screens compared to mockups state by state. Deviations are defects, not interpretations.

---

## 2. Agent roles — concrete definitions

Two distinct layers, both defined as files in Phase 0.

### 2.1 Development-tooling agents (repo files)

| Role | Home | Charter (summary) |
|---|---|---|
| **Builder** | Cursor + `.cursor/rules` + AGENTS.md | Builds from versioned package specs only. Plan-first; AMBER plans STOP for owner approval. Never certifies, never audits, never edits goldens or the constitution. |
| **Auditor** | `.claude/agents/auditor.md` | Read-only. Evidence with pointers or nothing. Verdict scale CONFIRMED / REFUTED / PARTIAL / CANNOT DETERMINE. Forbidden from recommendations. (The charter that produced the hypothesis audit, made permanent.) |
| **Harness runner** | `.claude/agents/harness-runner.md` + `run-harness` skill | Executes golden packs, emits the five-layer scorecard with SHA + dataset version + model config in the header. Runs headless in CI and post-deploy. |
| **Security reviewer** | `.claude/agents/security-reviewer.md` | Our Layer-2 gate: `/security-review` profile on every PR; escalation rules for engine-prompt and parsing changes. |
| **NGO reviewer (judge)** | `.claude/agents/ngo-reviewer.md` | LLM-as-judge persona of the M&E officer: scores readability, tone, and V4 conformance in the harness. Calibrated against Pranab-rated samples before its scores gate anything — an uncalibrated judge is noise. |
| **Adjudicator** | Claude (this chat) + `adjudicate-run` skill | Scores runs against goldens, classifies gaps into the four bins, owns sequencing. The one role that never moves into the repo, because it is the domain-judgment seat. |

Deterministic hooks (not agents, but the enforcement floor): funder/fixture-string guard on engine paths; golden-file and constitution-file write guard; secrets patterns alongside Gitleaks.

### 2.2 Product engine agents (bounded AI services)

The teardown's "bounded AI services" checklist becomes the **mandatory header of every engine agent definition**: input contract, output schema, prompt version, failure mode, quota behaviour, persistence rule, user-visible caveat. No engine agent exists without all seven.

| Engine agent | Model policy | Package |
|---|---|---|
| Reader (M&E) | Strongest available, full-bundle context | P2 |
| Validator | Pure code, no model | P2 |
| Writer (M&E) | Benchmarked on the harness: current frontier vs gpt-5.4, readability scored separately | P4 |
| Meaning Checker (qualitative) | Strong model, full-ledger context | P5 |
| Org-profile Reader | Same pattern as M&E Reader, org ontology | Phase 3 |
| Fit Scan analyst | Existing GP-F02 contract; re-certified by its golden pack | Phase 3 |
| Proposal writer + Submission Reviewer | Existing contracts; measured first; P5 primitives backported only on evidence | Phase 3 |

---

## 3. Human Writing Instructions V4 — wired everywhere words are produced

V4 is house style — engine-owned knowledge under the contract (it is how *we* write, not how a funder writes; funder tone overrides live in template data). It applies at every writing surface, with a named mechanism at each:

| Writing surface | Mechanism |
|---|---|
| M&E report prose (Writer, P4) | V4 as a versioned prompt component; NGO-reviewer judge scores conformance in the harness |
| Gap questions (P6) | V4 phrasing rules in the question-authoring contract; golden Layer 3 question script is the reference register |
| Critic flag copy + all Gate 1/2/3 microcopy | V4 checklist applied at mockup approval (step 4 above), so copy is fixed before build |
| Proposal sections + Submission Review findings text | Same prompt component; conformance added to the Proposal golden pack |
| Fit Scan Decision Brief prose | Same, via the Fit Scan golden pack |
| Generic template prose | Inherits the Writer's V4 component by construction |
| Org-profile drafter output | Same component, Phase 3 |
| Transactional emails | Existing spec re-checked against V4 once, in Phase 0 housekeeping |

**Open item, third request: V4 has not yet been supplied to me.** It is now a Phase 0 blocker — the judge cannot be calibrated and the golden record's prose-conformance pass cannot run without it.

---

## 4. Build vs borrow — the inventory

Principle: **borrow plumbing, never the moat.** Goldens, the ontology, contracts, funder data packs, and the honesty machinery are ours and are the business. Parsing, crawling, eval-running, and scaffolding are commodities where the open-source ecosystem is ahead of anything we would build. The teardown said this first: "Do not build document parsing engines from scratch if Docling or equivalent is the selected parser."

| Capability | Decision | Rationale |
|---|---|---|
| Document parsing (PDF/DOCX/XLSX) | **Keep Docling** (already committed) | Independent 2026 comparisons consistently place Docling top for complex-table fidelity — exactly our load-bearing case (logframes, finance grids). MarkItDown is 50–100× faster but shallow on table structure — wrong trade for us; Marker is GPU-hungry. No change, validated. |
| Web scraping (org-profile builder) | **Firecrawl managed API first; revisit Crawl4AI at volume** | Managed reliability and zero infrastructure suit a solo founder; it also parses PDFs/DOCX in the same call. Crawl4AI (open source, self-hosted) wins on cost at high volume — a Phase-4+ revisit, not a launch decision. |
| Structured extraction | **Anthropic structured outputs + Pydantic** (already our pattern) | No new dependency; the Reader's typed ledger is a schema, not a framework. |
| Eval harness | **Bespoke assertions, borrowed runner** — pytest + DeepEval components for dataset management and judge scaffolding | The five-layer assertions ARE the moat and stay ours; the running/reporting machinery is commodity. Judge calibration follows standard EDD practice. |
| Spec-driven scaffolding | **Adopt the conventions** (AGENTS.md constitution, EARS criteria, Spec → Plan → Tasks → Implement), take tooling à la carte | The convention is the value; tool lock-in is not. |
| DOCX generation | **Keep python-docx path** | Working, contract-tested. |
| Agent orchestration frameworks (LangGraph et al.) | **Deliberately not adopted** | Our pipeline is a typed, staged workflow with human gates — plain code + SDK. A framework here is death-star risk. |
| Vector DB / RAG stack | **Deliberately not adopted** | Full-context reading at 1M-token windows makes chunk-retrieval unnecessary at our document volumes; RAG would reintroduce the fragmentation we just diagnosed. |
| Community agent/hook packs | **Reference, don't import** | We copy patterns for `.claude/agents` and hooks; we do not vendor fifty unused agent definitions into the repo. |

---

## 5. The Grantable teardown, mapped to phases

The teardown's recommendations, checked against where they now live:

| Teardown recommendation | Status / home |
|---|---|
| Knowledge Bank as the compounding asset — "every Fit Scan, proposal, and report strengthens the reusable Knowledge Bank" | **The strategic spine.** Implemented as the shared org ontology (Phase 3 org-profile builder) feeding all three modules, plus the M&E confirmed ledger. This is also the one-ledger-many-reports upsell. |
| Fit Scan → **Decision Brief** structure (recommendation, hard gates, alignment, readiness, risks, missing data, effort, requirements preview, next action) with "Recommended / Apply with Caveats / Not Recommended" labels and a hard ban on win-probability language | Becomes the Fit Scan golden pack's report layer + the Decision Brief mockup, Phase 3. The banned-language list joins the Fit Scan forbidden outputs. |
| Proposal Builder: checklist-led workflow, assumptions panel, source panel | Proposal golden pack + workspace mockup refresh, Phase 3 — adopted where the measurement walk shows the gap, per anti-death-star. |
| **Submission Readiness Review**: four passes (compliance, persuasiveness, evidence safety, polish) with CRITICAL / IMPORTANT / SUGGESTION severity, where only CRITICAL blocks the export badge | Two adoptions. (a) The severity taxonomy is the **fix for Gate 3's "Must fix before download" wall** — it goes into P5's flag model for M&E now. (b) The four-pass review becomes the Proposal module's meaning-checker, built on P5 primitives, Phase 3. |
| Donor Intelligence Lite, Phase 1 (opportunity-level donor card from existing `funding_opportunities` fields) | Cheap and real. Parked as a Phase 4 product decision for Pranab — scope, not engineering. |
| Artefacts not conversations; bounded AI services; Cursor prompt governance (scope-of-one, STOP conditions, contract references) | Already absorbed into the constitution and package lifecycle. The bounded-services checklist is now mandatory (§2.2). |
| Pricing: introduce **Impact Pro $99** carrying M&E, rather than M&E inside Impact $79 | **Open product decision, flagged for Pranab at Phase 4** alongside Stripe live mode. Teardown's argument: reporting is high-pain, high-value — do not underprice it. Not an engineering call. |

---

## 6. Phase 0 checklist (amended)

Governance files + hooks; CI eval gate with Bridgelight assertions and SHA lineage; sealed NLCF golden; decontamination + VfM + cover truth; housekeeping debt; **plus, from this addendum:** the six dev-agent definition files and three skills; the V4 prompt component (blocked on receipt of V4); the M&E screen inventory and state ledgers drafted so Phase 1's design track starts warm.

**Decisions surfaced for Pranab (none block Phase 0):** Impact Pro pricing (Phase 4), Donor Card Lite scope (Phase 4). **Blocker owned by Pranab: send Human Writing Instructions V4.**
