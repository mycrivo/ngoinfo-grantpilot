# REPORT_REQUIREMENT_SNAPSHOT_SCHEMA.md

**Status:** Canonical (LOCKED for V2 build)  
**Applies to:** `donor_reports.requirement_snapshot_json` — the runtime-compiled reporting contract for one report  
**Replaces at runtime:** `FUNDER_TEMPLATE_SCHEMA.md` / `FUNDER_TEMPLATE_SCHEMA_AS_BUILT.md` (historical from V2)  
**Decisions:** D-085, D-086, D-087

---

## 1. Purpose

The snapshot is what the funder asked for, read from the funder's own document at run time (or instantiated from the generic structure when no confirmed funder document exists). Every downstream stage — evidence matrix, Gate 2, writer, critic, formatter — reads the snapshot and nothing else for structure. There are no authored slugs, archetypes, hint keys, data-source bindings or funder-owned section lists anywhere else in the engine.

Two properties are non-negotiable:
- **Shown before use.** The NGO sees source, sections and tables and confirms (D-086).
- **Immutable after confirmation.** A changed source produces a new version before Gate 1; after Gate 1 confirmation the snapshot cannot change for this report.

---

## 2. Schema

```json
{
  "schema_version": "1.0.0",
  "compiler_version": "string",
  "compiled_at": "ISO-8601",
  "basis": "FUNDER_REQUIREMENTS | GENERIC_FALLBACK",
  "source": {
    "kind": "upload | web_official | web_candidate | generic",
    "document_id": "uuid or null",
    "url": "string or null",
    "title": "string or null",
    "publisher_domain": "string or null",
    "fetched_at": "ISO-8601 or null"
  },
  "funder_name": "string — as entered by the user",
  "report_type": "annual | quarterly | interim | final | other | null",
  "document_title": "string — the title the report should carry, e.g. 'Annual Review' or 'Progress Report'",
  "language": "string — BCP-47, default 'en-GB'",
  "terminology": {
    "prefer": { "outputs": "deliverables", "beneficiaries": "participants" },
    "avoid": ["string"],
    "notes": "string or null"
  },
  "global_constraints": {
    "page_limit": "integer or null",
    "word_limit": "integer or null",
    "tone": "string or null",
    "instructions": ["verbatim or close-paraphrase instruction", "…"],
    "attachments_required": ["string"]
  },
  "sections": [ { "...": "Section object — §2.1" } ],
  "annexes": [ { "annex_key": "a01", "heading": "string", "owner": "ngo | funder", "mandatory": false, "instructions": "string" } ],
  "funder_completes": ["plain-language list of anything the funder fills in or scores"],
  "unmapped": [
    { "text": "what the document asks for that the compiler could not express in this schema", "source_location": "string" }
  ],
  "compiler_notes": ["string"]
}
```

### 2.1 Section object

```json
{
  "section_key": "s03",
  "order": 3,
  "heading": "string — the funder's exact heading",
  "funder_numbering": "string or null — e.g. 'B.2'",
  "owner": "ngo | funder | shared",
  "mandatory": true,
  "applies_to_report_types": ["annual", "final"],
  "purpose": "one or two sentences, in the funder's words where possible, on what this section is for",
  "instructions": ["each instruction the document gives for this section, with its source_location kept in requirements[]"],
  "requirements": [ { "...": "Requirement object — §2.2" } ],
  "tables": [ { "...": "Table object — §2.3" } ],
  "word_limit": "integer or null",
  "source_location": "string — page/heading in the funder document",
  "notes": "string or null"
}
```

### 2.2 Requirement object

```json
{
  "requirement_key": "s03.r1",
  "text": "plain-language statement of what must be reported — e.g. 'Progress against each output indicator for this reporting period, compared with the year milestone'",
  "kind": "narrative | figure | table | list | attachment | score | statement",
  "mandatory": true,
  "domain_hint": "indicators | finance | beneficiaries | risks | safeguarding | activities | partners | learning | identity | other",
  "facet_hint": "actual | target | milestone | baseline | variance | context | null",
  "comparator": "period_milestone | endline_target | baseline | prior_period | budget | none",
  "period_scope": "this_period | cumulative | grant_to_date | final | null",
  "evidence_expectation": "string or null — what the funder says counts as evidence",
  "final_report_only": false,
  "source_location": "string"
}
```

`domain_hint`, `facet_hint`, `comparator` and `period_scope` are **hints for the evidence judge**, expressed in the ledger's vocabulary (`DB_FIELD_CONTRACT_GRANTS.md` §3). They are not lookup keys; the judge reads `text` and the whole ledger.

### 2.3 Table object

```json
{
  "table_key": "s03.t1",
  "title": "string — the funder's table title",
  "mandatory": true,
  "row_entity": "indicator | budget_line | risk | activity | beneficiary_group | partner | other",
  "columns": [
    { "column_key": "c1", "label": "string — the funder's column heading, verbatim", "kind": "text | integer | number | money | percent | date", "facet_hint": "baseline | milestone | target | actual | variance | context | null", "period_hint": "this_period | cumulative | endline | null" }
  ],
  "min_rows": "integer or null",
  "instructions": ["string"],
  "source_location": "string"
}
```

The writer fills a table by emitting one row per ledger entity of `row_entity`, one cell per column, each value cell bound to a `fact_key` (`DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md` §6). Column headings render **verbatim** from `label`.

---

## 3. Compiler rules

1. **Whole document, one read.** The compiler receives the entire funder document (text and tables) in one context and produces one snapshot. No per-heading extraction passes.
2. **Meaning, not headings.** A heading with instructions beneath it becomes a section with `requirements[]` that state what is asked, in plain language. A form field becomes a requirement of `kind = figure | statement`. A scoring box the funder fills becomes `owner = funder` and an entry in `funder_completes`.
3. **Order is the funder's order.** `order` follows the document. Nothing is reordered, merged or added.
4. **Nothing is invented.** A section, table or column not in the document is not in the snapshot. Where the award letter's reporting clause mandates content the template omits (e.g. a value-for-money section), the compiler adds it **only when the award letter is the governing document or the NGO confirms the addition at the requirements screen**; otherwise it is listed in `compiler_notes` and the evidence judge treats it as `not_applicable`.
5. **Express or expose.** Anything the compiler cannot express in this schema goes to `unmapped[]` with its location; it is shown to the NGO on the requirements screen. Silent loss is a defect.
6. **No funder vocabulary in the compiler.** The compiler prompt contains no funder name, no fixture phrase, no expected section count. The funder-string guard applies.
7. **Validation before persistence.** The snapshot is schema-validated; `section_key`/`requirement_key`/`table_key` are ordinal and unique; a `money` column requires a currency somewhere in `global_constraints.instructions` or the ledger; a section with `owner = funder` has no NGO requirements.
8. **Versioning.** Each compile increments `donor_reports.requirement_version`; the confirmed one is frozen with `requirement_confirmed_at`.

---

## 4. Generic fallback instance (D-087)

Instantiated verbatim from this section when `basis = GENERIC_FALLBACK`. It is the **only** authored structure in the system. It is never merged into a funder-specific snapshot; it may be used internally to classify requirements (`domain_hint`) and for nothing else.

`document_title`: "Progress Report" (or "Final Report" when `report_type = final`). `language`: en-GB.

| order | section_key | heading | requirements (kind · comparator) | tables |
|---|---|---|---|---|
| 1 | s01 | Cover and summary | organisation, programme, funder, reference, period (statement); one-page summary of results, deviations, finance, risks, next steps (narrative) | — |
| 2 | s02 | Programme overview | objectives, target groups, geography, partners, context for the period (narrative · context) | — |
| 3 | s03 | Progress against results | per outcome and output: indicator, baseline, period milestone, achieved, variance and explanation (figure · period_milestone); disaggregation where reported (figure) | t1 Results — Indicator · Baseline · Milestone for period · Achieved · Variance · Comment (row_entity indicator) |
| 4 | s04 | Activities and deliverables | activities and deliverables in the period, by output (list · context) | — |
| 5 | s05 | Deviations, challenges and adaptations | what changed against plan, why, what was agreed (narrative · prior_period) | — |
| 6 | s06 | Beneficiaries | reach and disaggregation where data exists (figure · this_period); beneficiary voice or case study where provided (narrative) | t2 Beneficiaries — Group · Planned · Reached · Comment (row_entity beneficiary_group) |
| 7 | s07 | Risks and safeguarding | risk register update (list · context); safeguarding activity or a nil return only where stated (statement) | t3 Risks — Risk · Rating · Mitigation · Status (row_entity risk) |
| 8 | s08 | Partners, governance and staffing | partner performance, coordination, staffing changes (narrative · context) | — |
| 9 | s09 | Financial report | budget against actual by line, variance and explanation, spend against envelope, unspent funds (figure · budget) | t4 Finance — Budget line · Budget · Actual · Variance · Comment (row_entity budget_line; money columns) |
| 10 | s10 | Learning, evaluation and next steps | lessons, evaluations, recommendations, next-period plan (narrative) | — |
| 11 | s11 | Annexes | evidence sources; assumptions and disclosures; data tables (list) | — |

All sections `owner = ngo`, `mandatory = true` except s06 beneficiary voice, s07 safeguarding nil return, s08, s11, which are `mandatory = false`. `applies_to_report_types = ["annual","quarterly","interim","final","other"]`.

**Disclosure:** a report with `basis = GENERIC_FALLBACK` carries, in the app and as a removable note on the DOCX cover, the sentence: "This report uses GrantPilot's standard structure because your funder's reporting guidance was not confirmed." The reason (`generic_reason`) is shown in the app only.

---

## 5. Fixtures

| Fixture | Source | Proves |
|---|---|---|
| FCDO Annual Review | `FCDO_Annual_Review___April_2025___March_2026__1_.docx` (upload) | complex, funder-owned scoring, tables, period comparator |
| Contrasting funder | sourced under P0.5 (upload or discovery) | simpler narrative format, different vocabulary |
| Generic | §4 instance | fallback and disclosure |
| Unseen funder | chosen at P10.3, not used during P3 | generalisation |

The compiler prompt is authored without reading any fixture beyond the FCDO document's **structure**; fixture-specific wording in the prompt fails the guard.

---

## 6. Build Enforcement

Invalid and must not be merged:
- any engine read of `funder_report_templates` for structure after P3;
- a snapshot mutated after `requirement_confirmed_at`;
- a funder-specific snapshot containing a generic section it did not source from the document;
- a compiler prompt containing a funder name or fixture phrase;
- a snapshot persisted with unvalidated keys or an empty `sections[]` for a confirmed funder document.
