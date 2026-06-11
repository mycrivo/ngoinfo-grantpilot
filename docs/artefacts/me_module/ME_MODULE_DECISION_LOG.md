# M&E Module — Decision Log

Append-only record of deliberate choices. Do not silently pivot — add a row and reference it in PRs/prompts.

---

## Locked decisions (seeded Stage A — 2026-05-24)

| ID | Date | Decision | Rationale | Stage |
|----|------|----------|-----------|-------|
| D-001 | 2026-05 | **Modular monolith** — M&E in `app/reports/`, same repo as core backend | Solo-founder ops simplicity; hooks enforce isolation | A |
| D-002 | 2026-05 | **One-way dependency** — M&E imports core; core never imports M&E | Killable module; proposal product protected | A |
| D-003 | 2026-05 | **Single mounting seam** — conditional `include_router` in `app/main.py` only | One line mounts/unmounts entire API | A |
| D-004 | 2026-05 | **SUPERSEDED by D-048 — Impact Pro** — $99/mo, new plan enum **`IMPACT_PRO`** | Do not overload IMPACT; dual-capability tier (proposals + reports) | J |
| D-005 | 2026-05 | **SUPERSEDED by D-048 — 2 M&E reports/month** on Impact Pro | Cost ceiling ~$49.50/report revenue | J |
| D-006 | 2026-05 | **JSONB `_json` suffix canonical** — `report_sections_json`, `format_rules_json`, `terminology_map_json`, `knowledge_bank_json`, etc. | Avoid column-name drift; consistent with `content_json`, `agent_trace_json` | B |
| D-007 | 2026-05 | **UI semantic colours** — purple (agent), blue (gate), navy (action) | Authoritative over stale teal/plum/orange in master memory §14 | I |
| D-008 | 2026-05 | **Docling** for document extraction (Layer 1) | MIT; PDF/DOCX/XLSX/PPTX/images | C |
| D-009 | 2026-05 | **Claude Agent SDK** for agent runtime (Layer 2) | Hooks = gates; subagents | D–G |
| D-010 | 2026-05 | **docxtpl** for M&E export — separate `report_export_service.py` | Funder templates in Word; do not modify core `export_service.py` (python-docx) | H |
| D-011 | 2026-05 | **In-app job queue + worker** — not Railway sandboxes at launch | `run_pipeline(report_id)` swappable later | C |
| D-012 | 2026-05 | **Railway Buckets** for uploads — net-new Stage C | S3-compatible object storage | C |
| D-013 | 2026-05 | **gpt-5.4** for section synthesis at build; re-evaluate before launch | Reuse humaniser library | F |
| D-014 | 2026-05 | **Level 2 agentic** — three server-enforced human gates; not Level 3 | Compliance product; human owns truth | D–G |
| D-015 | 2026-05 | **Fact-safety critic mandatory** | No unverified specifics in export | F |
| D-016 | 2026-05 | **Frontend separate repo** — API contract self-sufficient | Backend-only repo; Next.js elsewhere | I |
| D-017 | 2026-05 | **Reference docs canonical path** — `docs/artefacts/me_module/` | Planning copies; `M_E_Module/` legacy reference | A |
| D-018 | 2026-05 | **n8n** for template ingestion post-launch only — not orchestrator | Plumbing; Stage L | L |
| D-019 | 2026-05 | **Cheap multimodal API** for vision agent (vendor TBD Stage D) | Not local VLM at launch | D |
| D-020 | 2026-05 | **10 launch templates** — NLCF + FCDO stress-test schema in Stage B | 8 funder-specific + 2 generic | B, H |
| D-021 | 2026-05-24 | **Stage B structure lock** — field contracts, FUNDER_TEMPLATE_SCHEMA, REPORT_INPUTS_FIELD_MAPPING, API §12, ENUM_REGISTRY §5 | Spec before code; NLCF/FCDO instances deferred to B-validation (T2) | B |
| D-022 | 2026-05-24 | **NLCF reporting frequency** — `reporting_frequency: "annual"`; end-of-grant section via `conditional_display` (`report_type == 'final'`), not composite enum value | Invalid/non-registry frequency `annual_or_end_of_grant`; keeps ENUM_REGISTRY §5 clean | B |
| D-023 | 2026-05-24 | **FUNDER_TEMPLATE_SCHEMA v1.1.0** — first-class `conditional_display` + `evidence_rules` on sections; `format_rules_json.extensions` documented | T2 normalization; critic/gap agent per-section rules without schema migration | B |
| D-024 | 2026-05-24 | **Stage B-validation complete** — NLCF + FCDO canonical instances pass schema stress test | [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json), [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json); FUNDER_TEMPLATE_SCHEMA v1.1.0 | B |
| D-025 | 2026-05-24 | **M&E upload storage env vars** — `ME_DOCUMENTS_S3_*` prefix (`ENDPOINT`, `ACCESS_KEY`, `SECRET`, `BUCKET`); generic `S3_*` reserved for future core exports | Module-scoped kill switch; untrusted uploads vs trusted exports boundary | C |
| D-026 | 2026-05-24 | **Stage C foundations complete** — `app/reports/` skeleton, migration 0014, worker stub, storage interface, docling adapter; three kill switches rehearsed | Empty mountable module; no agents/AI | C |
| D-027 | 2026-05-24 | **CLAUDE.md agent-layer top-up** — inlined `30-agents.mdc` governance (Level 2, gates, injection fence, bounded-agent contract, model routing, isolated testing) | Claude Code reads CLAUDE.md only, not Cursor rules | D |
| D-028 | 2026-05-24 | **Document classifier agent (Stage D step 1)** — bounded `app/reports/agents/classifier.py` on Claude Agent SDK; cheap model; ENUM_REGISTRY §5.3 output | First isolated agent; no orchestrator | D |
| D-029 | 2026-05-25 | **Dependency baseline ratified for Claude Agent SDK** — `fastapi>=0.115`, `uvicorn>=0.30`, `httpx>=0.27` (resolves `anyio>=4` conflict with prior `fastapi==0.104` pin); core 22/22 smoke green locally on current `requirements.txt` | SDK install gate passed; revenue engine unchanged at API contract level | D |
| D-030 | 2026-05-25 | **Classifier `max_turns` 1→2** — `app/reports/agents/classifier.py` now `max_turns=2` | SDK structured-output path (`output_format` JSON schema) needs a second turn to emit the result; live run failed at 1 with "Reached maximum number of turns (1)". Still hard-bounded (2 turns, `TIMEOUT_SECONDS` unchanged, tools disallowed). **Monitor:** extractors use richer structured output — may need ≥2 turns each. | D |
| D-032 | 2026-05-25 | **Proposal extractor `max_turns` 2→3** — `app/reports/agents/proposal_extractor.py` now `max_turns=3` | D2 diagnostic on FCDO cached fixture: objective count bistable (2 vs 6 on identical input); targetless equity/VfM indicator (`equity_support_reach_qualitative`) captured 0/10; Batch A run 4 hard-failed at max_turns=2 with zero structured output (~20% failure rate). Prompt tightened for flat 2-tier objectives and targetless indicators; model class unchanged (haiku). | D |
| D-033 | 2026-05-25 | **Proposal extractor default timeout 60→90s** — `TIMEOUT_SECONDS` default and matching `API_TIMEOUT_MS` in `build_agent_options()` | Post–prompt-tighten: instrumented turn-2 long pole; 0/5 at 60s; 2/5 at 75s with successes at 72–74s API / ~12k output tokens and failures &gt;80s wall. No structured-output retry subtype observed. 90s covers observed success path + slow-tail bimodal failures without model-class change. Classifier remains 60s default. | D |
| D-034 | 2026-05-25 | **Grant-terms extractor `max_turns` 2→3** — `app/reports/agents/grant_terms_extractor.py` | D3 FCDO acceptance: structured JSON schema + multi_value reporting_period; live run hit `Reached maximum number of turns (2)` during batch gate. Award letter smaller than proposal; 2 was justified floor but insufficient for stable structured output. Timeout unchanged at 90s (D-033). | D |
| D-035 | 2026-05-25 | **Grant-terms timeout variance: bounded retry + `extraction_outcome: degraded`** — `grant_terms_extractor.py`, `grant_terms_extraction_v1.py`, `grant_terms_extraction_service.py` | Closes D-033 carry-forward for D3: keep 90s per-attempt ceiling; on timeout retry once (independent re-draw); second timeout returns typed terminal `degraded` in `extracted_json` (`DEGRADED_EXTRACTION_TIMEOUT`) without raise/hang. DB `extraction_status` stays `FAILED`; orchestrator/UI surfacing deferred to G/I. Gate reshaped: 1 correctness + 3 stability runs; recorded fixture at `tests/fixtures/grant_terms_extractor/recorded/`. FCDO gate wall spread: min 55932ms, max 66114ms, median 64087ms (4 runs). | D |
| D-036 | 2026-05-25 | **Indicator-data extractor (D4): direct spreadsheet parse + bounded agent** — `spreadsheet_input.py` (`openpyxl`/csv), `indicator_data_extractor.py`, `indicator_data_extraction_service.py`, `indicator_data_extraction_v1.py` | Docling markdown rejected for `indicator_data`: loses `0`/blank/`N/A` distinction and cell locators. Direct read preserves `cell_state` and row identity; agent input is JSON grid in `&lt;document_data&gt;`. Inherits D-035 timeout pattern (`max_turns=3`, 90s×2→`degraded`). Gate: 1 correctness + 3 sequential stability runs; recorded fixture at `tests/fixtures/indicator_extractor/recorded/`. FCDO gate wall spread: min 44654ms, max 179853ms, median 62803ms (4 runs). Does not write `donor_reports.indicator_actuals_json`. | D |
| D-037 | 2026-05-25 | **D4 gate instrumentation: per-run outcome + `attempt_count` on trace** — `indicator_data_extractor.py`, `indicator_data_gate.py`, `IndicatorDataAgentTrace.num_turns` | Successful and degraded runs now set `agent_trace.attempt_count` (1 or 2); `gate_wall_times_ms.json` stores a `runs[]` record per gate slot (label, outcome, attempt_count, num_turns, wall_ms, degraded_code). Retry events are recorded, not inferred. **Drift diagnosis:** on fingerprint drift failure, gate writes compared payloads to `recorded/_drift_debug/` (not the recorded fixture); standard for subsequent agent gates (E1 onward). | D |
| D-038 | 2026-05-26 | **D4 CLOSED — instrumentation &amp; eval-harness standing decisions** — `indicator_data_extractor.py`, `indicator_data_gate.py`, `recorded/fcdo_bridgelight_recorded_extraction.json`, `gate_wall_times_ms.json` | **D4 signed off:** live gate 4/4 `complete`, 8 rows each, zero fingerprint drift, no degraded path. Clean-path wall spread 56–87s (median ~60s); retry-worst ~180s from earlier session — both Stage-G capacity inputs (extract stage gated by slowest concurrent extractor; Gate-1 UX must tolerate ~90s typical / ~180s retry-worst). **D-035 retry proven:** earlier session `stability_1` at `attempt_count=2`, `complete` — retry recovered, recorded not inferred. Residual accepted: fingerprint divergence in that retried session never field-diffed (payloads not preserved then); subsequent clean 4/4 pass with zero retries shows normal path stable; divergence correlated with retry path, not baseline instability — closed-by-circumstance; save-on-drift (D-037) auto-captures if recurs. **D-037 standard confirmed for E1+:** per-run outcome + `attempt_count` + `num_turns` + `wall_ms`; save-on-drift on failure — gates that discard evidence on drift are non-compliant. **Eval harness:** bespoke gate (fingerprint + grader + save-on-drift) sufficient through quality gate; not extended further after D-stage. Post–quality-gate: evaluate migrating eval/regression to Claude skill-creator eval + benchmark mode (Mar 2026) only after doc verification covers structured-extraction determinism (run-N-times, content-fidelity, planted-error survival, failing-payload capture) — not on blog assumption. Extraction logic and domain fact-safety rules remain hand-built; eval plumbing only is migration candidate. **Vision (D5) deferred:** AI photo interpretation → Phase 2 post-launch on demand. | D |
| D-039 | 2026-05-26 | **Low-content guard + typed `unreadable` outcome (pre-E1)** — `docling_adapter.py`, `docling_content_guard.py`, `*_from_path` on classifier/proposal/grant_terms extractors | Closes silent-fabrication hole on Docling path: surface `ConversionResult.status`; assess after Docling with failure/skipped status OR &lt;200-char floor; return `extraction_outcome: unreadable` + `UNREADABLE_DOCUMENT_LOW_CONTENT` (no LLM on junk). DB `extraction_status` stays `FAILED`; distinction in `extracted_json` (mirrors degraded). Classifier uses `intake_outcome: unreadable` (no `other` mis-route). D4 openpyxl path untouched. **OCR/engine config out of MVP** ([`MVP_SCOPE_LOCK.md`](../MVP_SCOPE_LOCK.md)); guard makes system honest about unreadable input, does not read scans better; full scanned-document support deferred post-launch on demand. Proof: `scripts/d039_unreadable_guard_proof.py` + `tests/fixtures/docling_intake/image_only_no_text_layer.pdf`. | D |
| D-040 | 2026-05-24 | **E1 knowledge-bank reconciler — surface only, never resolve** — `knowledge_bank_reconciliation_v1.py`, `reconciliation/input_builder.py`, `knowledge_bank_reconciler.py`, `knowledge_bank_reconciliation_service.py`, `tests/reconciliation_grading.py`, `scripts/knowledge_bank_reconciler_gate.py` | Cardinal inversion: E1 may disambiguate meaning into distinct `fact_key`s and annotate conflicts; MUST NOT set `resolved_value`, prefer sources, or invent facts without candidates. Deterministic input layer flattens recorded D2/D3/D4 `extracted_json` only (no extractor re-run); D-039 unreadable → `unreadable_sources[]`, excluded from facts. Strong model (`ME_RECONCILER_MODEL`, default `opus`), `max_turns=5`, D-035 timeout → `reconciliation_outcome: degraded`. **Timeout:** `ME_RECONCILER_TIMEOUT_SECONDS=180` per attempt (×2 → degraded) is deliberate for the Opus-class reconciler comparing multi-document candidate bundles with `max_turns=5`, not a drift from the D-stage 90s extractor ceiling — D-038’s ~180s retry-worst informed capacity planning; E1 uses the upper bound as the per-attempt default because reconciliation is heavier than single-doc extraction. Post-LLM `validate_e1_knowledge_bank` fail-closed. Persistence: `donor_reports.knowledge_bank_json` only; no `gate1_confirmed_at`, no Gate 1 API (E2), no orchestrator (G1). FCDO gate: four planted cases (same-field VALUE_MISMATCH, target-vs-actual non-conflict, cross-source target temptation, unreadable flag); graders locate by normalized value + `source_document_id`, not agent `fact_key`. OCR still out of scope. | E |
| D-041 | 2026-05-24 | **E1 gate stability reframed — invariant grading, not byte identity** — `scripts/knowledge_bank_reconciler_gate.py` | E1 certifies the product contract (surface recall, no resolution, provenance via `grade_knowledge_bank`), not run-to-run byte identity. Correctness + all stability runs must each pass invariant grading; `stability_fingerprint` remains computed and written to `recorded/_drift_debug/` on every gate run (pass or fail) for inspection only — fingerprint inequality is no longer a gate failure. Benign shape variation (e.g. 3-way vs 2-way conflict surfacing for the same VALUE_MISMATCH) must not fail the gate when invariants hold. Grading failures persist the failing run’s knowledge bank and assertion list to drift-debug. Reconciler, model, answer key, and graders unchanged. | E |
| D-042 | 2026-05-24 | **E1 corroboration rule — multi-source identical value** — `knowledge_bank_reconciler.py` SYSTEM_PROMPT, `fcdo_bridgelight_reconciliation_answer_key.json`, `reconciliation_grading.py` | Same normalized value + semantic quantity in multiple documents is corroboration (never a self-conflict, never a single-source pick). Standalone: one `agreed` fact with all sources cited (`source_document_id` + `interpretation_note`). Inside VALUE_MISMATCH: one conflict value entry per corroborating source on that side (FCDO case1: 1,240,000 from award letter **and** indicator sheet vs 1,184,000 from amended schedule). Answer key derived from fixture inputs, not model output. | E |
| D-043 | 2026-05-24 | **E1 conflict-validity rule — no spurious VALUE_MISMATCH** — `knowledge_bank_reconciler.py` SYSTEM_PROMPT, `reconciliation_grading.py` `assert_no_spurious_conflicts` | A conflict requires ≥2 genuinely different non-empty values for the same quantity; lone values, blank/absence parties, and same-value representation variants are facts not conflicts. Global mechanical grader: distinct normalized value count (not all entries distinct — corroboration repeats allowed) plus no blank parties. Complements D-042; case 1–4 graders unchanged. | E |
| D-044 | 2026-06-04 | **Stage H export built ahead of plan order** — `report_export_service`, `docx_renderer` (`render_mode: from_scratch` python-docx), `GET /api/reports/{id}/export` | Stage F quality gate must produce a real `.docx` at the end; stubbed export would make the gate meaningless. Long-run docxtpl path unchanged — activates when a base FCDO `.docx` template is supplied. Quality-gate criteria unchanged. | F, H |
| D-045 | 2026-06-04 | **Terminology corruption fixed at render layer** — `docx_renderer.py` | `canonical_to_funder` applied to **labels only** (not blind find-replace across body prose); template schema-key prose-strip removed; whole-marker citation removal. F1 synthesis and citation hygiene unchanged — stored `content_json` prose was always clean; defect was export-only. | H |
| D-046 | 2026-06-04 | **F1 reliability bundle (pre-resume)** — per-section KB trim, synthesis-only timeout retry (1), concurrency 5→2 | Each section receives only facts/gaps it needs plus shared programme/grant/reporting context. One retry on transport timeout for `feature=report_synthesis` only. `ME_SYNTHESIS_MAX_CONCURRENCY` default **2**. **90s timeout unchanged.** | F |
| D-047 | 2026-06-04 | **F1 synthesis resumable/idempotent** — `report_synthesis_service.py`, `content_json_v1.py` | Generate only incomplete sections (missing / `FAILED` / empty); merge-preserve `GENERATED` / `ACCEPTED` / `human_edited` sections and sibling keys (`export`, gate stamps); `DEGRADED` on partial failure, `DRAFT` on full completion. **Rationale:** atomic all-section regeneration fails as ≈p⁸ under transient OpenAI errors; resume converges. Per-section incremental DB commit (medium path) **explicitly not taken** — SQLAlchemy Session thread-safety cost not justified. | F |
| D-048 | 2026-06-06 | **Two-plan model — Impact Pro retired** | M&E folds into **Impact $79** (2 reports/mo bundled); plan enum stays **FREE \| GROWTH \| IMPACT** only. Free/Growth → upgrade-to-Impact gate on M&E entry. Supersedes D-004, D-005. | J |
| D-049 | 2026-06-06 | **Impact Fit Scans 20→10** | Aligns pre-award quota with canonical two-plan target (Growth and Impact both 10 Fit Scans/mo). | J |
| D-050 | 2026-06-06 | **Plan 1 DOCX scope = structural hardening only** | Existing python-docx renderers (`export_service`, `docx_renderer`); **D-010 docxtpl** + **D-020** 10 funder templates remain long-run target, deferred post-Plan-2 quality gate. | H |
| D-051 | 2026-06-07 | **REPORT_CREATE refund on pipeline failure** | Charge at report create (`report:create:{id}`); on any terminal `report_jobs.status = failed`, insert idempotent `REPORT_CREATE_REFUND` (`report:refund:{id}`). Net used = creates − refunds. List API exposes `latest_job_status` for failed UX. | J |
| D-052 | 2026-06-07 | **REPORT_CREATE charge at first COMPLETE (D6 / P8)** | Charge `REPORT_CREATE` exactly once when `donor_reports.status` first becomes `COMPLETE` in `export_and_persist` (export stage). Idempotency key `report:create:{donor_report_id}`. Create-time charge and `mark_job_failed` refund path **removed**. Never-completed reports are never charged. **Supersedes D-051.** | J |

---

## Open items (not yet decided)

| ID | Topic | Notes |
|----|-------|-------|
| O-001 | Vision API vendor | Pick at Stage D; **D5 AI photo interpretation deferred Phase 2 (D-038)** |
| ~~O-002~~ | ~~`ME_MODULE_ENABLED` default~~ | **Resolved Stage C (D-025):** default `false` in Settings + ENV_VARS_REFERENCE §J |
| ~~O-003~~ | ~~Report quota event types~~ | **Resolved Stage B:** REPORT_CREATE, REPORT_EXPORT — ENUM_REGISTRY §3.3, §5.10 |
| O-004 | Stripe `STRIPE_PRICE_ID_IMPACT` | Stage J — Impact $79 includes bundled M&E (D-048) |
| ~~O-005~~ | ~~Stage B-validation~~ | **Resolved 2026-05-24 (D-024):** NLCF + FCDO instances validated; see FUNDER_TEMPLATE_SCHEMA §6 |

---

## Revisions

*(Append rows when a locked decision changes.)*

| ID | Date | Supersedes | New decision | Why |
|----|------|------------|--------------|-----|
| D-048 | 2026-06-06 | D-004, D-005 | Two-plan model; M&E on Impact $79; enum FREE\|GROWTH\|IMPACT | A-00 contract reset |
| D-052 | 2026-06-07 | D-051 | REPORT_CREATE at first COMPLETE; remove create charge + failure refund | P8 / locked D6 |

---

## Stage B-validation (COMPLETE — 2026-05-24)

**Full Stage B exit gate satisfied.** Structure lock (D-021) + instance stress test (D-024).

| Requirement | Status | Artefact |
|-------------|--------|----------|
| NLCF template instance | **Complete** | [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json) |
| FCDO template instance | **Complete** | [`TEMPLATE_INSTANCE_FCDO.json`](TEMPLATE_INSTANCE_FCDO.json) |
| Schema holds simple + complex funders | **Complete** | FUNDER_TEMPLATE_SCHEMA v1.1.0 §6 |
| Zero-gap proof (structure) | **Complete** | All T2 non-canonical shapes normalized (D-022, D-023) |

**Next stage:** Stage D — document extraction pipeline (wire docling adapter + upload flow).

---

## Stage C exit gate (COMPLETE — 2026-05-24)

| Requirement | Status |
|-------------|--------|
| Four M&E tables + migrations 0014 + 0015 | **Complete** |
| Models match contracts (parity hook) | **Complete** |
| `ME_MODULE_ENABLED` mount/unmount | **Complete** |
| Worker separate process (Procfile) | **Complete** |
| Reversible downgrade (kill switch 3) | **Complete** — `0014_me_module_tables.downgrade()` |
| Isolation veto + migration parity hooks | **Complete** |

---
DECISION (2026-06-04) — Funder-template schema: closed-enum policy, funder-addition process, deferred items.
Context: ME_DB_FUTUREPROOF_AUDIT_2026-06-04.md.

1. Catalog model confirmed. Funder-specific layout is data in JSONB on funder_report_templates. Adding a funder whose cadence fits {end_of_grant, annual, quarterly, interim, final}, whose uploads fit {proposal, grant_letter, mou, indicator_data, photo, deck, other}, and whose form fits report_sections_json / format_rules_json / terminology_map_json is a DATA-ONLY insert: zero schema, zero code.

2. Closed enums stay closed. The CHECK enums on reporting_frequency, uploaded_documents.classification, report_jobs.stage, report_jobs.status, and donor_reports.status are product-internal canonical vocabularies, not funder surface labels. A new cadence, document class, pipeline stage, or lifecycle status changes pipeline behaviour and therefore requires a deliberate, contracted migration carrying the REAL value. Speculative enum widening (e.g. adding milestone / six_monthly / ad_hoc before a profiled funder needs them) is prohibited — it is the imagined-data failure mode.

3. Precondition for any M&E migration: the scratch-Postgres migration harness (pgcrypto / gen_random_uuid) must run clean first. Executable guard before invisible setting.

4. Deferred (intent locked, build when exercised, not now):
   (a) report_type ('annual' | 'final' | ...) to be persisted as a canonical field on donor_reports (default 'annual'), set at report-create, with the conditional-section evaluator generalised beyond report_type == 'final'. Build with report-creation wiring, after the pgcrypto harness fix. Until then, NLCF final-only sections rely on the code default.
   (b) Per-report template snapshot: donor_reports to pin template version or template-JSON hash at create time, so later template edits do not change the semantics of existing reports. Build with report-creation wiring. Low urgency pre-launch (no live customer reports exist yet).

5. echo_blocks / header_fields / section guidance / table max_rows remain unexercised by NLCF/FCDO. Validate against a real EU/ECHO funder profile before claiming support. No action now.
---
DECISION (2026-06-08) — P3 orphan reaper (D3 Route A, D4).
Context: M_E_Module/P3_ORPHAN_REAPER_PLAN.md; owner approved build.

1. Liveness from `started_at` + `agent_trace_json.stages.*.completed_at` only — no migration, no heartbeat column.
2. Stage-aware silence thresholds with default margin `ME_ORPHAN_REAPER_MARGIN_SECONDS=900`; absolute backstop `ME_ORPHAN_REAPER_MAX_SECONDS=7200` for empty-trace pathological runs.
3. Recovery via existing `mark_job_failed` with `failure.event = orphan_reaped` — same refund/UX as other failures; no requeue.
4. Worker triggers: startup sweep + idle-cycle sweep in `job_runner.run_forever()` when `poll_once()` returns 0.
5. Out of scope: worker stability/OOM/Railway restart policy; dead worker with no process restart stays orphaned until infra restarts worker.
---
DECISION (2026-06-11) — P3-2 worker recovery (supersedes reaper D3 Route A + D4).
Context: Phase 3 Plan v2 · [`P3_2_DECISION_LOG.md`](audits/P3_2_DECISION_LOG.md); diagnosis [`P3_2_EXTRACT_HANG_DIAGNOSIS.md`](audits/P3_2_EXTRACT_HANG_DIAGNOSIS.md).

1. Migration 0017: `last_heartbeat_at`, `lease_owner`, `lease_expires_at`, `requeue_count` on `report_jobs`.
2. Heartbeat on claim, stage entry, per-document classify/extract, checkpoints; reaper prefers heartbeat over stage `completed_at`.
3. Requeue bound 1 (0→1) then terminal `orphan_reaped`; degraded jobs never requeued; stage-boundary restart only.
4. F-11 unified timeout via `job_timeout.py` (stage-aware budget + shared failure path).
5. Supersedes prior D3 Route A (no migration) and D4 (fail-only); does not change stage-D4 indicator extractor degrade.
---
DECISION (2026-06-08) — P2 extract isolation (engine survives bad input).
Context: M_E_Module/P2_ENGINE_SURVIVES_BAD_INPUT_PLAN.md; owner approved classification + build.

1. Per-document degrade (Table A): proposal/grant/indicator extract paths and `load_document_text` / `load_spreadsheet_json` intake errors inside extract isolation — one bad document does not fail the job; completed siblings persist.
2. Hard fail (Table B): preflight `*ExtractionServiceError`, infra-signature agent stops, and explicit systemic stop codes route via `ExtractHardFailure` → `StageFailure` unchanged.
3. Table C fail-closed (non-optional): first ambiguous `STOP_AGENT_ERROR` (no infra signature) degrades; second consecutive ambiguous stop with no intervening extract success hard-fails; any prior extract success resets the consecutive counter. Single classifier: `is_systemic_extraction_failure()` in `systemic_extraction_failure.py` — shared by Table B and Table C.
4. Option B (no schema change): `extraction_outcome: degraded` on `extracted_json` maps to existing `unreadable_sources[]` in `input_builder.py` only; degraded payloads never enter reconciler fact candidates (zero-hallucination fence unchanged).
5. Out of scope: synthesis/gap/critic prompts; classify-stage intake (extract-stage only for P2 intake wrap).
---
DECISION (2026-06-08) — P5 indicator_data tabular coverage (.docx tables).
Context: M_E_Module/CURSOR_BUILD_INSTRUCTIONS.md §P5.

1. `parse_docx_tables()` in `spreadsheet_input.py` — Docling `export_to_dataframe` → shared cell grid; values read, never inferred.
2. `parse_spreadsheet_from_path` routes `.docx` alongside `.xlsx`/`.csv` for indicator_data intake.
3. D1 door messages updated to name Word (.docx) with tables for monitoring data; `.docx` already accepted at upload via text lane.
4. Empty/no-table `.docx` raises `ValueError` → P2 degrade path (no fabrication).
5. Out of scope: binary `.doc`, OCR, images-of-tables.
---
DECISION (2026-06-08) — P4 status legibility (user sees the truth).
Context: M_E_Module/P4 plan; owner approved build including sentinel filter policy A.

1. Stage-specific failure copy on reading screen keyed off `job.stage` (reading / drafting / export) — never raw `job.error`.
2. Gate 1 `unreadable_sources[]` panel for P2 degraded documents; confirm not blocked.
3. Terminal `DEGRADED` list chip → "Completed with limitations"; done page leads with degraded notice.
4. Upload enqueue routes to `/reports/{id}/reading`; quota exhausted on enqueue uses same screen as create.
5. Empty sentinel shell list filter (display only): hide when `__default__` + `__lifecycle_default__` AND `latest_job_status === null` AND `document_count === 0` — never uses `donor_reports.status`.
6. §12.10 additive field: `document_count` on list items.
7. Export client uses GET to match live backend. Gate 3 display polish only — §12.11 PATCH out of scope.
8. `UNSUPPORTED_DOCUMENT_FORMAT` passes through server lane-specific message on upload (`me-error-messages.ts`).
---
DECISION (2026-06-08) — E3 deterministic-first gap identification (D-049).
Context: Report `230290ce-d28a-4138-ae08-901cf1ad69c0` failed at gap stage when Anthropic returned prose instead of JSON after degraded E1 reconcile.

1. **Gap identification is deterministic by default** — `unsatisfied_requirements()` + logframe merge in `deterministic_gaps.py`; `run_gap_compliance` skips LLM unless `ME_GAP_COMPLIANCE_USE_LLM=1` or tests inject `query_fn`.
2. **LLM parse failure is non-fatal** when LLM path is enabled — after retries, fall back to deterministic output (same contract shape).
3. **JSON extraction fallback** — shared `app/reports/parsing/json_from_text.py` for gap + reconciler prose/preamble responses.
4. **Gate 1 confirm** stamps `confirmed: true` on all facts; unresolved conflicts block confirm.
5. **E1 reconciler** default `MAX_OUTPUT_TOKENS` raised to 32768 via `ME_RECONCILER_MAX_OUTPUT_TOKENS`.
---
DECISION (2026-06-11) — P3 gate3 quota timestamp fence (H5 retroactive ratification).
Context: `bd72572` changed `app/services/quota_service.py` `get_or_create_user_plan` to set explicit `created_at`/`updated_at` on insert.

1. **Category-d only** — timestamp population on new plan insert; no change to charge timing, entitlement amounts, or billing-period semantics.
2. **Prod probe clean** — no null or inconsistent `user_plans` timestamps at hold-clearance probe.
3. **Standing rule (forward)** — any `app/services/**` change ships with an explicit fence note at commit time stating behavioural category (a–d per P3 audit pack H5).
---
DECISION (2026-06-11) — NLCF regression pin (Phase B owner ratification).
Context: walk `e7fa9bee`; owner line `NLCF RATIFIED: regression pin`.

1. **Pin-class, not adjudicated truth** — `G-nlcf-gap-regression-pin` asserts exact 18-ref set from walk on default docset; status `matches_observed_e7fa9bee`.
2. **Section count 6** — annual visible NGO sections unchanged vs template.
3. **Typing parity queued** — `budget_vs_actual` table vs indicator typing not enforced in pin gate until follow-up.
4. **Fixture** — `tests/fixtures/gap/keys/nlcf_regression_pin_e7fa9bee.json`; offline replay `--nlcf-pin`.
---
