# M&E Module — Decision Log

Append-only record of deliberate choices. Do not silently pivot — add a row and reference it in PRs/prompts.

---

## Locked decisions (seeded Stage A — 2026-05-24)

| ID | Date | Decision | Rationale | Stage |
|----|------|----------|-----------|-------|
| D-001 | 2026-05 | **Modular monolith** — M&E in `app/reports/`, same repo as core backend | Solo-founder ops simplicity; hooks enforce isolation | A |
| D-002 | 2026-05 | **One-way dependency** — M&E imports core; core never imports M&E | Killable module; proposal product protected | A |
| D-003 | 2026-05 | **Single mounting seam** — conditional `include_router` in `app/main.py` only | One line mounts/unmounts entire API | A |
| D-004 | 2026-05 | **Impact Pro** — $99/mo, new plan enum **`IMPACT_PRO`** | Do not overload IMPACT; dual-capability tier (proposals + reports) | J |
| D-005 | 2026-05 | **2 M&E reports/month** on Impact Pro | Cost ceiling ~$49.50/report revenue | J |
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

---

## Open items (not yet decided)

| ID | Topic | Notes |
|----|-------|-------|
| O-001 | Vision API vendor | Pick at Stage D; **D5 AI photo interpretation deferred Phase 2 (D-038)** |
| ~~O-002~~ | ~~`ME_MODULE_ENABLED` default~~ | **Resolved Stage C (D-025):** default `false` in Settings + ENV_VARS_REFERENCE §J |
| ~~O-003~~ | ~~Report quota event types~~ | **Resolved Stage B:** REPORT_CREATE, REPORT_EXPORT — ENUM_REGISTRY §3.3, §5.10 |
| O-004 | Stripe `STRIPE_PRICE_ID_IMPACT_PRO` | Stage J |
| ~~O-005~~ | ~~Stage B-validation~~ | **Resolved 2026-05-24 (D-024):** NLCF + FCDO instances validated; see FUNDER_TEMPLATE_SCHEMA §6 |

---

## Revisions

*(Append rows when a locked decision changes.)*

| ID | Date | Supersedes | New decision | Why |
|----|------|------------|--------------|-----|
| — | — | — | — | — |

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
| Four M&E tables + migration 0014 | **Complete** |
| Models match contracts (parity hook) | **Complete** |
| `ME_MODULE_ENABLED` mount/unmount | **Complete** |
| Worker separate process (Procfile) | **Complete** |
| Reversible downgrade (kill switch 3) | **Complete** — `0014_me_module_tables.downgrade()` |
| Isolation veto + migration parity hooks | **Complete** |
