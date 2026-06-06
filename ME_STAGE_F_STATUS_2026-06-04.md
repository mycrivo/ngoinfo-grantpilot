# Stage F Status — Synthesis (F1), Fact-Safety Critic (F2), Gate 3

**Date:** 2026-06-04  
**Method:** Read-only — live code under `app/reports/`, F diagnostic artefacts, synced contracts (`DB_FIELD_CONTRACT_DONOR_REPORTS.md`, `ME_MODULE_MASTER_MEMORY.md`), F-related tests. No pipeline runs, no edits elsewhere.  
**Code tip:** `origin/main` at `55d1673` (docs-only); Stage F runtime unchanged since **`d19b9de`** (F1 claim-granular emission, 2026-06-01).

---

## Verdict

Stage F is **built and orchestrator-wired end-to-end through Gate 3 halt**, but **not quality-gate-ready**. F1 synthesis writes `content_json`, runs claim-granular emission plus C1/C2 hygiene, and parks at the critique boundary; F2 critic runs on worker re-claim and halts at `(awaiting_human, export)`; Gate 3 confirm/re-enqueue exists but **section acceptance has no HTTP route** and **export (Stage H) is a stub**. The last recorded prod walk on deploy **`d19b9de`** achieved **8/9 planted conflicts caught**, **0 dangerous unflagged prose**, and **18 citation-resolution BLOCKs** (down from 21 on `9b430a1`) — residual binding gaps dominate, not critic false positives. Two named diagnostic artefacts (`F1_CITATION_BINDING_DIAGNOSIS*`, `R0_KB_CONSUMER_SEAM_AUDIT*`) **were not found** in the repo; `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` partially substitutes but is **stale** on wiring (written when synthesise/critique were stubs).

---

## 1. What exists and wiring state

| Component | Location | Orchestrator | Status |
|-----------|----------|--------------|--------|
| **F1 synthesis** | `app/reports/services/report_synthesis_service.py`, `app/reports/ai/prompts/synthesis.py`, `app/reports/services/synthesis_citation_emission.py` (d19b9de), `app/reports/services/synthesis_output_hygiene.py` (9b430a1), `app/reports/services/report_inputs_builder.py` | `_run_synthesise_stage` in `app/reports/orchestration/pipeline.py` | **Built + wired** |
| **F2 critic** | `app/reports/agents/fact_safety_critic.py`, `app/reports/services/report_fact_safety_service.py`, `app/reports/schemas/fact_safety_critic_v1.py` | `_run_critique_stage` → `_halt_gate3` | **Built + wired** |
| **Gate 3** | `app/reports/services/gate3_confirmation_service.py`, `app/reports/api/routes/gate3.py` (confirm only), `require_gate3_confirmed` in `gate_preconditions.py` | Post-critique halt at `stage=export`; `confirm_gate3` → `re_enqueue_gate3_job` → `_run_export_stage` stub | **Partial** — confirm path only; no section PATCH API |
| **Export (Stage H)** | `_run_export_stage` in `pipeline.py` | Marks job `done`; no docx export | **Stub** |

### Orchestrator flow (live code)

```
Gate 2 confirm → job (queued, synthesise)
  → _run_synthesise_stage → content_json written → park (awaiting_human, critique)
  → worker re-claim → _run_critique_stage → critic_flags → halt Gate 3 (awaiting_human, export)
  → HTTP confirm_gate3 (all BLOCKs accepted, all sections ACCEPTED) → gate3_confirmed_at → re-queue (export)
  → _run_export_stage stub → job done
```

**What triggers F:** `gate2_confirmed_at` on `knowledge_bank_json` plus Gate 2 re-enqueue (`gate2_gap_answer_service.re_enqueue_gate2_job` finds `(awaiting_human, synthesise)`). Worker `run_orchestrated_walk` dispatches `_run_synthesise_stage` when `job.stage == synthesise` and status is `queued`/`running`. **Source:** live code (`pipeline.py`, `gate_preconditions.py`, `gate2_gap_answer_service.py`).

**Preconditions:** F1/F2 call `require_gate2_confirmed` only; they do **not** read `gap_analysis_json`. **Source:** live code.

**Tests proving wiring:** `tests/test_orchestrator_synthesis.py`, `tests/test_orchestrator_critique.py` (mocked synthesis/critic query fns). **Source:** live code + tests.

---

## 2. Citation BLOCK state (last recorded — no fresh run)

| Metric | Value | Source | Deploy / report |
|--------|------:|--------|-----------------|
| **Citation-resolution BLOCKs** | **18** | `FCDO_PLANTED_CONFLICT_POST_F1_WALK_b91ae3e0.json` → `f1_hygiene_audit.citation_resolution_block_count` | **`d19b9de`**, report `b91ae3e0-92fb-430d-9feb-1dcd9b878b70` |
| Total critic BLOCKs | 19 | Same artifact → `total_critic_blocks` | Same |
| Prior citation-resolution BLOCKs | 21 | `F1_BLOCK_DECOMPOSITION_6643d922.md` + walk `6643d922` | **`9b430a1`**, report `6643d922` |
| Pre-hygiene baseline (~) | 55 | Walk artifacts → `prior_walk_citation_resolution_blocks_approx` | Recorded in walk JSON |
| `evidence_used` bindings | 306 (vs 182 prior) | Prod walk summary in transcript; walk JSON hygiene section | **`d19b9de`** vs **`9b430a1`** |

**Stated root cause (recorded, not re-derived):** On **`9b430a1`**, decomposition classified **16/21 BLOCKs as bucket C (backfill miss)** — admissible `facts{}` or `gap_answers{}` existed but were **not bound in `evidence_used[]`**, so the critic correctly BLOCKed specifics. **3/21 bucket B** (derived aggregates, wrong report window) are **intended** critic behaviour. **2/21 bucket A** (malformed keys, e.g. space after `fact:`). **Source:** `F1_BLOCK_DECOMPOSITION_6643d922.md` (2026-06-01). Code at **`d19b9de`** added `emit_claim_granular_evidence()` to address C themes before C1/C2; prod walk shows **−3 BLOCKs** but no post-`d19b9de` decomposition doc exists.

**Note:** `b91ae3e0.json` precondition field still shows `github_main_sha_prefix: cd15e37` (stale metadata); walk was executed against deploy **`d19b9de`** per session record. **Source:** artifact + transcript.

---

## 3. KB consumption seam (how F1/F2 read the knowledge bank)

### Live behaviour

| Step | Mechanism | Namespace binding |
|------|-----------|-------------------|
| **Input assembly** | `build_knowledge_bank_inputs()` → `facts{}`, answered `gap_answers{}`, resolved `conflicts` | Keys are **whatever E1 reconciler persisted** — no separate enum |
| **Prompt** | `build_synthesis_user_prompt()` embeds KB subset; system prompt forbids inventing keys | Instructs `fact:financials.lines.*`, `gap:{item_key}`, exact key shape |
| **F1 emission pass** | `emit_claim_granular_evidence()` before hygiene | Binds only keys **present in** `facts{}` / `gap_answers{}` dicts; can **passthrough** unknown keys for C1 to drop |
| **F1 hygiene (C1/C2)** | `sanitize_generated_content()` / `sanitize_evidence_used()` / `enrich_evidence_from_kb()` | Allowlist = KB dict keys; near-miss repair, drop nonexistent, auto-backfill |
| **F2 critic** | `resolve_cited_sources(evidence_used, facts, gap_answers)` then LLM verify | Only `fact:` / `gap:` refs in `evidence_used[]`; values from KB maps |

F1/F2 **do not read** `gap_analysis_json`. Gap answers consumed at F are **`knowledge_bank_json.gap_answers`** (merged at Gate 2). **Source:** live code.

### Recorded seam audit (partial substitute)

`F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` (Seam 1) concluded KB is **CONSTRAINED**: facts trace to documents; human gap content lives in parallel `gap_answers{}`; no persisted confidence; critic must read **facts + gap_answers + conflicts**. **Still matches live F2** (`report_fact_safety_service.py` lines 113–115, 139–142). **Source:** prior doc + live code cross-check.

**Code moved since that audit:** Seam 2–4 items marked “stub / no writer” are **now implemented** (content_json writer, `_run_synthesise_stage`, `_run_critique_stage`, Gate 3 confirm/re-enqueue). **Source:** compare audit §Seam 2–4 vs current `pipeline.py`.

### Missing artefact

**`R0_KB_CONSUMER_SEAM_AUDIT*`** — **not found** anywhere in repo (`docs/`, root, `M_E_Module/`). KB seam summary above is from **live code** + **`F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` Seam 1** only.

---

## 4. Test grounding

| Test file | KB namespace asserted | Matches prod reconciler? |
|-----------|----------------------|---------------------------|
| `tests/test_synthesis_citation_emission.py` | `BRIDGELIGHT_*` with `.y1_actual` / `.y1_budget`, `financials.lines.op*`, gap `section:indicator:*` keys | **Mostly yes** — aligns with prod walk keys in `F1_BLOCK_DECOMPOSITION_6643d922.md` |
| `tests/test_synthesis_output_hygiene.py` | `KB_FACTS` uses `.ar1_actual` / `.ar1_target`, `fcdo.summary.overall_progress` | **No** — fictional shorthand; recorded fixture uses `.actual`/`.target` (`fcdo_bridgelight_recorded_knowledge_bank.json`) |
| `tests/orchestrator_mocks.py` (`fcdo_synthesis_query_fn`) | Emits `fact:fcdo.summary.overall_progress` | **No** — not a reconciler-produced key |
| `tests/test_fact_safety_critic_agent.py` | `fact:indicators.OP1.1.actual` | **No** — shape differs from prod (`.y1_actual` or `.actual`) |
| `tests/test_orchestrator_synthesis.py` / `test_orchestrator_critique.py` | Full pipeline with mocked LLM; no live KB namespace assertion | Orchestration only |

**Finding:** Unit tests for emission use **prod-like BridgeLight keys**; hygiene and orchestrator mocks use **fixture/fictional namespaces** that the running reconciler does not produce. Tests can pass while prod walks still hit citation BLOCKs on real key shapes. **Source:** live tests + recorded fixture grep.

---

## 5. Contract-sync impact (2026-06-04, `55d1673`)

| Synced contract change | F1/F2 impact |
|------------------------|--------------|
| `gap_analysis_json` flattened (no nested `structured`) | **None** — F stages never read `gap_analysis_json`; Gate 2 intake uses it via `require_gap_analysis` only |
| `knowledge_bank_json` shape (`facts`, `gap_answers`, gate stamps) | **Aligned** — F reads same fields the contract documents |
| Gap answers merged into `knowledge_bank_json` at Gate 2 | **Already assumed** — `build_knowledge_bank_inputs` and F2 `_answered_gap_answers` filter answered entries |
| `agent_trace_json` → `stages{}` (not `runs[]`) | **No F input impact** — trace is observability only |

**No finding** of F code assuming a KB or gap shape that today's synced contracts contradict. **Source:** live F code + `DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.6, §2.9 (read only, not edited).

---

## 6. Gap to Stage F quality gate

**Quality gate definition (from master memory):** Funder-grade report on hand-confirmed data, zero hallucinated specifics, critic catches deliberately planted errors.

### Needs code / product work

| Gap | Evidence |
|-----|----------|
| **18 residual citation-resolution BLOCKs** on last prod walk | Walk JSON `b91ae3e0`; decomposition logic in `F1_BLOCK_DECOMPOSITION_6643d922.md` still applicable pattern-wise |
| **1/9 planted conflict not caught** (same on `9b430a1` and `d19b9de`) | Walk JSON planted-conflict section |
| **Gate 3 section review API missing** — no `content_json` GET/PATCH under `app/reports/api/` | Grep: zero matches; tests mutate DB directly (`_accept_all_sections_for_gate3`) |
| **`donor_reports.status` never leaves `DRAFT`** | Only set at create (`donor_report_lifecycle_service.py`); contract `GENERATING`/`COMPLETE` unimplemented |
| **Export stage stub** | `_run_export_stage` → `export_boundary_not_implemented` |
| **E3 gap-agent JSON flake** blocks walks without retry loop | Session record; out of F scope but blocks golden validation |

### Needs golden fixture / deliberate test run (not code fix alone)

| Item | Why |
|------|-----|
| **Post-`d19b9de` block decomposition** for `b91ae3e0` | Quantify which of 18 BLOCKs are A/B/C after emission pass |
| **End-to-end Gate 3 UX path** on real content | Confirm human can accept sections + BLOCKs via API (route does not exist yet) |
| **Full quality-gate sign-off** | Requires stable prod walk on golden FCDO set with hand-confirmed KB, not unit mocks |

---

## 7. Most likely next action (what the code implies)

Run a **read-only block decomposition on report `b91ae3e0`** (same method as `F1_BLOCK_DECOMPOSITION_6643d922.md`) against the **`d19b9de` walk artifact and prod DB snapshot**, to classify the **18** remaining citation BLOCKs before any further F1 binding changes — the emission pass reduced count by 3 but **no dated decomposition exists** for the current deploy, so the next binding fix target is unverified.

---

## Diagnostic artefact inventory

| Pattern | Found | Date | Code moved since? |
|---------|-------|------|-------------------|
| `F1_BLOCK_DECOMPOSITION*` | `F1_BLOCK_DECOMPOSITION_6643d922.md` | 2026-06-01 | **Yes** — predates `d19b9de` `emit_claim_granular_evidence` |
| `F1_CITATION_BINDING_DIAGNOSIS*` | **Not found** | — | — |
| `R0_KB_CONSUMER_SEAM_AUDIT*` | **Not found** | — | — |
| `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT*` | `F_SYNTHESIS_CRITIC_GATE3_SEAM_AUDIT_2026-06-01.md` | 2026-06-01 | **Yes** — Seams 2–4 stale (F now wired); Seam 1 still valid |

---

## Source attribution (major claims)

| Claim | Source |
|-------|--------|
| F1/F2/Gate3 wired in orchestrator | **Live code** — `pipeline.py` |
| Park at critique after synthesis; Gate 3 halt at export | **Live code** — `pipeline.py` |
| 18 citation-resolution BLOCKs | **Prior doc/run** — `FCDO_PLANTED_CONFLICT_POST_F1_WALK_b91ae3e0.json` |
| 21 BLOCKs / A-B-C decomposition | **Prior doc** — `F1_BLOCK_DECOMPOSITION_6643d922.md` |
| KB dual namespace (facts + gap_answers) | **Prior doc (Seam 1)** + **live code** confirm |
| F ignores gap_analysis_json | **Live code** |
| Test namespace drift | **Live code** — tests + recorded fixture |
| Contract sync no F impact | **Live code** + synced contract read |
| Missing R0 / CITATION_BINDING artefacts | **Repo search** — zero files |

---

*Read-only status pass. Single deliverable. No code, test, contract, schema, or DB changes.*
