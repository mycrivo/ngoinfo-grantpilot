# M&E F1 synthesis — resume seam diagnosis (2026-06-04)

**Scope:** Read-only static analysis. No code changes, no runs, no mutation of report `6643d922`.

**Question:** Is F1 synthesis atomic (regenerate all 8, overwrite wholesale), so successful sections are discarded on every retry? Where is the smallest seam to make it resumable?

---

## Verdict (plain language)

**Yes — atomic full overwrite is confirmed in code.** Every call to `synthesise_and_persist` builds a fresh 8-section list from the **template only**, generates **all** of them concurrently, assembles a **new** `content_json` object, and **replaces** `donor_reports.content_json` in a **single commit at the end**. There is no read of prior `GENERATED` sections, no merge helper, and no per-section DB write. A re-run **discards** previously good section prose and re-rolls every section (including ones that succeeded on the prior pass).

This matches the observed prod behaviour across three full runs on `6643d922`: failures rotated across sections (C/D → E → A/B) while other sections were regenerated each time rather than preserved.

---

## 1. Section selection (worklist)

**Always the full template list — never skips existing `GENERATED` sections.**

Entry point loads sections exclusively from `FunderReportTemplate.report_sections_json`:

```333:338:app/reports/services/report_synthesis_service.py
    sections = _visible_sections(template.report_sections_json or [])
    if not sections:
        raise ReportSynthesisServiceError(
            "STOP_NO_SECTIONS",
            "Template has no report sections",
        )
```

`_visible_sections` only filters invalid dicts / missing keys; it does **not** consult `report.content_json`:

```226:234:app/reports/services/report_synthesis_service.py
def _visible_sections(sections: list[Any]) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    for item in sections or []:
        if not isinstance(item, dict):
            continue
        if not item.get("section_key"):
            continue
        visible.append(item)
    return visible
```

The thread-pool worklist is **every** template section — one future per section, no skip logic:

```262:272:app/reports/services/report_synthesis_service.py
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                _generate_one_section,
                section=section,
                report_inputs=inputs_by_key[str(section["section_key"])],
                query_fn_synthesis=query_fn_synthesis,
                user_id=user_id,
            ): section
            for section in sections
        }
```

**Conclusion:** Worklist = all 8 FCDO sections, every run. Zero resume/filter today.

---

## 2. Persistence model (overwrite vs merge)

### End-of-run single blob write (not incremental)

After all futures complete, results are ordered and passed to `assemble_content_json`, which builds a **brand-new** top-level object (sections + generation_summary only — no `export` key):

```105:120:app/reports/schemas/content_json_v1.py
def assemble_content_json(
    sections: list[dict[str, Any]],
    *,
    warnings: list[str],
) -> dict[str, Any]:
    generated = sum(1 for s in sections if s.get("generation_status") == "GENERATED")
    failed = sum(1 for s in sections if s.get("generation_status") == "FAILED")
    return {
        "sections": sections,
        "generation_summary": build_generation_summary(
            total_sections=len(sections),
            generated=generated,
            failed=failed,
            warnings=warnings,
        ),
    }
```

Persistence is one assignment + one commit — explicit overwrite docstring:

```307:353:app/reports/services/report_synthesis_service.py
async def synthesise_and_persist(
    ...
) -> ReportSynthesisStageResult:
    """Generate all template sections and overwrite donor_reports.content_json."""
    ...
    content_json = assemble_content_json(ordered, warnings=warnings)
    report.content_json = content_json
    db.add(report)
    db.commit()
```

There is **no** merge with prior `report.content_json`, **no** preservation of top-level keys such as `export` (added later by `report_export_service`), and **no** per-section commit inside the `as_completed` loop (results accumulate in `results_by_key` in memory only).

### Does a re-run discard good sections?

**Yes.** The unit test `test_idempotent_overwrite` encodes this as intentional behaviour: a second `synthesise_and_persist` replaces all section text (e.g. summary prefixed with `UPDATED `).

**Corroboration from prod runs (artefacts, not live DB reads):**

| Run | Artefact | Generated | Failed sections |
|-----|----------|-----------|-----------------|
| 1 | Gate run / original F1 | 6/8 | C, D (timeout) |
| 2 | `F1_RERUN_6643d922.json` | 7/8 | E (timeout) |
| 3 | `M_E_Module/gate_run/full_run_stage1.json` | 6/8 | A (502), B (timeout) |

Run 3 regenerated C, D, E (all `GENERATED` with fresh text lengths) even though C/D had succeeded on run 1 and E had failed on run 2 — consistent with full re-roll, not merge.

### Contract vs implementation gap

`DB_FIELD_CONTRACT_DONOR_REPORTS.md` §2.4–2.5 states:

> **Partial-success rule:** If some sections succeed and others fail, persist as `DEGRADED` with per-section status in `content_json` — **never discard completed sections.**

Within a **single** run, failed and generated sections coexist in the written blob (partial per-section status is persisted). On a **subsequent** run, completed sections **are** discarded by full overwrite. `synthesise_and_persist` also does **not** set `donor_reports.status = DEGRADED` on partial failure (only `ReportSynthesisStageResult.degraded=True` is returned; report row status is untouched until export).

---

## 3. Failure handling (within one run)

Per-section failures do **not** abort the batch.

`_generate_one_section` catches errors and returns a failed-shaped dict (or `build_failed_section` adds label/constraints):

```144:165:app/reports/services/report_synthesis_service.py
    except OpenAIServiceError as exc:
        ...
        return {
            "section_key": section_key,
            "generation_status": "FAILED",
            "failure_reason": exc.category,
        }
```

Failed sections get empty text via `build_failed_section`:

```57:75:app/reports/schemas/content_json_v1.py
    return {
        ...
        "generation_status": "FAILED",
        ...
        "content": {
            "text": "",
            ...
        },
        "failure_reason": failure_reason,
        ...
    }
```

Other futures continue; warnings list records failed keys; `degraded = failed > 0`:

```296:302:app/reports/services/report_synthesis_service.py
    for section in sections:
        key = str(section["section_key"])
        ordered.append(results_by_key[key])
        if results_by_key[key].get("generation_status") == "FAILED":
            warnings.append(f"section {key} failed")
```

```367:372:app/reports/services/report_synthesis_service.py
    return ReportSynthesisStageResult(
        ...
        degraded=failed > 0,
        warnings=warnings,
    )
```

**Orchestrator:** `_run_synthesise_stage` always calls full `synthesise_and_persist`, records `degraded` in trace, and **still parks at critique** — no abort on partial failure:

```390:415:app/reports/orchestration/pipeline.py
        outcome = await dispatch_stage(
            synthesise_and_persist(
                session,
                job.donor_report_id,
                query_fn_synthesis=ctx.query_fn_synthesis,
            ),
            stage=stage,
        )
    ...
    synthesise_trace = {
        ...
        "degraded": result.degraded,
        ...
    }
    ...
    _park_critique_boundary(session, job)
```

**Conclusion:** Intra-run partial success is represented in `content_json.sections[]` and `generation_summary`, but the stage completes and advances to critique regardless. Re-entry at synthesise (via Gate 2 re-enqueue) would invoke the same full overwrite path — no “retry failed only” branch exists.

---

## 4. Proposal-side precedent (GP-P02)

**File:** `app/services/proposal_service.py`

**Pattern (one paragraph):** Initial proposal creation calls `_generate_sections`, which runs a bounded concurrent batch via `ThreadPoolExecutor`, collects per-item `GENERATED` / `FAILED` / `MANUAL_REQUIRED` / `NEEDS_USER_INPUT` outcomes into a single `sections` list, and persists **once** with `proposal.status = "DEGRADED"` when `summary["failed"] > 0` (otherwise `DRAFT`) — partial success is kept in one atomic write, not discarded mid-run. Explicit regeneration (`regenerate_proposal` → `_regenerate_sections`) walks **existing** sections but **re-generates every generatable section** (only `MANUAL_REQUIRED` and `NEEDS_USER_INPUT` are copied forward unchanged); it does **not** skip sections already `GENERATED`. So the precedent is **persist-what-worked within a single pass + DEGRADED status**, not **resume-only-failed on retry**. M&E synthesis matches the single-pass shape but lacks DEGRADED report status and lacks any preserve-on-retry logic.

---

## 5. Recommended resume seam (described, not implemented)

### Smallest viable change (merge at end, skip-if-done worklist)

| Step | Location | Change |
|------|----------|--------|
| **A. Worklist filter** | `synthesise_and_persist` (before `_generate_all_sections`) | Load `existing = sections_by_key(report.content_json.get("sections") or [])`. Build `to_generate` = template sections where existing is missing, `generation_status == "FAILED"`, or `content.text` empty — **exclude** `ACCEPTED`, `human_edited == True`, and optionally `AWAITING_REVIEW` with non-empty text + critic_flags. |
| **B. Partial generation** | `_generate_all_sections` | Accept `sections` subset only (already supports arbitrary list length). |
| **C. Merge** | New helper in `content_json_v1.py` e.g. `merge_synthesis_sections(existing_sections, template_order, new_results_by_key)` | Walk template order; for each key use `new_results_by_key[key]` if present else keep `existing[key]`. Recompute `generation_summary` from merged list. Preserve top-level keys outside `sections` / `generation_summary` (e.g. `export`) if present. |
| **D. Persist** | `synthesise_and_persist` | Replace `assemble_content_json(ordered)` with merge helper; optionally set `report.status = DEGRADED` when `failed > 0` per contract. |

**Decision point:** `synthesise_and_persist` lines 333–353 — split “select worklist” from “merge + commit”.

### Optional stronger seam (persist each section as it completes)

Hook inside `_generate_all_sections` `as_completed` loop (lines 273–294): after each `results_by_key[section_key] = result`, merge into DB. **Obstacle:** `Session` is not thread-safe; worker threads must not share the request `Session`. Options: (1) marshal commits back to main thread via queue; (2) open a new `Session` per completion with row-level lock on `donor_report_id`. This is **medium** complexity vs **small** for merge-at-end-only.

---

## 6. Safety edges (for build — not solved here)

### ACCEPTED / human_edited — must never clobber

- `build_generated_section` sets `human_edited: False` on every fresh generation.
- Gate 3 requires all sections `ACCEPTED` (`gate3_confirmation_service._sections_pending_review`).
- Resume filter **must** treat `generation_status in ("ACCEPTED",)` and `human_edited is True` as **immutable** — copy forward without API call.
- Re-running synthesis after Gate 3 accept-all (validation pattern) already overwrote accepted sections with fresh `GENERATED` — resume logic would fix that class of regression.

### Orchestrator stage cursor

- Normal path: Gate 2 confirm → job `(queued, synthesise)` → worker `_run_synthesise_stage` → `(awaiting_human, critique)`.
- Manual re-synthesis (scripts) bypasses worker and can leave job at `critique/awaiting_human` with stale `agent_trace_json.stages.critique.action = parked_at_critique_boundary`.
- Resume-only-failed still fits `_run_synthesise_stage` if worklist filter lives inside `synthesise_and_persist`; no stage regression required. Re-entering from `export` or `COMPLETE` would need explicit job rewind (not built today).

### Concurrent-write / double-generation idempotency

- With concurrency=2, two **retry** invocations on the same report could race if both read the same FAILED set before either commits — risk of duplicate OpenAI spend for the same section key.
- Mitigation for build: job-level `queued/running` lock (already on worker), or DB advisory lock for synthesis start, or single-flight guard in `synthesise_and_persist`.

### F2 / critic_flags on preserved sections

- Preserved `GENERATED` sections retain prior `critic_flags` until F2 re-run.
- Re-synthesis of a previously FAILED section should clear `critic_flags` for that section (fresh `build_generated_section` sets `critic_flags: []`).
- Merge must not wipe critic data on skipped sections.

### Top-level `content_json.export`

- `assemble_content_json` drops `export`; a full re-synthesis today removes export metadata until re-export. Merge-at-end should preserve sibling keys.

---

## 7. Section status fields (system already knows outcomes)

Per contract §2.8 and builders in `content_json_v1.py`:

| Field | Success | Failure |
|-------|---------|---------|
| `generation_status` | `GENERATED` | `FAILED` |
| `failure_reason` | `null` | e.g. `timeout`, `server_error`, `INSUFFICIENT_INPUT` |
| `content.text` | non-empty prose | `""` |
| Post-F2 | `AWAITING_REVIEW` if flagged | — |
| Post-Gate 3 | `ACCEPTED` | — |

These fields are sufficient to drive a skip-if-done worklist; they are written today but **not read** on synthesis re-entry.

---

## One-line summary

**atomic-overwrite confirmed=yes**, resume seam is **`synthesise_and_persist` + `_generate_all_sections` (worklist filter + `content_json_v1.merge_synthesis_sections`)**, build size **small** (merge-at-end + skip-if-done) or **medium** (+ per-section incremental commit + session threading).
