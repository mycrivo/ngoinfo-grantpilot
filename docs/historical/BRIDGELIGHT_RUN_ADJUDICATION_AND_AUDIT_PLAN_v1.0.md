# Bridgelight Live Run — Adjudication Against the Golden Record, and the Root-Cause Audit Plan

**Version:** 1.0 — 2026-07-25
**Run:** report `dfd17248` on production, Bridgelight FCDO bundle, owner-executed
**Measured against:** `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`
**Evidence:** Gate 1 screen (facts), Gate 2 screen (questions), Gate 3 screen (review + flags), exported DOCX
**Author:** Claude (CTO co-pilot). Adjudication only — no remediation is authorised by this document.

---

## 0. The verdict in three sentences

The moat's honesty held: the pipeline invented no numbers, disclosed its gaps, and refused to estimate. Everything around the honesty collapsed: roughly nine in ten golden facts never reach the report, every table renders empty, three of the six sections contain no content relevant to their own heading, the cover states a reporting period that exists in no document, and the one interactive decision the product asked of the user forced a false comparison into the final report. The failure mode has fully inverted since June — the product no longer over-claims; it under-delivers to the point of uselessness while remaining scrupulously honest about it.

---

## 1. Stage scores

### 1.1 Layer 1 — Knowledge-bank fidelity: ~55% of golden facts, plus two corruption-class entries

**What extraction got right (preserve — do not regress):**
- All ten reported indicator actuals, correctly valued: 684, 472, 438, 31, 17, 392, 571, 68%, 3, 136.
- All ten evidence/delivery notes, verbatim, correctly attributed to D3.
- Contract basics from the award letter: funder, programme code, start and end dates, £1,240,000.
- The award letter's "October to September" inception-call mention was captured — the raw material for C-02 existed in the bank, even though nothing used it.
- Full disaggregation grid captured faithfully (see below for why faithful-but-undiscriminating is its own problem).

**What never reached the bank (extraction loss, by golden ID):**

| Missing | Golden IDs | Downstream casualty |
|---|---|---|
| **The entire finance table** — all ten forecast/actual cost lines, the £880,000/£920,420 totals, every finance note | F-067…F-078 | Section F has literally nothing to say; "Financials by output: 1 item — currency: —" |
| The proposal budget table and total £1,184,000 | F-079, F-080, F-081 | C-01 undetectable; no budget figure appears anywhere in the report |
| The 612 internal-note figure | C-03 input | C-03 undetectable |
| All baselines (38%, 31%, 41%, and the OP2.1 baseline of 6) | F-032…F-034, F-043 | No baseline column exists in the Gate 1 UI at all; C-07 undetectable |
| Y1 milestones for the three outcome indicators (55/48/58) | F-032…F-034 | Outcome rows show endline only |
| Impact weightings and risk ratings | F-035…F-038, F-014 partially | Risk section starved |
| VfM content — £987/girl, cost drivers, the four-Es approach | F-082, F-083, F-106 | No VfM material anywhere |
| Design risks and safeguarding controls | F-101, F-102 | Risk & Safeguarding section starved |
| Proposed output scores and the DRAFT worksheet status | F-020, C-09 input | — |
| Organisational context — org name, charity number, 40 schools, 1,200-girl population, priority groups | F-001…F-003, F-021…F-025 | Cover page carries the account profile name instead |

**Corruption-class entries (worse than missing):**
- **A fact reading "actual achieved: girls re-enrolled — 33 girls."** The 33 is the OP1.1 Female 18–24 disaggregation cell, promoted to a headline actual. The bank simultaneously holds 684 and 33 as actuals for the same indicator, and no conflict was raised between them — while a false conflict was raised elsewhere.
- **Post-resolution, OP1.1's Year 1 comparison target is 1,200** (see 1.2). This is a user-confirmed wrong fact, manufactured by the resolution UI.

**Validation absent entirely:** none of golden Layer 1's arithmetic checks has anywhere to run. 681 ≠ 684 and 227 ≠ 291 pass silently; meetings disaggregated by age and sex pass silently; 392 all-male caregivers pass silently. The 133-item Gate 1 list is the direct symptom: extraction emits atoms, nothing classifies, aggregates, or sanity-checks them, so the UI has no choice but to render the raw pile.

### 1.2 Layer 2 — Conflict handling: 0 of 9 genuine conflicts detected; 1 false conflict manufactured; its resolution corrupted the bank

The nine golden conflicts: none surfaced. C-01 (budget) and C-03 (612 vs 684) were undetectable because one side of each was never extracted. C-02 (reporting period) is the damning one: **both sides were in the bank** — the contractual dates and the October-to-September mention — and no conflict fired.

The one conflict that did fire is not a conflict. "1,200 girls (proposal) vs 650 girls (logframe)" compares OP1.1's **endline target** with its **Year 1 milestone** — two different facts both documents agree on. The resolution UI then offered choose-A / choose-B / enter-another. There is no "both are true — these are different things" path, so every available action destroys a true fact. The run's outcome: the report states *"684 girls were re-enrolled or newly retained against a target of 1200"* — converting the programme's best result (105% of milestone) into an apparent 57% failure — followed one sentence later by *"delivery was above milestone."* A materially misleading performance statement and an internal contradiction, in consecutive sentences, in a document addressed to a funder. **This is the single worst line the pipeline produced, and the user was made complicit in producing it.**

### 1.3 Layer 3 — Gap behaviour: recall 2/10, precision 2/3, and the most valuable question in the product was never asked

Asked: OP2.3 actual (G-02 ✓) and OP4.2 actual (G-03 ✓) — correctly identified, though both quote the endline target instead of the Year 1 milestone, and both leak plumbing ("OP2_3", "indicator-data actual").

Asked wrongly: *"please provide the progress against expected results"* — a template requirement slug surfaced verbatim as a question. The bank held ten actual-versus-milestone results; progress against expected results is precisely what the engine exists to write. Golden counter-list violation (FB-14).

Never asked: **G-01 — the outcome actuals.** The single question a real FCDO reviewer would put first. The satisfaction logic saw outcome-indicator *target* facts in the bank and marked the requirement met — facet-blind matching: needs an ACTUAL, finds a TARGET, satisfied. Also never asked: G-04 risk update, G-05 safeguarding, G-06 partner performance, G-07 programme-level finance, G-09 the period question, G-10 evaluation. The narrative-typed requirements auto-satisfy at Gate 2; the finance requirement was satisfied by a single null-valued `financials.currency` atom.

**And the two matchers disagree with each other.** Gate 2's satisfaction logic declined to ask about major deviations and disaggregation (satisfied); the report's caveats layer then declared the same requirements "not included in submitted records" (unsatisfied) — while a hundred-plus disaggregation facts sat in the bank. Same bank, same requirements, opposite verdicts at two pipeline stages. June's principle applies: a rotating failure pattern means the structure is wrong, not the element.

June's failure was 46 questions where ~2 were real. Today's is 3 questions where 10 are real, missing the most important one. The pendulum swung through correct without stopping, which is what happens when the matcher is tuned rather than typed.

### 1.4 Layer 4 — The report: ~10% content coverage, empty tables, off-topic sections, three material errors

Set the exported DOCX beside golden Layer 4:

- **Coverage.** The whole report uses roughly a dozen distinct facts. Golden Section A alone uses more than fifty. Only 7 of the 10 extracted actuals appear anywhere — OP3.3 (68%), OP4.1 (3 meetings) and OP4.3 (136 trained) were extracted, confirmed at Gate 1, and then silently dropped from every section. Silent impoverishment of facts the user explicitly confirmed.
- **Tables: 0 of 5 populated.** Every required table renders a single all-"not provided" row. Golden fills four of the five substantially from material the pipeline *had* (outcome statement, evidence sources, design-stage risk ratings, recommendations derivable from the gaps themselves).
- **Section relevance.** Risk & Safeguarding contains no risk and no safeguarding — it recites the review dates and OP1.1/OP1.2. Section F contains no financial content. Recommendations contains no recommendations. Four sections are near-identical recyclings of the same four facts. The starved sections weren't left short; they were padded with off-topic filler — which is its own subtle dishonesty about what the report contains.
- **Material errors (3).** The cover states *"Reporting period: 2025-04-01 to 2026-03-31"* — a period appearing in no document, contradicted by the body two lines later; it is report-creation metadata rendered unreconciled. The 684-against-1,200 line (above). And *"571 girls received a school re-entry kit … against a target of not reported this period"* — a null verbalised into prose as if it were a value (the critic's one true catch).
- **Identity.** The report is titled for the account-profile organisation, not the organisation in the documents — no reconciliation between profile identity and document identity exists.
- **Prose.** Single-sentence paragraphs; raw ISO dates ("2024-10-15") in funder prose; broken grammar ("The programme impact was adolescent girls complete basic education…"); every section opening with the same recital. Readability: fail — and see 2.4 for *why* the dates are ISO, because it is not carelessness.
- **What held.** The Assumptions & Caveats section is genuinely good architecture: per-section disclosure, "disclosed as a gap rather than estimated," no invention. Skipped answers flowed through honestly. The moat's *character* survived; its *usefulness* did not.

### 1.5 Layer 5 — Forbidden outputs: honesty assertions pass; disclosure assertions fail

| Verdict | Assertions |
|---|---|
| **Pass** | FB-01 (no totals-row reach claims), FB-02 (no derived outcome %), FB-04 (£1.184m nowhere — by omission), FB-06 (no disaggregation claims), FB-08/09 (no scores stated), FB-10 (no invented risk ratings), FB-11 (no fabricated safeguarding nil), FB-12/13, FB-15 (no funder-owned items asked), FB-17, FB-18 |
| **Fail** | **FB-03 variant** — the mandated period-offset disclosure never happens, and the cover states a third, fabricated period; **FB-05** — OP2.3/OP4.2 absent from the body without indicator-specific flagging, plus OP3.3/OP4.1/OP4.3 silently dropped despite confirmation; **FB-14** — a question the bank could answer was asked |
| **Caveat on the passes** | Several passes are passes-by-starvation: the pipeline couldn't state £987/girl or output scores because it never extracted them. A pass earned by missing data is not a safety property. The harness must distinguish the two. |

### 1.6 Gate 3 critic: the false-positive flood is back, at the token level

Approximately thirty "Must fix before download" flags, and all but one are date fragments: 2024, 2025, 2026, 10, 11, 14, 15, 21 — the checker decomposes prose into numeric tokens and demands each token match a bound claim `value_token`, so every rendered date yields two to three violations, and definitional numerals inside indicator names ("80%") flag too. One true positive (the OP3.2 garble) buried in noise — exactly the calibration failure that trains rubber-stamping. The flag copy ("Uncited numeric in prose not covered by any bound claim value_token") is engine internals shown to an NGO, and "Must fix before download" on all of them tells the user the whole report is broken. Pranab's read is correct; the UX failure is real — but it is downstream of the checker, not a copywriting problem.

---

## 2. Root causes

Seven, and they chain. The June remediation treated symptoms inside this chain; the chain itself was never named.

**RC1 — There is no typed fact model.** Facts are flat label-value strings; facet identity — baseline vs milestone vs endline vs actual vs disaggregation-cell vs derived total — lives only in English inside the label. Every headline failure traces here: the false 1,200-vs-650 conflict (two facets collided into one key), the "33" promotion (a cell mistaken for an actual), the satisfaction blindness (a TARGET satisfying a need for an ACTUAL), the 133-item UI (atoms with no hierarchy to fold), and the lost outcome milestones. The knowledge bank also lacks three states golden Layer 1 requires: *caveated* (a value carrying a limitation that must survive into prose — the period offset is unwritable without it), *extracted-but-not-reportable* (the totals row), and *absent-as-a-first-class-object* (OP2.3/OP4.2 as renderable holes).

**RC2 — No validation layer between extraction and the bank.** Nothing sums, cross-foots, or credibility-checks. Golden Layer 1's arithmetic (681≠684, 227≠291, meetings-with-genders, all-male caregivers) has no architectural home. Extraction is faithful and undiscriminating, and nothing downstream discriminates either.

**RC3 — Requirement satisfaction is substring matching, implemented twice, inconsistently.** The Gate 2 matcher and the synthesis-caveat matcher evaluate the same requirements against the same bank and reach opposite conclusions. Narrative-typed requirements auto-satisfy at Gate 2 (so risk, safeguarding, evaluation are never asked) yet are declared missing at caveats. A null `financials.currency` atom satisfies the finance requirement by prefix. This is the June "semantic, not lexical" finding, still unlanded — and now provably bidirectional: it over-asked in June and under-asks today, because tuning a lexical matcher just moves the error.

**RC4 — Verification runs at token level, and the prose is hostage to it. This is the regression mechanism.** The P1 citation-at-generation architecture *did* ship — "bound claim value_token" in the flag copy proves it. But the deterministic verifier decomposes prose into numeric tokens instead of comparing typed claims to typed facts. Two consequences, and together they are the answer to "why is quality worse than where we began": the flood (dates and definitional numerals flag), and the flattening — synthesis learns that any reformatting risks a token mismatch, so it echoes bank formats verbatim. **The ISO dates in funder prose are not sloppiness; they are the synthesis surviving its own verifier.** We shipped citation integrity measured by citation metrics, and paid for it in prose nobody measured. The golden's separated scoring (coverage / correctness / readability) exists precisely so this trade can never be invisible again.

**RC5 — Section-fact routing starves synthesis, and starvation is padded rather than disclosed.** Archetype-based fact-prefix trimming handed Risk and F sections almost nothing (compounded by RC-extraction losing the finance table outright), and synthesis filled the void by recycling OP1.1 rather than writing a short honest section. Off-topic filler is silent impoverishment wearing a costume.

**RC6 — Template and metadata truth gaps.** The VfM section the award letter mandates is absent from the live template (established in the golden record; unchanged). The cover reporting period comes from create-time metadata and is never reconciled against extracted dates — the April 2025–March 2026 fabrication. The profile organisation is never reconciled against the document organisation. All five tables' `data_source` bindings resolve to nothing, so tables are structurally dead. Three of ten Gate 2-adjacent template details quote endline instead of milestone.

**RC7 — The Gate 1 resolution model can only corrupt when the conflict is false.** Choose-A / choose-B / enter-other assumes single-valued facts. Faced with a facet collision, every option deletes a truth, and the user's confirmation launders the corruption into "human-verified." The product's one moment of interactive judgment made the report worse.

**The causal chain, in one paragraph.** Untyped extraction atomises the documents (RC1) with no validation (RC2); the reconciler, comparing labels, invents a false conflict and misses nine real ones (RC1); the resolution UI forces a corruption (RC7); substring satisfaction sees targets and nulls as answers, so Gate 2 asks three questions instead of ten and skips the one that matters (RC3); prefix routing starves four sections (RC5); synthesis pads the starvation and formats defensively for a token-level verifier (RC4); the verifier floods anyway; the render layer stamps unreconciled metadata on the cover and empty tables in the body (RC6). Honesty survives at every step because honesty was built as a value; usefulness dies at every step because meaning was built as strings.

---

## 3. The audit plan — five interrogations, not a findings register

The scorecard has localised every failure, so the code audit is no longer exploratory. Claude Code runs **read-only**, one interrogation at a time, each a specific question with named evidence to retrieve. **Evidence only — no recommendations, no fixes.** A finding without an evidence pointer does not enter the record. I adjudicate each return against this document; Pranab arbitrates anything that becomes a product call.

**A1 — Extraction loss.**
*Question:* At which exact point did the finance columns of D3, the proposal budget table, the 612 note, the baselines, and the outcome Y1 milestones fail to survive — extractor scope, docx-table parsing, prompt schema, or reconciler drop? And where was the "33" cell promoted to an actual?
*Evidence:* per-document `extracted_json` for all three documents; reconciler input bundle and output bank; the D2–D4 extractor schemas for docx-borne tables (this run's logframe was a **docx**, not xlsx — establish whether the finance-column loss is substrate-specific).
*Adjudicates:* RC1/RC2 boundary, and whether extraction repair is prompt-schema work or parser work.

**A2 — Fact model and the false conflict.**
*Question:* Where is facet identity represented, if anywhere? Show the exact fact keys under which 1,200 and 650 were stored, the reconciler's comparison that declared them conflicting, and precisely what the Gate 1 resolution wrote into the bank.
*Evidence:* `knowledge_bank_json` for this run; the resolution record; key-shape inventory against `FUNDER_TEMPLATE_SCHEMA_AS_BUILT` §7.
*Adjudicates:* RC1, RC7 — and defines the typed-fact-model package's true scope.

**A3 — The two satisfaction matchers.**
*Question:* Trace requirement-by-requirement evaluation for section B and section F at both checkpoints — Gate 2 and the caveats layer. Why did `outcome_indicators` and `financial_delivery` satisfy at Gate 2; why did narrative requirements satisfy at Gate 2 and fail at caveats; which hint entries fired.
*Evidence:* `gap_analysis_json`; both satisfaction code paths; `DATA_BACKED_HINTS` as deployed; per-requirement evaluation trace if persisted — if it is not persisted, that absence is itself a finding.
*Adjudicates:* RC3 — and settles whether June's P2-1/P2-2 semantic-matching packages shipped, partially shipped, or regressed.

**A4 — Synthesis inputs and the token verifier.**
*Question:* Produce the exact per-section payload synthesis received (if not persisted: finding — prose quality has been undiagnosable by design). How many facts reached Risk and F? Where does the deterministic checker tokenize prose, and what claim-binding shape does synthesis emit? Is there any instruction or pressure producing ISO date echo?
*Evidence:* synthesis input payloads per section; claims/`content_json`; the checker implementation; the F1 prompts as deployed.
*Adjudicates:* RC4, RC5 — and confirms or kills the format-echo mechanism as the prose-regression cause.

**A5 — Metadata, template, and render truth.**
*Question:* What populates the cover reporting period and organisation name; where do the five tables' `data_source` bindings resolve; what does the renderer do when a table resolves empty; and confirm the live template's section set against the award letter's mandated pack.
*Evidence:* `donor_reports` row for `dfd17248`; renderer inputs; live template row.
*Adjudicates:* RC6 — most of which is already evidence-complete from this run and needs only source-location.

**Sequencing:** A1 and A2 first (they share evidence and gate everything), then A3, A4, A5 in parallel-capable order. Each is a bounded read-only session; no interrogation exceeds its question.

---

## 4. After the audit — repair shape (proposal; build authorisation is separate)

Stated now so the interrogations are read with the destination in mind; nothing here is authorised until audit returns land and Pranab signs the sequencing.

- **Package 0 — the harness inherits this scorecard.** Every score in §1 becomes an assertion; the Bridgelight run becomes the standing regression gate. Passes-by-starvation are marked so they cannot masquerade as safety. Nothing merges unless a re-run scores same-or-better on every layer. This precedes all fixes — it is the mechanism that prevents a fourth worse-than-before cycle.
- **Evidence-complete config-class fixes** (can move immediately after their audit source-location, as GREEN/AMBER-low): restore the VfM section NGO-owned (owner decision, already evidenced); cover period drawn from confirmed bank facts with mismatch surfaced, never from raw metadata; profile-vs-document organisation reconciliation surfaced at Gate 1; milestone-vs-endline quoting in gap questions.
- **The two structural AMBER packages, in order:** the **typed fact model** (facets, caveats, not-reportable, absence as first-class — RC1/RC2/RC7's shared fix; the conflict UI gains a "both are true" resolution as part of it), then **typed-claim verification** replacing the token checker (RC4 — dates verify as dates, derived values verify by derivation, prose is freed to be prose). Each is Plan-Mode with STOP; each is certified by the harness, not the builder.
- **Then** unified semantic satisfaction (RC3, one implementation, both checkpoints), section-fact routing with honest-short-section behaviour (RC5), and only after engine truth: the Gate 1 information architecture and Gate 3 language pass (the June sequencing logic stands — presentation follows correctness).

---

## 5. Preserve list — confirmed under live fire this run

The honest-skip flow ("Skipped — not provided" through to the report); the caveats architecture and its "disclosed as a gap rather than estimated" language; zero numeric fabrication end-to-end; verbatim evidence-note capture; the "GrantPilot does not choose between conflicting figures" principle (the principle is right — the conflict *detection* feeding it is what failed); the six-step funnel UX skeleton; the critic's one true catch (the checker's discrimination exists; its input representation is what floods).

*End of adjudication. Interrogations A1–A5 are ready to hand to Claude Code verbatim, one at a time, read-only.*
