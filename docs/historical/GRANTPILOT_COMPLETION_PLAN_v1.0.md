# GrantPilot Completion Plan
**From current state to a finalised GrantPilot module — v1.0, 2026-07-25**
**Scope:** M&E engine rebuild, Fit Scan, Proposal Writer, org-profile auto-builder, generic M&E template, launch surfaces. WordPress side excluded (handled).
**Governing documents:** ME Engine Behavioural Contract v1.0 (ratified), Golden Record FCDO Bridgelight v1.0, Bridgelight Run Adjudication v1.0, Hypothesis Audit (commit a74d5e3).

---

## Part A — Lessons codified as standing rules

Each lesson from the last six months, converted into a rule with a named enforcement mechanism. A rule without an enforcement mechanism is a wish — that is lesson zero, and it is why every row here has a third column.

| # | What happened | Standing rule | Enforced by |
|---|---|---|---|
| R1 | We had robust documentation; Cursor drifted anyway. Docs described intent; nothing checked conformance at build or merge time. | **Docs don't govern; gates govern.** The constitution lives in the repo where agents auto-load it, and conformance is checked by machines, not memory. | `AGENTS.md` + `CLAUDE.md` + `.cursor/rules` (one source, mirrored); CI eval gate; deterministic hooks |
| R2 | The golden record arrived six months into the build and immediately triggered a rebuild. | **Golden before build.** No module or major feature starts without its golden pack: fixtures, expected outputs, forbidden outputs, acceptance shape. | Package lifecycle step 1; CI refuses eval-gated merges for modules without a registered golden pack |
| R3 | Three audit cycles read code and produced finding registers; quality got worse. The one audit that worked measured output against ground truth first. | **Measure outputs first; read code second, and only with a specific question.** | Adjudication-before-interrogation pattern (now standard); audit briefs must cite the measurement that motivated them |
| R4 | M&E screens were built without mockups; the result "looked like a coder built it," and Gate 1/Gate 3 actively damaged trust. | **Mockups and a state ledger before any frontend build.** Every screen is designed including waiting, degraded, error, empty and over-quota states, in NGO language, before a build package exists. | Design artifacts are package prerequisites; Cursor Design Mode used against the mockups, never freestyle |
| R5 | The builder graded its own work; local green certified regressions. | **Builder never certifies.** Certification = harness score + independent review. | CI eval gate (harness); Bugbot `/review` pre-push; Claude Code PR review + `/security-review` |
| R6 | June's remediation plan was half-shipped — the checker landed, the semantic layer never existed on any branch — and nobody noticed for six weeks. | **Plan-to-merge traceability.** Every planned package has a named landing check; every eval run records the deployed SHA it ran against. | Package ledger with landing checks; harness prints SHA + dataset version + prompt version in every report (run lineage) |
| R7 | Extractor prompts quoted Bridgelight's dates and expected counts verbatim — fixture answers coached into the engine. | **Sealed fixtures and prompt hygiene.** At least one golden pack per module is sealed (never quoted anywhere); no funder or fixture string may exist in engine code or prompts. | Sealed NLCF golden; deterministic pre-commit/PreToolUse hook greps engine paths for funder/fixture strings and blocks the write |
| R8 | Per-section synthesis inputs were never persisted; prose quality was undiagnosable by design for months. | **Persist every stage's inputs and outputs.** The run bundle is a product requirement. | Contract cross-cutting duty; schema check in CI |
| R9 | Symptoms were converted into fix-prompts for Cursor instead of updating the spec — the loop the SDD literature now names as the core anti-pattern. | **Fix the spec, not the chat.** When behaviour is wrong, the spec or golden is amended first; the build follows the amended artifact. | CTO discipline; package specs are versioned files, and Cursor builds only from them |
| R10 | Scoped packages were the right instinct all along — what was missing was the gate underneath them. | **One scoped package at a time, under a gate.** Unchanged, now enforceable. | Everything above |

---

## Part B — The July 2026 toolchain and how we use it

### Cursor (3.x line) — the builder
Current relevant capabilities: agent-first interface with parallel agents across worktrees and cloud environments; plan-before-execution (the agent presents its plan and can be redirected before work starts); Cursor Router "Auto" with Cost / Balance / Intelligence optimisation modes and per-request model classification; Bugbot code review (~90s, `/review` runs locally pre-push, reviews can be scoped to new changes); Design Mode in the browser (click, draw, or voice-direct UI changes with the agent seeing element code and layout); Automations and cloud agents in isolated VMs; side chats for tangents without polluting the main agent context.

**Our usage decisions:**
- Plan-first is now native: every AMBER package uses Cursor's plan step as the STOP point — Pranab reviews the plan text before authorising execution. GREEN work runs on Auto (Balance); AMBER runs on Auto (Intelligence) or a pinned frontier model.
- `/review` (Bugbot local) becomes mandatory before every push; Bugbot PR review stays on, scoped to new changes.
- Design Mode is used only against approved mockups (R4) — it accelerates faithful implementation, not improvisation.
- Cloud agents/Automations: adopted cautiously for GREEN mechanical work only (lint cycles, dependency bumps, test scaffolding). Nothing AMBER runs unattended. Side chats replace our habit of derailing a build session with an investigation.

### Claude Code (v2.1.x) — the auditor, enforcer, and CI brain
Current relevant capabilities: Sonnet 5 default with native 1M context; Opus 5 available per session; the layered system — CLAUDE.md memory, hooks at ~25 lifecycle points (PreToolUse can deny a tool call deterministically), skills (folder-based procedure packs), subagents with isolated context, Dynamic Workflows (lead agent fans out parallel subagents, with an outcome grader that forces revision against a rubric); background agents that work in worktrees and open draft PRs; `/security-review`; headless operation in GitHub Actions.

**Our usage decisions:**
- CLAUDE.md carries the distilled constitution + repo hazards (real frontend root, Command Prompt rule, read-only areas).
- Hooks are the constitution's teeth: PreToolUse guard blocking funder/fixture strings in engine paths (R7), blocking edits to golden files and to `AGENTS.md` without an explicit flag, secrets patterns (alongside existing Gitleaks).
- Skills encode our repeatable procedures so they survive session boundaries: "run the harness and produce the scorecard," "adjudication template," "audit brief format." Written once, invoked by name.
- Subagents/Dynamic Workflows: used for parallel *read-only* work — e.g., the five-interrogation pattern as five subagents with an evidence-pointer rubric. Never for building.
- CI: Claude Code headless runs the eval harness on every PR touching engine paths, printing the scorecard with SHA lineage; `/security-review` stays as Layer 2 of the standing security gate.
- Models: the M&E reader step and golden-adjacent work pin to the strongest available model; the 1M context window removes the last excuse for per-document chunked reading.

### The division of labour, restated
Claude (this chat, CTO): specs, goldens, contracts, adjudication, sequencing, package prompts. Cursor: builds from specs, plan-first, Bugbot-checked. Claude Code: audits, enforces, runs evals, reviews PRs, security. The separation is absolute for certification (R5); overlap is acceptable only inside GREEN mechanical work.

### The industry frame we are adopting by name
Spec-driven development (constitution → spec → plan → tasks → implement → verify, with acceptance criteria written in verifiable EARS-style statements) and eval-driven development (golden datasets, eval gates in CI, run lineage, judges calibrated against human judgment, production bugs promoted to permanent goldens). Two sizing disciplines from the literature we adopt: keep golden sets small and high-quality (on the order of tens to low hundreds of cases, grown from real failures, not synthetically inflated), and use code-based assertions wherever a failure is code-verifiable, reserving LLM-as-judge for genuinely subjective dimensions like readability.

---

## Part C — The operating system: package lifecycle

Every package, GREEN or AMBER, moves through the same pipe. AMBER adds the STOP.

1. **Spec** (Claude/CTO): problem, decisions verbatim, invariants, EARS-style acceptance criteria, tier, landing check. Versioned file in the repo.
2. **Golden delta** (if behaviour changes): the golden pack gains or amends assertions *before* the build.
3. **Plan** (Cursor): agent presents its plan. AMBER → Pranab reviews and authorises (STOP). GREEN → proceeds.
4. **Build** (Cursor): scoped to the spec.
5. **Local review**: Bugbot `/review` before push.
6. **PR**: Claude Code review + `/security-review`; hooks have already blocked constitution violations at write time.
7. **CI eval gate**: harness runs the affected golden packs; scorecard printed with SHA, dataset version, model config. Below-threshold → blocked, no exceptions (anti-bent-ruler: thresholds move only when the correct answer genuinely changed, with the change listed).
8. **Merge → deploy → post-deploy verification**: harness re-run against the deployed SHA (catches the "merged but never deployed" failure class from R6).

---

## Part D — Module state and required work

**1. M&E engine (rebuild in flight).** Packages as agreed, unchanged in shape: P0 harness + sealed NLCF golden; P1 decontamination + VfM restoration + cover truth (on current engine); P2 the Reader (strongest model, whole bundle, typed ledger + conflicts + gaps) with deterministic validation; P3 Gate 1 semantics ("both are true" resolution, folders not atoms); P4 the Writer (full ledger + full template, writer-filled tables, honesty mechanisms carried by pointer); P5 the meaning Checker (token verifier deleted); P6 Gate 2 (reader-authored questions, counter-list enforced). Certification: Bridgelight same-or-better on all five layers + sealed NLCF pass, every package.

**2. Generic M&E template (parked → unlocked by the contract).** Under the funder-agnostic contract, the generic template is the engine's native lens — the "true state of your programme" report. It becomes a data-pack authoring task after P4, certified by the standard mini-golden process. It is also the strategic wedge: one confirmed ledger, many funder reports.

**3. Fit Scan (built, live).** Measure-first retrofit, no reflexive rebuild (anti-death-star). Work: author a small golden pack (representative org-profile + opportunity inputs → expected fit outputs and reasoning quality bars, including forbidden outputs), run the NGO-shoes screen walk, register the pack in CI. Fix only what measurement shows. Decision on backporting new engine primitives is taken on evidence, not symmetry.

**4. Proposal Writer (stabilised 2026-03, 22/22 smoke).** Same measure-first retrofit: golden pack (one proposal end-to-end with expected section quality and honesty behaviour), NGO walk, CI registration. Known deferred item (Research Plan archetype timeout) stays deferred unless the golden shows user-visible harm. Evaluate whether the M&E Writer/Checker primitives should backport — after they exist and only if the proposal golden shows the gap.

**5. Org-profile auto-builder (parked → sequenced deliberately).** This is the Reader pattern pointed at websites and PDFs: full-context typed extraction into an org ontology, with the human confirmation gate as provenance guard. Sequence it after P2 proves the pattern, then run it as its own track exactly as previously decided (feature-flagged, all tiers, activation lever, generous drafter + confirmation gate). Prerequisites in order: org ontology spec (shared consumer contract — Fit Scan, Proposal, M&E all read from it), golden pack (three real-ish org websites/PDFs → expected profiles), mockups + state ledger, then build.

**6. Cross-cutting and launch surfaces.**
- Auth reliability thread: audit showed auth Package 1 landed; verify the 401-mid-synthesis fix under the new harness's long-run test and close or re-scope the two historical branches.
- Track 3: audit shows D-053/D-056/D-057 landed on main; verify closure with a witnessed walk assertion in the harness, then formally close.
- Housekeeping: decision-log entries for everything ratified this week; resolve the D-046/D-049 numbering collision; prune the fifteen stale remote branches (several are month-old audit branches).
- Stripe live mode, signup hardening: unchanged scope, Phase 4.
- Security: Layers 1–2 continue on every PR; a Layer-3 episodic deep audit (OWASP ZAP + adversarial prompt-injection probes) is scheduled at the end of Phase 2, because the rebuild changes the attack surface (new prompts, new parsing).
- Cold stranger walk and the narrow-vs-full launch decision: Phase 4 gates. The launch decision stays open until the sealed golden passes — deciding it earlier would be deciding on hope.

---

## Part E — Phased roadmap

Sequence and exit criteria, not calendar promises. Phases overlap where tracks are independent.

**Phase 0 — Foundations (immediate).**
Repo governance files (AGENTS.md constitution + CLAUDE.md + .cursor/rules); hooks (funder-string guard, golden-file guard); CI eval gate skeleton running the Bridgelight scorecard assertions with SHA lineage; sealed NLCF golden authored (Claude) and registered; Package 1 decontamination + VfM + cover truth on the current engine; housekeeping debt cleared.
*Exit: a PR that degrades Bridgelight scores is mechanically blocked; the constitution is machine-loaded; the honest (post-coaching) baseline is measured and recorded.*

**Phase 1 — The Reader.**
P2 (reader + deterministic validation) and P3 (Gate 1 semantics). Parallel design track: mockups + state ledgers for all six M&E screens.
*Exit: reader output scores ≥ golden Layer 1–3 thresholds on Bridgelight AND sealed NLCF; Gate 1 can express "both are true"; mockups approved.*

**Phase 2 — The Writer and the Checker.**
P4, P5, P6; generic template lens authored; M&E frontend rebuilt to the approved mockups (Design Mode against mockups); Layer-3 security audit at phase end.
*Exit: Bridgelight full-report score at golden level on all five layers; sealed NLCF passes; NGO-shoes walk sign-off on the new screens; security audit green.*

**Phase 3 — The Siblings.**
Fit Scan and Proposal golden packs + walks + evidence-based fixes; org-profile builder (ontology → golden → mockups → build) behind its flag.
*Exit: three modules with golden packs green in CI at deployed SHA; org-profile builder demonstrably lifts activation in internal walk.*

**Phase 4 — Launch.**
Stripe live; signup hardening; auth thread closed; cold stranger walk (a real NGO, never seen the product, end to end); narrow-vs-full decision taken and executed.
*Exit = the definition of "GrantPilot finalised": every module golden-green in CI at the deployed SHA; NGO-walk sign-off per module; contract conformance; security gates green; billing live; a cold stranger completes the core journey unassisted.*

---

## Part F — Risks owned

Frontier-model cost on the reader step: accepted (£3–5/report against the $79 plan; Cursor Router disciplines build-time spend). Background/cloud agents: convenience is real, so is the risk — confined to GREEN. Eval maintenance burden: contained by the small-high-quality rule and by promoting only real failures to goldens. The CTO-time bottleneck on golden authorship: accepted deliberately — domain judgment is the scarce asset and the moat; it is the one thing we never delegate to the builder.

**Decisions requested from Pranab:** ratify this plan; authorise Phase 0 start. The narrow-vs-full launch decision is scheduled, not requested now.
