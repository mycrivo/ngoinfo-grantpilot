# Stage F — Synthesis / Critic / Gate 3 Seam Audit — Ground Truth

**Date:** 2026-06-01  
**Scope:** Read-only inspection of committed code for Stage F prerequisites: claim provenance on `knowledge_bank_json`, `content_json`, worker resume/dispatch at the synthesise checkpoint, Gate 1/2 re-enqueue parity (Gate 3 scaffold), and `donor_reports.status` lifecycle. Canonical context: `M_E_Module/ME_MODULE_MASTER_MEMORY.md` §7.4–7.5, §18 (updated 2026-05-31).  
**Method:** Static inspection of listed modules; no code changes, no pipeline/worker runs, no model calls.

---

## Summary

**No BLOCKER verdicts.** Seam 1 (claim provenance) is **CONSTRAINED**: entries in `knowledge_bank_json.facts{}` carry mandatory document-level provenance (`source_document_id`, `provenance.excerpt`, `coverage`, `source_label`) suitable for tracing to an uploaded document, but human-confirmed gap content lives in a **parallel** `gap_answers{}` map (not in `facts{}`), reconciler `confidence` is **not persisted**, and successful E1 facts do not retain extractor `candidate_id`/`field_path` (only degrade pass-through encodes candidate id in the `fact_key` prefix). A fact-safety critic is **possible** but must read `facts`, `gap_answers`, `conflicts`, and `unreadable_sources` together — not a single unified per-claim record. Seams 2–5 are **CONSTRAINED** or **CLEAR** with explicit gaps: `content_json` has contract shape only (no M&E writer/reader); synthesise/critique stages are enum + pipeline stubs (`_park_synthesise_boundary` re-parks on Gate 2 resume); Gate 3 re-enqueue does not exist; `donor_reports.status` beyond `DRAFT` is **never set** in committed `app/reports/` code (contract-only lifecycle).

---

## Seam 1 — Claim provenance (priority)

### Question

For the knowledge bank Stage E produces (`donor_reports.knowledge_bank_json`): does every fact carry enough provenance to trace it back to either a source document / extractor candidate, or `human_confirmed_gap_answer`? What fields encode source, confidence, coverage, and confirmation? Given a single fact, can a downstream agent determine what it came from?

### Evidence

**Persisted top-level shape** (`envelope_to_knowledge_bank_json` flattens E1 structured output onto the report row):

```1171:1197:app/reports/agents/knowledge_bank_reconciler.py
def envelope_to_knowledge_bank_json(envelope: KnowledgeBankReconciledEnvelope) -> dict:
    structured = envelope.structured
    data = structured.model_dump(mode="json")
    data["reconciliation_version"] = envelope.reconciliation_version
    data["reconciler_agent"] = envelope.reconciler_agent
    data["reconciled_at"] = (
        envelope.reconciled_at.isoformat() if envelope.reconciled_at else None
    )
    ...
    return data
```

**Per-fact schema** (`KnowledgeBankFact` — what E1 persists under `facts[<fact_key>]`):

```27:38:app/reports/schemas/knowledge_bank_reconciliation_v1.py
class KnowledgeBankFact(BaseModel):
    value: Any = None
    unit: str | None = None
    semantic_label: str = Field(min_length=1)
    coverage: FactCoverage = "single_source"
    source_document_id: str = Field(min_length=1)
    source_label: str = Field(min_length=1)
    provenance: KnowledgeProvenance
    interpretation_note: str | None = None
    confirmed: bool = False
    confirmed_at: datetime | None = None
    confirmed_by_user: bool = False
```

**Provenance sub-object** (required `excerpt`; optional locator fields):

```18:24:app/reports/schemas/knowledge_bank_reconciliation_v1.py
class KnowledgeProvenance(BaseModel):
    excerpt: str = Field(min_length=1)
    section_label: str | None = None
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    cell_ref: str | None = None
```

**Coverage enum:** `FactCoverage = Literal["agreed", "single_source"]` (`knowledge_bank_reconciliation_v1.py:15`).

**Confidence:** present on the **LLM parse model only**, not on persisted facts:

```242:246:app/reports/schemas/knowledge_bank_reconciliation_v1.py
class KnowledgeBankReconcilerLLMOutput(BaseModel):
    facts: list[_LLMFact] = Field(default_factory=list)
    ...
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
```

No `confidence` field on `KnowledgeBankFact`; not included in `model_dump` for persisted facts.

**E1 / Gate 1 validation** requires document provenance on every fact (fail-closed):

```171:175:app/reports/schemas/knowledge_bank_reconciliation_v1.py
    for fact_key, fact in output.facts.items():
        if not fact.source_document_id:
            errors.append(f"fact {fact_key!r} missing source_document_id")
        if not fact.provenance or not fact.provenance.excerpt:
            errors.append(f"fact {fact_key!r} missing provenance excerpt")
```

**Successful reconcile mapping** copies reconciler output to `facts[fact.fact_key]` — reconciler-chosen key, not extractor `candidate_id`:

```406:428:app/reports/agents/knowledge_bank_reconciler.py
    for fact in parsed.facts:
        facts[fact.fact_key] = KnowledgeBankFact(
            value=fact.value,
            ...
            source_document_id=fact.source_document_id,
            source_label=fact.source_label,
            provenance=_to_provenance(fact.provenance.model_dump()),
            interpretation_note=fact.interpretation_note,
        )
```

**Extractor candidate id** exists only on the **degrade pass-through** path (`fact_key = f"degraded_pass_through:{candidate.candidate_id}"`):

```60:82:app/reports/reconciliation/degrade_resilience.py
def pass_through_facts_from_candidates(
    bundle: ReconciliationInputBundle,
) -> dict[str, KnowledgeBankFact]:
    ...
        fact_key = f"degraded_pass_through:{candidate.candidate_id}"
        ...
        facts[fact_key] = KnowledgeBankFact(
            ...
            source_document_id=candidate.document_id,
            source_label=candidate.source_label,
            provenance=_provenance_from_candidate(candidate),
            interpretation_note=DEGRADED_PASS_THROUGH_NOTE,
            confirmed=False,
            confirmed_by_user=False,
        )
```

Upstream candidates carry `candidate_id`, `document_id`, `field_path` (`input_builder.py:14–26`) but those paths are **not** copied onto normal E1 facts.

**Human-confirmed gap answers** — separate namespace `gap_answers[item_key]`, **not** entries in `facts{}`:

```7:7:app/reports/gap/gap_answer.py
HUMAN_GAP_ANSWER_SOURCE = "human_confirmed_gap_answer"
```

```75:87:app/reports/services/gate2_gap_answer_service.py
    return {
        "disposition": GAP_ANSWER_DISPOSITION_ANSWERED,
        "answer_text": text,
        ...
        "provenance": {
            "source": HUMAN_GAP_ANSWER_SOURCE,
            "excerpt": text,
        },
        "source_label": HUMAN_GAP_ANSWER_SOURCE,
        "source_document_id": None,
    }
```

E3 treats gap answers as an allowed satisfaction source (`gap_compliance_agent.py:57–59`); prompt KB subset includes `gap_answers` (`gap_compliance_agent.py:177–183`).

**Conflicts** (unresolved at E1) carry per-value provenance in `conflicts[].values[]` (`ConflictValueEntry` — `knowledge_bank_reconciliation_v1.py:41–46`); human may set `resolved_value` / `resolved_at` at Gate 1 (`validate_gate1_knowledge_bank` allows resolutions; E1 forbids them at `validate_e1_knowledge_bank:177–184`).

**Contract synthesis filter** (spec, not enforced in code yet): only `facts[].confirmed = true` and resolved conflicts enter synthesis inputs (`docs/artefacts/me_module/REPORT_INPUTS_FIELD_MAPPING.md:141–142`).

**Recorded fixture example** (FCDO): fact with `source_document_id`, `provenance.excerpt`, optional `cell_ref`, `coverage`, `confirmed: false` — `tests/fixtures/reconciler/recorded/fcdo_bridgelight_recorded_knowledge_bank.json:4–22`.

### Traceability answer (single record)

| Record type | Trace to source document? | Trace to extractor candidate? | Trace to `human_confirmed_gap_answer`? |
|-------------|---------------------------|-------------------------------|----------------------------------------|
| `facts[<key>]` (E1 complete) | **Yes** — `source_document_id` + `provenance` | **No** explicit field; key is reconciler-assigned | **N/A** — not in `facts{}` |
| `facts[degraded_pass_through:<candidate_id>]` | **Yes** — `source_document_id` | **Partial** — `candidate_id` embedded in `fact_key` only | **N/A** |
| `gap_answers[<item_key>]` | **No** (`source_document_id: null`) | **N/A** | **Yes** — `provenance.source == "human_confirmed_gap_answer"` |
| `conflicts[].values[]` | **Yes** per competing value | **No** | **N/A** |

### Verdict: **CONSTRAINED**

Document-backed facts in `facts{}` are traceable to an upload id and text excerpt (and often `cell_ref`). Human-confirmed content is traceable in `gap_answers{}` with explicit human provenance. There is **no** single-fact shape that covers both; **no persisted confidence**; **no extractor `field_path`/`candidate_id`** on successful reconcile facts. Fact-safety critic is **feasible** against this model but must consume multiple KB sub-structures.

### Stage F constraints

- Critic and synthesis must read **`facts` + `gap_answers` + `conflicts` (+ optionally `unreadable_sources`)**, not `facts` alone.
- Treat `interpretation_note` on pass-through facts (`DEGRADED_PASS_THROUGH_NOTE`) and `confirmed: false` as unverified until Gate 1 human confirmation (`REPORT_INPUTS_FIELD_MAPPING.md` confirmed-only rule).
- Do not assume a `confidence` field on persisted KB rows.
- Deep trace to `uploaded_documents.extracted_json` field paths requires joining `source_document_id` + `semantic_label` / excerpt — not stored as a direct pointer on the fact.

---

## Seam 2 — `content_json`

### Question

Current shape/schema of `content_json` on the report record; what writes/reads it today; existing merge precedent for human edits into JSONB (e.g. Gate 2 → `knowledge_bank_json`).

### Evidence

**Column definition:**

```47:49:app/reports/models/donor_report.py
    content_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
```

**Initialization (only M&E writer today):**

```119:123:app/reports/services/donor_report_lifecycle_service.py
        status=DonorReportStatus.DRAFT.value,
        knowledge_bank_json={},
        gap_analysis_json={},
        indicator_actuals_json={},
        content_json={},
```

**Explicit non-writer in E1 service:**

```42:43:app/reports/services/knowledge_bank_reconciliation_service.py
    Does not set gate1_confirmed_at (E2). Does not write content_json or
    indicator_actuals_json. Does not call extractors.
```

**Grep under `app/reports/`:** no other assignments or reads of `content_json` (only model + lifecycle init above).

**HTTP layer:** lifecycle routes return report summary (`status`, template ids) and knowledge bank — **no** route returns or accepts `content_json` (`app/reports/api/routes/lifecycle.py`; Gate 1/2 routes touch `knowledge_bank_json` only).

**Contract shape** (`docs/artefacts/me_module/DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.8): top-level `{ "sections": [...], "generation_summary": {...} }`; each section has `section_key`, `label`, `generation_status`, `content.{text, assumptions, evidence_used}`, `critic_flags[]`, `human_edited`, etc.

**API contract** (specified, not implemented under `app/reports/`): section PATCH at §12.11; Gate 3 completion sets `gate3_confirmed_at` and `status: COMPLETE` (`docs/artefacts/API_CONTRACT.md:1530–1533`).

**Merge precedent — Gate 2 → `knowledge_bank_json.gap_answers`:** shallow merge per `item_key`; clears `gate2_confirmed_at` on partial submit; stamps when all gaps resolved:

```144:162:app/reports/services/gate2_gap_answer_service.py
    kb = dict(report.knowledge_bank_json or {})
    gap_answers = dict(kb.get("gap_answers") or {})
    ...
    for item_key, response in responses.items():
        gap_answers[item_key] = _persisted_answer(response, responded_at=now)
    kb["gap_answers"] = gap_answers
    kb.pop("gate2_confirmed_at", None)
    ...
    if gate2_unlocked:
        kb["gate2_confirmed_at"] = now.isoformat()
    report.knowledge_bank_json = kb
```

**Merge precedent — Gate 1:** full payload overwrite after validation (not merge-by-key):

```74:88:app/reports/services/gate1_confirmation_service.py
    payload = dict(knowledge_bank_json)
    payload.pop("gate1_confirmed_at", None)
    ...
    payload["gate1_confirmed_at"] = confirmed_at.isoformat()
    report.knowledge_bank_json = payload
```

**Core proposal analogue** (outside M&E, same JSONB pattern): regen replaces entire `sections` + `generation_summary` (`app/services/proposal_service.py:586–589`).

### Verdict: **CONSTRAINED**

Column exists with contract schema; M&E code initializes `{}` only. No synthesis/critic/Gate 3 writer or reader. Gate 2 provides the closest **in-module** merge model (map merge + conditional gate stamp); Gate 1 is full-document replace.

### Stage F constraints

- First writer of `donor_reports.content_json` will be Stage F synthesis/critic/Gate 3 paths.
- Section-level human edits at Gate 3 should follow contract §2.8 (`critic_flags`, `generation_status`, `human_edited`) — no existing M&E merge helper to reuse.
- `evidence_used` in contract is the natural hook for synthesis→critic provenance links; nothing populates it today.

---

## Seam 3 — Resume + dispatch

### Question

How the worker re-claims a job at `(awaiting_human, synthesise)`, dispatches the next stage, how stages read KB + gap answers, stage registration in plain-Python dispatch, uniform wrapper contract, and where `synthesise` / `critique` slot in.

### Evidence

**Worker claim:** `claim_next_job` selects `status == queued`, `FOR UPDATE SKIP LOCKED`, flips to `running` (`app/reports/worker/job_runner.py:29–65`).

**Gate 2 re-enqueue** (after full gap resolution): sets same job row `status → queued`, **stage unchanged** (`synthesise`):

```28:56:app/reports/services/gate2_gap_answer_service.py
def re_enqueue_gate2_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.SYNTHESISE.value,
        )
        ...
    )
    job.status = ReportJobStatus.QUEUED.value
```

**Proven test path:** Gate 2 confirm → `QUEUED` + `stage=synthesise` → `run_pipeline` → re-park (`tests/test_orchestrator_gate1.py:609–627`).

**`run_pipeline` entry:** if `status == queued`, set `running` + `started_at`; call `run_orchestrated_walk_sync` (`app/reports/worker/run_pipeline.py:45–57`).

**Orchestrator cursor dispatch** (`run_orchestrated_walk`):

```441:449:app/reports/orchestration/pipeline.py
    stage = job.stage

    if stage == ReportJobStage.GAP.value:
        await _run_gap_stage(session, job, context)
        return

    if stage == ReportJobStage.SYNTHESISE.value:
        _park_synthesise_boundary(session, job)
        return
```

**Gap stage reads KB + Gate 1 stamp; writes `gap_analysis_json`; halts Gate 2:**

```156:194:app/reports/orchestration/pipeline.py
    report = session.get(DonorReport, job.donor_report_id)
    ...
    require_gate1_confirmed(report.knowledge_bank_json)
    ...
    outcome = await dispatch_stage(
        run_gap_compliance(
            knowledge_bank_json=report.knowledge_bank_json,
            template_payload=template_payload,
            ...
        ),
        stage=stage,
    )
    report.gap_analysis_json = envelope_to_gap_analysis_json(result.envelope)
    _halt_gate2(session, job, report, gap_trace=gap_trace)
```

**Synthesise boundary (current Stage F stub):** checks `require_gate2_confirmed`, appends trace, leaves `(awaiting_human, synthesise)`:

```196:223:app/reports/orchestration/pipeline.py
def _park_synthesise_boundary(session: Session, job: ReportJob) -> None:
    ...
    require_gate2_confirmed(report.knowledge_bank_json)
    ...
    job.status = ReportJobStatus.AWAITING_HUMAN.value
    job.stage = ReportJobStage.SYNTHESISE.value
```

**Pre-Gate-2 forward path:** `classify → extract → reconcile → _halt_gate1` (sets `stage=gap`, `awaiting_human`); resume from `gap` runs E3 (`pipeline.py:110–117`, `421–462`).

**Stage enum includes `critique` and `export`; no handlers:**

```38:45:app/reports/models/enums.py
class ReportJobStage(str, enum.Enum):
    CLASSIFY = "classify"
    ...
    SYNTHESISE = "synthesise"
    CRITIQUE = "critique"
    EXPORT = "export"
```

DB CHECK matches (`alembic/versions/0014_me_module_tables.py:33–35`).

**Uniform dispatch wrapper:**

```62:89:app/reports/orchestration/dispatch.py
async def dispatch_stage(coro, *, stage: str, ...) -> DispatchOutcome:
    ...
    except _STOP_ERRORS as exc:
        raise StageFailure(stage, exc.message) from exc
    ...
    degraded = is_degraded_result(result)
    return DispatchOutcome(result=result, degraded=degraded)
```

Contract: success → `DispatchOutcome(result=..., degraded=bool)`; hard failures → `StageFailure` (caught in `run_pipeline.py:58–70`, marks job `failed`).

**`_STOP_ERRORS` today:** classifier, proposal, grant-terms, indicator, reconciler, **not** gap/compliance (`dispatch.py:21–28`). Gap failures still become `StageFailure` via generic `Exception` handler (`dispatch.py:83–84`).

**Gate 2 precondition for synthesis:**

```52:59:app/reports/services/gate_preconditions.py
def require_gate2_confirmed(knowledge_bank_json: dict | None) -> None:
    kb = knowledge_bank_json or {}
    if not kb.get("gate2_confirmed_at"):
        raise DomainError(..., error_code="GATE2_NOT_CONFIRMED", ...)
```

**Pipeline stage order (locked in master memory §7.4):** … Gate 2 → **6 SYNTHESISE** → **7 CRITIQUE** → Gate 3 → **8 EXPORT**.

### Where `synthesise` / `critique` slot in

| Location | Current behavior | Stage F insertion point |
|----------|------------------|-------------------------|
| `run_orchestrated_walk` `stage == synthesise` branch | `_park_synthesise_boundary` only | Replace with `_run_synthesise_stage`; on success `_commit_checkpoint(..., next_stage=critique)` or Gate-3 halt |
| No `stage == critique` branch | — | Add `_run_critique_stage`; halt Gate 3 (likely `stage=export` per cursor convention — see Seam 4) |
| `dispatch_stage` | Used for classify, extract, reconcile, gap | Wire synthesis/critic agent calls similarly |
| `require_gate2_confirmed` | Called only from park stub | Synthesise stage entry must call before writing `content_json` |

### Verdict: **CONSTRAINED**

Resume/re-enqueue through `(awaiting_human, synthesise) → queued → worker` is **implemented and tested**; forward execution **re-parks** at the synthesise boundary. Gap stage demonstrates KB + template read pattern. `critique` stage is enum/DB-only. No `require_gate3_confirmed` in `app/reports/`.

### Stage F constraints

- Replacing `_park_synthesise_boundary` is the mandatory first orchestrator change for F forward walk.
- Synthesis must load `report.knowledge_bank_json` (facts, gap_answers, gates) and template from `FunderReportTemplate` — mirror `_run_gap_stage` assembly (`pipeline.py:165–175`).
- New agent errors should be added to `_STOP_ERRORS` if they should map to clean `StageFailure` messages (gap currently relies on generic wrap).
- Job row stays on **one** `report_jobs` record across gates; worker uses `job_id` from claim (`run_pipeline(job_id)`), not re-query by report id (orchestrator audit issue from 2026-05-30 is **resolved** in current `run_pipeline.py:32`).

---

## Seam 4 — Gate scaffolding parity

### Question

How `re_enqueue_gate1_job` and `re_enqueue_gate2_job` work; gate timestamp stamping; `(awaiting_human, stage=X)` cursor convention; job-find keys; what Gate 3 re-enqueue needs to avoid collision.

### Evidence

**Gate 1 re-enqueue key:**

```22:47:app/reports/services/gate1_confirmation_service.py
def re_enqueue_gate1_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.GAP.value,
        )
        .order_by(ReportJob.started_at.desc().nullslast(), ReportJob.id.desc())
        ...
    )
    job.status = ReportJobStatus.QUEUED.value
```

**Gate 1 timestamp:** strip incoming stamp, validate, set ISO `gate1_confirmed_at`, overwrite KB, then re-enqueue (`gate1_confirmation_service.py:74–90`).

**Gate 2 re-enqueue key:** `(awaiting_human, synthesise)` — `gate2_gap_answer_service.py:33–49`.

**Gate 2 timestamp:** merge answers; **pop** `gate2_confirmed_at` on any partial submit; set only when `_remaining_gaps` empty (`gate2_gap_answer_service.py:151–162`).

**Orchestrator halts (cursor convention):**

| Event | `report_jobs.status` | `report_jobs.stage` | KB stamp |
|-------|----------------------|---------------------|----------|
| After reconcile (Gate 1) | `awaiting_human` | `gap` | (no gate1 stamp until HTTP confirm) |
| After E3 (Gate 2) | `awaiting_human` | `synthesise` | (no gate2 until HTTP gap responses) |
| After Gate 2 resume (F stub) | `awaiting_human` | `synthesise` | `gate2_confirmed_at` set |

Locked narrative: `M_E_Module/ME_MODULE_MASTER_MEMORY.md:155` — Gate 1 guards `(awaiting_human, gap)`; Gate 2 guards `(awaiting_human, synthesise)`.

**Gate 3 schema slot (unused in services/routes):**

```86:88:app/reports/schemas/knowledge_bank_reconciliation_v1.py
    gate3_confirmed_at: datetime | None = None
```

Included in `STRUCTURED_KNOWLEDGE_BANK_KEYS` (`knowledge_bank_reconciliation_v1.py:110–112`). **No** `re_enqueue_gate3_job`, **no** `require_gate3_confirmed`, **no** Gate 3 HTTP route under `app/reports/api/routes/`.

**Collision analysis for Gate 3 re-enqueue:**

| Gate | Find filter `stage` | Collides with |
|------|---------------------|---------------|
| 1 | `gap` | Gate 2/3 — **no** |
| 2 | `synthesise` | Gate 1/3 — **no** |
| 3 (not implemented) | Must differ from `gap` and `synthesise` | Per §7.4 pipeline, post-critique human review precedes export → **likely** `(awaiting_human, export)` if cursor = next stage to run (mirrors Gate 2 parking at `synthesise` before synthesis runs). **`critique` stage as halt cursor would collide with nothing today but is unused.** |

**HTTP routes mounted:** `gate1.py`, `gate2.py` only (`app/reports/router.py` pattern from grep); no gate3 module.

### Verdict: **CONSTRAINED**

Gate 1/2 re-enqueue pattern is clear and proven. Gate 3 has **schema capacity only** (`gate3_confirmed_at`); no re-enqueue function, no orchestrator halt after critique, no timestamp writer. Stage discriminator for Gate 3 job-find **cannot be read from code** — must follow the locked cursor convention when F is built (`export` vs `critique` — see master memory §7.4).

### Stage F constraints

- Gate 3 re-enqueue must use a **unique** `(status=awaiting_human, stage=<X>)` pair; `gap` and `synthesise` are taken.
- Mirror Gate 2 partial-submit behavior if Gate 3 allows incremental section acceptance (API §12.11 implies per-section PATCH — no partial `gate3_confirmed_at` logic exists yet).
- `gate3_confirmed_at` should live on `knowledge_bank_json` (same as gates 1–2), not on `content_json` alone (API §12.11: stamp on KB + `status: COMPLETE`).

---

## Seam 5 — Status lifecycle

### Question

`donor_reports.status` enum, transitions (where each is set), specifically `GENERATING`, `DEGRADED`, and `COMPLETE`.

### Evidence

**Enum definition:**

```4:10:app/reports/models/enums.py
class DonorReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    EXTRACTING = "EXTRACTING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    GENERATING = "GENERATING"
    DEGRADED = "DEGRADED"
    COMPLETE = "COMPLETE"
```

**Committed writers in `app/reports/`:** only `DRAFT` at create:

```119:119:app/reports/services/donor_report_lifecycle_service.py
        status=DonorReportStatus.DRAFT.value,
```

**Grep `app/reports` for status assignments:** no matches for `EXTRACTING`, `AWAITING_REVIEW`, `GENERATING`, `DEGRADED`, or `COMPLETE`.

**Parallel job lifecycle (actively updated):**

| Transition | Where set |
|------------|-----------|
| `queued` → `running` | `job_runner.claim_next_job` / `run_pipeline` (`job_runner.py:54–56`, `run_pipeline.py:45–50`) |
| → `awaiting_human` | `_halt_gate1`, `_halt_gate2`, `_park_synthesise_boundary` (`pipeline.py:116`, `132`, `215`) |
| `awaiting_human` → `queued` | `re_enqueue_gate1_job`, `re_enqueue_gate2_job` |
| → `failed` | `mark_job_failed` (`job_failure.py:50`) |
| `done` | enum exists; **no writer** in orchestrator paths inspected |

**Contract-intended map** (`docs/artefacts/me_module/DB_FIELD_CONTRACT_DONOR_REPORTS.md:71–78`, `ENUM_REGISTRY.md` §5.1):

| Status | Contract meaning |
|--------|------------------|
| `DRAFT` | Created; intake not started |
| `EXTRACTING` | Pipeline pre–Gate 1 |
| `AWAITING_REVIEW` | Halted at human gate |
| `GENERATING` | Synthesis + critic running |
| `DEGRADED` | Partial section success in `content_json` |
| `COMPLETE` | All sections accepted; export ready |

**API contract Gate 3 → COMPLETE:** when all sections accepted, server sets `gate3_confirmed_at` and `status: COMPLETE` (`API_CONTRACT.md:1533`) — **not implemented** in `app/reports/`.

**Partial-success rule (contract):** `DEGRADED` + per-section status in `content_json` (`DB_FIELD_CONTRACT_DONOR_REPORTS.md:80`); proposal core sets `DEGRADED` on partial regen (`proposal_service.py:590`) — **no M&E equivalent**.

### Transition map (as committed)

```
DRAFT  ──(create_donor_report)──►  [no further donor_reports.status transitions in app/reports/]

report_jobs.status (separate enum) — actively driven by orchestrator + gates + worker
```

`EXTRACTING`, `AWAITING_REVIEW`, `GENERATING`, `DEGRADED`, `COMPLETE`: **defined in enum + docs only; no runtime writers in M&E code.**

### Verdict: **CONSTRAINED**

Human-visible report status is **decoupled** from pipeline progress today: UI must infer state from `report_jobs` + KB gate stamps until Stage F implements contract transitions. `GENERATING` / `DEGRADED` / `COMPLETE` are spec-only for donor reports.

### Stage F constraints

- Stage F should define when to flip `donor_reports.status` per contract (likely `GENERATING` during synthesise/critique, `AWAITING_REVIEW` at Gate 3 halt, `DEGRADED`/`COMPLETE` from `content_json` outcomes) — **no existing code to extend**.
- Do not conflate `report_jobs.status` (`awaiting_human`, etc.) with `donor_reports.status` (`AWAITING_REVIEW`, etc.); both exist (`ORCHESTRATOR_SEAM_AUDIT_2026-05-30.md:112` still applies to donor report status).

---

*End of audit. Observation only — no code changes except this report.*
