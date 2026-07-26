# M&E Engine Behavioural Contract
**Funder-agnostic law of the engine — v1.0, 2026-07-25**
**Status:** RATIFIED 2026-07-26 — governs the rebuild; every package is certified against this document plus the golden records.

---

## 1. The one-line law

**The engine's judgment is universal; the funder's demands are data; the report is the universal judgment shaped by that data.**

The engine behaves like a competent M&E consultant who has never heard of the funder until handed the template. Everything the consultant knows about *monitoring and evaluation* — what a baseline is, what makes a conflict, what honesty requires — lives in the engine. Everything the funder wants — structure, wording, word limits, which content is mandatory, what the sections are called — lives in template data. Adding a funder means authoring data. Retiring a funder means deactivating data. Neither ever means touching engine code or prompts.

## 2. The universal fact ontology

Every M&E programme, under every funder, is made of the same kinds of facts. The engine reads any document bundle into this ontology and nothing else:

**Programme identity** — implementer, funder, title, reference codes, geography, contract dates, award value and currency.
**Reporting context** — contractual reporting period, data-coverage period (*always modelled as two distinct facts; their equality is a finding, not an assumption*), report cycle, due date.
**Results framework** — a hierarchy (impact / outcome / output, or the funder's equivalents) of indicators, each carrying **facets**: definition, unit, baseline, period milestone(s), final target, achieved value(s) per period, evidence source, variance note, disaggregation cells (dimension × band), and derived totals.
**Finance** — line-level forecast, actual, variance and note; programme-level envelope versus spend; unit costs with their stated basis.
**Risk** — register entries (risk, rating at a point in time, mitigation, owner, status) and overall rating, each time-stamped: a design-stage rating and a current rating are different facts.
**Safeguarding** — controls at design; period activity. *A nil return is a statement; absence of information is not a nil return.*
**Partners, suppliers and governance.**
**Learning and evaluation outputs.**
**Qualitative narrative** — activities, context, deviations, beneficiary voice.

Every fact carries: typed facet identity (never encoded in a label string), provenance (document, location), and exactly one state — **confirmed**, **caveated** (true but carrying a limitation that must survive into prose), **conflicted**, **extracted-but-not-reportable** (e.g. cross-indicator totals), or **absent**. Absence is a first-class object: a hole with a name, renderable and askable.

The ontology is engine-owned and funder-blind. No funder's vocabulary appears in it.

## 3. The six behaviours

**B1 — Read whole, read once.** The bundle is understood in a single act of full-context reading into the ontology, not through per-document narrow schemas. The reader also captures document-status signals — draft markings, amendment traces, dates that contradict a document's own header — as caveats on the facts they touch. Scope is defined by the ontology, never by an expected document shape: no expected counts, no named sections, no quoted phrases from any known fixture or funder.

**B2 — Validate deterministically.** Pure code, zero model judgment: column sums, disaggregation-to-headline reconciliation, unit sanity, envelope arithmetic, credibility screens (a person-level breakdown on a non-person indicator; a movement in the wrong direction under a stated explanation). Findings attach to facts as caveats or reclassify state; they never silently alter a value.

**B3 — Reconcile, never resolve.** A conflict exists only between values occupying the *same ontology slot*. Cross-facet comparisons are structurally impossible. Detected conflicts go to the human with the evidence for each side and, where the ontology implies one, a proposed resolution rationale (e.g. a later contracting document supersedes a proposal) — proposed, never imposed. Legitimate resolutions include **"both are true — these are different facts,"** which files the values into their correct slots. Superseded values remain in the ledger as history, never deleted.

**B4 — Determine gaps semantically.** A gap exists exactly when the template requires content in an ontology slot (with facet) and the confirmed ledger's slot is empty. Satisfaction is checked against the ontology — an actual is not satisfied by a target; a finance requirement is not satisfied by a currency code — and by one implementation with one verdict per requirement, used identically at question time and at disclosure time. Questions are asked in the NGO's language about their programme, quoting the correct comparator for the period. Never asked: anything the ledger already holds (offer confirmation instead), anything funder-owned, anything the template does not require. The question set for a well-documented programme is small; every question must be one a competent reviewer would also ask.

**B5 — Write honestly from the confirmed ledger and the whole template.** Every specific claim binds to a confirmed fact or a given answer. Section content must be section-relevant: if the ledger holds nothing relevant to a section, the engine writes the honest short section — it never pads with off-topic material, because off-topic filler is silent impoverishment wearing a costume. Tables are filled by the writer as structured rows bound to facts; a table with nothing to say says so once, honestly. Absences are disclosed where a reader would expect the content, named specifically ("the safeguarding referral indicator was not reported"), not as requirement-slug lists. Caveats attached to facts must surface in prose. Prose is written for a human reader: dates as a human writes them, no internal identifiers, no engine vocabulary, tone and terminology from the template's data.

**B6 — Verify meaning, not tokens.** Dates compare as dates in any rendering; numbers compare normalized; stated derivations are recomputed; qualitative claims are checked against the full ledger by a model that has read it. A blocking flag means a reader-facing falsehood risk, and is worded so the NGO understands what is wrong and what to do. Flag volume is part of the contract: a flood of false alarms is itself a defect, because it trains the user to stop reading.

**Cross-cutting duties.** Rendered metadata — cover period, organisation, titles — comes from the confirmed ledger or is reconciled against it before render, with mismatches surfaced at Gate 1. Every stage persists its inputs and outputs (the run bundle); no behaviour may be undiagnosable by design. The human gates remain the product: confirm facts, answer gaps, review flags, own the document.

## 4. The boundary law

**Engine (code and prompts) may contain:** the ontology; the six behaviours; the honesty invariants; universal M&E domain knowledge.
**Template data may contain:** section structure and labels; word limits; tone, terminology and formatting; requirement declarations *expressed in ontology vocabulary* (slot + facet + scope); table definitions mapping columns to ontology facets or to writer-composed content; scoring vocabularies; funder-owned exclusions (content the NGO must never be asked for); mandatory-disclosure rules.
**Nowhere, ever:** funder names, slugs, expected counts, or quoted phrases in engine code or prompts; substring hint maps; archetype guessing. A template that under-declares its requirements **fails loudly at template validation** — the engine never compensates silently at run time, because silent compensation is where funder knowledge leaks back into code.

## 5. What "the right M&E report" means, for any funder

The golden record's five layers, generalised, are the universal acceptance shape: a complete typed fact ledger; every genuine conflict surfaced and none invented; a small, precise gap set with a counter-list of what must not be asked; a report that is traceable, complete relative to its inputs, honest about what is missing, and readable as professional prose; and a set of forbidden outputs that never appear. Per-funder golden packs instantiate this shape; the engine is certified against the shape, not against any funder.

## 6. Funder onboarding and retirement

A funder is a **data pack**: the template authored in the requirement vocabulary, plus a mini golden pack (one fixture bundle and its expected ledger, gaps and forbidden outputs) used to certify the pack before activation. Onboarding cost is authorship and certification; engine cost is zero. Retirement is deactivation; engine cost is zero. The pack process is also the quality gate that stops template authors from smuggling requirements the ontology cannot express — which is the moment we discover the ontology needs a considered extension, through governance rather than through a hint map.

## 7. Consequences accepted by signing this contract

The FCDO-slug hint map, the archetype fallback, the per-document extraction schemas, the token verifier, and every fixture-quoting prompt line are non-conformant and scheduled for removal in the rebuild packages. Bridgelight scores will drop when prompt coaching is stripped; that drop is the honest baseline and is accepted. The sealed second fixture is authored under a different funder specifically to prove this contract — the engine must score to standard on a funder it has never seen, using only that funder's data pack.

*Signature: engineering direction — Claude (CTO). Product ratification — Pranab.*
