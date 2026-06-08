# M&E / Donor Report Writer — Static Audit Findings (Handoff)

> **Export, not a new audit.** This document consolidates the findings already produced in the Track A static audit. No re-analysis, no re-derivation, no fixes. Severities, caveats, confidence, and "pending live capture" markers are carried over verbatim. Remediation is decided later, elsewhere.

---

## 1. Provenance

| Field | Value |
|---|---|
| **Repo root audited** | `/home/user/ngoinfo-grantpilot` |
| **Confirmed as** | FastAPI **backend** engine (✓ `app/main.py`, ✓ `app/reports/`, ✗ root `package.json`). Not the `"frontend"` Next.js repo; not the `.next/`-only stub. |
| **Branch** | `claude/sharp-euler-e4chi3` |
| **Commit SHA** | `a338ed021c25cbf33a5fc1f465c53996504c621c` (`a338ed0`) |
| **Audit date** | 2026-06-08 |
| **Mode** | Read-only. No edits/commits/PRs/migrations during analysis. No LLM pipeline executed; no production keys used. Only the deterministic parsers were run, against fixtures. (This handoff file is the one authorized write.) |

### Pipeline dimensions covered

1. Architecture & code robustness (data flow, per-doc isolation, systemic-failure arbiter, job-state machine/gates, synthesis resumability, quota idempotency, transaction atomicity).
2. The agents on the static rubric (build / input-contract / output-contract / robustness / stability / moat-exposure): **D1 classifier, D2–D4 extractors, E1 reconciler, E3 gap/compliance, F1 synthesis, F2 fact-safety critic, export/DOCX renderer.**
3. Cross-agent concerns (mixed substrate Messages-API vs Agent-SDK-subprocess; contract seams; worker as agent host; orphan reaper / two-clock backstop).
4. Extraction / parsing fidelity — **deterministic parsers executed** (§5).
5. Knowledge-bank structure.
6. Template-model robustness (whose-field, mandatory-vs-conditional).
7. Contracts & data integrity (export metering, `updated_at`, enum registry).
8. Known-debt reconciliation (5 test failures, enforcement-timing dead code, R2-then-DB delete, two-clock backstop, stale-doc reconciliation).
   Plus the proposed read-only **live-capture SQL** (delivered in the original audit; bridge summarized in §6).

### Explicitly NOT assessed (no finding fabricated to fill these)

- **Frontend** — out of scope by design (separate pass).
- **Live agent/model output quality and cost** — the LLM pipeline was not run (no prod keys). All "does it do its job *well*" questions are **PENDING LIVE CAPTURE**.
- **Vision agent** — not present as code in `app/reports/agents/` (vendor TBD per CLAUDE.md); **not assessed**.
- **Orchestrator as an LLM agent** — orchestration is implemented as **procedural dispatch** (`app/reports/orchestration/pipeline.py`), not a wired LLM "orchestrator agent." The procedural orchestration was assessed; no LLM-orchestrator agent exists to assess.
- **Docling's ML pipeline at runtime** — not installable in the audit container; the `.docx` table path was characterized from code + the prod degrade diagnosis and demonstrated via python-docx on the same fixtures (§5).

### Confidence provenance (how each finding was established)

- **High** = the relevant code/contract/fixture was read or run **directly in this session**.
- **Medium** = primarily from a read-only sub-agent's verbatim code characterization and/or a project diagnosis artefact; not personally re-read line-by-line.
- Where a finding rests on a **recorded prod artefact** (not a fresh run), that is stated.

### Numbering note (fidelity guard — discrepancy disclosed, not overwritten)

The original register contains **no standalone finding "F-15"**: the label `F-15` appeared once as a section-header typo introducing the Area-4 parser findings (which are **F-16/F-17/F-18**), and `F-7` cross-references "F-15" for the "report creation is free / unmetered" point — that point actually lives in **F-25**. Numbers are preserved as-issued for traceability; the cross-reference is corrected to **F-25** and disclosed here rather than silently renumbered.

### Fixtures used for the deterministic parser run

| Fixture | Nature |
|---|---|
| `tests/fixtures/indicator_extractor/fcdo_bridgelight_indicator_data.xlsx` | **Purpose-built / representative** test fixture (clean 11-col indicator grid; contains deliberately adversarial rows e.g. `hidden_continuation_row`, `cell_state_demo`). |
| `M_E_Module/Sample_docs/FCDO_Test_Set/BridgeLight Logframe and Finance AR1 Export.xlsx` | **Real-shape anonymised FCDO** export (human-formatted logframe+finance). |
| `M_E_Module/Sample_docs/FCDO_Test_Set/03_FCDO_BridgeLight_Logframe_Data_Table.docx` | **Real anonymised FCDO** Word logframe table. |
| `M_E_Module/Sample_docs/NLCF_Test_Set/03_NLCF_Southbank_Monitoring_and_Spend_Table.docx` | **Real anonymised NLCF** Word monitoring/spend table. |
| `M_E_Module/Sample_docs/FCDO_Test_Set/02_FCDO_BridgeLight_Award_Letter.docx` | **Real anonymised FCDO** award letter. |
| `exports/grantpilot_columns.csv` | A DB-schema CSV (exercises the `csv` reader; not M&E indicator data). |

Parsers executed: **openpyxl** (real `parse_xlsx_workbook`), **csv** (real `parse_csv_file`), **python-docx** (substitute for Docling, which was not installable). `parse_docx_tables`'s Docling pathway itself was **not executed** (characterized from code + the prod `fe6bf98b` diagnosis).

---

## 2. Findings register

Severity: 🟥 **MOAT** (threatens trustworthy-output moat) · 🟧 **BLOCKS** (blocks paying users) · ⬜ **COSMETIC/LOW**. **AMBER** = eventual fix touches moat, quota/entitlements, auth, or a contract/schema. Fix-cost is the rough class only (re-authoring / config / agent-rebuild / contract-or-migration / frontend) — **not** a remediation plan.

### Area 1 — Architecture & code robustness

**F-1 · Classifier confidence is computed but never gates routing.**
*Means:* if the cheap classifier mislabels an upload, the wrong extractor runs (or none) and nothing flags it — the only signals (`confidence`, `justification`, `truncated`) are discarded.
*Dimension/cause:* contract gap between D1 output and dispatch; classifier emits confidence, `pipeline.py:413-438` reads only `classification`.
*Severity:* 🟥 MOAT · *Fix cost:* config/agent-glue (threshold + low-confidence → `other`/review) · **AMBER (moat)** · *Confidence:* High (dispatch read directly; classifier internals from sub-agent) · *Live:* — .

**F-2 · `is_systemic_extraction_failure()` is the single shared arbiter (good) but triggers on a broad substring regex.**
*Means:* the one function deciding "abort the whole run vs degrade one document" can be tripped by a document whose error text merely contains words like `anthropic`, `endpoint`, `unauthorized`.
*Dimension/cause:* `systemic_extraction_failure.py:25-47` matches concatenated `code+message`, no score/threshold; confirmed sole arbiter, no parallel copies (called from `extract_isolation.py:64`, `extract_stage_state.py:32`).
*Severity:* 🟧 BLOCKS · *Fix cost:* re-authoring (anchor signatures to error origin) · Not AMBER · *Confidence:* Medium (sub-agent verbatim quote; not re-read) · *Live:* — .

**F-3 · Per-document isolation is real, but "degraded" is invisible at the top level.**
*Means:* one bad upload correctly does not kill the run, but the report advances to Gate 1 looking healthy; degraded doc IDs hide in the trace.
*Dimension/cause:* `extract_isolation.py` returns `degraded=True`, loop continues (`pipeline.py:470-491`); IDs land only in `agent_trace_json.stages.extract.degraded_documents`.
*Severity:* 🟧 BLOCKS · *Fix cost:* frontend + readiness surfacing · Not AMBER (observability) · *Confidence:* High (read directly) · *Live:* — .

**F-4 · Job-state gate convention is sound; resume triggers do NOT collide.**
*Means:* good news — Gate 1/2/3 each re-queue only their own stage; no cross-gate misdispatch.
*Dimension/cause:* `re_enqueue_gate1/2/3_job` filter `status=awaiting_human AND stage=gap|synthesise|export` respectively.
*Severity:* ⬜ (no defect) · *Fix cost:* — · Not AMBER · *Confidence:* High (grep + claim query read directly) · *Live:* — .

**F-5 · Synthesis resumability + merge-preservation is now correctly implemented — prior debt CLOSED.**
*Means:* re-running synthesis no longer discards good or human-edited sections.
*Dimension/cause:* `synthesise_and_persist` (`report_synthesis_service.py:344-388`) builds `to_generate` via `section_needs_synthesis` (skips `ACCEPTED`, `human_edited:true`, non-empty `GENERATED/AWAITING_REVIEW`); `merge_synthesis_sections` carries existing sections forward and preserves the `export` sibling key. **Supersedes `ME_SYNTHESIS_RESUME_SEAM_DIAGNOSIS_2026-06-04.md`, which is now stale.**
*Residual caveat:* preservation is in-memory carry-forward, **not** a byte-for-byte hash; **no single-flight guard** against two concurrent synthesis runs double-spending OpenAI on the same section.
*Severity:* ⬜ LOW (residual concurrency edge) · *Fix cost:* config (advisory lock) · Not AMBER · *Confidence:* High (both files read directly) · *Live:* — .

**F-6 · Quota idempotency is sound in practice; only a theoretical double-charge race remains.**
*Means:* a report is charged once, at first COMPLETE, keyed `report:create:{id}` — safe on re-runs.
*Dimension/cause:* `charge_report_on_first_complete` checks `has_report_create_charge` then idempotency-keyed `record_usage`; **no DB unique constraint** on the ledger key, so two simultaneous completions could both insert. Practically gated by the single-active-job invariant (one export per report).
*Severity:* ⬜ LOW · *Fix cost:* migration (unique index) · **AMBER (quota)** by tier-rule, low severity · *Confidence:* Medium (sub-agent characterization of `quota_service.py`; charge call-site read directly) · *Live:* — .

**F-7 · Transaction atomicity at the charge point is correct.**
*Means:* the quota charge and `status=COMPLETE` commit together; no half-charged state.
*Dimension/cause:* `export_and_persist:136-141` charges with `commit=False`, then one `db.commit()`. There is **no create-time decrement to be atomic** (create is free — see **F-25**); the removed `self.db.begin()` is moot.
*Severity:* ⬜ (no defect) · *Fix cost:* — · Not AMBER · *Confidence:* High (read directly) · *Live:* — .

### Area 2 — The agents (build / contract / robustness / stability / moat)

**F-8 · E1 reconciler can mint facts with no provenance linkage.**
*Means:* the reconciler is told "don't invent facts without a candidate_id," but nothing in code enforces that an emitted `fact.source_document_id` traces to a real candidate; LLM-authored `semantic_label` / `excerpt` / `fact_key` flow straight into the bank humans confirm at Gate 1.
*Dimension/cause:* `knowledge_bank_reconciler.py` validation enforces conflict shape (✅) but not key↔candidate binding.
*Severity:* 🟥 MOAT · *Fix cost:* re-authoring (post-validation candidate cross-check) · **AMBER (moat)** · *Confidence:* Medium (sub-agent; not re-read) · *Live:* moat impact PENDING LIVE CAPTURE.

**F-9 · Three human gates are genuinely server-enforced state-machine halts (good); skip ≠ invention (good).**
*Means:* gates are real DB halts, not UI theatre; a skipped gap answer marks the item resolved with `answer_text=None` and does not itself fabricate content.
*Dimension/cause:* `gate_preconditions.require_gate1/2/3_confirmed` block each stage; `gap_answer.is_gap_answer_resolved` treats `skipped` (reason ∈ {not_applicable, cannot_provide}) as resolved-without-value. F1/F2 read only `ANSWERED` entries, so the moat holds there.
*Residual:* any future consumer reading `answer_text` without checking `disposition` would see `None`.
*Severity:* ⬜ (no defect; noted as a contract-discipline dependency) · *Fix cost:* — · Not AMBER · *Confidence:* High (gate preconditions read in `pipeline.py`); skip logic Medium (sub-agent) · *Live:* — .

**F-10 · Silent input truncation: 120k chars in E1/E3, 80k in F2.**
*Means:* a large multi-document bank is cut mid-JSON with **no warning and no flag in the payload** — facts past the cut vanish from reconciliation/critique. The ~10-document report is exactly the large case.
*Dimension/cause:* hard slices at `knowledge_bank_reconciler.py:565`, `gap_compliance_agent.py`, `fact_safety_critic.py:172`.
*Severity:* 🟥 MOAT · *Fix cost:* re-authoring (chunk/segment + truncation flag) · **AMBER (moat)** · *Confidence:* Medium (sub-agent verbatim quotes) · *Live:* whether real banks exceed the limit is PENDING LIVE CAPTURE.

**F-11 · Mixed substrate yields asymmetric timeout semantics.**
*Means:* an extractor timeout *degrades one document and continues*; a classifier/reconciler/gap/critic timeout *fails the whole job*. Same wall-clock event, opposite blast radius.
*Dimension/cause:* D2/D3/D4 (Claude Agent SDK subprocess) catch `asyncio.TimeoutError` → degraded result; Category-B (Messages API) timeout maps to `StageFailure` at `dispatch.py:74-76`. Subprocess death (no `ResultMessage`) → `STOP_NO_RESULT` → degrade unless infra-regex matches.
*Severity:* 🟧 BLOCKS · *Fix cost:* re-authoring (unify failure policy) · Not AMBER · *Confidence:* Medium (sub-agent; `dispatch.py` not re-read) · *Live:* — .

### Area 3 — Cross-agent concerns

**F-12 · Output-contract seams are fixture-grounded, but "complete" is overloaded.**
*Means:* D2 `partial` and D3 single-field-present both persist `extraction_status=COMPLETE`, so a consumer trusting the top-level status over-trusts the data; LLM-"normalized" dates/amounts (D3) are never re-parsed.
*Dimension/cause:* outcome math in `proposal_extraction_service` / `grant_terms_extractor`.
*Severity:* 🟧 BLOCKS · *Fix cost:* contract tightening · **AMBER (contract)** · *Confidence:* Medium (sub-agent) · *Live:* — .

**F-13 · Orphan reaper is hosted inside the worker loop — total-fleet death = no reaping.**
*Means:* the reaper runs only at worker startup and idle cycles (`job_runner.py:130,137`). With ≥1 worker still polling, dead workers' jobs *are* reaped (the query has no alive-worker filter — `orphan_reaper.py:182-192` reaps all stale `RUNNING`). But if the **entire** worker fleet dies and never restarts, **nothing** runs the reaper and jobs hang. The two-clock backstop (stage-aware silence budget + `_MAX_RUNNING_SECONDS=7200`) is real but only fires when a live worker executes it; there is no external cron.
*Dimension/cause:* reaper invocation site + reaper query.
*Severity:* 🟧 BLOCKS · *Fix cost:* config/infra (external scheduled reaper) · Not AMBER · *Confidence:* High (`run_forever` read directly; reaper query from sub-agent) · *Live:* — .
*Note:* this refines the audit-scope premise — the reaper is NOT "alive-worker-only" by query; the residual gap is the **reaper's host** (a dead fleet runs no reaper).

**F-14 · Critique boundary parks at `(awaiting_human, critique)` with NO re-enqueue path — the live worker cannot advance past synthesis.**
*Means:* after synthesis, `_run_synthesise_stage` → `_park_critique_boundary` sets `status=awaiting_human, stage=critique` (`pipeline.py:214-215`). The worker's `claim_next_job` selects **only `QUEUED`** (`job_runner.py:34`); there is **no `re_enqueue_critique_job`** (grep-confirmed — only gate1/2/3 exist), and the reaper ignores `awaiting_human`. So in the **event-driven worker path** the parked critique job is never re-claimed — critique / Gate 3 / export are reachable **only by scripted/direct `run_orchestrated_walk` invocation** (how the recorded FCDO walks were produced).
*Reconciliation:* aligns with `ME_STAGE_F_STATUS_2026-06-04.md` (`donor_reports.status` "never leaves DRAFT"; Stage F→H acknowledged not production-live), but the re-enqueue gap **persists in current code**.
*Dimension/cause:* state-machine wiring (park as `awaiting_human` with no trigger to re-queue).
*Severity:* 🟧 BLOCKS (autonomous pipeline cannot complete) · *Fix cost:* re-authoring (set `QUEUED` at boundary, or add `re_enqueue_critique`) · **AMBER (state-machine contract)** · *Confidence:* High (park, claim, and grep all read directly) · *Live:* — .

### Area 4 — Extraction / parsing fidelity

(Full parser output in §5.)

**F-16 · Deterministic parsing is faithful but layout-flattening.**
*Means:* openpyxl/csv preserve exact raw values, `cell_state` (stated/blank/not_applicable), and row identity with zero inference (✅). But a real funder export is a **41%-blank, title-offset, 24-wide sparse grid** — all semantic structure (which column is "actual"? which rows form a merged output block?) is pushed onto the downstream LLM. The clean 11-col fixture is not what real funders submit.
*Dimension/cause:* `spreadsheet_input.py` flat cell-grid model.
*Severity:* 🟧 BLOCKS (drives F-17) · *Fix cost:* re-authoring (header detection / structural pre-pass) · Not AMBER · *Confidence:* High (parsers run directly) · *Live:* — .

**F-17 · The actuals carrier silently produces zero rows (recorded prod degrade).**
*Means:* on report `fe6bf98b`, the `.xlsx` AR1 export (the file that *holds the actuals*) **timed out** in D4 (90 s ceiling, 0 rows), and the `.docx` logframe was `UNPARSEABLE` — the KB ended with **33 facts, zero `*.actual` keys**. Synthesis then writes a report with targets but no achievements: the single most moat-damaging failure, degrading *silently* to Gate 1.
*Dimension/cause:* `D4_INDICATOR_EXTRACTOR_DEGRADE_DIAGNOSIS_2026-06-01.md` (prod-DB-grounded) + code; D4 `MAX_EXTRACTION_ATTEMPTS=1` (current), 90 s ceiling vs observed ~180 s SDK runs.
*Severity:* 🟥 MOAT · *Fix cost:* config (timeout/budget) + re-authoring (don't pass Gate 1 readiness when the actuals doc degraded) · **AMBER (moat)** · *Confidence:* High, but the failure is from a **recorded 2026-06-01 prod walk, not a fresh run** — fresh confirmation is PENDING LIVE CAPTURE · *Live:* PENDING (re-walk on current deploy).

**F-18 · The `.docx`→D4 `UNPARSEABLE` trap is partially CLOSED (reconciliation).**
*Means:* the 2026-06-01 diagnosis said any `.docx` routed to D4 always failed (intake accepted only `.xlsx`/`.csv`). Current `spreadsheet_input.py:178-179` **adds a `.docx` branch via `parse_docx_tables` (Docling)** — addressed *in code*.
*Caveat:* this puts Docling's heavy ML pipeline on the extract hot path, inheriting the same latency/timeout risk that already breaks the `.xlsx` path (F-17); merged-cell logframes (25 distinct cells in a 288-cell grid — §5) are a known structure-loss hazard for any flattener.
*Dimension/cause:* code moved ahead of the diagnosis doc.
*Severity:* 🟧 BLOCKS (latency) / verify live · *Fix cost:* config (timeout) + live verification · **AMBER (moat-adjacent)** · *Confidence:* High (`.docx` branch read directly) · *Live:* whether Docling completes within budget on real `.docx` is PENDING LIVE CAPTURE.

### Area 5 — Knowledge-bank structure

**F-19 · KB fact-key shape is load-bearing but unconstrained.**
*Means:* `facts` keys are arbitrary LLM-chosen strings; E3 satisfaction and F1/F2 citation all match on these keys, so a malformed/renamed key silently orphans a fact (the documented root of the citation-BLOCK churn).
*Dimension/cause:* no enforced key format/namespace in `knowledge_bank_reconciliation_v1`; corroborated by `KB_KEY_UNICODE_CORRUPTION_DIAGNOSIS` / `ME_KB_NAMESPACE_CAPTURE` (filenames seen; not read in full).
*Severity:* 🟥 MOAT · *Fix cost:* re-authoring (key normalization/registry) · **AMBER (moat)** · *Confidence:* Medium (sub-agent + doc titles) · *Live:* the **extracted-but-ignored split** (fact never extracted vs in-bank-but-asked) is PENDING LIVE CAPTURE.

### Area 6 — Template-model robustness

**F-20 · Contract drift: `knowledge_bank_json.gap_answers` shape.**
*Means:* `DB_FIELD_CONTRACT_DONOR_REPORTS.md §2.6` documents `gap_answers[key] = {answer_text, answered_at}`; the code uses `{disposition, skip_reason, answer_text, provenance{source, excerpt}}`. Consumers coded to the contract would misread skips/provenance.
*Dimension/cause:* contract vs implementation divergence.
*Severity:* 🟧 BLOCKS (integration) · *Fix cost:* contract re-sync · **AMBER (contract/schema)** · *Confidence:* High (contract read directly; code shape from sub-agent) · *Live:* the live bank will reveal the real persisted shape — PENDING LIVE CAPTURE.

**F-21 · Structural: the template schema encodes neither whose-field nor item-level conditionality.**
*Means:* confirmed against the real `TEMPLATE_INSTANCE_FCDO.json` — `required_indicators` include `output_scores`, `impact_weightings`, `risk_ratings`, `FCDO_management_actions` (the FCDO **reviewer's** assessment), yet E3 enrolls them as items the **NGO** must satisfy/answer; `..._where_relevant` indicators are treated as fully mandatory. No field marks ownership or applicability.
*Dimension/cause:* `FUNDER_TEMPLATE_SCHEMA` has no `field_owner`/`applicability`; `template_requirements.enumerate_template_requirements` enrolls every `required_indicators[]`/`required_tables[]`; `_section_visible` evaluates only `required:false` and `report_type=='final'`.
*Severity:* 🟥 MOAT (engine asks NGOs to invent the funder's verdict — credibility failure) + generalisation blocker beyond FCDO · *Fix cost:* schema change (`field_owner`, `applicability`) + E3 triage · **AMBER (contract/schema)** · *Confidence:* High (real FCDO instance + schema + `template_requirements` summary read) · *Live:* whether these items actually surface as NGO gaps on a real run — PENDING LIVE CAPTURE (static attribution says yes).

### Area 7 — Contracts & data integrity

**F-22 · Export metering diverges from contract §12.13.**
*Means:* contract = `POST /export` + `REPORT_EXPORT` ledger write + `429`. Actual = **`GET /api/reports/{id}/export`** (`export.py:21`) that just streams already-rendered bytes via `fetch_export_bytes` — **no ledger write, no quota check, no 429**. The render+charge happens earlier in the worker export *stage* and charges **`REPORT_CREATE`**, not `REPORT_EXPORT`. Net: the canonical POST endpoint does not exist and **`REPORT_EXPORT` / `report_exports` entitlement is never written or enforced anywhere**.
*Dimension/cause:* implementation folds export into the job pipeline; download route is unmetered.
*Severity:* 🟧 BLOCKS (entitlement unenforceable) + contract drift · *Fix cost:* re-authoring + contract reconciliation · **AMBER (quota + contract)** · *Confidence:* High (route + service read directly) · *Live:* — .

**F-23 · `updated_at` has no `onupdate`.**
*Means:* contract §2.10 says `donor_reports.updated_at` is "updated on any mutation," but the model sets only `server_default=now()` with **no `onupdate=func.now()`** (contrast core `User`). Gate confirmations, synthesis, export do not bump `updated_at`; `report_jobs` has no `updated_at` at all.
*Dimension/cause:* model/migration omission vs contract.
*Severity:* ⬜ LOW (staleness; cache/sort bugs) · *Fix cost:* migration + model · **AMBER (schema)**, low severity · *Confidence:* High (contract read directly); model column from sub-agent (Medium on the column line) · *Live:* — .

**F-24 · Enum adherence is clean.**
*Means:* classifier labels match §5.3 (`photo`/`deck` deliberately excluded from the text path — routed by MIME upstream, validator rejects them); stage/status enums match §5.6/§5.7; critic severity `BLOCK|WARN` matches §5.9.
*Severity:* ⬜ (no defect) · *Fix cost:* — · Not AMBER · *Confidence:* High (ENUM_REGISTRY read directly; classifier labels from sub-agent) · *Live:* — .

### Area 8 — Known-debt reconciliation

**F-25 · Create-time enforcement removed → GENERATING limbo is REAL in current code.**
*Means:* `require_impact_plan` checks **plan tier only** (`plan_gate.py:26`), not the 2/month count; `create_donor_report` does zero quota work. An over-quota IMPACT user does *all* gate work and only hits the wall at export, where `export_and_persist`'s `except ForbiddenError` **resets the report to `GENERATING`** (`report_export_service.py:158-164`) while the job is marked `FAILED` upstream — a confusing limbo; the `/reports/new` 429 warning the frontend expects **never fires** (create is unmetered per contract D6).
*Dimension/cause:* enforcement-timing moved to export; no create/enqueue pre-flight.
*Severity:* 🟧 BLOCKS · *Fix cost:* re-authoring (pre-flight remaining-quota check) + frontend · **AMBER (quota/entitlements)** · *Confidence:* High (`plan_gate` + ForbiddenError handler read directly) · *Live:* — .

**F-26 · R2-then-DB delete can orphan a row silently.**
*Means:* document delete does `store.delete_object(...)` **then** `db.delete(...)`+`commit` with no compensation (`donor_report_lifecycle_service.py:257-260`); a DB failure after the object delete leaves a row pointing at a vanished object. Should "fail loudly," currently silent.
*Dimension/cause:* ordering + missing 2-phase/compensation.
*Severity:* ⬜ LOW · *Fix cost:* re-authoring (DB-first or 2-phase) · Not AMBER · *Confidence:* Medium (sub-agent only) · *Live:* — .

**F-27 · The 5 pre-existing test failures, validated against code reality.**
*Means / per item:*
- **Auth account-linking ×2** (`test_auth_account_linking.py`): `get_or_create_user_for_*` now returns `tuple[User, bool]`; tests call `.id` on the tuple → `AttributeError`. **Real failure, stale test.**
- **Gate1 fixture** (`test_gate1_confirmation.py`): `MagicMock` db doesn't satisfy `get_owned_donor_report` + `re_enqueue_gate1_job` query chain. **Fixture brittleness.**
- **Worker/SQLite concurrency ×2** (`test_me_module_worker.py`, `test_orphan_reaper.py`): assert exclusive-claim semantics that depend on `FOR UPDATE SKIP LOCKED`, which **SQLite does not enforce** — the test substrate, not the prod (Postgres) path, is the problem.
*Dimension/cause:* test/substrate drift; none indicates a prod-path defect.
*Severity:* ⬜ LOW debt · *Fix cost:* test re-authoring · Not AMBER · *Confidence:* Medium (static characterization; tests **not executed**) · *Live:* — .

**F-28 · Several debt-register / contract-doc items are now STALE (code moved ahead).**
*Means:* synthesis resume seam **closed** (F-5); export stage **implemented** (no longer the `export_boundary_not_implemented` stub that `DB_FIELD_CONTRACT_REPORT_JOBS.md §2.4` still lists); `.docx`→D4 branch **added** (F-18); D4 retry count changed (2→1, per F-17 vs the diagnosis's 2). Docs/registers should be re-synced.
*Dimension/cause:* documentation drift behind code.
*Severity:* ⬜ COSMETIC · *Fix cost:* doc re-sync · Not AMBER · *Confidence:* High (the code moves were read directly) · *Live:* — .

### Severity rollup (descriptive, from the severity field above — not a priority directive)

- 🟥 **MOAT:** F-1, F-8, F-10, F-17, F-19, F-21 (and moat-adjacent F-18).
- 🟧 **BLOCKS:** F-2, F-3, F-11, F-12, F-13, F-14, F-16, F-20, F-22, F-25.
- ⬜ **LOW/COSMETIC:** F-5 (residual), F-6, F-23, F-26, F-27, F-28.
- ✅ **No defect (positive findings):** F-4, F-7, F-9, F-24.
- **AMBER-flagged:** F-1, F-6, F-8, F-10, F-12, F-14, F-17, F-18, F-19, F-20, F-21, F-22, F-23, F-25.

---

## 3. Agent verdict table

Build / Stability / Moat-exposure: ✅ sound · ⚠️ caveats · ❌ defect. Model = what *actually* runs (env-var resolved). **Live job-performance is PENDING for every agent — the LLM pipeline was not run.**

| Agent | API / model (as built) | Build | Stab. | Moat-exp. | Sharpest finding | Live job-perf |
|---|---|---|---|---|---|---|
| **D1 Classifier** | Anthropic **Messages API** direct · `ME_CLASSIFIER_MODEL`→`haiku` (`claude-haiku-4-5`) | ✅ | ⚠️ | ⚠️ | Single attempt, **no retry**; `confidence`/`truncated` emitted but never read — a low-confidence misroute silently mis-extracts (F-1). | **PENDING** |
| **D2 Proposal** | **Claude Agent SDK subprocess** · `ME_CLASSIFIER_MODEL`→`haiku` | ⚠️ | ⚠️ | ⚠️ | Prompt **hard-codes "expect 16 indicators / 2 objectives"** — invites count-padding; `partial` persists as `COMPLETE` (F-12). | **PENDING** |
| **D3 Grant-terms** | Claude Agent SDK subprocess · same env var | ✅ | ⚠️ | ⚠️ | `complete` fires if **≥1 field present**; LLM-"normalized" dates/amounts never re-parsed (F-12). | **PENDING** |
| **D4 Indicator** | Claude Agent SDK subprocess · same env var · **`MAX_EXTRACTION_ATTEMPTS=1`** | ⚠️ | ❌ | 🟥 | **Actuals carrier silently fails**: real `.xlsx` times out → 0 rows → no `.actual` facts; `.docx` historically `UNPARSEABLE` (F-17/F-18). | **PENDING** |
| **E1 Reconciler** | Anthropic Messages API · `ME_RECONCILER_MODEL`→`claude-sonnet-4-6` | ✅ | ⚠️ | ⚠️ | Conflict-surfacing correct & schema-enforced (✅), but LLM authors arbitrary `fact_key`s with **no candidate_id linkage check** (F-8). | **PENDING** |
| **E3 Gap/Compliance** | Anthropic Messages API (default **deterministic**; LLM behind `ME_GAP_COMPLIANCE_USE_LLM`) · `claude-sonnet-4-6` | ✅ | ✅ | ⚠️ | Empty template → `readiness=100, ready_for_gate2=True` (false green); treats **funder-side fields as NGO gaps** (F-21). | **PENDING** |
| **F1 Synthesis** | **OpenAI** `app.integrations.openai_client` · `OPENAI_MODEL_PRIMARY`=`gpt-5.4` (✅ correct path, not Claude) | ✅ | ⚠️ | 🟥 | **Now resumable** (prior debt closed, F-5); only anti-hallucination control is prompt + citation-key hygiene — **no semantic numeric check** vs KB (F-10/F-19). | **PENDING** |
| **F2 Critic** | Anthropic Messages API · `ME_FACT_SAFETY_CRITIC_MODEL`→**`claude-sonnet-4-6`** (not Opus) | ⚠️ | ⚠️ | 🟥 | Sees **only `cited_sources`**, not the full KB → an uncited hallucinated number has nothing to diff against; **no retry**; default model Sonnet, not spec's Opus-class. | **PENDING** |
| **Export / DOCX** | python-docx (no AI) | ⚠️ | ⚠️ | ⬜ | `FAILED` sections render **heading-only, no placeholder** — silently-incomplete report; base-template append never clears prior body (F-16-adjacent). | N/A (deterministic) |

---

## 4. Gap-wall attribution

| Question | Static attribution (code + real FCDO instance) | Status |
|---|---|---|
| **Template scope** | E3 `enumerate_template_requirements` enrolls **every** `required_indicators[]`/`required_tables[]` of every visible section as a requirement; section suppression supports only `required:false` and `report_type=='final'`. | Attributed |
| **Whose-field** | **No schema field marks ownership.** Real FCDO `required_indicators` include `output_scores`, `impact_weightings`, `risk_ratings`, `FCDO_management_actions` (reviewer's assessment) — E3 enrolls them as NGO-satisfiable items. | Attributed |
| **Mandatory vs conditional ("where relevant")** | Conditionality is baked into indicator **name strings** (`..._where_relevant`) with no structured flag; E3 has no indicator-level conditional logic → all treated as mandatory. | Attributed |
| **Extracted-but-ignored split** (fact never extracted vs in-bank-but-asked-anyway) | Requires the **live knowledge bank** for a real job — cannot be split statically. | **PENDING LIVE CAPTURE** |

**Plain verdict on the whose-field question:** **Yes — the engine asks the NGO to author funder-side fields.** The template model cannot express whose field an item is, so the gap agent cannot triage by ownership; ingesting a funder template verbatim causes the NGO to be asked for the funder's own assessment (FCDO output scores, management actions, impact weightings). This is **structural** (no prompt tuning fixes it while `report_sections_json` lacks an ownership/applicability marker). **AMBER (contract/schema).** Confidence: High (static); live confirmation that these surface as gaps on a real run is PENDING LIVE CAPTURE.

---

## 5. Parser execution results (deterministic; no LLM)

Real runs in the audit container. **What was captured well:** exact raw values, `cell_state` (stated/blank/not_applicable), and row identity — **zero inference**. **Where structure was lost/degraded:** real human-formatted layouts (title banners, offset/padding columns, merged cells, multi-row headers) flatten into sparse positional grids, deferring all semantics to the downstream LLM.

```
XLSX  tests/fixtures/indicator_extractor/fcdo_bridgelight_indicator_data.xlsx  (purpose-built)
  Indicators: 10 rows × 11 cols — header [row_id, indicator_ref, indicator_name, target, actual, unit,
              disagg_dimension, disagg_total, …]; state {stated:61, blank:48, not_applicable:1}
      r2: ['op1_1_girls_reenrolled','OP1.1','Girls re-enrolled…','1200','985','persons',<blank>,<blank>]
  Financials: budget_total — budget=1240000 actual=1184000 GBP
  serialized=7,384 chars · truncated=False · sha256=25aa867e… · row_ids preserved
              (incl. adversarial: 'hidden_continuation_row','cell_state_demo','op1_1_target_only')
  → CAPTURED WELL: clean, header-aligned, well under the 120k limit.

XLSX  M_E_Module/Sample_docs/FCDO_Test_Set/BridgeLight Logframe and Finance AR1 Export.xlsx  (REAL shape)
  Sheet1: 20 rows × 24 cols = 480 cells — **195 blank (41%)**; title "BridgeLight Logframe…" sits in col F, not A1
  serialized=29,275 chars
  → STRUCTURE DEGRADED: sparse, title-offset, no header alignment; semantics pushed onto the LLM (cf. F-16/F-17).

DOCX (python-docx; Docling ML pipeline NOT executed — not installable in container)
  03_FCDO_BridgeLight_Logframe_Data_Table.docx — table2 = 12 rows × 24 cols; HEAVY merges
      (288 grid cells but only 25 distinct <tc> elements)
      header [Output, Impact weighting, Risk rating, Indicator ID, Indicator text, Baseline, Y1 target, Endline…]
  03_NLCF_Southbank_Monitoring_and_Spend_Table.docx — table2 = 17 rows × 13 cols; merges (221 cells / 14 distinct)
  02_FCDO_BridgeLight_Award_Letter.docx — 1 small 2-col metadata table + 22 paragraphs
  → MERGED-CELL HAZARD: vertical merges repeat/blank values; any flattener (incl. Docling export_to_dataframe)
    risks structure loss. Docling's own output was not produced here (characterized from code + F-17 diagnosis).

CSV   exports/grantpilot_columns.csv
  145 rows × 5 cols — all 'stated'; header [table_name, column_name, data_type, is_nullable, ordinal_position]
  → CAPTURED WELL (note: this is a DB-schema dump, not M&E indicator data; exercises the csv reader only).
```

---

## 6. Pending-live-capture list (bridge to the live reconciliation)

These questions can be answered **only** by the live artifacts of a single real post-P8 report job. (The original audit also delivered the exact read-only `SELECT` statements to capture them — `funder_report_templates` id `55f891ac…`; `donor_reports.knowledge_bank_json` / `gap_analysis_json` / `content_json.export`; `report_jobs.agent_trace_json`; related `uploaded_documents`. Note `knowledge_bank_json`/`gap_analysis_json` live on **`donor_reports`**, not `report_jobs`.)

1. **Live job-performance / quality for every agent** (D1–F2): does each do its job *well* on real input? (Agent verdict table column — all PENDING.)
2. **Extracted-but-ignored gap split (F-19):** for each Gate-2 gap, is the underlying fact *absent from the bank* or *present but asked anyway*? Compare `knowledge_bank_json.facts` / `indicator_actuals_json` against `gap_analysis_json.gaps[]`.
3. **Whose-field, live (F-21):** do FCDO funder-side items (`output_scores`, `FCDO_management_actions`, `impact_weightings`, `risk_ratings`) actually appear as gaps directed at the NGO on a real run?
4. **Actuals presence (F-17):** does `indicator_actuals_json` / `knowledge_bank_json.facts` contain `*.actual` values on a current deploy, or does D4 still degrade the actuals carrier? (Recorded prod walk `fe6bf98b` showed zero — needs fresh confirmation.)
5. **`gap_answers` real shape (F-20):** does the live bank use `{disposition, skip_reason, provenance}` (code) or the contract's `{answer_text, answered_at}`?
6. **Truncation reality (F-10):** does a real ~10-document bank exceed the 120k/80k limits and silently lose facts?
7. **Docling `.docx` viability (F-18):** does `parse_docx_tables` complete within the extract budget on a real funder `.docx`, or inherit the F-17 timeout?
8. **Agent cost/latency (cost-ceiling check):** `report_jobs.agent_trace_json` per-stage tokens/cost vs the locked per-report ceiling.
9. **Citation-BLOCK residual (recorded 18 on `b91ae3e0`):** re-derive the A/B/C decomposition on a current-deploy walk (no fresh decomposition exists post-`d19b9de`).

---

*End of handoff. Static audit only — no LLM pipeline was run; no remediation is proposed here. Findings, severities, confidence, and pending-live-capture markers are carried over from the Track A audit verbatim.*
