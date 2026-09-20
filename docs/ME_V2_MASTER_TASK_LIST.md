# ME_V2_MASTER_TASK_LIST.md

**Status:** Master development file — M&E Report Writer V2 (retrofit)  
**Version:** 1.0 · 6 September 2026  
**Authority:** `GrantPilot_ME_Report_Writer_Product_Vision_v1.1.docx` → `ME_MODULE_MASTER_REBUILD_PROJECT_PLAN_V2.md` (architecture, with the approved beta cuts recorded in §0.2 below) → the five V2 contracts → this file.  
**Owner:** Pranab (product, launch, production triggers) · **CTO co-pilot:** Claude (sequencing, prompt authoring) · **Builder:** Cursor · **Auditor:** Claude Code (read-only, one pass per package)

---

## 0. Rules of the build

### 0.1 Non-negotiables

1. **Contract before code, per package.** Each package's contract lines are final before its Plan Mode spec is issued. No sixteen-document phase; the five V2 contracts plus per-package additions carry the build.
2. **Tiers.** GREEN — Cursor runs autonomously inside the package fence. AMBER — Plan Mode STOP before any build (anything touching the moat, schema, quota, auth, or the live journey). OWNER — production mutations and live validation are triggered by Pranab.
3. **Builder never grades its own work.** Every package gets one independent Claude Code audit before merge. A second pass only on a BLOCKER.
4. **Anti-bent-ruler.** Tests assert the correct target; code changes to match. A target moves only when the correct answer has changed, and every moved target is listed in the PR.
5. **Anti-death-star.** One scoped package at a time. A package that grows past its fence stops and reports.
6. **No fixture content in prompts or engine files.** The funder-string guard blocks it; a package that needs a guard exception has the wrong design.
7. **Rollback path in every package.** Schema changes additive; old paths remain readable until P8.4 cutover.
8. **Kill switch untouched.** `ME_MODULE_ENABLED`, frontend flag and worker switch keep working at every commit; proposal, Fit Scan, auth and billing are never altered by M&E packages.
9. **The gate is the rendered document.** The scorecard is the regression instrument; reading the exported DOCX against the golden record is the acceptance instrument. Both run, every package.

### 0.2 Approved beta cuts (from Plan V2)

| Plan V2 item | Beta decision |
|---|---|
| Grant parent + persistent ledger | **In** — write-through at gate confirmations; pipeline keeps reading the report KB (D-084) |
| Requirement snapshot, source precedence, generic fallback | **In** (D-085, D-086, D-087) |
| Web discovery of official funder guidance | **In**, behind a provider interface, shown before use |
| Conversational Gates 1–3 | **In**, one component, replies compile to recorded actions (D-090) |
| Requirement → Evidence matrix | **In** (D-091) |
| Arithmetic | **Derived numbers computed by code, never written by the model** (D-089). Column sums, disaggregation totals, currency checks — post-beta |
| Prior report / funder feedback / management actions | **`prior_report` document role only.** Feedback and action memory — post-beta |
| Next-report carry-forward workflow, grant dashboard/history | **Post-beta** (schema is ready for it) |
| Stage 0 audit | **Done** — `ME_STATUS_AUDIT_2026-09-03` (Claude Code) and Cursor's counterpart |
| Stage A sixteen documents | **Five contracts** (§0.3) + decision log |
| Frontend last | **Interleaved** from Day 11 on gate payloads contracted in P4–P6 |

### 0.3 The five V2 contracts

| File | Governs |
|---|---|
| `DB_FIELD_CONTRACT_GRANTS.md` | `grants` table, ledger fact shape, fact-key grammar, write-through |
| `DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md` | new report columns, evidence matrix, conversation log, deprecations |
| `DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS_V2_DELTA.md` | document roles, grant link, routing rules |
| `REPORT_REQUIREMENT_SNAPSHOT_SCHEMA.md` | the runtime-compiled reporting contract and the generic fallback instance |
| `API_CONTRACT_ME_V2.md` | §12 v2: grants, requirements, gate conversations, display labels, deprecations |

### 0.4 Decisions recorded by this build (numbering continues from D-083; adjust to the log)

D-084 Grant is the parent entity; the confirmed ledger persists on the grant by write-through at gate confirmations; the run reads the report KB. · D-085 The requirement snapshot is the runtime source of report structure; immutable after confirmation; `report_basis` ∈ {FUNDER_REQUIREMENTS, GENERIC_FALLBACK}. · D-086 Source precedence: NGO upload → official web document → web candidate (explicit confirmation) → generic; a funder document is never applied unseen. · D-087 The generic structure is fallback only; never blended into a funder-specific report. · D-088 Facts carry facet, period, scope and entity; a conflict exists only for the same metric, period and scope; "keep both" is a resolution. · D-089 Derived numbers are computed by code; the model never performs arithmetic. · D-090 Gates are bounded conversations; each reply compiles to recorded actions that are echoed before the next step; Gate 2 asks at most four questions per turn. · D-091 The Requirement → Evidence matrix is the single satisfaction judgement, reused by gaps, synthesis eligibility, critic traceability and disclosures. · D-092 The critic compares meaning; severities CRITICAL / IMPORTANT / SUGGESTION; only CRITICAL blocks export. · D-093 One deterministic DOCX formatter; no per-funder files. · D-094 `funder_report_templates` is retired progressively: no new engine reads from P3 on; rows kept until post-beta approval. · D-095 The server supplies a display label for every enum it returns; the frontend renders labels, never raw values. · D-096 Post-beta: next-report workflow, feedback/action memory, full arithmetic suite, grant dashboard, organisation-profile builder.

---

## 1. Sequence at a glance

| Day | Package | Cursor prompts (titles) | Tier | Claude Code audit |
|---|---|---|---|---|
| 0 | P0 Owner actions | (in flight — Railway variables, PDF image check, smoke env, git status, frontend access) | OWNER | — |
| 1 | P1 Contracts · P2 Persistence | P1.1 · P2.1 | GREEN · AMBER | after P2 |
| 2 | P2 · P3 Requirements | P2.2 · P3.1 | AMBER | after P3 |
| 3 | P3 | P3.2 | AMBER | |
| 4 | P3 | P3.3 · P3.4 | AMBER | ✔ P3 |
| 5 | P4 Ledger & Gate 1 | P4.1 · P4.2 | AMBER | |
| 6 | P4 | P4.3 · P4.4 | AMBER | ✔ P4 |
| 7 | P5 Evidence & Gate 2 | P5.1 · P5.2 | AMBER | ✔ P5 |
| 8 | P6 Writer, critic, Gate 3 | P6.1 | AMBER | |
| 9 | P6 | P6.2 · P6.3 | AMBER | |
| 10 | P6 · P7 Formatter | P6.4 · P7.1 | GREEN | ✔ P6, P7 — **Checkpoint A: engine walked through the API on both fixtures** |
| 11 | P8 Frontend | P8.0 (Claude Code) · P8.1 | AMBER | |
| 12 | P8 | P8.2 | AMBER | |
| 13 | P8 · P9 Instrumentation | P8.3 · P8.4 · P9.1 | AMBER · GREEN | ✔ P8 |
| 14 | P10 Certification | P10.1 · P10.2 | OWNER | |
| 15 | P10 | P10.3 · P10.4 · P10.5 | OWNER | ✔ launch audit — **Checkpoint B: beta opens** |

Each evening from Day 5: one live run on the FCDO fixture through the API; bundle export; scorecard; DOCX read against `GOLDEN_RECORD_LAYER4_v1_1`. Same-or-better on Layers 1, 4, 5 is the merge condition; Layers 2–3 are expected to move as the engine changes and are reviewed, not gated.

---

## 2. Task list by package

Format per task: **ID · Cursor prompt title** — tier — depends on — delivers — acceptance.

### P0 — Owner actions (OWNER, in flight)

- **P0.1 · Set extraction model to Sonnet on web and worker; raise classifier timeout ceiling** — done/confirm.
- **P0.2 · Verify the deployed worker image has Docling's PDF libraries (Railpack ignores nixpacks.toml)** — if missing, becomes P3.1's first task.
- **P0.3 · Set SMOKE_FUNDING_OPPORTUNITY_ID so the proposal journey runs in CI; one manual proposal end to end** — proposal writer status becomes verified.
- **P0.4 · git status; frontend repo access for Claude Code** — enables P8.0.
- **P0.5 · Source the contrasting funder's reporting document and a matching NGO bundle** — due Day 8 (feeds P10.1). Longest lead.
- **P0.6 · Confirm five beta NGOs across different funders; one with a funder document, one without** — due Day 12.

### P1 — Contracts (GREEN, docs only)

- **P1.1 · Adopt the five V2 contracts, extend ENUM_REGISTRY §5, record D-084–D-096, mark template-catalogue documents historical** — depends P0 — delivers contracts in `docs/`, enum registry additions (§5.3 classification values, §5.6 `requirements` stage, §5.9 critic severities v2, new §5.11 report_basis, §5.12 evidence status, §5.13 conversation actions), deprecation record for `funder_report_templates` — acceptance: no contract conflict list is empty; Claude Code confirms in P2 audit.

### P2 — Persistence (AMBER — schema)

- **P2.1 · Migration: grants table, donor_reports V2 columns, uploaded_documents V2 columns, enum extensions, backfill of existing reports into per-report grants; bundle export includes V2 fields** — depends P1.1 — delivers additive schema per contracts; every existing report gains a `grant_id`; migrations run from clean DB and from production schema; downgrade proven — acceptance: existing production reports readable; scorecard bundle for dfd17248 exports with V2 fields present (empty).
- **P2.2 · Ledger write-through at gate confirmations; grants list and detail endpoints** — depends P2.1 — delivers confirmed facts, conflict resolutions and answers written to `grants.ledger_json` with supersession at Gate 1/2/3 confirm; `GET /api/grants`, `GET /api/grants/{id}`; `POST /api/reports` V2 body with inline grant — acceptance: after a Gate 1 confirm on the fixture, the grant ledger holds every confirmed fact with provenance; a second confirm supersedes rather than overwrites; pipeline reads unchanged.

### P3 — Requirements: intake, compiler, discovery, confirmation (AMBER — moat)

- **P3.1 · Funder guidance intake: `funder_guidance` and other V2 document roles, user-declared role at upload, routing to the requirements job, exclusion from fact extraction** — depends P2.1 — delivers role field on upload, classifier bypass when the user declares a role, `requirements` job stage, guidance documents never enter the knowledge bank — acceptance: uploading the FCDO Annual Review docx with role `funder_guidance` produces no facts and queues a requirements job; a proposal uploaded without a role still classifies.
- **P3.2 · Requirement compiler: any confirmed funder document → requirement snapshot v1; generic fallback instantiation; FCDO and generic fixtures** — depends P3.1 — delivers the compiler agent (strong model, whole document), snapshot validation against `REPORT_REQUIREMENT_SNAPSHOT_SCHEMA`, `unmapped` list, generic instance from the 11-section structure — acceptance: FCDO docx compiles to its sections and tables in order with owner and comparator set; anything the award letter mandates that the template omits is not silently added (it is listed for Gate 2 under the matching section); no funder name or fixture phrase in the compiler prompt; generic instance validates.
- **P3.3 · Web discovery provider: official-source search and fetch behind a provider interface, candidate classification and ranking, no-result and unavailable paths** — depends P3.2 — delivers provider abstraction with one maintained search/fetch library, official-domain preference, candidate list with provenance, timeouts, clean degradation to upload/generic — acceptance: for a funder with a published format the top candidate is the reporting template or grantee guidance, not a proposal form or the funder's own annual report; for a funder without one, `discovery_status = no_result`; provider outage returns `unavailable`, never an error to the NGO.
- **P3.4 · Requirements resolve/confirm API: proposal with source and preview, candidates, unmapped items, confirm / swap / generic; snapshot freeze; report_basis** — depends P3.3 — delivers the three requirements endpoints, `requirement_source_json`, immutability after confirmation, re-resolve allowed until Gate 1 confirm — acceptance: nothing downstream runs before `requirement_confirmed_at`; confirming a web candidate records the user decision; generic confirmation records the reason; no code path in P3 reads `funder_report_templates`.

### P4 — Ledger facets, reconciliation, derived numbers, Gate 1 conversation (AMBER — moat)

- **P4.1 · Facts carry facet, period, scope and entity; extractors emit baseline, milestone, target and actual with periods; keys follow the V2 grammar; hygiene no longer collapses facets; expected-count and fixture lines removed from extractor prompts** — depends P2.1 — delivers V2 fact shape end to end (extract → KB → citation → hygiene) — acceptance: the proposal's endline target and year-one milestone land under distinct keys with periods; the spreadsheet's actual lands under a third; a citation to a milestone survives to the writer's output as a milestone.
- **P4.2 · Period-and-scope-aware reconciliation with "keep both"; conflicts only for the same metric, period and scope; entity alias merging** — depends P4.1 — delivers reconciler rule change and the `keep_both` resolution writing both facts — acceptance: milestone vs endline target is not a conflict; two actuals for the same indicator and period from different sheets are; the same indicator seen as "OP1.1" and "Output 1.1" merges.
- **P4.3 · Derived numbers computed, never written: variance, percentage of target, totals as `derived` facts with `derived_from`; writer and critic consume them; model forbidden from arithmetic** — depends P4.2 — delivers deterministic derivation on every ledger mutation — acceptance: every percentage in the fixture's draft is a derived fact; a planted wrong percentage in prose is caught by the critic against the derived value.
- **P4.4 · Gate 1 conversation: material-facts summary bound to facts; reply compiler to recorded actions (confirm, correct, clarify period, resolve, keep both, add); echo of applied actions; confirm; view-all items** — depends P4.3 — delivers gate conversation endpoints for gate1, summary generator with claim binding, reply compiler agent with deterministic action schema — acceptance: the summary states programme, period, organisation (from documents), material results, finance and each genuine conflict with the proposed treatment; a typed correction to a budget figure is recorded as `correct_value` on the right key and echoed; an off-topic reply gets a plain redirection and records no action.

### P5 — Requirement → Evidence matrix and Gate 2 conversation (AMBER — moat)

- **P5.1 · Requirement → Evidence matrix: one judgement per requirement against the confirmed ledger; contract statuses; drives gaps, synthesis eligibility and disclosures; hint map, slug checklist and clause maps removed from the path; readiness score removed** — depends P4.4, P3.4 — delivers `evidence_matrix_json` and the judge agent (full ledger + requirement text) — acceptance on the FCDO fixture: outcome actuals are a gap; "progress against expected results" is not; funder-owned items are `funder_owned`; a requirement with a null-currency fact is not `satisfied`; the disclosure text for an `unavailable` item is the same object the writer will use.
- **P5.2 · Gate 2 conversation: three to four questions per turn in plain language with the period comparator quoted; answer normaliser writes ledger facts with `user_answer` provenance; "not available" handling; view all remaining** — depends P5.1 — delivers gate2 conversation on the shared endpoints — acceptance: ≤10 questions in total on the fixture, none answerable from the bundle; no internal key or slug in any question; an answer of "we reached 684 girls" becomes an `actual` fact for the right indicator and period and the matrix item flips to `answered`.

### P6 — Writer, critic, Gate 3 (AMBER — moat)

- **P6.1 · Section writer from snapshot and whole ledger: funder order and terminology, structured table rows bound to facts under the funder's columns, honest absence disclosures from the matrix, human dates, no identifiers, no funder-specific rules or archetypes, cover fields from confirmed facts** — depends P5.2 — delivers the rewritten synthesis stage with a structured `table_rows` channel in `content_json` and per-section inputs persisted for audit — acceptance: every confirmed actual appears; tables populate wherever facts exist; an empty section is one honest sentence; no ISO dates; no "OP2_3"-style strings; cover period and organisation match the award letter; funder_report_templates not read.
- **P6.2 · Meaning-level fact-safety critic: typed comparison of numbers, dates and money; derived claims recomputed; definitional numerals exempt; CRITICAL / IMPORTANT / SUGGESTION; only CRITICAL blocks; flag text says what is wrong and what to do** — depends P6.1 — delivers the replacement checker and severity model — acceptance: ≤5 flags on the fixture, none from date formatting; a planted wrong number, wrong period and unsupported claim are each caught as CRITICAL; a planted paraphrase is not flagged.
- **P6.3 · Gate 3 conversation: material flags in words; reply compiler (accept flag, correct claim, edit section); section edit persists as human-edited; confirm; export gate honours CRITICAL only** — depends P6.2 — delivers gate3 conversation and the accept-all removal — acceptance: an NGO can resolve every CRITICAL by reply or edit; IMPORTANT and SUGGESTION never block; export refuses only on unresolved CRITICAL.
- **P6.4 · Remove retired template-driven code paths and contamination residue; funder-string guard sweep of the whole tree** — GREEN — depends P6.3 — delivers deletion of hint maps, archetype rules, slug clause maps, FCDO-owned section sets, per-funder fallbacks and dead readers of the template table (rows kept) — acceptance: tree-wide guard report is empty; all fixtures still pass through the harness.

### P7 — DOCX formatter (GREEN)

- **P7.1 · Deterministic DOCX formatter: cover page, contents, numbered headings in snapshot order, fact-bound tables, page numbers, page borders, consistent styles; generic-basis note; idempotent re-export** — depends P6.1 — delivers renderer v2 on python-docx from scratch; no docxtpl, no per-funder files — acceptance: an 11-section generic report and a 7-section funder report both render valid, editable DOCX; contents updates on open; re-export is byte-stable except timestamps.

### P8 — Frontend (AMBER — journey; separate repo)

- **P8.0 · Frontend current-state audit (Claude Code, read-only): routes, gate screens, enum rendering, feature flag, template picker dependencies** — depends P0.4 — delivers the map the next three prompts need.
- **P8.1 · Start report and reporting requirements screens: funder and period; upload guidance or find it; source shown; confirm, swap or continue with the standard structure; progress copy in user language** — depends P3.4, P8.0 — acceptance: an NGO with no funder document reaches a confirmed generic basis in under two minutes and is told why.
- **P8.2 · Gate conversation component, used for all three gates: turns, reply box, applied-actions echo, view-all drawer, confirm; loading states; error copy that never blames the user** — depends P4.4, P5.2, P6.3 — acceptance: the same component renders gate1, gate2 and gate3 with no gate-specific code beyond copy.
- **P8.3 · My grants and reports list, report detail, download; every enum rendered from the server's label** — depends P2.2, P7.1 — acceptance: no raw enum, key or status string visible on any screen (rendering guard test).
- **P8.4 · Retire the template picker and old gate screens; feature-flag cutover; remove dead routes** — depends P8.1–P8.3 — acceptance: old endpoints unused by the frontend; kill switch still hides the module cleanly.

### P9 — Instrumentation (GREEN)

- **P9.1 · Scorecard header and per-report metrics surfaced from existing schema: keep rate, cost per report, p95 latency, requirement source kind, question count, turns, flag count, time to draft, failures by stage** — depends P6.3 — acceptance: every beta report shows the numbers Plan V2 §J lists; no new model calls.

### P10 — Certification and beta (OWNER + Claude Code)

- **P10.1 · Second fixture golden pack: contrasting funder document and NGO bundle, Layers 1–5 light** — Claude authors from P0.5 — due Day 14.
- **P10.2 · Regression run through the harness: FCDO fixture, contrasting fixture, generic fallback; DOCX read; scorecard same-or-better** — OWNER — acceptance: all three pass their exit lines from P3–P7.
- **P10.3 · Blind unseen-funder run: a funder document not used while building the compiler; found by discovery if possible** — OWNER + Claude Code adjudication — acceptance: compiles without funder-specific branches; report credible after light editing. Failure here stops launch.
- **P10.4 · Launch readiness audit (Claude Code): kill switch, quota not consumed on failed jobs, no secrets or report bodies in logs, Impact gating, Stripe live paths untouched** — acceptance: no BLOCKER.
- **P10.5 · Beta onboarding runbook and first five NGO runs** — OWNER — acceptance: the beta pass criteria in Plan V2 §K, items 1–12, 14–17.

---

## 3. Verification loop (every package)

1. Cursor delivers on a branch with the package's tests passing (targets asserted, not bent).
2. Claude Code audit, read-only, one pass: verdict per acceptance line, pointers, no recommendations.
3. Pranab runs the live fixture (OWNER): bundle export, scorecard, DOCX read.
4. Merge only when the audit has no BLOCKER and the scorecard is same-or-better on Layers 1, 4, 5.
5. Decision log updated in the same PR when a locked decision was touched (it should not be).

---

## 4. Post-beta backlog (first candidates, in order)

1. Start next report for this grant — carry-forward, delta questions, prior-period actuals as history (schema ready from P2).
2. Funder feedback and management-action memory (`funder_feedback`, `management_action` roles are reserved, not routed).
3. Arithmetic suite: column sums, disaggregation totals, currency consistency, duplicate totals.
4. "What your funder asked for" as a first-class editable screen with per-requirement toggles.
5. Grant dashboard and history; portfolio view.
6. Organisation-profile auto-builder; Drive/Gmail connectors.
7. Physical removal of `funder_report_templates` after a stability window (D-094).

---

## 5. Change log

| Date | Change |
|---|---|
| 2026-09-06 | v1.0 — created from Plan V2 with approved beta cuts |
