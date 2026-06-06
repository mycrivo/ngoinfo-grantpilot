# M&E Module — Status Through E4 (Gate 2)

**Generated:** 2026-05-24 (read-only audit)  
**Scope:** Stages A–E4 built state, engine map, migrations, git/deploy, F-readiness signals.  
**Source of truth:** Repository code + `git` read-only state + pytest (not `ME_MODULE_MASTER_MEMORY.md`, which is stale).

**Important:** Gate 1, E3, E4, and much of E2-era work exist in the **working tree** but are largely **untracked / uncommitted** at audit time. Last commit: `5ea7579` on `main`, **ahead of `origin/main` by 2**.

---

## 1. Stage status (A → E4)

| Stage | Built? | Key paths | Tests |
|-------|--------|-----------|-------|
| **A — Governance / isolation** | Yes | `.cursor/rules/`, `.cursor/hooks/me_module_hooks.py`, `docs/artefacts/me_module/REPO_MAP_ME_MODULE.md` | `tests/test_me_module_mount.py` |
| **B — Spec lock** | Yes (docs) | `FUNDER_TEMPLATE_SCHEMA.md`, `DB_FIELD_CONTRACT_*.md`, `TEMPLATE_INSTANCE_NLCF.json`, `TEMPLATE_INSTANCE_FCDO.json` | Spec-only |
| **C — Foundations** | Yes | `0014_me_module_tables.py`, `app/reports/models/`, `app/reports/router.py`, `Procfile`, `app/reports/worker/run_pipeline.py` (stub), `ME_MODULE_ENABLED` in `app/core/config.py` | `test_me_module_*`, migration parity |
| **D1 — Classifier** | Yes | `app/reports/agents/classifier.py` | 13 tests — pass (working tree) |
| **D2 — Proposal extractor** | Yes | `app/reports/agents/proposal_extractor.py` | 14 tests — pass |
| **D3 — Grant-terms extractor** | Yes | `app/reports/agents/grant_terms_extractor.py` | 16 tests — pass |
| **D4 — Indicator / tabular** | Yes | `app/reports/agents/indicator_data_extractor.py`, `extraction/spreadsheet_input.py` | 12 tests — pass |
| **D5 — Vision / photo AI** | **Not built (deferred)** | D-038 / O-001 in `ME_MODULE_DECISION_LOG.md`; photo/deck routed upstream in classifier only | N/A |
| **E1 — Reconciler** | Yes | `knowledge_bank_reconciler.py`, `knowledge_bank_reconciliation_service.py` | 11 tests — pass |
| **E2 — Gate 1** | Yes (working tree) | `gate1_confirmation_service.py`, `api/routes/gate1.py`, `require_gate1_confirmed` | 6 tests — pass |
| **E3 — Gap / compliance agent** | Yes (working tree, untracked) | `gap_compliance_agent.py`, `gap_compliance_service.py`, `gap_analysis_json` | 9 tests — pass |
| **E4 — Gate 2** | Yes (working tree, untracked) | `gate2_gap_answer_service.py`, `api/routes/gate2.py`, `require_gate2_confirmed` | 10 tests — pass |
| **F — Synthesis / critic / export** | **Not built** | Enums only (`ReportJobStage.SYNTHESISE`, `CRITIQUE`, `EXPORT`); F1 guard exists, no F1 agent | N/A |

### Gate enforcement (server-enforced, no model calls)

| Gate | Unlock field | Service / precondition |
|------|--------------|------------------------|
| **Gate 1 (E2)** | `knowledge_bank_json.gate1_confirmed_at` | `confirm_gate1()` — `gate1_confirmation_service.py`; `require_gate1_confirmed()` → 409 `GATE1_NOT_CONFIRMED` |
| **Gate 2 (E4)** | `knowledge_bank_json.gate2_confirmed_at` | `submit_gate2_gap_responses()` — all E3 gaps answered or explicitly skipped; `require_gate2_confirmed()` → 409 `GATE2_NOT_CONFIRMED` |
| **E3 precondition** | — | `require_gate1_confirmed()` before gap agent runs |

**HTTP routes (when `ME_MODULE_ENABLED=true`):**

- `POST /api/reports/donor-reports/{id}/knowledge-bank/gate1/confirm`
- `POST /api/reports/donor-reports/{donor_report_id}/knowledge-bank/gate2/gap-responses`

### Worker / orchestrator

- `app/reports/worker/run_pipeline.py` — **stub only** (job `RUNNING` → `DONE`; no agents).
- No orchestrator; no stage dispatcher wired to `report_jobs`.

### Pytest snapshot (M&E batch, working tree)

- **118 passed, 1 failed** — failure: `tests/test_claude_sdk_env.py::test_classifier_build_agent_options_forwards_key` (D1 migrated to Messages API in uncommitted `classifier.py`; test still expects SDK `options.env`).

---

## 2. Agent engine map

### Working tree (current code)

| Agent | Engine | Evidence |
|-------|--------|----------|
| **D1 classifier** | Anthropic Messages API (uncommitted) | `AsyncAnthropic` + `messages.create` in `classifier.py` |
| **D2 proposal** | Claude Agent SDK | `ClaudeAgentOptions`, `query_fn` / `ResultMessage` in `proposal_extractor.py` |
| **D3 grant-terms** | Claude Agent SDK | Same pattern in `grant_terms_extractor.py` |
| **D4 indicator** | Claude Agent SDK | Same pattern in `indicator_data_extractor.py` |
| **E1 reconciler** | Anthropic Messages API (committed) | `knowledge_bank_reconciler.py` — `AsyncAnthropic.messages.create`, `temperature=0` |
| **E3 gap** | Anthropic Messages API (untracked) | `gap_compliance_agent.py` — same pattern as reconciler |

**At HEAD `5ea7579`:** D1 classifier is still **SDK** in committed tree; API migration is unstaged.

### Reconciler reference pattern (D-migration target)

1. `AsyncAnthropic(timeout=...)` client  
2. `messages.create(..., temperature=0, system=..., messages=[user])`  
3. Instruction-driven JSON (not SDK `output_format` on live path)  
4. `_parse_json_from_text` → Pydantic LLM model → domain validation  
5. `query_fn` test seam (duck-type `structured_output`)  
6. Default model: `ME_RECONCILER_MODEL` → `claude-sonnet-4-6`  
7. Degraded path on timeout (`reconciliation_outcome: "degraded"`)

### Shared SDK substrate (D2–D4 only)

- `app/reports/agents/claude_sdk_env.py` — `merge_claude_subprocess_env()` for CLI subprocess auth  
- **No** shared base class; per-agent copy of `build_agent_options` + `query_fn` loop  

**Migration classification:** **MECHANICAL** (~2–3 days for D2–D4 + test/gate fixes), not structural.

---

## 3. Persistence & JSONB homes

| Data | Column / path |
|------|----------------|
| Knowledge bank (E1 + Gate 1) | `donor_reports.knowledge_bank_json` |
| Gate 1 stamp | `knowledge_bank_json.gate1_confirmed_at` |
| Gap analysis (E3) | `donor_reports.gap_analysis_json` |
| Gap answers (Gate 2) | `knowledge_bank_json.gap_answers[item_key]` |
| Gate 2 stamp | `knowledge_bank_json.gate2_confirmed_at` |
| Section content (F, future) | `donor_reports.content_json` (column exists, no writer) |
| Indicator actuals | `indicator_actuals_json` (D4 does not write per D-036) |

**Gate 2 `gap_answers` shape (extended in-app, no E3 contract change):**

- **Answered:** `disposition: "answered"`, `answer_text`, `provenance.source: "human_confirmed_gap_answer"`, `provenance.excerpt`, `responded_at`  
- **Skipped:** `disposition: "skipped"`, `skip_reason: "not_applicable" | "cannot_provide"`, `responded_at` (never inferred from absence)

**Migrations:**

- `alembic/versions/0014_me_module_tables.py` — core M&E tables  
- `alembic/versions/0015_donor_reports_gap_analysis_json.py` — additive `gap_analysis_json` (untracked at audit)  
- Working tree also adds `gap_analysis_json` to 0014 `create_table` for greenfield parity  

---

## 4. Git / deploy state (audit snapshot)

| Item | Value |
|------|--------|
| Branch | `main` |
| HEAD | `5ea7579` — M&E checkpoint (D1–D4 + worker + 0014) |
| Also local | `7c1a666` — E1 Messages API migration |
| vs origin | Ahead by **2** commits |

**Untracked M&E to keep:** Gate 1/2 routes & services, E3 agent/service/schemas, `app/reports/gap/`, 0015, gate/E3 tests, `tests/fixtures/gap/`.

**Modified tracked:** `classifier.py` (API), `donor_report.py`, `router.py`, `0014`, `knowledge_bank_reconciliation_v1.py`.

**Railway / worker today:**

- Worker stub → **no** agents, **no** CLI required yet.  
- Full extract pipeline (pre-convergence): needs **`claude` CLI + `claude-agent-sdk`** for D2–D4.  
- API path (D1, E1, E3): **`ANTHROPIC_API_KEY`** + HTTPS only.  
- `requirements.txt`: both `claude-agent-sdk>=0.1.59` and `anthropic>=0.42.0`.  
- M&E enabled: `ME_MODULE_ENABLED=true` + `ME_DOCUMENTS_S3_*` + `alembic upgrade head`.

---

## 5. F-readiness (partial — not started)

| Prerequisite | Status |
|--------------|--------|
| Confirmed KB + provenance | Ready in schema/model |
| Gap analysis + Gate 2 | Built (working tree) |
| `report_jobs` stage enums | Defined; **not wired** to worker |
| F1 synthesis agent | **Not built** |
| Report archetype prompts in `app/ai/` | **Not present** — only in template JSON (`ARCH_EXECUTIVE_REVIEW_SUMMARY`, etc.) |
| Proposal humaniser | `app/ai/prompts/proposal.py` (proposal archetypes only) |
| FCDO template JSON | `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` — loadable; **no DB seed** in 0014 |
| DOCX template files | `docx_template_ref` paths — **not found** under `app/reports/templates/` |

**F1 guard (exists, no F1 stub):**

```python
from app.reports.services.gate_preconditions import require_gate2_confirmed
require_gate2_confirmed(report.knowledge_bank_json)
```

---

## 6. Harness & live gates

| Agent | Pytest | Live gate script |
|-------|--------|------------------|
| D1 | `test_classifier_agent.py` | None |
| D2 | `test_proposal_extractor_agent.py` | None |
| D3 | `test_grant_terms_extractor_agent.py` | `scripts/grant_terms_gate.py` |
| D4 | `test_indicator_data_extractor_agent.py` | `scripts/indicator_data_gate.py` |
| E1 | `test_knowledge_bank_reconciler_agent.py` | `scripts/knowledge_bank_reconciler_gate.py` |
| E3 | `test_gap_compliance_agent.py` | None |

---

## 7. Core test failures (non–M&E)

Still failing at audit (do not block M&E unit tests):

- `tests/test_quota_service.py` — 2 failures (API signature drift)  
- `tests/test_auth_account_linking.py` — 2 failures (tuple vs `.id` on user helpers)  

No `app/reports/` imports in those tests.

---

## 8. ME_MODULE_MASTER_MEMORY.md — known stale claims

Do **not** trust the memory file without reconciling to repo:

| Memory says | Repo says |
|-------------|-----------|
| “pre-build, Stage A not drafted” | A–E4 largely coded |
| “No product code written” | Full `app/reports/` tree |
| SDK for all D–G agents | Split: D2–D4 SDK; D1/E1/E3 API; gates no model |
| E1 default `opus` | Code default `claude-sonnet-4-6` |

**Refresh memory from this file + `ME_MODULE_DECISION_LOG.md` (D-035–D-043); add rows for Gate 1, E3, E4 when governance catches up.**

---

## 9. Recommended next steps (informational — not executed in audit)

1. **Commit** Gate 1, E3, E4, 0015, and related tests (single logical checkpoint).  
2. **D-stage engine convergence** — migrate D2–D4 to Messages API (mechanical; reconciler/classifier as template).  
3. **Fix** `test_claude_sdk_env.py` after D1 convergence.  
4. **Refresh** `ME_MODULE_MASTER_MEMORY.md` from this status doc.  
5. **Stage F** — report synthesis prompts + F1 agent; wire worker/orchestrator later (Stage G).

---

*End of status through E4.*
