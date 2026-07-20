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
| D-040 | 2026-05-24 | **E1 knowledge-bank reconciler — surface only, never resolve** — `knowledge_bank_reconciliation_v1.py`, `reconciliation/input_builder.py`, `knowledge_bank_reconciler.py`, `knowledge_bank_reconciliation_service.py`, `tests/reconciliation_grading.py`, `scripts/knowledge_bank_reconciler_gate.py` | Cardinal inversion: E1 may disambiguate meaning into distinct `fact_key`s and annotate conflicts; MUST NOT set `resolved_value`, prefer sources, or invent facts without candidates. Deterministic input layer flattens recorded D2/D3/D4 `extracted_json` only (no extractor re-run); D-039 unreadable → `unreadable_sources[]`, excluded from facts. Strong model (`ME_RECONCILER_MODEL`, default `opus`), `max_turns=5`, D-035 timeout → `reconciliation_outcome: degraded`. **Timeout:** `ME_RECONCILER_TIMEOUT_SECONDS=180` per attempt (×2 → degraded) is deliberate for the Opus-class reconciler comparing multi-document candidate bundles with `max_turns=5`, not a drift from the D-stage 90s extractor ceiling — D-038's ~180s retry-worst informed capacity planning; E1 uses the upper bound as the per-attempt default because reconciliation is heavier than single-doc extraction. Post-LLM `validate_e1_knowledge_bank` fail-closed. Persistence: `donor_reports.knowledge_bank_json` only; no `gate1_confirmed_at`, no Gate 1 API (E2), no orchestrator (G1). FCDO gate: four planted cases (same-field VALUE_MISMATCH, target-vs-actual non-conflict, cross-source target temptation, unreadable flag); graders locate by normalized value + `source_document_id`, not agent `fact_key`. OCR still out of scope. | E |
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
| D-053 | 2026-07-18 | **Track 3 — narrative Gate 2 elevation on proposal-failure proceed** | Template-data flag `elevate_on_proposal_failure`; NLCF map exactly 2 community indicators; FCDO map empty by omission; trigger = checkpoint `proceed_with_gap` only. See narrative DECISION below. | G |
| D-054 | 2026-07-05 | **Gate 2 gap question copy — readable English** (retro-log of `7570bec`) | Deterministic section-first phrasing via `gap_question_copy.py`; replaces underscore-swap f-strings. See narrative DECISION below. | E |
| D-055 | 2026-07-18 | **Track 3 prod NLCF scoped reconcile** — `community_involvement` only | Live row predated Package A/B template fields; owner Option 2 scoped. See narrative DECISION below. | G |
| D-056 | 2026-07-19 | **Track 3 closure — proposal timeout-degrade fault flag** | Env-only `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE` (Option B); retained default-off. See narrative DECISION below. | G |
| D-057 | 2026-07-19 | **Track 3 Phase 2 witnessed walk — first prod checkpoint + validation** | Induced flag-window walk on worker; both branches exported. See narrative DECISION below. | G |
| D-058 | 2026-07-19 | **D-A — Write-time conflict integrity invariant** | Every conflict persisted to the knowledge bank must be resolvable through the standard resolution path. See narrative DECISION below. | G |
| D-059 | 2026-07-19 | **D-B — Ambiguous/null candidates never directly acceptable** | Ambiguous candidate visible but routes to explicit entry; backend rejects null `resolved_value`. See narrative. | G |
| D-060 | 2026-07-19 | **D-C — Sibling facts are provenance, not claims** | After resolution, exactly one canonical truth flows downstream; siblings retained as provenance only. | G |
| D-061 | 2026-07-19 | **D-D — One-off owner-authorized orphan repair** | Scan + repair orphan conflict shape; creates resolvability only, never a resolved value. | G |
| D-062 | 2026-07-19 | **D-E — Gate 1 save-path error experience designed** | Known domain codes map to NGO-safe messages; generic banner last resort; no internal identifiers. | G |

---

## Open items (not yet decided)

| ID | Topic | Notes |
|----|-------|-------|
| O-001 | Vision API vendor | Pick at Stage D; **D5 AI photo interpretation deferred Phase 2 (D-038)** |
| ~~O-002~~ | ~~`ME_MODULE_ENABLED` default~~ | **Resolved Stage C (D-025):** default `false` in Settings + ENV_VARS_REFERENCE §J |
| ~~O-003~~ | ~~Report quota event types~~ | **Resolved Stage B:** REPORT_CREATE, REPORT_EXPORT — ENUM_REGISTRY §3.3, §5.10 |
| O-004 | Stripe `STRIPE_PRICE_ID_IMPACT` | Stage J — Impact $79 includes bundled M&E (D-048) |
| ~~O-005~~ | ~~Stage B-validation~~ | **Resolved 2026-05-24 (D-024):** NLCF + FCDO instances validated; see FUNDER_TEMPLATE_SCHEMA §6 |
| O-006 | **Track 3.1** — shared-floor objectives/activities thinning when proposal fails | Deferred debt (D-053). Not part of Track 3 elevation build. Revisit separately. |
| O-007 | Track 3 residual — never-uploaded proposal (no checkpoint → no elevation) | Conscious narrowing in D-053; revisit on evidence of real no-proposal runs. |
| O-008 | **NLCF live template drift (non-community sections)** | Live prod row `2d5d75b7…` missing `fact_namespaces` + `source_section_labels` on sections other than `community_involvement` vs committed `TEMPLATE_INSTANCE_NLCF.json`. Evidence: [`TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json`](audits/TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json). Scoped reconcile (D-055) fixed community only; remaining drift awaits owner adjudication. |
| O-009 | **Track 3.2** — intake-level “no readable proposal present” | Deferred. Covers unreadable→`classification=other` path (prod report `18976580-62af-4836-bdc3-9b35ee3f3f06`, [`TRACK3_STOP_B_EVIDENCE_PACK_2026-07-18.md`](audits/TRACK3_STOP_B_EVIDENCE_PACK_2026-07-18.md)). Reuse existing checkpoint + elevation plumbing. Sit next to O-007; **not built in D-056**. |
| O-010 | **E1 grader alignment for observed-but-unnormalisable conflict parties** | D-059 refines D-043 for Gate 1 UX/PATCH. Grader `assert_no_spurious_conflicts` in `tests/reconciliation_grading.py` still rejects blank parties. Align grader/prompt/answer-key in a future package — **not changed in D-058–D-062**. |

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
DECISION (2026-06-11) — Phase B exec: purge in-flight test reports + one-op template replace.
Context: Owner exec 2026-06-11; supersedes M1–M4 re-stage order and staged 8-delta intent.

1. **B2a authorized** — delete all `donor_reports` + `report_jobs` (+ FK children) referencing template `55f891ac` at execution time; guard stops on any owner email outside audit-mint `@grantpilot-test.org` or `pranabksingh@gmail.com`; pre-delete JSON dump; usage_ledger untouched; R2 objects deleted via storage lifecycle path with failures listed.
2. **B2b authorized** — full JSONB replace from committed `tests/fixtures/templates/fcdo_55f891ac_post_deletion_v1.2.0.json` (6 sections, kill-list absent, 30/30 v1.2.0 tags); rollback from snapshot `aa6c9926…` ready before UPDATE; in-transaction read-back verification.
3. **Rationale** — all in-flight rows are owner test data; funder-owned template rows leave the DB ahead of multi-funder scaling.
4. **Artefacts** — `scripts/audit/b2_phase_exec.py`, `scripts/audit/build_fcdo_post_deletion_template.py`.

**Amendment (2026-06-11, guard resolved):** `probe-upload2@test.org` and `probe-upload3@test.org` are owner-recognized test accounts; their reports join B2a purge scope (full **41/41** on template `55f891ac`). **B2a-2** hard-scoped deletion of the two user rows (+ dependents incl. ledger) after purge; usage_ledger touched only in B2a-2 for those accounts.
---
DECISION (2026-06-08) — P3-7 Plate the dish: synthesis prose + export fidelity.
Context: Owner-approved correction package from [`P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md`](audits/P3_FCDO_EMPTY_RENDER_DIAGNOSIS.md); scope fence — no template rows, gap engine, typed matcher, reconciler, extraction; no prod writes; no live walks.

**S1 — Decisive experiment (branch i):** Git diff `b20b27a..HEAD` on synthesis prompt/schema/binder: P3-4 tone/proposal blocks only (`ab66dd9`, `bd72572`); `synthesis_claim_binding.py` unchanged in window. P2 clean fixture has non-empty section `text`. Recorded raw response artefact: `tests/fixtures/synthesis/p3_b3_fcdo_summary_empty_top_level_text_raw.json` (walk `7cdcc3a8`, `summary_and_overview` — empty top-level `generated_content.text`, populated `claims[].text`). **Branch (i):** prose present in claims, dropped at bind — fix: assemble bound claim text into section prose when top-level text empty; fail closed on `EMPTY_SECTION_PROSE` when assembly still empty; prompt requires non-empty `generated_content.text`.

**S2 — Honesty gates:** (1) Synthesis fails `EMPTY_SECTION_PROSE` / never `GENERATED` with whitespace-only body when citable inputs exist. (2) Critique: empty-content skip → `UNVERIFIED` + `critique_incomplete` when `empty_content_skipped > 0`. (3) Accept API rejects `FAILED` and empty-prose sections. (4) Gate 3 `confirm_gate3` requires non-empty prose + structured bind status on accepted sections.

**S3 — Table rendering:** `app/reports/export/kb_table_renderer.py` — deterministic logframe `output_score_table` (12 OP rows, 10 actuals + honest `not provided` for `op2_3`/`op4_2` gaps) and NLCF `budget_vs_actual` from KB facts; wired in `docx_renderer` + export service (no LLM).

**S4 — Docx machine-check:** `app/reports/eval/docx_export_assertions.py`; `G-section-prose` in offline replay gates.

**S5 — Carry-overs:** `phase2_owner_validation --fcdo-complete` grades gap-set at Gate-2 boundary via `p3_b3_gap_stage_7cdcc3a8.json`; readiness message `Complete — N items skipped`; `stages.synthesise.openai_input_tokens` / `openai_output_tokens` in pipeline trace.

**STOP:** Validation ladder complete locally; owner-triggered live re-walk (one FCDO + one NLCF) remains out of scope for agent.
---
DECISION (2026-06-11) — P3-8 Forbidden-ref reclassification + empty-section policy.
Context: P3-7 re-walk GO; owner conditions C1–C4; build authorized.

**Forbidden moat (complete FCDO, post-change — full set):**
- `review_summary_sheet` — adjudicated funder (summary RSS table; funder-owned)
- `outcome_assessment` — adjudicated narrative (`table_requirements.outcome_assessment.requirement_type = narrative`)
- `outcome_indicators` — regression pin (P3-B1 R4 walk-3347590c namespace; not owner-adjudicated reclass)

**Reclassified out:** `progress_against_expected_results` — ordinary NGO data gap (`DATA_BACKED_HINTS`: `ar1_actual`, `ar1_milestone_target`); P3-7 Gate-2 on default BridgeLight docset; supersedes P3-B1 R4 regression pin for this ref only.

**Complete gap pin (3 refs):** `progress_against_expected_results`, `logframe_row:op2_3`, `logframe_row:op4_2` — P3-7 rewalk `1beb588b` Gate-2 boundary on `DEFAULT_DOCSETS[fcdo]` (BridgeLight proposal + award + logframe/finance xlsx); not account-specific uploads. Committed distill `3347590c` on same docset class yields 2 refs when `progress_against` satisfied via global ar1 hint match — eval pin follows live walk, documented in fixture sidecar.

**Empty-section policy:** `structured_bind_status = insufficient_data` + engine insufficiency prose when zero NGO requirements satisfied for section (preflight before OpenAI); `FAILED` unchanged when any input satisfied but output empty/broken (P3-7 gates intact). Partial sections (some inputs, some gaps) route to `bound` / `honest_empty` only.

**STOP:** CI green; owner-triggered confirming re-walk (FCDO + NLCF) out of scope for agent.
---
DECISION (2026-06-13) — Package C.1: sparse-section routing (model refusal → honest `insufficient_data` preflight).
Context: P3-9 Cluster C / A-MODEL; P3-8 NLCF walk `588c3e7d` froze at Gate-3 (`community_involvement` + `changes_and_next_steps` FAILED on model `INSUFFICIENT_INPUT` while preflight over-counted skipped gaps and narrative-indicator auto-satisfy). Build authorized after plan review.

**Shipped (`e475c7b`):**
1. **`purpose` param on `evaluate_requirement_satisfaction`** — default `"gate"` (Gate-2 / gap agent / gap-check unchanged); only `section_has_synthesizable_inputs` passes `purpose="synthesis"`.
2. **Synthesis preflight tightened** — skipped gap answers do not count as substrate; narrative indicators no longer auto-satisfy without citable facts; section-scoped citable-facts fallback via `build_knowledge_bank_inputs_for_section`.
3. **Offline proof** — `tests/fixtures/kb/p3_8_nlcf_post_gate2_skip_kb.json` + routing table tests in `tests/test_section_insufficiency.py`; wired to Smoke Test P0 M&E allowlist.
4. **A-JSON untouched** — `_extract_json_payload` / parse-failure path unchanged; JSON-parse FAILED stays FAILED.
5. **CI** — Smoke Test run `27477844306` and P3 Offline Replay run `27477844292` green on `main` after push.

**Owner confirming re-walk (`d8e7518b`, 2026-06-13):** Fresh mint account; default 3-file NLCF docset; Gate-2 **13/13 skipped**. **Verdict: `completed`** — accept-all, Gate-3 confirm, export (40 614-byte DOCX). **Gate-3 freeze cleared** vs P3-8 NLCF on same protocol. **Routing table not reproduced on live KB:** all six sections `structured_bind_status = bound` (no `insufficient_data` path fired). Reconciler emitted two `objectives.*` facts absent on P3-8 freeze KB (`588c3e7d`); shared-prefix scoped-facts fallback routed sparse sections to synthesis — documented for follow-up (C.2 candidate), not a rollback of C.1 predicate on the P3-8 distilled fixture.

**Evidence:** `docs/artefacts/me_module/audits/snapshots/c1_nlcf_rewalk_d8e7518b.json`, `c1_nlcf_rewalk_export_d8e7518b.docx` (commit `ca1e57d`).

**STOP:** No engine change in evidence commit; owner read gate complete pending C.2 scoping if programme-level `objectives.*` must not alone unlock narrative sections.
---
DECISION (2026-06-14) — Package 2: FCDO indicator data-table scope (output-vs-outcome split not invented).
Context: Generic template-driven table renderer (`kb_table_renderer.py`) drives off `required_tables` + real KB fact namespaces; deleted the hardcoded `FCDO_LOGFRAME_OPS` 12-row OP skeleton (latent integrity defect — it could render OP rows no fact backed). Diagnosis confirmed the renderer cannot derive an output-vs-outcome indicator classification from the facts: real recorded shapes are `indicators.<id>.<facet>` (e.g. `indicators.op1_1_girls_reenrolled.actual`, `indicators.ocm1_attendance_80pct.target`) with no declared indicator-type tag.

**Decision (honest-not-invented):**
1. **Single indicator data-table populates from ALL real indicator facts.** A `data_source` table is treated as a per-entity data table only when its declared columns map to ≥2 distinct fillable value families (`actual`/`budget`/`target`). FCDO `output_score_table` (actual + milestone) qualifies and receives every `indicators.*` entity as a row; each cell fills fail-closed on exact facet-family membership, honest `not provided` otherwise.
2. **`outcome_assessment` and `vfm_measures` render honest-empty** (declared columns + one `not provided` row): their columns are narrative / single-family, so no indicator actual is dumped into them. This deliberately does NOT split outcome indicators (`ocm*`) out of the output table into the outcome-assessment table.
3. **Why not split:** the output/outcome distinction is **not declared in the facts** (no indicator-type field in template or reconciler output). Synthesising a split from id-prefix conventions (`op*` vs `ocm*`) would be inventing a classification the data does not carry — a moat breach by the same standard as inventing a row. Every rendered cell traces to a real fact; row-to-table placement across indicator sub-types is the only thing left undeclared, and we leave it honest rather than guess.

**Deliberate data-layer limitation — revisit only if FCDO reviewers require the split.** Implementing it would need an indicator-type tag carried in the funder template (per-indicator `indicator_type`) and/or surfaced by the reconciler/extractor onto each `indicators.*` fact — **out of scope here** (no fact reshaping in this package). Recorded so the first live FCDO report is not a surprise: all indicators appear in the single indicator data-table; the outcome-assessment table is honestly empty.

**Evidence:** proven against real `c1_nlcf_rewalk_d8e7518b.json` (NLCF financials) and recorded `tests/fixtures/reconciler/recorded/fcdo_bridgelight_recorded_knowledge_bank.json` (FCDO indicators) in `tests/test_funder_table_rendering.py` (Smoke P0 M&E allowlist), NOT the favourable `fcdo_complete_3347590c` fixture.

**STOP:** owner-triggered double re-walk (clean human caveats + populated funder tables, one walk) is the next gate.
---
DECISION (2026-06-14) — Package A: section-scoped visibility + remit-scoped, disclosure-complete caveats (template-driven, source-routed).
Context: KB-starvation cluster Class A (losses 2, 3a, project_story budget self-contradiction). Built after owner plan approval with three adjustments (disclosure-completeness, resolver fail-safe, Docling gating first). AMBER / moat-adjacent.

**Gating step PASSED (first):** Docling export of the real NLCF monitoring `.docx` reliably locates the section column — Sheet `Table2`, header `A1 = "Section for NLCF update"`, verbatim labels in column A per row (Project story / Difference made / Community involvement / Learning / Spend summary). The deterministic `cell_ref -> row -> column-A` join works on the real walk KB (`pkg2_nlcf_rewalk_703f0dcf.json`): row9/row10 actuals → Learning, volunteer count (D5) → Difference made, financials (C/D 11-17) → Spend summary, proposal targets (`cell_ref=None`) → declared-needs. Real section column captured to `tests/fixtures/kb/nlcf_monitoring_section_column.json`.

**Shipped:**
1. **Source-section carrier (routing infra only, not content-capture):** `ExtractedIndicatorRow.section_assignment` (deterministic post-pass reads column A by header label via `locate_section_assignment_column`; LLM never authors section) → `FactCandidate.source_section` (flatten) → `KnowledgeBankFact.source_section` (reconciler `cell_ref` join; fail-safe `None`). Indicator-scoped (FinancialLine unchanged; financials route via the `financials` namespace).
2. **Namespace-root matcher:** `grant_*`/`reporting_*`/`objectives.*` now match the shared floor (root match, not dotted `startswith`) — fixes the "two facts only" NLCF starvation.
3. **`subset_facts_for_section` routing:** source PIN (fact visible ONLY to its assigned section) → declared-needs fallback (`fact_namespaces` + `required_tables` data_source + archetype FALLBACK for legacy sections only) → shared floor. Resolver fail-safe: unmatched source label → declared-needs (never dropped/misrouted) and logged (observable). Legacy indicator-token matching gated to sections that declare NO `fact_namespaces` key (removes the accidental `indicators`/`work→workers` bleed).
4. **Template declarations (`TEMPLATE_INSTANCE_NLCF.json`):** per-section `source_section_labels` + `fact_namespaces`, incl. the four LOCKED namespaces routed forward-compatibly — `partnerships`/`engagement` → community_involvement, `indicators.*.note` → changes_and_next_steps, `indicators.*.disaggregation*` → difference_made. FCDO untouched (archetype fallback preserved).
5. **Remit-scoped, disclosure-complete caveats (`remit_disclosure.py`):** owner-only emission (a section discloses only its OWN required items) + present-elsewhere suppression using the SAME presence notion the data-table renderer uses (KB facts under the table's data-source namespace) — so a populated budget table is never contradicted by "not available", and project_story (empty financial remit) never disclaims the budget. Deterministic disclosure injected into the owning section's `assumptions[]` so a genuinely-absent owned item is disclosed IN THE OUTPUT regardless of the model. Synthesis prompt clause 6a added (disclaim only in-remit).
6. **Critic parity:** `build_qualitative_kb_view` now receives the template section + full report_sections so the critic's per-section fact view mirrors synthesis's (no false "unsupported" flags on source-routed facts).

**C.1 reconciliation (the one behavioural change to a must-not-regress test):** `section_has_synthesizable_inputs` now requires ≥1 SECTION-SPECIFIC (non-shared-root) fact — the shared programme floor is context, not synthesizable content. On the pre-carrier `p3_8_nlcf_post_gate2_skip_kb.json` fixture (no `source_section`), `learning` is now correctly insufficient: its old "sufficient" came from the `"work"→"workers"` financial-token-leak bug this package removes; its notes (`indicators.9/10`, positional) are not routable without the source signal. `test_p3_8_nlcf_sparse_section_routing_table` updated to move `learning` to `expect_insufficient` (C.1 MECHANISM intact; the real source-routed proof — learning sees row9/row10 — is in `test_section_visibility`). `test_p3_8_..._preflight_skips_openai` (community + changes) unchanged and green.

**CI:** `tests/test_section_visibility.py` (16 tests, proven against the REAL walk KB + real captured section column + synthetic locked-namespace facts) added to Smoke P0 M&E allowlist alongside `test_report_inputs_builder.py`. Full local suite: 13 pre-existing failures unchanged with vs without this package (auth/migration/worker/env-docling/orchestrator-gate1 — all fail identically on the clean-of-this-package tree); this package adds 16 passing tests and 0 new failures. C.1/Pkg-1/Pkg-2 routing/redaction/table tests green.

**STOP:** owner audit before push; owner-triggered NLCF re-walk (narrative sections narrating routed facts with true caveats) is the real gate — requires re-seeding the live NLCF template with the new `source_section_labels`/`fact_namespaces`.
---
DECISION (2026-06-14) — Packages C + D: demographics promotion (C) + table-cell provenance leak (D). Two independent, separately-buildable workstreams on merged Package A; not blended.

**Package C (GREEN, promotion-only) — demographic disaggregation becomes routed facts.** Root: `_flatten_indicator_data` (input_builder.py) looped only `target`/`actual`, dropping the populated `row.disaggregation` array (loss 4). Fix: per row, promote each `disaggregation[].breakdown[]` band to a `FactCandidate` at `indicators.<row_id>.disaggregation.<dim_slug>.<band_slug>` — value from the band's `normalized`/`raw`, provenance via the existing `_locator_provenance` (carries `cell_ref`, e.g. `Table2!F3`), clean `semantic_hint` (no cell ref), `source_section` carried from the row exactly as `target`/`actual`. **Bands only — `stated_total` NOT promoted** (it duplicates the row actual). Skip `absent` bands. No schema/extractor/LLM change. Routing reuses A unchanged: the namespace matches A's forward-wired `indicators.*.disaggregation*` on `difference_made`, and the real rows 3-7 carry `source_section="Difference made"` so they source-pin there.

**Package D (AMBER, deterministic) — clean budget identity cells + widened tripwire.** Roots: PL-a — reconciler passed `semantic_label` verbatim and render `_FACET_SUFFIX_RE` is `$`-anchored, so a leaked `"Sessional youth workers — budget (Table2!C12)"` reached the cell; PL-b — `_LEAK_PATTERNS` had no A1-notation / em-dash-facet pattern. Fix (guarantee is code, not prompt): (1) **load-bearing** render strip — `_strip_facet_prefix` drops a trailing `(<Sheet>!<Cell>)` BEFORE the facet-suffix strip (requires the sheet `!`, so `(Q1)`/`(2024)` untouched); (2) **deterministic defense-in-depth** — `_llm_to_structured` sanitizes a trailing A1-ref off `semantic_label` at fact assembly (cell ref stays in `provenance.cell_ref`); (3) **tripwire WIDENED only** — added `spreadsheet_cell_ref` (`<name>!<ColRow>`) and `entity_facet_provenance` (`— <facet> (<A1ref>)`) patterns; proven both directions (fires on the real leak, silent on cleaned render + legitimate em-dash/number prose). No model instruction carries load.

**Stale-data re-point (named):** D's PL-a proof is anchored to the post-A walk `pkg2_nlcf_rewalk_703f0dcf.json` (where `semantic_label`s carry the real leak), NOT `c1_nlcf_rewalk_d8e7518b.json` (whose labels are clean — `Table2!` only in `provenance.cell_ref` there, a pre-leak snapshot). Existing `d8e7518b` proofs are unchanged; a real-data leak proof is added alongside. C is proven against the real `703f0dcf` monitoring `structured` joined with the REAL captured section column (`nlcf_monitoring_section_column.json`), since `703f0dcf` predates A's `section_assignment` capture.

**CI:** `tests/test_disaggregation_promotion.py` (C, new, 4 tests) added to the Smoke P0 M&E allowlist; `tests/test_export_identifier_leak.py` + `tests/test_funder_table_rendering.py` (D, extended) already on it. Full local `tests/` suite: 13 pre-existing failures unchanged with vs without C/D (auth/migration/worker/env-docling/orchestrator-gate1 — confirmed identical on the stashed pre-C/D tree); C/D add passing tests and 0 new failures. A/C.1/number-binding/refusal-meaning/Pkg-1/Pkg-2 green.

**STOP:** owner audit before push. Real gate (deferred, owner-triggered): consolidated re-walk after B — demographics narrated, no provenance in any rendered cell.
---
DECISION (2026-06-14) — Package B: capture the document content the extractor has no field for (named partners + consultation narrative + monitoring evidence/notes). Extraction-coverage class (losses 1, 3 change-note half, 5, 6). Built on merged A/C/D; internally split B1 (proposal-side) / B2 (monitoring-side). AMBER.

**Real-source fixtures (faithful derivation, no hand-shaping).** Minted from the local NLCF docset via the project's own adapters and committed: `tests/fixtures/proposal_extractor/nlcf_southbank_proposal.md` (Docling markdown of `01_NLCF_Southbank_Application_Proposal.docx`) and `tests/fixtures/indicator_extractor/nlcf_southbank_monitoring_grid.json` (the real grid from `03_..._Monitoring_and_Spend_Table.docx` via `parse_docx_tables`; `source_path` normalised for portability). The real partner list differs from the diagnosis approximation (proposal Project story names *local schools, the GP social prescribing team, two tenants groups, the food pantry* — no mosque; the mosque appears only in the monitoring row-8 note) — proof of deriving from source, not from the diagnosis.

**B1 (proposal partners + consultation).** Schema: `ExtractedPartner` + `ExtractedEngagement` added to `proposal_extraction_v1` (+ `partners`/`consultation` lists; counted in summary). Extractor: `_LLMPartner`/`_LLMEngagement` + bounded prompt rules (name as written, relationship only if stated, count only if a number is written, every item provenance-backed, absent stays absent). Flatten (`_flatten_proposal`): each extracted partner → `partnerships.<slug(name)>`, each consultation item → `engagement.<slug(key)>`, both `source_section=None` so they route by A's forward-wired namespaces (`partnerships`/`engagement` → community_involvement). Promotion only; every value is what the proposal states.

**B2 (monitoring evidence/notes).** Schema: optional `note: TabularCellField` on `ExtractedIndicatorRow` (+ `_LLMExtractedIndicatorRow.note`, mapper, prompt rule 12 — copy the evidence/note column verbatim with cell_state + source_locator; blank → absent; never invent/move). Flatten (`_flatten_indicator_data`): per row, a non-absent note → `indicators.<row_id>.note` via the existing `_tabular_field_candidate` (cell_ref in provenance, clean `semantic_hint`). **Anti-stranding (deliberate): the note candidate carries NO `source_section`** — a note inheriting the row's column-A label (Difference made / Spend summary) would source-pin there and strand away from changes; with `source_section=None` it routes by A's forward-wired `indicators.*.note` → changes_and_next_steps. The real extraction puts all rows 2-17 in `indicators[]`, so the spend-variance reasons (E11-E17) are captured via the indicator-row representation. Note routing is **uniform/content-agnostic** (no interpretation of what a note "is about" — that would be inference); the row-8 partner-list note therefore also reaches changes, while partner *content* independently reaches community_involvement via B1.

**Gap re-point (pin #2 — carried by real proof, not a bare edit).** Through the REAL `evaluate_requirement_satisfaction` path on B-captured facts:
- `changes_made` (NLCF, **data** type) — moved gap→satisfied. Carried by adding ONE namespace hint `DATA_BACKED_HINTS["changes_made"] = [".note"]` (same data-driven shape as the existing ref→namespace entries; not a per-funder branch). Proven in `tests/test_monitoring_notes_capture.py`: satisfied=True with a real `indicators.*.note` fact, stays False with no note fact.
- `community_participation_examples` / `partner_or_local_collaboration_examples` (**narrative** type) — no satisfaction change needed (narrative indicators already gate-satisfy); B makes them genuinely *narratable*. Proven via `section_has_synthesizable_inputs` (community_involvement is synthesizable with B facts, insufficient without).
- **Honest gaps stay gaps:** `planned_changes`, `support_needed` (and the learning refs) — B does not fill them; asserted still unsatisfied even with notes present.
- **The frozen `nlcf_regression_pin_e7fa9bee.json` is intentionally NOT edited:** it records what walk e7fa9bee (pre-B) observed; its stored KB has no B facts, so re-running gap detection on it would still report those gaps — editing it would be a bare false edit. The live flip lands in the owner re-walk.

**What the unit tests PROVE vs do NOT (false-green discipline).** They prove the schema/mapper carry the new content, the flattener promotes it into the right namespaces with provenance and zero invention, and A's real routing makes it visible to (and only to) the narrating section — all on real-derived data, with every captured value asserted to be a literal substring of the real proposal text / a real grid cell. They do **NOT** prove the live model extracts partners/consultation/notes from prose on its own (mocked LLM) — that is the owner re-walk.

**CI:** `tests/test_proposal_content_capture.py` (B1, 7 tests) + `tests/test_monitoring_notes_capture.py` (B2, 9 tests) added to the Smoke P0 M&E allowlist. Full local `tests/` suite: pre-existing failures unchanged with vs without B — confirmed by stashing B's source files and re-running (identical 11: auth×2, extract-isolation×1, migration×1, worker×1, orchestrator-gate1×6; the env-ordering `test_gate1_confirm_endpoint_404_when_module_disabled` passes in isolation and on the P0 allowlist). B adds 16 passing tests and 0 new failures. A (section-visibility), C (disaggregation), D (leak + table render), C.1, number-binding, refusal-meaning, Pkg-1, Pkg-2 all green.

**STOP:** owner audit before push. Real gate (deferred, owner-triggered): consolidated re-walk after B — partners, consultation, and delivery-change notes narrated in their sections; honest gaps still disclosed.
---
DECISION (2026-07-05) — A-JSON: synthesis JSON-parse resilience. A malformed/truncated synthesis response must never freeze the report (P3-9 Cluster A-JSON: `_extract_json_payload` bare `json.loads` → section FAILED → Gate-3 accept-all freeze). Cause-agnostic: no token-limit change, no prompt edit. AMBER.

**Parse ladder + completeness gate (adjustment #1, moat-critical).** New `app/reports/services/synthesis_parse.py::parse_synthesis_response(response)` runs: (1) strict `json.loads(content)` — succeeds only on a fully-closed document, so success is inherently complete; (2) `json_from_text.extract_complete_json_object(content)` — reuses the existing balanced-object extractor but accepts ONLY the OUTER object that closes cleanly with nothing but whitespace trailing (fences/preamble recoverable; trailing content or an unterminated outer object → None), plus a structural check that the recovered object carries the synthesis envelope (`generation_status`/`generated_content`). A truncated-mid-string payload (the real P3-8 `char 8092` class) has no matching close → None → NOT bound. Deliberately NOT the general `extract_json_object_from_text`, which would salvage a complete INNER claim fragment — proven contrast in the tests. Raw payload is NEVER salvaged into a "complete-looking but silently truncated" section.

**Bounded retry (no cause-directed change).** `_synthesise_with_parse_ladder` re-issues the IDENTICAL request once (`MAX_SYNTHESIS_PARSE_ATTEMPTS = 2`) and re-parses; no token/prompt change. `_call_openai_section` split into `_call_openai_section_raw` (returns the raw response, parsing deferred). `_extract_json_payload` kept intact for external scripts.

**Terminal state, distinct from insufficient_data.** `section_prose.build_synthesis_parse_failure_section` → GENERATED + `structured_bind_status = "synthesis_parse_failure"`, honest engine prose ("the automated drafting system returned a response that could not be read … not an indication the evidence was missing"), zero fabricated claims, zero digits/identifiers. Never converted to `insufficient_data`/`honest_empty`. Gate-3 `_sections_not_export_ready` allowlist widened to include `synthesis_parse_failure`, so one unreadable section no longer freezes export — the report completes with it honestly surfaced.

**Bounded resume (adjustment #2).** The section carries a plain integer `content.parse_failure_cycles` (not raw payload). `section_needs_synthesis` retries a `synthesis_parse_failure` section on resume only while `parse_failure_cycles < MAX_SYNTHESIS_PARSE_FAILURE_CYCLES` (=2); at the ceiling it SETTLES into the terminal state and the report completes. `_generate_one_section(prior_parse_failure_cycles=…)` increments per failed run.

**Instrumentation, trace-only (adjustment #3).** Each failed attempt records `{finish_reason, response_head/tail (bounded_response_snippet, reused), response_length, parse_error, parse_strategy, model, max_tokens, tokens}` into a per-section diagnostics sink → `ReportSynthesisStageResult.parse_failures` → `pipeline` writes `stages.synthesise.parse_failures[]` in `agent_trace_json`. NEVER onto `content_json`, the section, the DOCX, or caveats. Proven both directions: the raw sentinel appears in the diagnostics blob AND is absent from the persisted section + rendered DOCX + assumptions appendix.

**Stale-data / anchoring.** Tests anchored to the REAL P3-8 unterminated-string class (large object, complete inner claims, cut mid-string), not favourable hand-shaped JSON. `tests/test_report_synthesis_service.py` unpacking updated for `_generate_all_sections`' new 5th return (`parse_failures`) — mechanical signature adaptation, not a weakened assertion.

**CI:** `tests/test_synthesis_parse_resilience.py` (16 tests) added to the Smoke P0 M&E allowlist. Full local `tests/` suite: pre-existing failures unchanged with vs without A-JSON — confirmed by stashing this package and re-running the exact set (identical: auth×2, extract-isolation×1, indicator-extractor-env-docling×1, migration×1, worker×1, orchestrator-gate1×6; `test_gate1_confirm_endpoint_404_when_module_disabled` passes in isolation/P0 — env-ordering flake). This package adds 16 passing tests and 0 new failures. Cluster A/B/C/D + C.1 + number-binding + refusal-meaning + Pkg-1 + Pkg-2 green.

**STOP:** owner audit before push. Real gate (deferred, owner-triggered): the FCDO walk that previously froze on the `evidence_and_evaluation` parse failure now completes; the next real parse failure leaves its raw payload in the trace for root-cause.
---
DECISION (2026-07-05) — Gate-1 PATCH knowledge-bank save (`PATCH /api/reports/{id}/knowledge-bank`). Pre-existing gap since June 2026: frontend wired conflict/fact saves to PATCH; backend had GET only (405). AMBER — integrity-critical owner write.

**Scope:** Full §12.5 PATCH in one build — `conflict_resolutions` + `facts` partial updates (conflict resolve, fact edit, add fact, client dedup). Single service, single DB commit.

**Moat — dual materialization (non-negotiable).** Owner conflict resolution MUST atomically set `conflicts[].resolved_value` + `resolved_at` AND overwrite `facts[conflict.fact_key].value` (plus source/provenance from the chosen `conflict.values` entry, or `owner-attested` markers for custom figures). Synthesis cites `facts[fact_key].value` via `filter_citable_facts` — `resolved_value` alone is audit-only. Rejected figure must not remain at the canonical key.

**Confirm path:** PATCH is save-only. `confirm_gate1: true` on PATCH → 422 `USE_GATE1_CONFIRM_ENDPOINT`. Canonical confirm remains `POST .../gate1/confirm` (§12.5a). Reconciler E1 fence unchanged (`resolved_value` forbidden at reconcile).

**Frontend:** PATCH save failures show inline `saveError` on the facts panel; page-level error reserved for initial GET load failure.

**CI:** `tests/test_knowledge_bank_patch.py` (14 tests, OP1.1 1200-vs-650 moat, custom owner-attested, confirm blocked until resolved) on Smoke P0 allowlist.

**STOP:** owner live-walk on report `f33be000-4443-47d1-82f6-12f02947d972` after deploy approval.
---
DECISION (2026-07-05) — Proposal extraction reliability + blocking checkpoint (D-046). AMBER — extract/degrade path + user-facing halt.

**Scope:** Mode C stream early-exit after successful `ResultMessage`; `ME_PROPOSAL_TIMEOUT_SECONDS` default 180 (Mode B — does not fix Mode A total silence); retry backoff (3s) + differentiated attempt-2 prompt; proposal-only blocking checkpoint at `EXTRACT`/`awaiting_human` with `proposal_checkpoint` trace; `POST .../jobs/proposal-checkpoint/ack` proceed path; unreadable_sources dedupe by `document_id`; Mode A instrumentation fields on `attempt_traces` (unsolved root).

**Checkpoint:** Failed proposal after retries halts before reconcile — primary CTA re-upload/re-enqueue; secondary ack `proceed_with_gap` continues with missing objectives/indicators/partners/consultation surfaced. Grant/indicator degrades unchanged (D-040).

**Not in scope:** narrative Gate 2 gaps when proposal missing (future dependency); Mode A root-cause closure.

**CI:** `tests/test_proposal_extractor_agent.py`, `tests/test_proposal_extraction_checkpoint.py` on Smoke P0 allowlist.

**STOP:** owner approval before deploy.
---
DECISION (2026-07-18) — Track 3 STOP 1 adjudication + elevation mechanism (D-053). AMBER — gap path / moat.

**Numbering note (collision audit):** Table IDs D-046 and D-049 already collide with older freeform labels — table D-046 = F1 reliability bundle (2026-06-04) while the 2026-07-05 proposal-checkpoint narrative also says “D-046”; table D-049 = Fit Scans 20→10 while the E3 gap narrative says “D-049”. New IDs assigned only after that check: **D-053** (this entry), **D-054** (gap-grammar retro-log). No renumbering of historical collisions in this build.

**STOP 1 owner verdicts (verbatim, final):**
- NLCF elevation map — ACCEPTED at exactly 2: `community_participation_examples` and `partner_or_local_collaboration_examples`. No additions.
- FCDO elevation map — ACCEPTED at 0. Empty map is the correct answer, not a placeholder (omission of `elevate_on_proposal_failure` flags).
- All four borderline exclusions ACCEPTED: `project_story`; section-level `community_involvement` row (double-ask); FCDO `partner_performance` (wrong content class); objectives/activities elevation.
- Track 3.1 (shared-floor objectives/activities thinning on proposal failure) is named deferred debt (**O-006**) — not part of this build; Phase 2 must not reach toward it.

**Mechanism (generic):** Optional per-indicator template flag `indicator_requirements.<slug>.elevate_on_proposal_failure` (boolean). Engine reads the flag generically; which refs elevate lives only in template JSON. Trigger: `report_jobs.agent_trace_json.stages.extract.proposal_checkpoint` with `acknowledged=true` and `ack_action=proceed_with_gap`. Post-pass after deterministic gap build emits those items as mandatory Gate 2 gaps (existing `build_gap_question` grammar); answers reuse `gap_answers` + `gap:` provenance (no new `facts{}` promotion). Healthy proposal path: detector false → no elevation → Gate 2 unchanged.

**Trigger narrowing (conscious owner decision — residual debt O-007):** Trigger is checkpoint-acked failure only, not “failed or absent” in the broader sense. A never-uploaded proposal produces no checkpoint and no elevation. Accepted to preserve intake/checkpoint semantics; revisit on evidence of real no-proposal runs.

**Rollout split:** Committed instance JSON + engine in repo. Live NLCF row `2d5d75b7-12f5-46b5-adaa-d5939a5249a8` mutation is **OWNER-TRIGGERED** only (pre-mutation snapshot first, same discipline as FCDO Phase B). Cursor never mutates prod `funder_report_templates`. FCDO prod: no mutation. Generic UK/US/India templates out of scope; mechanism must not prevent pure-JSON adoption later.

**STOP:** PR-ready for independent audit; no merge/prod mutation in this build.
---
DECISION (2026-07-05) — Gate 2 gap question copy readable English (D-054). Retro-log of commit `7570bec`. AMBER — UX / Gate 2 surface.

**Shipped at `7570bec` (not previously decision-logged):** Replaced underscore-swap f-string gap questions with deterministic section-first phrasing in new `app/reports/gap/gap_question_copy.py` (`build_gap_question` for data, table, narrative, and logframe shapes; `is_well_formed_gap_question` guardrails). `deterministic_gaps.requirement_to_gap_item` now delegates to that module. Regression tests in `tests/test_gap_question_copy.py` wired onto Smoke P0 M&E allowlist via `.github/workflows/smoke-test.yml`.

**Rationale:** Gate 2 questions must be plain funder-facing English — no internal slug leakage via naive `ref.replace("_", " ")` phrasing.

**STOP:** already on `main` at `7570bec`; this entry is documentation parity only.
---
DECISION (2026-07-18) — Track 3 prod NLCF scoped reconcile (D-055). Owner-triggered. AMBER — template data / prod seed.

**(a) Drift discovery:** Pre-mutation snapshot of live `funder_report_templates.id = 2d5d75b7-12f5-46b5-adaa-d5939a5249a8` (SHA256 `64e6ebc60be775d20e451a51cd796f23e3829726c08617d8f580e8e808661afa`, path [`audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json`](audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json)) vs committed [`TEMPLATE_INSTANCE_NLCF.json`](TEMPLATE_INSTANCE_NLCF.json) showed the live row **predated Package A/B template fields** — missing `fact_namespaces` / `source_section_labels` on every section, and missing `community_involvement.indicator_requirements` (including both Track 3 `elevate_on_proposal_failure: true` entries). Full field-level evidence: [`audits/TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json`](audits/TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json) (13 divergences). Scalars / `format_rules_json` / `terminology_map_json` matched.

**(b) Owner scoped-reconcile decision (verbatim Option 2):** Reconcile `community_involvement` to the committed instance for exactly three fields — `fact_namespaces`, `source_section_labels`, and `indicator_requirements` (both elevate flags). Committed instance is canonical authored template; live missing fields are un-applied Package A/B seed, not intended state. **Scope fence:** `community_involvement` only — no other section mutated regardless of remaining drift. Applied on prod: `version` 1→2; FCDO `55f891ac…` untouched. Evidence: [`audits/TRACK3_PHASE_A_SCOPED_RECONCILE_EVIDENCE_2026-07-18.json`](audits/TRACK3_PHASE_A_SCOPED_RECONCILE_EVIDENCE_2026-07-18.json). Rollback source remains the pre-Track3 snapshot (not re-snapshotted).

**(c) Remaining drift — open adjudication:** Non-community sections still lack `fact_namespaces` / `source_section_labels` vs committed instance. Named open item **O-008**. Do not reconcile in this operation.

**STOP:** confirming walk (Phase B) proceeds under owner release; no further template mutation.
---
DECISION (2026-07-19) — Track 3 closure fault flag Option B (D-056). AMBER — extraction path, flag-gated.

**Context:** Confirming walk could not induce proposal extraction failure (dense filler completes; image-only PDF fails at classify as `other`). Checkpoint + Track 3 elevation were CI-proven and prod-seeded but never prod-observed.

**Owner Option B (verbatim):** Fault-flag variant, not timeout-lowering. A deliberate fault flag on the proposal extractor is chosen over a temporarily lowered timeout because a flag cannot be accidentally left misconfigured in a way that harms real users.

**Mechanism:** Env-only `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE` (`1`/`true`/`yes`). When active, clamps per-attempt timeout to 0.05s inside `extract_proposal_text` so the real dual-`TimeoutError` → `_build_degraded_timeout_result` path runs (`DEGRADED_EXTRACTION_TIMEOUT` + `attempt_traces`). Not a shortcut via `build_degraded_extraction_stop_result`. Default off. Not on Pydantic Settings; never from user input. WARNING log on every invocation while active. Induced runs tagged: document `agent_trace.fault_injected` / `fault_flag`, and job `stages.extract.proposal_fault_injected` / `proposal_fault_flag`.

**Retention (owner STOP 1):** **Retain** post-launch, default-off, for future witnessed walks; induced runs permanently trace-tagged. **Re-evaluate the flag-window risk model before any post-launch use** — a live customer base changes the blast radius of an open window (any concurrent real extract would degrade).

**Deferred — O-009 Track 3.2:** intake-level “no readable proposal present” (evidence: report `18976580…`); not built here.

**Scope fence:** proposal extractor seam (+ schema + halt-trace mirror only). No checkpoint/elevation/classifier semantics changes.

**STOP:** PR-ready for independent audit; witnessed walk is owner-delegated after merge (flag window declared start/end UTC).
---
DECISION (2026-07-19) — Track 3 Phase 2 witnessed walk outcome (D-057). GREEN — prod validation closed under declared flag window.

**Window (worker `exemplary-encouragement` only):**
- Deploy verified containing feature commit `67f94ca` via merge `1a7ccde` before flag set.
- `ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE=true` set → read-back `true` → WARNING audible on first induced extract.
- Window start UTC: `2026-07-19T08:05:11.736690+00:00`
- Window end UTC: `2026-07-19T08:46:21.812309+00:00` (duration **2470.1s**)
- Flag unset → read-back absent/`None` on worker; web never had the key.
- **Window-exposure statement:** any concurrent real proposal extract on this worker would have degraded while the flag was on. Acceptable pre-launch; re-evaluate post-launch.

**Induced report IDs (named as induced — not organic customer traffic):**
| Branch | donor_report_id |
|--------|-----------------|
| answered | `b007f125-cf33-4bba-8acf-6eccde27d063` |
| skip | `46fdb1b1-f03c-4266-bdfc-69ed3bbf549f` |

**First prod checkpoint firing:** both runs halted `awaiting_human`/`extract` with `proposal_checkpoint.degraded_code=DEGRADED_EXTRACTION_TIMEOUT`, `attempts=2`, `proposal_fault_injected=true`, flag name tagged. First captured payload: [`audits/TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json`](audits/TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json).

**Track 3 prod-validation outcome:** after `proceed_with_gap`, Gate 2 showed exactly `community_participation_examples` + `partner_or_local_collaboration_examples`, funder-facing copy, zero internal-identifier leaks. Answered branch: both elevated items answered with distinct traceable text → synthesis/Gate 3/export **done**; community claims carry `gap:community_involvement:indicator:…` provenance. Skip branch: both elevated items skipped with valid reasons → community section `structured_bind_status=insufficient_data`, honest blank / no invented narrative → export **done**.

**Auth diagnostics outcome:** `AUTH_REFRESH_DIAG` count **0** across both full-export walks (refresh never invoked; no 401 subtype). Ops note only: one mistaken non-owner resume → HTTP **404** (not 401); corrected by owner-session resume. Evidence: [`audits/TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt`](audits/TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt).

**Prod mutation invariant held:** flag set/unset was the only prod mutation; flag not active outside the declared window; no product/auth fixes applied during the walk.

**STOP:** full evidence pack [`audits/TRACK3_PHASE2_STOP3_EVIDENCE_PACK_2026-07-19.md`](audits/TRACK3_PHASE2_STOP3_EVIDENCE_PACK_2026-07-19.md). No further action.
---
DECISION (2026-07-19) — Package 1 Gate 1 conflict integrity (D-058…D-062). AMBER — Gate 1 moat. Owner-approved with amendments.

**Numbering note (Amendment 5):** Verified decision-log table head was **D-057** before append; next IDs are **D-058–D-062**. No renumbering of historical collisions.

**D-058 (D-A, verbatim):** Write-time integrity invariant. Every conflict persisted to the knowledge bank must be resolvable through the standard resolution path. A conflict whose key has no materializable fact entry is an integrity violation that must be impossible to persist. The fix lands at emit time. The patch validator's strictness stays exactly as it is — it caught a real defect and must not be loosened to make the symptom pass.

**Mechanism:** Deterministic normalizer `ensure_conflicts_materializable` at the final persistence seam in `knowledge_bank_reconciliation_service.reconcile_and_persist` (not a reconciler rewrite). Creates an unresolved canonical stub (`value=null`, `verification_status=unverified`) when needed. **Amendment 1:** every repair emits WARNING structured log + `agent_trace.conflict_integrity_repairs` entry (report id, conflict key, every provenance-only key). PATCH missing-fact `KB_PATCH_VALIDATION_FAILED` guard unchanged.

**D-059 (D-B, verbatim):** Ambiguous and null candidates are never directly acceptable as resolved values. The ambiguous candidate remains visible in the conflict card for transparency, but selecting it routes the user into explicit entry, pre-contextualised with what is known (e.g. the ambiguous month reference). The backend independently rejects a null `resolved_value` with a specific domain code — defense in depth. An unnormalisable value must never become a stated fact.

**Domain code:** `KB_CONFLICT_RESOLUTION_VALUE_REQUIRED` (422) for null or blank-string `resolved_value`.

**D-043 quote (operative rule):** “A conflict requires ≥2 genuinely different non-empty values for the same quantity; lone values, blank/absence parties, and same-value representation variants are facts not conflicts.”

**Scoped refinement:** Observed-but-unnormalisable evidence remains legitimate grounds to *surface* a conflict and appears as **non-selectable context** in the Gate 1 card, but is never a resolvable party and never becomes a stated fact via null PATCH. **Open follow-up (O-010):** E1 gate grader `assert_no_spurious_conflicts` still encodes the blank-party prohibition; no grader, reconciler, prompt, or answer-key change in this package.

**D-060 (D-C, verbatim):** Sibling facts are provenance, not claims. After resolution, exactly one canonical truth for the disputed fact flows to gap logic, synthesis, summary, and export. The suffixed sibling rows are retained as provenance but must never surface downstream as independent or duplicate claims.

**Mechanism:** Optional fact field `provenance_only_for` (canonical conflict key). **Amendment 2:** mark only on exact value AND source correspondence to a specific conflict candidate, together with key relationship (`key.startswith(conflict_key + "_"|".")`); otherwise do not mark (err toward visible duplication). Citability (`is_fact_citable`) and DOCX table inputs exclude provenance-only facts.

**D-061 (D-D, verbatim):** Existing stuck data gets a one-off owner-authorized repair. Scan production knowledge banks for the orphan shape (conflict key with no fact entry) — expected blast radius is small — and repair affected reports so they become resolvable. Repair creates resolvability only; it never creates a resolved value and never invents data. `cb090edb…` must be resolvable by the owner after repair.

**Bounds:** Fleet scan STOP if any orphan outside `cb090edb-715b-41cb-b3be-61c006fbdb55`. Repair reuses the same product normalizer; same loud telemetry as emit-time.

**D-062 (D-E, verbatim):** Error experience is designed, not defaulted. On the Gate 1 save path, every known domain code maps to a specific, plain-English, NGO-appropriate message; the generic banner is the last resort for unknown codes only. No internal identifiers — fact keys, gate numbers, agent names, error slugs — ever appear in user-facing text. Error, loading, and disabled states on this journey follow the brand and frontend specs. The quality bar is world-class SaaS.

**STOP:** Build + tests + deploy first; production scan/repair/witness only under D-061 bounds after deploy. No further product scope in this package.
---
NARRATIVE (2026-07-19) — Gate-integrity: CI silently skipped async tests (Package 1 fix round 2). No new D-number.

**Discovery:** Independent delta re-audit of PR #10 head `9316716` found CI Smoke Test reported **269 passed / 25 skipped**. The skips were `@pytest.mark.asyncio` tests collected without an async pytest plugin: pytest's default is to **skip** unhandled `async def` tests rather than fail. Among the skips were Package 1's seam regression `test_reconcile_and_persist_normalizes_orphan_at_seam` and pre-existing smoke-selection tests including `tests/test_gap_compliance_agent.py::test_fcdo_complete_distilled_gap_set_exact` and the proposal-extractor suite. Layer 1 had been claiming coverage it did not execute.

**Cause:** `.github/workflows/smoke-test.yml` installs from `requirements.txt` verbatim; that file listed `pytest==7.4.3` but **no** `pytest-asyncio` (or other async plugin). Local developer environments that happened to have the plugin installed saw the full suite green (auditor: 294 passed / 0 skipped), masking the CI blind spot.

**Since when (history):** `pytest-asyncio` never appears in `requirements.txt` history. Async smoke coverage entered the workflow install path earlier without a matching dependency: proposal-extractor async suite was added to the smoke selection in `fcf35e5` (Proposal extraction reliability…); the named FCDO gap-set gate entered in `bd72572` (Phase 3 P3-1..P3-6…). From those commits until this restoration, CI could silently skip those async tests whenever the runner lacked a locally preinstalled plugin.

**Restoration (this round):** Add `pytest-asyncio==0.21.1` to `requirements.txt` (matches the locally verified pin). Configure `pytest.ini` with `asyncio_mode = auto` and elevate `pytest.PytestUnhandledCoroutineWarning` to **error** so an unrunnable async test fails the gate instead of skipping. No mass test rewrites; resurrected tests must pass unmodified.

**STOP:** Delta re-audit #2 of the PR head after push; no merge from this narrative alone.
---
