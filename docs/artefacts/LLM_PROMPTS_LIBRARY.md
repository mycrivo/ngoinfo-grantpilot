# LLM_PROMPTS_LIBRARY.md

**Status:** Canonical registry (LOCKED FOR BUILD)  
**Registry document version:** 2.0.0  
**Last Updated:** 2026-07-26  
**Decision:** D-072  
**Depends on:** DB_FIELD_CONTRACT_FUNDING_OPPORTUNITY.md, PROMPT_INPUTS_FIELD_MAPPING.md, ENV_VARS_REFERENCE.md  
**System of Record:** Railway Postgres (GrantPilot DB)  

> **Versioning note:** `2.0.0` is this **registry document** version. Persisted `prompt_version` columns use the runtime constant `PROMPT_LIBRARY_VERSION` in the owning module (core GP path currently `1.1.0`). Do not write the registry document version into DB `prompt_version`.

---

## Canonical rule

**Deployed code is canonical. This registry indexes it.**

- Do **not** duplicate prompt bodies or quote prompt text in this document.
- Model identity is recorded **only** as a pointer to an environment-variable name (`OPENAI_MODEL_PRIMARY`, `OPENAI_MODEL_FALLBACK`, or the relevant `ME_*_MODEL` var). Never assert a hardcoded model name as current fact.
- Behavioural or schema changes require a version bump here **and** a matching change in the owning deployed module.
- Bounded-service header (mandatory per Addendum v1.1 §2.2): input contract, output schema, prompt version, failure mode, quota behaviour, persistence rule, user-visible caveat.

---

## Global style (pointer only)

Former §0 voice / anti-AI / human-writing rules are **not** duplicated here.

| Pointer | Location |
|---------|----------|
| Human Writing Instructions V4 | **Not present in this repo** (filename expected: `Human_Writing_Instructions_v4` / equivalent). Supply and wire before golden v1.1 prose-conformance. |
| Core proposal humaniser (deployed) | `app/ai/prompts/proposal.py` (`GP_P01_SYSTEM_PROMPT`, `ARCHETYPE_RULES`) |
| M&E synthesis humaniser (deployed) | `app/reports/ai/prompts/synthesis.py` (`REPORT_SYNTHESIS_SYSTEM_PROMPT` — Humaniser V3 string) |
| Post-hoc detection (no rewrite) | `app/reports/services/synthesis_output_hygiene.py` (`detect_humaniser_violations`) |
| Fit Scan plain-English language rules | `docs/artefacts/FIT_SCAN_LANGUAGE_REFERENCE.md` |

---

## Model configuration (env pointers only)

| Surface | Env vars (see `ENV_VARS_REFERENCE.md`) |
|---------|----------------------------------------|
| Core OpenAI path (Fit Scan, Proposal, M&E synthesis) | `OPENAI_MODEL_PRIMARY`, `OPENAI_MODEL_FALLBACK` |
| M&E classifier + extractors | `ME_CLASSIFIER_MODEL` |
| M&E reconciler | `ME_RECONCILER_MODEL` |
| M&E gap/compliance | `ME_GAP_COMPLIANCE_MODEL` (fallback: `ME_RECONCILER_MODEL`) |
| M&E fact-safety critic | `ME_FACT_SAFETY_CRITIC_MODEL` (fallback: `ME_RECONCILER_MODEL`) |

Runtime stamp for core GP library version: `PROMPT_LIBRARY_VERSION` in `app/ai/prompt_runner.py` and `app/ai/fit_scan_executor.py` (currently **1.1.0** until a code bump).

---

## Registry — core GrantPilot

| ID | Deployed source | Model env | Input contract | Output schema | Prompt version | Failure mode | Quota behaviour | Persistence rule | User-visible caveat |
|----|-----------------|-----------|----------------|---------------|----------------|--------------|-----------------|------------------|---------------------|
| GP-F01 | `app/ai/fit_scan_executor.py` (system); re-export `app/ai/prompts/fit_scan.py` | `OPENAI_MODEL_PRIMARY` (+ `OPENAI_MODEL_FALLBACK`) | Role-only system message; paired with GP-F02 | N/A — system prompt (reason: no JSON schema of its own) | `PROMPT_LIBRARY_VERSION` **1.1.0** | Via GP-F02 path | Via GP-F02 | Via GP-F02 | Plain-English free text; no internal field paths |
| GP-F02 | `app/ai/fit_scan_executor.py`; `app/services/fit_scan_service.py`; `app/services/fit_scan_prompt_inputs.py` | `OPENAI_MODEL_PRIMARY` (+ `OPENAI_MODEL_FALLBACK`) | `prompt_inputs` (NGO + funding opportunity + requirements + derived variant) | JSON: fit summary, eligibility/alignment/readiness, risk flags, recommended modifications, proceed advice | **1.1.0** | `FIT_SCAN_FAILED` / `AI_SERVICE_ERROR`; no speculative invent | `enforce_quota(FIT_SCAN)` then `record_usage` on success | `fit_scans.result_json` + `prompt_version` | Assessment for NGO managers; not proposal prose |
| GP-U01 | `app/ai/prompts/user_input_norm.py`; config slot in `app/ai/prompt_runner.py` | Would use `OPENAI_MODEL_PRIMARY` / `FALLBACK` if wired | Doc-era: `prompt_inputs_json` → generation plan | Doc-era: `selected_variant_id`, `generation_plan`, `warnings` | Library **1.1.0**; **not deployed** (no importer) | N/A — not deployed (reason: unwired) | N/A — not deployed | N/A — not deployed | N/A — not deployed |
| GP-P01 | `app/ai/prompts/proposal.py` (`GP_P01_SYSTEM_PROMPT`, `ARCHETYPE_RULES`) | Via GP-P02 runner (`OPENAI_MODEL_PRIMARY` / `FALLBACK`) | Role + humaniser + archetype rules | N/A — system prompt (reason: no JSON schema of its own) | `PROMPT_LIBRARY_VERSION` **1.1.0** | Via GP-P02 | Via GP-P02 | Via GP-P02 | Consultant voice; no invented facts |
| GP-P02 | `app/ai/prompts/proposal.py`; `app/ai/prompt_runner.py`; `app/services/proposal_service.py` | `OPENAI_MODEL_PRIMARY` / `OPENAI_MODEL_FALLBACK` | `prompt_inputs` + fit_scan_output + submission_item + archetype rules | JSON: `generation_status` GENERATED\|UPLOAD_REQUIRED\|INSUFFICIENT_INPUT; archetype; text/assumptions/evidence_used | **1.1.0** | Per-section FAILED / INSUFFICIENT_INPUT; proposal `DEGRADED` if any fail; `AI_SERVICE_ERROR` → 503 | `enforce_quota(PROPOSAL_CREATE)` before gen; usage on persist | `proposals.content_json` + `prompt_version` | Draft only; human owns edits; missing inputs → empty text + warnings |
| GP-D01 | *(none — library-only legacy ID)* | N/A — not deployed | N/A — not deployed (reason: no runtime module) | N/A — not deployed | Historical library v1.0 | N/A — not deployed | N/A — not deployed | N/A — not deployed | N/A — not deployed |
| GP-X01 | *(none — library-only legacy ID)* | N/A — not deployed | N/A — not deployed (reason: no runtime module) | N/A — not deployed | Historical library v1.0 | N/A — not deployed | N/A — not deployed | N/A — not deployed | N/A — not deployed |
| GP-X02 | *(none — library-only legacy ID)* | N/A — not deployed | N/A — not deployed (reason: no runtime module) | N/A — not deployed | Historical library v1.0 | N/A — not deployed | N/A — not deployed | N/A — not deployed | N/A — not deployed |

---

## Registry — M&E (Donor Report Writer)

| ID | Deployed source | Model env | Input contract | Output schema | Prompt version | Failure mode | Quota behaviour | Persistence rule | User-visible caveat |
|----|-----------------|-----------|----------------|---------------|----------------|--------------|-----------------|------------------|---------------------|
| ME-C01 | `app/reports/agents/classifier.py` | `ME_CLASSIFIER_MODEL` | Extracted text in `<document_data>` (max length per agent STOP) | `classification` ∈ ENUM_REGISTRY §5.3 labels + confidence + justification | No dedicated `prompt_version` const; enum §5.3 | `ClassifierError` / STOP_*; timeout `ME_CLASSIFIER_TIMEOUT_SECONDS` | No per-call quota; report create/export quotas elsewhere | `uploaded_documents.classification` + `extracted_json` / `agent_trace_json` | Labels only; uncertain → `other` |
| ME-E01 | `app/reports/agents/proposal_extractor.py`; schema `proposal_extraction_v1.py` | `ME_CLASSIFIER_MODEL` | Single proposal document excerpt | `ProposalExtractedEnvelope` | `PROPOSAL_EXTRACTION_SCHEMA_VERSION` **1.0.0** | `DEGRADED_EXTRACTION_TIMEOUT`; retries; empty/invalid STOP | Pipeline / REPORT_CREATE quota surface | `uploaded_documents.extracted_json` | No invent; targetless equity indicator allowed |
| ME-E02 | `app/reports/agents/grant_terms_extractor.py`; `grant_terms_extraction_v1.py` | `ME_CLASSIFIER_MODEL` | grant_letter / mou excerpt | `GrantTermsExtractedEnvelope` | **1.0.0** | Timeout degrade; multi_value / absent fields | Same | `extracted_json` | Does not write KB/report columns directly |
| ME-E03 | `app/reports/agents/indicator_data_extractor.py` + schema | `ME_CLASSIFIER_MODEL` | Spreadsheet JSON in `<document_data>` | `IndicatorDataExtractedEnvelope` | **1.0.0** | `DEGRADED_EXTRACTION_TIMEOUT` / unparseable | Same | `extracted_json` | No recompute/drop rows; conflicts deferred to reconciler |
| ME-R01 | `app/reports/agents/knowledge_bank_reconciler.py`; `knowledge_bank_reconciliation_v1.py` | `ME_RECONCILER_MODEL` | Pre-extracted candidates in `<reconciliation_input>` | Gate-1 KB: facts + conflicts (no `resolved_value`) | `KNOWLEDGE_BANK_RECONCILIATION_VERSION` **1.0.0** | `DEGRADED_RECONCILIATION_TIMEOUT`; parse/STOP codes | Same | `donor_reports.knowledge_bank_json` | Surfaces conflicts; **never** picks truth |
| ME-G01 | `app/reports/agents/gap_compliance_agent.py` + deterministic gap path | `ME_GAP_COMPLIANCE_MODEL` (fallback `ME_RECONCILER_MODEL`); LLM gated by `ME_GAP_COMPLIANCE_USE_LLM` | Confirmed KB + template checklist | `GapComplianceOutput` / envelope | `GAP_COMPLIANCE_VERSION` **1.0.0** | Parse retry; else deterministic path / STOP | Same | `donor_reports.gap_analysis_json` | Questions only; no invented answers |
| ME-S01 | `app/reports/ai/prompts/synthesis.py`; `app/reports/services/report_synthesis_service.py` | `OPENAI_MODEL_PRIMARY` / `OPENAI_MODEL_FALLBACK` | `report_inputs` (KB facts/gaps) + section + tone + optional linked proposal (framing only) | Section JSON: claims[] + text + assumptions; status GENERATED\|INSUFFICIENT_INPUT | No `PROMPT_LIBRARY_VERSION`; Humaniser V3 in deployed prompt module | Parse ladder + retry → `synthesis_parse_failure`; OpenAI errors → section fail | No per-section quota | `donor_reports.content_json` | Retrospective only; no fabricated specifics; internal IDs forbidden in prose |
| ME-F01 | `app/reports/agents/fact_safety_critic.py` (+ qualitative/legacy schema modules) | `ME_FACT_SAFETY_CRITIC_MODEL` (fallback `ME_RECONCILER_MODEL`) | Section prose + scoped citable KB (qual) or `evidence_used` (legacy) | `specifics[]` VERIFIED\|FLAGGED + `fact_safety_status` | Schema modules `fact_safety_critic_v1` / `qualitative_critic_v1` (no prompt_version const) | `FactSafetyCriticError`; timeout env | Same | Flags on sections / Gate 3 via pipeline + `agent_trace_json` | BLOCK/WARN on unsupported claims |

Vision agent and orchestrator: not registered as prompt rows (no vision agent module at launch; orchestrator is dispatch, not a prompt body).

---

## Versioning and change control

Every registered prompt has `prompt_id` and a version (library stamp and/or schema version as listed above).

Any behavioural or schema change requires:
- Version bump in the owning deployed module
- Changelog entry in this registry

Rollback: select an earlier git revision of the owning source module; this file indexes, it does not ship prompt text.

### PROMPT_CHANGELOG

| Version | Date | Prompt ID | Change | Reason | Rollback Available |
|---------|------|-----------|--------|--------|-------------------|
| 1.0.0 | 2026-01-23 | ALL | Initial locked prompt library | Foundation aligned to Doctrine + DB Field Contract | No |
| 1.0.0 | 2026-01-23 | GP-P01/P02 | Set temp=0.65, frequency_penalty=0.4 for proposal generation | Prevent robotic, repetitive text | No |
| 1.0.1 | 2026-01-24 | ALL | Refactor all prompts to prompt_inputs_json-only + resolve CAPACITY budget mismatch + deterministic CAPACITY thresholds | Remove contract ambiguity blocking Cursor; preserve full functionality | Yes (to 1.0.0) |
| 1.0.2 | 2026-03-23 | ALL | Model selection moved from hardcoded constant to env-var-driven (`OPENAI_MODEL_PRIMARY` / `OPENAI_MODEL_FALLBACK`) with automatic fallback on HTTP 400 | Model deprecation broke smoke test B6; env-var approach prevents future breakage | Yes (to 1.0.1 by restoring hardcoded constant + setting env var) |
| 1.1.0 | 2026-04-01 | A0 / Model configuration (env pointers only) | Confirm model selection is env-driven via `OPENAI_MODEL_PRIMARY` / `OPENAI_MODEL_FALLBACK` | Keep runtime model choice configurable without code edits | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A1 / Global style (pointer only) — historical pre-v2 §0.2 | Strengthen consultant-grade voice with decisive drafting and explicit "should" soft-ban scope | Remove advisory hedging and probabilistic phrasing | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A2 / Global style (pointer only) — historical pre-v2 §0.3 | Expand banned adjectives/verbs/phrases and banned constructions aligned to runtime prompt guardrails | Reduce AI-detectable wording patterns | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A3 / Global style (pointer only) — historical pre-v2 §0.3 | Add mandatory human writing signals and rhythm enforcement | Improve human-like cadence and readability | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A4 / Global style (pointer only) — historical pre-v2 §0.4 | Enforce evidence density and `knowledge_bank` evidence usage | Increase specificity and traceability of claims | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A5 / Registry — core GrantPilot (GP-P01) — historical pre-v2 §6.1 | Restructure GP-P01 into explicit runtime blocks | Make instruction hierarchy explicit and enforceable | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A6 / Registry — core GrantPilot (GP-P01) — historical pre-v2 §6.1 | Align GP-P01 content to shipped constant | Remove spec-runtime drift | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A7 / Registry — core GrantPilot (GP-P02) — historical pre-v2 §6.3 | Add mandatory 9-point self-audit block in GP-P02 before JSON output | Enforce quality checks pre-output | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A8 / Registry — core GrantPilot (GP-P01/P02) — historical pre-v2 §6.2 + §6.3 | Materialise archetype rules in runtime (`ARCHETYPE_RULES`) | Ensure model sees archetype constraints at generation time | Yes (to 1.0.2) |
| 1.1.0 | 2026-04-01 | A9 / Related contracts / PROMPT_INPUTS_FIELD_MAPPING — historical pre-v2 §3 | Document `prompt_inputs.ngo.knowledge_bank` and derived payload parity | Keep input contract aligned with shipped prompt payloads | Yes (to 1.0.2) |
| 1.1.0 | 2026-05-30 | GP-F01, GP-F02 | Replace field-path citation rule with plain-English output language rules per `FIT_SCAN_LANGUAGE_REFERENCE.md` | Fit Scan free text exposed internal paths; UI showed raw enums | Yes (revert executor CRITICAL RULES + `PROMPT_LIBRARY_VERSION`) |
| 2.0.0 | 2026-07-26 | ALL | Rename prior prompts-library artefact → `LLM_PROMPTS_LIBRARY.md`; restructure as registry (seven bounded-service fields + deployed-source pointers); remove duplicated prompt bodies; model identity via env-var pointers only; index M&E agents ME-C01…ME-F01 | Spec drifted from deployed code; D-072 | Yes (prior filename + body form at pre-rename git revision) |

**Rollback Procedure:**
1. Identify target version in changelog
2. Revert owning deployed module(s) and this registry file to that git commit
3. Deploy to staging
4. Run regression test suite
5. If pass → deploy to production
6. If fail → investigate + document in changelog

---

## Related contracts

- `PROMPT_INPUTS_FIELD_MAPPING.md` — core `prompt_inputs_json` shape
- `docs/artefacts/me_module/REPORT_INPUTS_FIELD_MAPPING.md` — M&E report inputs
- `FIT_SCAN_LANGUAGE_REFERENCE.md` — Fit Scan output language
- `ENUM_REGISTRY.md` §5 — M&E agent output enums
