# M&E ENGINE REBUILD — HYPOTHESIS VALIDATION AUDIT

| | |
|---|---|
| **Audited repository** | https://github.com/mycrivo/ngoinfo-grantpilot |
| **Audited ref** | `origin/main` HEAD |
| **Commit SHA** (`git rev-parse HEAD`) | `a74d5e3e19116a87cecb529b68a526af46c2e225` |
| **Commit date** (`git log -1 --format=%cI`) | `2026-07-20T11:55:13+01:00` |
| **Clone / audit timestamp (UTC)** | `2026-07-25T17:02:23Z` |
| **Clone location** | `/home/user/ngoinfo-grantpilot` (audit ran in a Linux container; the brief's `C:\audit\` path does not exist here — deliverable written to `/home/user/audit/`, outside the clone) |
| **Verification** | working tree clean; after `git fetch origin --prune`, local HEAD == `origin/main` (`a74d5e3`). All pointers below are `path:lines` at this commit. |
| **Constraints honoured** | read-only; no edits, branches, commits, or pushes; no production queries. |

Reference-run context supplied by the brief (report id `dfd17248-9b46-48d9-8bc6-5348eab44a1c`) is treated as observed fact, not as evidence; code evidence is cited independently.

---

## SECTION 0 — REPO STATE

### git log --oneline -15 origin/main

```
a74d5e3 Package 1: Gate 1 conflict integrity - seam normalizer, strict resolution semantics, repair tooling, CI async gate (D-058-D-062)
9fa406d docs(me): Gate 1 conflict-save + facts payload diagnostic audit
5f672d3 chore(audit): Phase 2 walk tooling and loose ops scripts
57ed4c4 docs(me): Track 3 Phase 2 STOP 3 + older audit evidence artefacts
d891147 docs(me): D-057 Track 3 Phase 2 witnessed-walk decision
1a7ccde Merge pull request #9 from mycrivo/feat/me-proposal-induce-timeout-degrade
67f94ca feat(me): D-056 proposal timeout-degrade fault flag for Track 3 witness
181c7d9 docs(me): Track 3 prod NLCF scoped reconcile + confirming-walk evidence
adea209 Merge pull request #8 from mycrivo/chore/auth-package-1-p0-p2-p3
64a9a76 chore(auth): Package 1 — audit refresh diag, linking contract tests, branch hygiene
8f38a30 Merge pull request #7 from mycrivo/feat/track3-narrative-gate2-elevation
b3d6d59 Track 3: elevate NLCF community narrative gaps after proposal-failure proceed.
fcf35e5 Proposal extraction reliability: stream fix, 180s timeout, checkpoint.
7570bec Fix deterministic Gate 2 gap question copy for readable English.
15f91c3 Add per-attempt instrumentation to proposal extractor for timeout diagnosis.
```

### Unmerged remote branches (`git branch -r --no-merged origin/main`), name + last-commit date

```
origin/claude/audit-google-oauth-PXTlp            2026-02-15T12:10:34+00:00
origin/claude/audit-grantpilot-backend-bMXL4      2026-02-04T08:12:22+00:00
origin/claude/audit-onboarding-pipeline-ImpDv     2026-03-03T22:04:22+00:00
origin/claude/eager-planck-vt2d49                 2026-06-14T06:16:21+00:00
origin/claude/nice-wright-nhtcP                   2026-06-06T15:27:19+00:00
origin/claude/nifty-cerf-x365du                   2026-06-09T08:27:07+00:00
origin/claude/package-1-prs-audit-l57vt5          2026-07-20T10:38:22+00:00
origin/claude/sharp-euler-e4chi3                  2026-06-08T19:57:04+00:00
origin/claude/smoke-test-grantpilot-m343C         2026-03-23T12:53:48+00:00
origin/claude/test-grantpilot-backend-57YvD       2026-03-09T16:48:42+00:00
origin/claude/zen-sagan-HppBG                     2026-06-02T05:44:18+00:00
origin/docs/defer-dashboard-lists-mvp             2026-02-22T10:46:36+00:00
origin/feat/frontend-bootstrap-design-system      2026-02-15T16:05:24+00:00
origin/feat/gate1-conflict-integrity              2026-07-19T17:20:15+01:00
origin/for-claude-code-review                     2026-02-23T18:19:05+00:00
```

Factual note: `git diff origin/main origin/feat/gate1-conflict-integrity --stat` is empty — that branch is content-identical to `origin/main` (its work is in `a74d5e3`).

### Remediation presence (facts only)

The citation/claim-binding modules are ON `origin/main`: `app/reports/services/synthesis_claim_binding.py`, `app/reports/services/synthesis_citation_emission.py`, `app/reports/services/numeric_fact_verifier.py` landed at `bd72572` (2026-06-11), with follow-ups `d78a628` (2026-06-11), `d15c97c` (2026-06-13), `92442a5` (KB table rendering, 2026-06-14), `79b7b89` (remit-scoped caveats, 2026-06-14), `e475c7b` (insufficient_data preflight, 2026-06-13). No module, file, or commit named "gap relevance" exists on `origin/main` or on any remote branch (searched: `git log --all -i --grep=relevance` → empty; `git ls-tree -r` over all remote branches for `*relevance*` → empty; `grep -ri relevance app/` → empty). The gap-side modules that do exist on main under other names: typed requirement satisfaction (`app/reports/gap/requirement_satisfaction.py`, `bd72572`/`e475c7b`), remit-scoped disclosure (`app/reports/services/remit_disclosure.py`, `79b7b89`), narrative Gate 2 elevation (`app/reports/gap/proposal_failure_elevation.py`, `b3d6d59`).

---

## VERDICT TABLE

| # | Hypothesis | Verdict (one line) |
|---|---|---|
| **H1** | Extraction loss | **PARTIAL** — proposal budget/£1,184,000, "612 girls" note, and the finance-note column die at prompt/schema by design; baselines and Y1 milestones are extracted from the proposal then dropped at reconciliation input assembly (and have no slot at all in the tabular lane); forecast-cost/actual-cost columns DO have schema slots (budget/actual), so "never captures" is not code-forced for them — settling that sub-item needs `uploaded_documents.extracted_json`. |
| **H2** | Untyped fact model | **CONFIRMED** — no typed facet field anywhere in the fact model; fact identity is an LLM-authored free-string `fact_key` plus free-text hints; conflict detection is LLM judgment over "same semantic quantity"; (a) and (b) are structurally forced/enabled as hypothesised; (c) confirmed for "stored alongside with no conflict", while "promoted as an indicator actual" is possible but not code-forced (artifact named). |
| **H3** | Two divergent satisfaction matchers | **PARTIAL** — exact boundary: it is ONE implementation (`evaluate_requirement_satisfaction`) with a `purpose` flag (`"gate"` vs `"synthesis"`), not two; but the hypothesised consequence is real and code-forced: the same requirement against the same KB returns satisfied at Gate 2 and "absent" at the caveats layer (narrative-indicator branch and skipped-gap-answer branch both flip on `purpose`); (b) substring/facet-blind hint satisfaction incl. `financials.currency` is confirmed. |
| **H4** | Token-level verification & format echo | **Part 1 CONFIRMED** — prose is tokenised by `\b(\d[\d,]*(?:\.\d+)?)\b`, ISO dates fragment into ≥3 flagged tokens, ≥2-digit definitional numerals (80) flag, and the observed reason string exists verbatim at `numeric_fact_verifier.py:262`. **Part 2 PARTIAL** — no explicit format-preservation instruction exists; the claim-binding contract structurally incentivises verbatim echo of KB values (exact normalized-token match, honest-omission substitution on mismatch); additionally the prose backstop flags multi-token dates in ANY format, ISO included. |
| **H5** | Section starvation by routing | **PARTIAL** — the trimming mechanism exists exactly as described, but for the FCDO template (no `fact_namespaces` declared) the archetype fallback WIDENS finance/risk sections to all `indicators.*`/`financials.*` facts, so their payload is off-topic rather than near-empty; an honest-short-section path exists but its preflight is passed by those same off-topic facts. The per-section synthesis input payload is NOT persisted anywhere — explicit finding. |
| **H6** | Metadata bypasses the knowledge bank | **CONFIRMED** for the cover (reporting period from `donor_reports` columns set at creation; organisation name from `ngo_profiles`; no reconciliation against KB anywhere on that path). Tables: 4 of the 5 tables in the repo's FCDO template fixture render all-"not provided" **by construction** (3× `data_source: manual`; `outcome_assessment` declares zero fillable-family columns); the 5th (`delivery_financial_performance`) empties iff no `financials.*` facts exist in the KB (deployed template + KB are DB state; artifacts named). |
| **H7** | Honesty paths (preserve list) | **LOCATED** — all four mechanisms found and pointered (skip→"not provided"; per-section assumptions + deterministic remit disclosure + honest-empty table caveats; no-invention constraints across five prompts + fail-closed binding; conflicts surfaced-never-resolved with human-only resolution and provenance-only siblings). |

---

## H1 — EXTRACTION LOSS — PARTIAL

**Routing context.** Uploads are classified into `proposal | grant_letter | mou | indicator_data | photo | deck | other` (`app/reports/models/enums.py:21-28`; classifier labels `app/reports/agents/classifier.py:70-74, 417-421`). Extraction routes by classification (`app/reports/orchestration/extract_isolation.py:266-291`): `proposal` → text lane (Docling markdown, `app/reports/orchestration/document_intake.py:99-108` → `app/reports/extraction/docling_adapter.py:18-53`); `grant_letter|mou` → text lane; `indicator_data` → spreadsheet lane (`document_intake.py:111-129` → `app/reports/extraction/spreadsheet_input.py:172-180`); `photo|deck|other` skipped (`extract_isolation.py:46-52`).

### Per-item death points

**(1a) Logframe finance-note column — dies at prompt/schema (extractor scope by design).**
The indicator-data financials contract has no note slot: `FinancialLine = {line_key, label, budget, actual}` (`app/reports/schemas/indicator_data_extraction_v1.py:91-96`); the LLM-side mirror is identical (`app/reports/agents/indicator_data_extractor.py:175-180`). The prompt scopes financials to "budget-vs-actual lines" (rule 10, `indicator_data_extractor.py:104`). A `note` slot exists only on indicator rows, not financial lines (`indicator_data_extraction_v1.py:78-81`). Downstream, the reconciliation flattener emits only `financials.currency` and `financials.lines.<key>.budget|.actual` (`app/reports/reconciliation/input_builder.py:371-398`) — no note path exists to drop.

**(1b) Logframe forecast-cost / actual-cost columns — NOT out of scope by design; loss point not determinable from code.**
Schema slots exist (`budget`, `actual` above) and, if extracted, they flatten into candidates (`input_builder.py:383-398`) — so they are neither schema-excluded nor dropped at reconciliation input assembly. Whether the run's extractor emitted them is model behaviour, not code. **CANNOT DETERMINE FROM CODE**; settling artifact: `uploaded_documents.extracted_json` (`structured.financials`) for the logframe/finance document of report `dfd17248-9b46-48d9-8bc6-5348eab44a1c`, and if present there, `donor_reports.knowledge_bank_json` (`facts`) for the same report to see whether the reconciler LLM carried them into facts.

**(2) Proposal budget table and £1,184,000 total — dies at prompt/schema (by design).**
The proposal extractor's whole scope is objectives, activities, indicators, partners, consultation (`app/reports/agents/proposal_extractor.py:95-134`; LLM output model `:377-383`). `ProposalExtractionOutput` has no budget/financial field of any kind (`app/reports/schemas/proposal_extraction_v1.py:118-126`). No budget instruction exists anywhere in the prompt.

**(3) "612 girls re-enrolled by 16 September 2025" note — dies at prompt/schema (by design).**
No slot for reported achievements/progress notes exists in the proposal schema (`proposal_extraction_v1.py:118-126`); the prompt's five categories (`proposal_extractor.py:95-134`) do not include achievements. (`consultation` is scoped to community-consultation items only, `:122`.)

**(4) Indicator baselines — extracted, then dropped at reconciliation input assembly (proposal lane); no slot at all (tabular lane).**
Proposal lane captures them: prompt line "Extract all logframe indicators (baseline/milestone/endline targets as stated)" (`proposal_extractor.py:113`) and schema slots `ExtractedIndicator.baseline/.milestone` (`proposal_extraction_v1.py:100-109`; LLM mirror `proposal_extractor.py:346-355`). The reconciliation input builder then reads ONLY `target`: `_flatten_proposal` emits `indicators.<key>.target` candidates (`input_builder.py:206-224`) and the strings `baseline`/`milestone` appear nowhere in the file (`grep -c "baseline\|milestone" app/reports/reconciliation/input_builder.py` → 0). Tabular lane: `ExtractedIndicatorRow` has only `target` and `actual` value facets — no baseline field (`indicator_data_extraction_v1.py:70-88`).

**(5) Year-1 milestones of the outcome indicators — same double death as baselines.**
Proposal lane: single `milestone` slot captured (`proposal_extraction_v1.py:105`), never flattened (`input_builder.py:188-270`, absence verified as above). Tabular lane: no milestone slot (`indicator_data_extraction_v1.py:70-88`); a milestone column in the source grid can survive extraction only if the model writes it into `target` — i.e. only by losing its facet identity (this is the H2(a) bridge).

### docx vs xlsx path for the same table

Same lane, same downstream contract. `parse_spreadsheet_from_path` routes `.xlsx` → `parse_xlsx_workbook`, `.docx` → `parse_docx_tables`, `.csv` → `parse_csv_file` (`spreadsheet_input.py:172-180`); all three produce the identical grid JSON shape (`sheets[].rows[].cells[]` with `ref/raw/cell_state`), serialized into the same extractor prompt (`indicator_data_extractor.py:199-214`). Differences confined to grid construction: docx grids are re-synthesized from Docling `table.export_to_dataframe()` — header row taken from `df.columns` and cell refs fabricated from dataframe position (`spreadsheet_input.py:61-90, 93-117`) — while xlsx reads real cells with true coordinates via openpyxl (`:120-146`); a docx with no `document.tables` raises and degrades (`:99-100`). No schema/prompt difference between formats; no milestone/baseline/note-column handling difference between formats.

**Contextual observation (factual):** the proposal extractor prompt hard-codes expectations specific to one document shape — "Extract exactly ONE additional targetless indicator from Value for Money §8 … `equity_support_reach_qualitative`", "Expected total: 15 logframe indicators with targets + 1 targetless equity indicator = 16 indicators", example key `op1_1_girls_reenrolled` (`proposal_extractor.py:114, 118, 131`). Likewise the grant-terms prompt hard-codes the reference run's period scenario: rule 8b names "October to September" vs "15 October 2024 to 14 October 2025" verbatim (`app/reports/agents/grant_terms_extractor.py:85`).

---

## H2 — UNTYPED FACT MODEL — CONFIRMED

### Fact-key shapes (actual, from code)

- **Candidate identity into the reconciler** (`app/reports/reconciliation/input_builder.py:23-39`): `FactCandidate{candidate_id, document_id, source_label, classification, field_path, semantic_hint, value_raw, value_normalized, unit, multi_value, stated_values, provenance, source_section}`. Facet identity exists only INSIDE the `field_path`/`semantic_hint` strings, e.g. `indicators.<row_id>.target` / `indicators.<row_id>.actual` (`:307-321`), `indicators.<key>.target` with hint "Proposal indicator target (<key>)" (`:206-224`), `indicators.<row>.disaggregation.<dim>.<band>` (`:330-354`), `financials.lines.<key>.budget|.actual` (`:383-398`), `reporting_period.start|.end` (`:147-160`).
- **Persisted fact identity** (`app/reports/schemas/knowledge_bank_reconciliation_v1.py:28-48`): `KnowledgeBankFact{value, unit, semantic_label, coverage, source_document_id, source_label, provenance, interpretation_note, verification_status, confirmed*, source_section, provenance_only_for}` keyed by `fact_key`. **There is no typed facet field** — no baseline/milestone/target/actual/disaggregation/total enum anywhere in the model. `fact_key` itself is free text authored by the reconciler LLM (`_LLMFact.fact_key: str`, `:225-235`) and flows into the dict unchanged (`app/reports/agents/knowledge_bank_reconciler.py:430-462`).
- **Conflict shape** (`knowledge_bank_reconciliation_v1.py:58-65`): `KnowledgeBankConflict{fact_key, conflict_type, values[≥2], annotation, resolved_value, resolved_at}`; `conflict_type` is only `VALUE_MISMATCH | UNIT_GRANULARITY` (`:14`) — no facet-mismatch type exists.

### Conflict-detection comparison basis

Conflict detection is LLM semantic judgment, not a typed key comparison. The reconciler system prompt (`knowledge_bank_reconciler.py:119-222`): "Zero numeric tolerance: any non-identical value for the same fact_key and same **semantic quantity** is a VALUE_MISMATCH conflict" (`:143-145`); "You MAY disambiguate MEANING: if two values answer DIFFERENT questions … file them as TWO distinct fact_keys" (`:131-135`). "Same semantic quantity" is decided by the model from `semantic_hint`/`field_path` strings; the only deterministic post-passes are E1 validation (provenance present, no resolutions — `knowledge_bank_reconciliation_v1.py:185-213`) and write-time conflict-key materialization (`app/reports/knowledge/conflict_integrity.py:131-224`) — neither adds facet typing. Model call: direct Anthropic Messages, `ME_RECONCILER_MODEL` default `claude-sonnet-4-6`, temperature 0 (`knowledge_bank_reconciler.py:105, 730-762`).

### (a) Cross-facet comparison → the 1,200 vs 650 "conflict" — CONFIRMED (mechanism)

Both lanes destroy the endline-vs-milestone distinction BEFORE the reconciler sees the values: the proposal's `milestone` is captured but never flattened (H1-4/5, `input_builder.py:206-224` + verified absence), and the tabular lane has no milestone slot so a milestone column can only arrive as `…target` (`indicator_data_extraction_v1.py:70-88`). The reconciler therefore receives two candidates whose facet strings both say "target" (hints "Proposal indicator target (…)" `input_builder.py:217` vs "indicator target (<row>)" `:307-310`) and no typed field exists to distinguish endline from Y1 milestone. Nothing in code prevents the model from filing them as one quantity; the observed Gate 1 conflict is consistent with exactly this. (Which values actually collided in the run: `donor_reports.knowledge_bank_json` → `conflicts[].values[]` for report `dfd17248-9b46-48d9-8bc6-5348eab44a1c`.)

### (b) Genuine conflicts producing no conflict — CONFIRMED (by construction)

- **£1,184,000 (proposal) vs £1,240,000 (award):** the proposal budget is never extracted (H1-2), so no candidate exists on the proposal side; the award side lands as `award_budget.amount` with hint "Total approved programme budget (contract)" (`input_builder.py:130-146`). A one-sided quantity cannot conflict; the prompt additionally instructs "Single-source silence is NOT a conflict" (`knowledge_bank_reconciler.py:147`).
- **Reporting period 15-Oct→14-Oct vs 01-Oct→30-Sep:** period candidates are produced ONLY by the grant-terms flattener (`input_builder.py:147-160`). The proposal flattener emits no period candidates at all (`:188-270`), and report-creation metadata (`donor_reports.reporting_period_start/end`) never enters reconciliation — the bundle is built exclusively from `uploaded_documents` rows (`input_builder.py:497-518`; service seam `app/reports/services/knowledge_bank_reconciliation_service.py:55-66`). When both periods appear in the SAME award letter, the extractor is told to put both into `reporting_period.*.stated_values` as multi_value (`grant_terms_extractor.py:85`), which flattens to sibling candidates of one field (`input_builder.py:83-99`); whether the model then files a conflict is its judgment ("differing surface forms … NOT a disagreement", `knowledge_bank_reconciler.py:189-191`). Cross-document period conflict against proposal-stated or metadata-stated periods is impossible by construction.

### (c) Disaggregation cell alongside indicator actual — CONFIRMED for "no conflict between them"; promotion not code-forced

A disaggregation cell becomes its own candidate `indicators.<row>.disaggregation.<dim>.<band>` with hint "<indicator name> - <dim> - <band>" (`input_builder.py:330-354`), deliberately excluding `stated_total` (comment `:322-325`). It coexists with `indicators.<row>.actual` as a different key; conflicts require the model to judge "same semantic quantity", and no typed relation links a band cell to its row actual — so silent coexistence is the structural default. Whether the run's reconciler ALSO promoted a band value under an actual-shaped `fact_key` cannot be forced or excluded by code (keys are LLM-authored free text). Settling artifact: `donor_reports.knowledge_bank_json` → `facts` key shapes for report `dfd17248-9b46-48d9-8bc6-5348eab44a1c`. Note for downstream surfaces: the DOCX table renderer cannot place a disaggregation key in a value column (facet token `<band>` has no family — `app/reports/export/kb_table_renderer.py:74-99`), but requirement-satisfaction hints DO count such keys (H3(b)).

---

## H3 — TWO DIVERGENT SATISFACTION MATCHERS — PARTIAL

**Exact boundary:** requirement satisfaction is ONE implementation — `evaluate_requirement_satisfaction` (`app/reports/gap/requirement_satisfaction.py:150-228`) — parameterised by `purpose: "gate" | "synthesis"` (`:133, :157`). "Two different implementations" is refuted. The hypothesised CONSEQUENCE — opposite verdicts for the same requirement against the same knowledge bank — is confirmed and code-forced, because the two consumers call with different `purpose` values and two branches flip on it.

### The two call paths

- **Gate 2 question generation** (purpose = `"gate"`): pipeline gap stage → `run_gap_compliance` (`app/reports/orchestration/pipeline.py:317-327`) → deterministic output is the DEFAULT (LLM path only if a test `query_fn` is injected or `ME_GAP_COMPLIANCE_USE_LLM` is set — `app/reports/agents/gap_compliance_agent.py:147-152, 498-514`) → `build_deterministic_gap_compliance_output` → `unsatisfied_requirements` (`app/reports/gap/deterministic_gaps.py:58-96`) → `is_requirement_satisfied` → `evaluate_requirement_satisfaction` with the DEFAULT purpose `"gate"` (`app/reports/gap/satisfaction.py:21-51`).
- **Assumptions/caveats disclosure** (purpose = `"synthesis"`): per-section synthesis appends a deterministic disclosure — `build_owned_absent_disclosure` (`app/reports/services/report_synthesis_service.py:335-337`, merged at `:393-394` and `:432-434`) → `owned_absent_requirements` → `_requirement_present` → `evaluate_requirement_satisfaction(..., purpose="synthesis")` (`app/reports/services/remit_disclosure.py:61-82, 85-118`); the disclosure sentence "The submitted records did not include {items} for \"{label}\". This has been disclosed as a gap rather than estimated." is built at `remit_disclosure.py:121-146`.

### (a) Narrative requirements: auto-satisfy at Gate 2, declared absent by caveats — CONFIRMED

Two independent mechanisms on the Gate 2 side: (i) inside the shared function, a narrative requirement of item type `indicator` **auto-satisfies whenever purpose ≠ "synthesis"**: `if requirement.required_item_type == "indicator" and purpose != "synthesis": return SatisfactionResult(satisfied=True)` (`requirement_satisfaction.py:175-176`); (ii) even when unsatisfied, narrative requirements are excluded from Gate 2 questions outright: `if requirement.requirement_type == "narrative": continue` (`deterministic_gaps.py:75-76`). On the caveats side the same requirement is evaluated with `purpose="synthesis"`, the auto-satisfy branch is dead, and with no matching citable facts it lands in the "did not include" disclosure (`remit_disclosure.py:104-118`). The only route by which narrative items reach Gate 2 at all is the proposal-failure elevation (D-053), which itself evaluates with `purpose="synthesis"` (`app/reports/gap/proposal_failure_elevation.py:49-111`, call at `:90-97`).

A second purpose-flip exists for gap answers: at `"gate"`, a SKIPPED answer (`skip_reason ∈ {not_applicable, cannot_provide}`) counts as satisfying (`requirement_satisfaction.py:136-147` → `app/reports/gap/gap_answer.py:13-32`); at `"synthesis"` only `disposition == "answered"` counts (`requirement_satisfaction.py:143-146`) — so a skipped item likewise satisfies Gate 2 yet is declared absent by the caveats layer.

### (b) Data-typed requirements: substring hints, facet-blind — CONFIRMED

**The deployed hint map** is `DATA_BACKED_HINTS` (`requirement_satisfaction.py:22-41`), reproduced:

```python
DATA_BACKED_HINTS = {
    "actual_results": ["ar1_actual", "indicators."],
    "output_indicators": ["indicators.", "ar1_milestone_target"],
    "outcome_indicators": ["indicators.", "proposal_target"],
    "logframe_milestones": ["ar1_milestone_target"],
    "progress_against_expected_results": ["ar1_actual", "ar1_milestone_target"],
    "forecast_vs_actual_costs": ["financials.lines", "financials."],
    "forecast_vs_actual_spend": ["financials.lines", "financials."],
    "financial_delivery": ["financials.lines", "financials."],
    "cost_drivers": ["financials.lines", "financials."],
    "beneficiary_numbers": ["indicators.", "beneficiar"],
    "outcome_indicators_where_available": ["indicators.", "outcome"],
    "changes_made": [".note"],
    "review_summary_sheet": ["programme_title", "programme_code", "review_date"],
    "outcome_assessment": ["indicators.", "outcome"],
    "delivery_financial_performance": ["financials."],
}
```

Matching is bare substring over citable fact KEYS: `if any(hint in key for key in fact_keys)` (`_hints_match`, `:82-89`), invoked from `_data_indicator_satisfied` (`:92-109`). No facet, no value inspection.

- **Outcome-actuals requirement satisfied by target-only facts:** `"outcome_indicators": ["indicators.", …]` matches ANY key containing `indicators.` — including `indicators.<row>.target` facts sourced from the monitoring sheet. The citable iterator excludes only PROPOSAL-sourced target facts (`_iter_citable_facts` skips `is_proposal_target_fact`, `:52-66`; predicate = target-facet key AND NOT indicator-data source, `app/reports/gap/logframe_completeness.py:82-108`) — indicator-data-sourced targets pass and satisfy. Facet-aware checking exists ONLY for the synthetic `logframe_row:opN_N` requirements (`_data_indicator_satisfied` → `has_indicator_data_actual_for_id`, `requirement_satisfaction.py:99-103`, `logframe_completeness.py:239-253`); every other data requirement is hint-substring only.
- **Financial requirement satisfied by a lone `financials.currency` fact:** hints for all four financial refs include `"financials."`; the key `financials.currency` contains it. Citability never inspects the VALUE — `is_fact_citable` checks only `gate1_confirmed_at`, `provenance_only_for`, `verification_status`, `confirmed_by_user` (`app/reports/knowledge/confirmed_kb.py:34-46`) — so a currency fact whose value is null or "-" satisfies `financial_delivery`, `forecast_vs_actual_costs`, `forecast_vs_actual_spend`, and `cost_drivers`. Table-type requirements are similarly token-substring matched against keys and `semantic_label`s (`_table_satisfied`, `requirement_satisfaction.py:112-124`).

---

## H4 — TOKEN-LEVEL VERIFICATION AND FORMAT ECHO

### Part 1 — deterministic checker tokenizes prose; dates fragment; definitional numerals flag — CONFIRMED

All in `app/reports/services/numeric_fact_verifier.py` ("P1-2 deterministic numeric/date/money verification — zero LLM", `:1-6`), invoked per section by the critic service (`app/reports/services/report_fact_safety_service.py:217-223`), flags merged and BLOCK flags counted for Gate 3 (`:260-271`, `:73-88`).

- **Tokenizer:** `_NUMBER_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\b")` (`:23`); `extract_significant_numbers` scans prose with it, keeping tokens with ≥2 digits (`_MIN_SIGNIFICANT_DIGITS = 2`, `:28`; `:82-105`). The pattern cannot span a hyphen, so `2024-10-15` in prose yields three tokens `2024`, `10`, `15` — each ≥2 digits, each independently checkable. This matches the observed flag population (2024, 10, 15, 21 …).
- **Coverage requirement:** the prose backstop flags every significant prose number not present in the set of normalized bound-claim `value_tokens` (`_verify_prose_backstop`, `:249-266`), with reason **exactly** `"Uncited numeric in prose not covered by any bound claim value_token"` (`:262`) — verbatim the observed reason. Claims-primary check additionally BLOCKs any claim token that doesn't match its cited source value (`:181-246`, reason `:241`).
- **Dates cannot be covered in any prose format:** a date value_token normalizes by stripping non-digits — `normalize_numeric_token("2024-10-15") → "20241015"` (`:45-62`) — while prose fragments normalize to `2024`/`10`/`15`; coverage is exact set membership (`covered` set, `:219-220`, `:255-257`), so fragments never match `20241015`. Fact-value matching is also set membership over whole-value forms (`_value_in_source`, `:141-156`); only GAP-ANSWER text gets a substring allowance (`:160-166`). Consequence: a full date written in prose — ISO or reformatted — produces flags either way; writing it as a claim value_token `"2024-10-15"` binds the CLAIM but still leaves the PROSE fragments uncovered.
- **Definitional numerals:** `80%` yields token `80` (2 digits → significant, `:82-87`); if the 80 inside indicator wording is not a bound claim value_token matching a cited value, it flags. Percent signs are not treated specially.
- The observed `"against a target of not reported this period"` sentence is manufactured upstream, not by the checker: claim binding replaces each unbound numeric token in claim text AND section prose with `HONEST_OMISSION_PHRASE = "not reported this period"` (`app/reports/services/synthesis_claim_binding.py:266-288`; phrase defined `numeric_fact_verifier.py:17`); the checker excludes the phrase itself from scanning (`:93`).

### Part 2 — format echo: instructed, incentivised, or not evidenced — PARTIAL (structurally incentivised; not explicitly instructed)

- **No explicit instruction to preserve KB formats exists.** Full synthesis prompt read: system prompt `app/reports/ai/prompts/synthesis.py:5-72`, user template `:126-199`. Nothing instructs ISO or verbatim date formats. (KB date values are ISO by the extraction contract: "normalized form (dates as YYYY-MM-DD…)", `grant_terms_extractor.py:81`.)
- **Structural incentive at the binding layer:** the contract requires each claim to carry `value_tokens[]` "numeric/date tokens **as they appear in claim.text**" (`synthesis.py:52-54`) and self-audit #2 requires "every value_token … appear in the cited fact or gap answer value" (`:163-165`); server-side, any token that fails exact normalized match against the cited value is REPLACED in the prose by "not reported this period" (`synthesis_claim_binding.py:139-180, 266-288`). Echoing the stored value verbatim is the only strategy that survives binding unmangled — that is the incentive.
- **Boundary:** the incentive explains verbatim VALUE echo, but does not fully explain flag-free ISO dates — as shown in Part 1, the prose backstop flags multi-token dates regardless of format, so ISO echo in the reference run cannot have been a strategy that satisfied the checker; the checker punishes dates in prose in every format. No date-reformatting code exists on the synthesis output path (`synthesis_output_hygiene.py` treats dates only as a "conservative" marker in the legacy auto-citation path, `:330-340, 439-440`).

---

## H5 — SECTION STARVATION BY ROUTING — PARTIAL

### Routing mechanism (as implemented)

`subset_facts_for_section` (`app/reports/services/report_inputs_builder.py:241-296`) filters the citable KB per section in this order: (1) **source pin** — a fact carrying `source_section` is visible only to the section whose `source_section_labels` claim it (`:272-281`); (2) **declared needs** — namespace-root/glob match against the section's `fact_namespaces` + `required_tables` data-source roots (`_fact_namespace_patterns`, `:99-123`); (3) **archetype fallback** — ONLY when the section declares no `fact_namespaces` key at all, the roots from `_ARCHETYPE_FACT_ROOTS` apply (`:45-54, 119-123`); (4) **shared floor** — roots `{grant, reporting, objectives}` visible to every section (`:41, 283-285`); (5) legacy `required_indicators` token match, again only without `fact_namespaces` (`:262-268, 287-288`). Assembled into the synthesis payload by `build_report_inputs_for_section` (`:357-404`).

### Starvation vs widening — the boundary

The hypothesis holds for the mechanism (per-section input IS trimmed by namespace/archetype routing) but inverts for the FCDO template's finance/risk sections: in both repo snapshots of that template every section OMITS `fact_namespaces` (`docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`; `tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json`), so the archetype fallback applies, and `_ARCHETYPE_FACT_ROOTS` grants e.g. `ARCH_RISK_ASSUMPTIONS_AND_CONTROLS → ("indicators","financials")` and `ARCH_DELIVERY_COMMERCIAL_FINANCIAL_REVIEW → ("indicators","financials")` (`report_inputs_builder.py:45-54`). A risk or finance section therefore receives ALL `indicators.*` facts that exist — an off-topic payload, not a near-empty one, whenever indicator facts were extracted but risk/finance facts were not. "Near-empty" occurs only if extraction produced nothing beyond the shared floor.

### Honest-short-section path exists but is bypassed by the same routing

`_generate_one_section` preflights `section_has_synthesizable_inputs` and, when false, emits a deterministic insufficiency section instead of calling the model (`app/reports/services/report_synthesis_service.py:241-252`; prose builder `app/reports/services/section_prose.py:69-126`: "…the organisation has left this section blank rather than report anything not supported by the available evidence."). But the preflight returns true if ANY requirement satisfies at `purpose="synthesis"` — which the facet-blind hint map can grant (H3(b)) — OR if any visible fact has a namespace root outside the shared floor (`report_inputs_builder.py:319-354`, decisive check `:352`). Under archetype fallback, any `indicators.*` fact anywhere makes every ARCH_* section "synthesizable", so the model runs with the off-topic payload. Whether it then pads or writes honestly is model behaviour (the prompt's controlled-uncertainty rule, `synthesis.py:16-19`, points the other way); code determines only the input composition.

### Payload persistence — FINDING: not persisted

Per-section `report_inputs` are built in memory per synthesis run and handed to worker threads (`report_synthesis_service.py:469-477`); only OUTPUTS are persisted (`content_json`, `:648-674`). A repo-wide search for `report_inputs` shows no write to any DB column or file (only prompt assembly, `app/reports/ai/prompts/synthesis.py:126-129, 252-270`). **The per-section synthesis input payload is not persisted anywhere**; what a given section was shown cannot be reconstructed from stored state. (Nearest stored proxies: `donor_reports.knowledge_bank_json` + the template row, from which routing is re-derivable only if both are unchanged since the run.)

---

## H6 — METADATA BYPASSES THE KNOWLEDGE BANK — CONFIRMED (cover); tables by construction (4/5) + KB-dependent (1/5)

### Cover: creation metadata + profile, end to end, no KB check

1. `reporting_period_start/end` are caller inputs at report creation, stored as `donor_reports` columns (`app/reports/services/donor_report_lifecycle_service.py:78-121`, validation `:87-92`, storage `:106-107`; model `app/reports/models/donor_report.py:34-35`).
2. At export, `export_and_persist` reads `report.reporting_period_start/end.isoformat()` and the organisation name from `ngo_profiles.organization_name` (`app/reports/services/report_export_service.py:98-116`; profile query `:98-101`, fallback string "Organisation" `:101`).
3. The renderer prints them verbatim on the title block: `add_branded_title_block(org_name=ngo_name…, subtitle_lines=[f"Reporting period: {reporting_period_start} to {reporting_period_end}", …])` (`app/reports/export/docx_renderer.py:181-194`).
4. No comparison against KB facts exists anywhere on this path — `knowledge_bank_json` enters the renderer solely as table-fill input (`docx_renderer.py:204-207, 226-231`). The reconciler can never flag the discrepancy either, because report metadata never becomes a fact candidate (H2(b); `input_builder.py:497-518`). Body prose gets its dates from KB facts via synthesis inputs (which ALSO carry the metadata period in a separate `report` block — `report_inputs_builder.py:378-391`), so a cover/body split is structurally possible whenever metadata ≠ extracted facts.

### The five tables: binding resolved at render time

Renderer: `table_rows_for_definition` (`app/reports/export/kb_table_renderer.py:220-243`) — `data_source: manual` → ALWAYS exactly one all-`"not provided"` row (`:240-243`, constant `:25`); `indicators|financials` → `_build_rows` (`:181-217`), which returns the single honest-empty row **by construction** when fewer than 2 of the table's `column_key`s resolve to fillable families (`_is_fact_data_table`, `:175-178`; return `:188-190`) or when no KB fact parses into that namespace as `namespace.entity.facet` with facet in the family token sets (`_parse_fact_key` `:87-99`; token sets `:31-52`; return `:192-194`); cells fill only on a single unambiguous same-family fact (`:123-131`).

Against the five-table FCDO template snapshot in-repo (`tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json`; same five present in `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`):

| Table | data_source | column_keys → families | All-"not provided" outcome |
|---|---|---|---|
| `outcome_assessment` | indicators | outcome_statement, progress_summary, evidence, issues, assessment → **all None** | **by construction** (`:188-190`) — no KB content can ever fill it |
| `evidence_quality_matrix` | manual | — | **by construction** (`:240-243`) |
| `risk_register_update` | manual | — | **by construction** (`:240-243`) |
| `recommendations_action_plan` | manual | — | **by construction** (`:240-243`) |
| `delivery_financial_performance` | financials | planned_position→budget, actual_position→actual, variance_or_issue→variance (+2 None) | empty **iff** the KB holds no citable, exportable `financials.*` facts with budget/actual facets at render time (ties to H1(1b)) |

Deployed template and run-time KB are DB state, so the per-run assertion for the fifth table (and the exact deployed table set) is **CANNOT DETERMINE FROM CODE**; settling artifacts: `funder_report_templates.report_sections_json` for the template referenced by `donor_reports.funder_report_template_id`, and `donor_reports.knowledge_bank_json` (`facts`), both for report `dfd17248-9b46-48d9-8bc6-5348eab44a1c`. Additional exclusion at render: conflict-sibling provenance-only facts are filtered from table binding (`docx_renderer.py:204-207` → `conflict_integrity.filter_exportable_facts:232-238`). When a declared table renders honest-empty, the engine appends the true-reason caveat "…no verified figures were available in the submitted records to populate it." (`docx_renderer.py:71-77, 236-238`).

---

## H7 — HONESTY PATHS (PRESERVE LIST) — LOCATED

**1. Skipped gap answers → "not provided"-class output.**
Persistence: skip with `skip_reason ∈ {not_applicable, cannot_provide}` stored in `knowledge_bank_json.gap_answers[item_key]` with `disposition: "skipped"`, `answer_text: null` (`app/reports/services/gate2_gap_answer_service.py:60-88`); skips count as resolved for Gate 2 unlock (`app/reports/gap/gap_answer.py:13-32`; `gate2_gap_answer_service.py:91-151`). Downstream honesty: at `purpose="synthesis"` a skipped answer does NOT count as present (`requirement_satisfaction.py:136-147`), so the owning section's deterministic disclosure names it ("…did not include … disclosed as a gap rather than estimated", `remit_disclosure.py:121-146`); tables render the literal `"not provided"` (`kb_table_renderer.py:25`); unbound numerics become "not reported this period" (`synthesis_claim_binding.py:266-288`; `numeric_fact_verifier.py:17`).

**2. Per-section assumptions/caveats disclosure.**
Model-authored `assumptions[]` per section, required to be plain-English and identifier-free (`synthesis.py:25-32, 152-161, 171-172`); deterministic remit-scoped disclosure appended server-side regardless of what the model wrote (`report_synthesis_service.py:214-221, 335-337, 393-394, 432-434`; builder `remit_disclosure.py:85-146` — owner-only emission + present-elsewhere suppression, header contract `:1-16`); honest-empty table caveats and false-attribution suppression at export (`docx_renderer.py:60-77, 236-238, 251-254`); all collected into the assumptions appendix (`docx_renderer.py:265`).

**3. No-invention constraints in the synthesis prompts (and enforcement).**
System prompt CARDINAL FACT RULE: "Every specific number, name, date, or proper noun MUST come from report_inputs.knowledge_bank… never fabricate a figure to fill the gap" (`synthesis.py:13-19`); task rules 1-3 restrict specifics to facts/gap answers and bar the linked proposal from supplying numbers (`:143-149`); rule 6/6a controlled-uncertainty + remit-scoped caveats (`:152-161`); self-audit (`:163-172`). Peer prompts: proposal extractor "never invent numbers / never drop an indicator for lacking a number" (`proposal_extractor.py:102, 116-117`); indicator extractor "NEVER recompute totals… do NOT invent an actual" (`indicator_data_extractor.py:90-100`); grant-terms "absent=true… do NOT pick a winner" (`grant_terms_extractor.py:80-85`); reconciler "NEVER resolve truth" (`knowledge_bank_reconciler.py:129-151`). Deterministic enforcement: claim binding fails closed (`MISSING_STRUCTURED_CLAIMS` when citable inputs exist but no claims bind — `synthesis_claim_binding.py:322-370`), honest-empty/insufficient-data/parse-failure terminal sections carry engine-owned prose and zero claims (`section_prose.py:69-178`), numeric verifier + qualitative critic BLOCK unsupported specifics (`numeric_fact_verifier.py:181-308`; `fact_safety_critic.py:42-73`; fail-closed UNVERIFIED on critic failure, `report_fact_safety_service.py:91-109, 251-258`).

**4. Conflicts presented to the user, never auto-resolved.**
Reconciler is forbidden to resolve (prompt `knowledge_bank_reconciler.py:129-151`; E1 validation rejects any `resolved_value/resolved_at`, `knowledge_bank_reconciliation_v1.py:185-213`). Write-time integrity guarantees every conflict key has a materializable facts entry and marks exact-match siblings provenance-only, never selecting a value (`conflict_integrity.py:131-224`; applied at persist `knowledge_bank_reconciliation_service.py:77-81`). Humans resolve via `PATCH /api/reports/{id}/knowledge-bank` — resolution requires a concrete value (D-059, `knowledge_bank_patch_service.py:72-82`) and is materialized onto the canonical fact with the winning source's provenance (`:85-140`); Gate 1 confirmation is blocked while any conflict is unresolved (`validate_gate1_knowledge_bank`, `knowledge_bank_reconciliation_v1.py:140-164`; `gate1_confirmation_service.py:151-204`). Provenance-only siblings are excluded from citation and export (`confirmed_kb.py:37-40`; `conflict_integrity.py:232-238`).

---

## SEAM MAP (as implemented at `a74d5e3`)

Stage cursor lives on `report_jobs.stage` (`classify → extract → reconcile → gap → synthesise → critique → export`, `app/reports/models/enums.py:38-46`) with `report_jobs.status ∈ {queued, running, awaiting_human, failed, done}` (`:48-54`). Worker: `job_runner`/lease claims queued jobs (`report_jobs.lease_owner/lease_expires_at/last_heartbeat_at/requeue_count`, `app/reports/models/report_job.py:39-48`) → `run_pipeline` (`app/reports/worker/run_pipeline.py:49-122`) → `run_orchestrated_walk` (`app/reports/orchestration/pipeline.py:695-745`). Gate halts set `status=awaiting_human` and advance `stage` to the NEXT stage before halting (`pipeline.py:141-154, 217-231, 339-366, 369-383`). Draft-first gap variant exists behind `ME_DRAFT_FIRST_GAP` (`pipeline.py:69-70, 271-315`).

| # | Stage boundary | Reads (persisted) | Writes (persisted) | Endpoints / gates consuming |
|---|---|---|---|---|
| 0 | Create report | `funder_report_templates` (active, `lifecycle_service.py:57-75`) | `donor_reports` row: `reporting_period_start/end`, `status='DRAFT'`, empty `knowledge_bank_json/gap_analysis_json/indicator_actuals_json/content_json`, `version=1` (`:100-119`) | `POST /api/reports` (`lifecycle.py:72`); reads `GET /api/reports`, `GET /api/reports/{id}` (`read.py:31,46` — detail exposes `content_json`, `knowledge_bank_json`, `gap_analysis_json`, `report_read_service.py:124-141`) |
| 1 | Upload documents | `donor_reports` (ownership) | `uploaded_documents` row (`storage_ref, original_filename, mime_type, classification=NULL, extracted_json={}, extraction_status='PENDING'`, `lifecycle_service.py:124-187`) + object storage bytes | `POST/GET/DELETE /api/reports/{id}/documents[/{document_id}]` (`lifecycle.py:90,114,133`) |
| 2 | Enqueue job | active-job check | `report_jobs` row `stage='classify', status='queued'` (`lifecycle_service.py:343-389`) | `POST /api/reports/{id}/job` (`lifecycle.py:152`); poll `GET /api/reports/{id}/job` (`:174` — job stage/status + `agent_trace_json`-derived fields) |
| 3 | classify | `uploaded_documents` (bytes via `storage_ref`) | `uploaded_documents.classification` (+ `extraction_status/extracted_json` degrade shape, `classify_isolation.py:50-59,76-78,163`); `report_jobs.agent_trace_json.stages.classify`; `donor_reports.status='DEGRADED'` on degraded notes (`pipeline.py:585-588`) | — |
| 4 | extract | `uploaded_documents.classification` + bytes | `uploaded_documents.extracted_json` = extractor envelope per lane (proposal `proposal_extraction_v1.py:177-187`; grant-terms `grant_terms_extraction_v1.py:118-128`; indicator-data `indicator_data_extraction_v1.py:134-142`); trace `stages.extract`. Degraded proposal → halt `stage='extract', status='awaiting_human'` + `proposal_checkpoint` in trace (`pipeline.py:157-214, 637-646`) | `POST /api/reports/{id}/jobs/proposal-checkpoint/ack` (`lifecycle.py:202`) |
| 5 | reconcile → **Gate 1 halt** | all `uploaded_documents.extracted_json` (bundle: `input_builder.py:497-518`) | `donor_reports.knowledge_bank_json` = `KnowledgeBankReconciliationOutput` + envelope keys (`facts{fact_key→KnowledgeBankFact}`, `conflicts[]`, `unreadable_sources[]`, `reconciliation_outcome`, `gate*_confirmed_at`, `gap_answers{}`, `agent_trace`; `knowledge_bank_reconciliation_v1.py:93-128`, `knowledge_bank_reconciler.py:1237-1263`) after `ensure_conflicts_materializable` (`knowledge_bank_reconciliation_service.py:77-81`); trace `stages.reconcile`; job → `stage='gap', status='awaiting_human'` (`pipeline.py:141-154`) | **Gate 1**: `GET/PATCH /api/reports/{id}/knowledge-bank` (`lifecycle.py:235,252` — PATCH blocked after confirm, `knowledge_bank_patch_service.py:50-62`); `POST …/knowledge-bank/gate1/promote` (`gate1.py:28`); `POST …/knowledge-bank/gate1/confirm` → validates, promotes, stamps `knowledge_bank_json.gate1_confirmed_at`, re-queues gap-stage job (`gate1.py:54`; `gate1_confirmation_service.py:151-204`) |
| 6 | gap → **Gate 2 halt** | `donor_reports.knowledge_bank_json` (requires `gate1_confirmed_at`, `gate_preconditions.py:10-18`), `funder_report_templates.report_sections_json/format_rules_json/terminology_map_json`, `report_jobs.agent_trace_json` (proposal-failure flag) | `donor_reports.gap_analysis_json` = `GapCompliancePersistedEnvelope` (`gap_agent, analyzed_at, report_context, structured{open_items_count, ready_for_gate2, gaps[], readiness_basis}, agent_trace`); trace `stages.gap`; job → `stage='synthesise', status='awaiting_human'` (`pipeline.py:217-231, 234-336`) | **Gate 2**: `GET /api/reports/{id}/gap-check` (`gate2.py:25`); `PATCH …/gap-answers` (partial save, `gate2.py:40` → `gap_check_service.py:155+`); `POST …/knowledge-bank/gate2/gap-responses` → writes `knowledge_bank_json.gap_answers{item_key→{disposition, answer_text|skip_reason, provenance…}}`, stamps `gate2_confirmed_at` when every surfaced gap resolved, re-queues synthesise-stage job (`gate2.py:60`; `gate2_gap_answer_service.py:106-168`) |
| 7 | synthesise → critique boundary park | `knowledge_bank_json` (requires `gate2_confirmed_at`), `gap_analysis_json.report_context`, template row, `ngo_profiles` (via `get_profile`), `proposals.content_json` if linked, `donor_reports.reporting_period_*` (`report_inputs_builder.py:357-404`; per-section inputs in-memory only) | `donor_reports.content_json` = `{sections[]{section_key,label,generation_status,archetype,content{text,assumptions,evidence_used,claims,citation_mode,structured_bind_status,…},critic_flags,failure_reason,constraints_applied,human_edited,last_edited_at}, generation_summary, synthesis_mode?}` (`content_json_v1.py:8-59, 208-221`); `donor_reports.status` DEGRADED/DRAFT by failure count (`report_synthesis_service.py:666-671`); trace `stages.synthesise`; job → `stage='critique', status='awaiting_human'` (`pipeline.py:339-366, 497-550`) | `POST /api/reports/{id}/job/resume-critique` (`review.py:28`) resumes the parked job |
| 8 | critique → **Gate 3 halt** | `content_json.sections`, `knowledge_bank_json` (citable view + section-scoped view mirroring synthesis routing, `report_fact_safety_service.py:152-231`), template sections | `content_json.sections[].critic_flags[]` (fence + deterministic numeric + qualitative; `severity/reason/accepted/…`), `generation_status→'AWAITING_REVIEW'` on flags, `generation_summary.critic_blocks/awaiting_review` (`report_fact_safety_service.py:58-88, 260-283`); trace `stages.critique` (incl. `action`, `critic_blocks`); job → `stage='export', status='awaiting_human'` (`pipeline.py:369-383, 386-433`) | **Gate 3**: `PATCH /api/reports/{id}/sections/{section_key}` (edit text / accept flags / mark ACCEPTED; edits set `human_edited`, blocked ACCEPT while unaccepted BLOCK flags — `review.py:50`; `report_section_review_service.py:104-198`); `POST …/sections/accept-all` (`review.py:73`; `:199-235`); `POST …/knowledge-bank/gate3/confirm` → requires critique_completed in latest job trace, zero unaccepted BLOCK flags, all sections ACCEPTED + export-ready, stamps `knowledge_bank_json.gate3_confirmed_at`, re-queues export-stage job (`gate3.py:19`; `gate3_confirmation_service.py:112-189`) |
| 9 | export → done | `content_json.sections`, template row (`report_sections_json`, `format_rules_json`, `docx_template_ref`), `knowledge_bank_json.facts` (exportable subset), `gap_analysis_json`, `donor_reports.reporting_period_*`, `ngo_profiles.organization_name` (requires `gate3_confirmed_at`; `report_export_service.py:56-123`) | object-storage docx; `content_json.export{storage_ref, filename, content_type, generated_at, template_version, render_mode}` (`:143-150`); quota charge; `donor_reports.status='COMPLETE'` (`:152-155`, DEGRADED on failure `:182-185`); trace `stages.export`; job `status='done', finished_at` (`pipeline.py:436-494`) | `GET /api/reports/{id}/export` streams via `content_json.export.storage_ref` (`export.py:21`; `report_export_service.py:194-208`) |

Gate enforcement is server-side at stage entry, keyed solely on `donor_reports.knowledge_bank_json.gate{1,2,3}_confirmed_at` (`gate_preconditions.py:10-71`; enforced in `pipeline.py:252, 345, 404, 455, 514-517` and in the gate services). All M&E routes sit behind the plan gate (`app/reports/router.py:16-24`). Job lease/recovery seams: `worker/job_lease.py`, `worker/orphan_reaper.py`, `worker/job_timeout.py`; reconciler chunking entry `reconciliation/chunked_reconcile.py` (via `knowledge_bank_reconciler.py:1188-1211`).

— END OF AUDIT —
