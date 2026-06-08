# M&E Ingestion Hardening Sprint — Build Instructions (Cursor)

This document is your complete instruction set for this sprint. Follow it exactly. It defines packages **P1–P8**, the rules you operate under, and which packages you may build autonomously versus which require owner approval before you write any code. It is the single source of truth and supersedes any other sprint or backlog document in this repo.

---

## How you operate (applies to every task)

1. **Verify the repo root before doing anything.** A phantom build-artifact stub exists at `…/NGOInfo-Grantpilot/frontend/` containing only `.next/` and `node_modules/` — no `package.json`, no `app/`. **Do not work there.** At the start of every task, state which root you are in and confirm:
   - Backend root: `…/NGOInfo-Grantpilot/` — FastAPI (`app/main.py`, `app/reports/`), its own git toplevel.
   - Frontend root: `…/NGOInfo-Grantpilot/ngoinfo-grantpilot-frontend/` — Next 15 App Router, React 19; `package.json` name is `"frontend"`; `app/` contains `.tsx` sources; separate git toplevel.

2. **Diagnose before you build.** Open every package in **Ask Mode (read-only)**. Produce a findings note with an explicit stop condition before writing any code. Validate at the layer you change.

3. **Anti-bent-ruler.** Assert the *correct* target and change the code to meet it. Never weaken a test, relax an assertion, bump a timeout, or fit an answer key to model output to make a test pass. If a test would have to be weakened to pass, **STOP and report** — that means the design is wrong, not the test.

4. **One package at a time.** Make a scoped commit for that package only, then **STOP** before the next. Do not chain packages.

5. **Tiering — know which rule each package is under:**
   - 🟢 **Green:** plan → diagnose → build → self-verify with tests, autonomously, within the stated scope fence. Stop only at the STOP conditions.
   - 🟠 **Amber:** run the read-only diagnosis and produce a **Plan Mode plan (`.md`)**, then **STOP and wait for owner approval before writing any code.**
   - 🔴 **Owner-triggered (production data):** you **do not execute** any production database mutation or data change. You propose the *exact* operation and **STOP**. The owner runs it. This is absolute for billing, quota, and auth.

6. **No contract or schema change without explicit owner approval.** Any new Alembic migration, response-shape change, or new stable `error_code` must be called out and approved *before* you make it.

7. **You cannot authenticate to the live app.** All end-to-end UI validation and all production data mutation are the owner's. Your responsibility ends at code, automated tests, and a self-verification note. Do not claim a package is validated against production.

8. **Backend is the source of truth** for field names and response shapes; the frontend binds to API shapes (contract §12), not DB internals. Call out frontend ripple for any contract-affecting change.

9. **Write all code as if a second Impact-plan subscriber exists** (the feature is gated by plan, not by a private link).

10. **Context hygiene.** If you detect hallucination or drift in a long session, stop and request a fresh session with a handoff note rather than pushing through.

**Modes & parallelism:** diagnose in Ask Mode; plan in Plan Mode (save the `.md`); build in Agent Mode after approval where required. Use worktrees/parallel agents **only** for the independent packages — **P1, P5, P8, P7**. **P2, P3, P4 are coupled — run them sequentially, never in parallel.** P6 shares the upload surface with P1.

---

## Locked decisions — build to these as facts

- **D5:** Job state (`latest_job_status`) is the source of truth for the report list chip. `donor_reports.status` is a coarse marker only — **do not invest in reconciling it.**
- **D6:** The `REPORT_CREATE` charge fires **exactly once, at the moment a report first reaches `COMPLETE`.** The create-time charge and the existing `REPORT_CREATE_REFUND` logic are **both removed** (this is package P8).
- **D1 — Upload accept/reject matrix per document classification:**
  - `proposal`, `grant_letter`, `mou`: accept `.docx`, `.pdf`, `.txt`
  - `indicator_data`: accept `.xlsx`, `.csv` ONLY (at this stage; **P5** later adds `.docx` tables)
  - `photo`, `deck`, `other`: **accept-not-extract** (locked for P1) — allow at upload door; classify assigns `photo`/`deck` via MIME or `other` via classifier/unreadable fallback; extract skips all three (`_EXTRACT_SKIP_CLASSIFICATIONS`); no data-extraction path. Hard synchronous bounce applies only to genuinely unsupported **data** formats (e.g. indicator lane: not `.xlsx`/`.csv`).
  - Anything else: reject with a specific, actionable message naming the accepted formats for that classification
  - **Rejection is SERVER-SIDE primary**; a client-side check is only a nicety, never the enforcement point.
- **D3 — Worker liveness storage: Route A (NO migration).** Infer liveness from `started_at` plus the per-stage `completed_at` timestamps in `agent_trace_json`; do **NOT** add a heartbeat or `updated_at` column. Route B (a `heartbeat_at` migration) is only revisited later if Route A proves too coarse — **do not build it now.**
- **D4 — Reaped orphan job: FAIL-and-surface, do NOT auto-requeue.** Route reaped jobs through the existing `mark_job_failed` so they behave identically to other failures. No requeue logic — avoids an infinite crash-loop on a deterministic cause.

## Already deployed — do not rebuild

- Failed-state UX: list chip "Generation failed" + "Start over", reading-screen error headline, upload-guard bypass for `failed`+`DRAFT`, and `latest_job_status`/`latest_job_stage` on `GET /api/reports` (contract §12.10). **Live. Do not rebuild.**
- The `REPORT_CREATE_REFUND` on terminal failure. **Live. P8 removes it.**
- **P6 — Document delete/replace:** owner-scoped `GET`/`DELETE /api/reports/{id}/documents`, job-state delete guard, upload UI hydrate + remove. **Live. Do not rebuild.**
- A dead worker leaves jobs stuck in `running` forever — **still occurs; P3 fixes it.**

## Open decisions — NOT provided. Do not guess.

If you reach a package gated on one of these, **STOP and request the value from the owner.** Do not assume a default.

*(None — D1, D3, and D4 are locked above.)*

---

## Packages

### P1 — Fail at the door (upload format gating) · 🟢 Green · independent (pairs with P6) · **unblocked (D1 locked)**

**Objective.** Reject an unsupported upload synchronously at upload time, with a specific actionable instruction, **before** a job is enqueued and **before** any metering — so a bad file never starts a pipeline.

**Diagnosis (Ask Mode).** Trace `POST /api/reports/{id}/documents` → where extension/MIME is recorded on `uploaded_documents` → where (if anywhere) format is validated. Confirm the rejection can land before job-enqueue and before metering. Identify the existing stable-`error_code` convention. Confirm the extractor dispatch's accepted formats per classification (must match D1).

**Scope fence.** Backend upload/validation path only. **Server-side primary** — a client-side check is a bypassable nicety, not the fix. One new stable `error_code` (e.g. `UNSUPPORTED_DOCUMENT_FORMAT`), flagged as the single contract touch. Do not touch the pipeline, worker, quota accounting, or auth.

**Acceptance.** An upload not accepted for its classification (per D1) is rejected synchronously with a clear, actionable, code-keyed message. No job created and no metered slot touched for a rejected upload. Accepted types proceed unchanged. Tests assert the D1 matrix.

**STOP.** If rejection cannot precede job-create/metering without touching quota accounting or the contract beyond a new `error_code` → STOP and surface. If the code's accept matrix disagrees with D1 → STOP and surface.

---

### P2 — Engine survives bad input (per-document isolation + graceful degradation) · 🟠 Amber · coupled with P3, P4

**Objective.** One document's extraction failing must not stall or kill the job. Mark the failed document as a known gap, continue the pipeline on the documents that could be read, and surface the gap at the human review gate and/or as a flagged or blank section in the output. **Never fabricate the missing data.**

**Honor existing infrastructure — do not invent.** The contract already supports degradation: `donor_reports.status` includes `DEGRADED`; `report_jobs.agent_trace_json` carries `extract.degraded_documents`, `classify.degraded_notes`, and per-stage `degraded` flags; the partial-success rule is to persist as `DEGRADED` and never discard completed work. Make the extract stage *honor* this path when a single document's extractor raises — do not build a new degradation mechanism.

**Diagnosis (Ask Mode → Plan Mode `.md`, then STOP for approval).** Trace the extract loop in `app/reports/orchestration/pipeline.py`: when one document's extractor raises (e.g. "Unsupported spreadsheet format: .docx"), does the exception propagate and fail the whole job, or route into `extract.degraded_documents`? Confirm whether the existing `degraded_*` machinery is written on per-document failure. Establish how a degraded extract flows through reconcile/gap/synthesise without cascading into a later failure. Locate exactly where the zero-hallucination guarantee lives. Confirm the charge behaviour under D6 (a DEGRADED report that reaches an acceptable completed state is charged like any completed report).

**Scope fence.** The extract stage's per-document failure handling and propagation to the gate/output. Do **not** change AI prompt quality. Do **not** weaken the zero-hallucination guarantee.

**Acceptance.** A multi-document job with one failed document completes on the rest; the failed document is a recorded gap, not a job-killer. The job reaches a stable coded state (`DEGRADED` or advances to a gate with the gap visible) — never indefinite `running`. Missing data surfaces at the human gate and/or as a flagged/blank section. **Zero fabricated values — assert this explicitly.** Completed work preserved byte-for-byte. Tests assert per-document isolation, degraded propagation, and no-fabrication.

**STOP.** If honoring degradation needs a contract-shape change beyond the existing `degraded_*` fields → STOP for approval. If no-fabrication cannot hold without a prompt-quality change → STOP and report (do not cross into prompt quality).

---

### P3 — Never hang (worker liveness / orphan reaper) · 🟠 Amber · coupled with P2, P4 · **unblocked (D3 Route A + D4 locked)**

**Objective.** A worker process dying mid-job must not leave the job in `running` indefinitely. The worker only claims `queued` jobs (`claim_next_job`, `SKIP LOCKED`), and `ME_WORKER_JOB_TIMEOUT_SECONDS` only fires if the worker thread is alive — so a dead-worker hang is currently unrecoverable.

**Gating pre-check (do first, read-only).** Confirm whether the M&E worker (second Railway service, `python -m app.reports.worker`) is currently running and stays up, and what the evidence (Railway logs, recent `report_jobs` rows) says about whether/why the prior process stopped. **If the worker cannot stay alive, designing a reaper is secondary — surface worker stability first.**

**Diagnosis (Ask Mode → Plan Mode `.md`, then STOP for approval).** Confirm worker liveness and the cause of any prior stop. Per **D3 (Route A — no migration):** infer liveness from `started_at` plus per-stage `completed_at` in `agent_trace_json`; scope the reaper threshold (must not falsely reap a legitimately slow stage). Confirm interaction with the "at most one active job per report" rule (re-enqueue returns `409 ACTIVE_JOB_EXISTS`); reaping a `running` orphan must clear this so the user can retry. **Per D4: route reaped jobs through `mark_job_failed`** — fail-and-surface, no auto-requeue.

**Scope fence.** Worker liveness, orphan detection, and reaper fail-only behaviour (**D4 locked**). **No schema migration** (**D3 Route A locked**). Do not redesign pipeline stages or the gate state machine.

**Acceptance.** A worker death mid-job results in the job reaching `failed` with a clear `error` within a bounded window — never indefinite `running`. After reaping, the user can retry. Per D4: failed-and-surfaced (not auto-requeued). The reaper does not falsely reap a live, legitimately-slow job (threshold accounts for the slowest real stage — assert). Tests assert orphan detection, the failed terminal state, and retry-unblocking.

**STOP.** If the pre-check shows the worker cannot stay up → STOP the reaper build and surface (stability may have to come first). Route B migration → STOP — not in scope. Any requeue design → STOP — D4 forbids it.

---

### P4 — User sees the truth (status legibility — remainder) · 🟠 Amber · coupled with P2, P3

**Objective.** Render the states that occur once P2/P3 make them possible, plus the remaining legibility gaps. (The failed-state surfaces are already live — do not rebuild them.)

**Remaining surfaces.**
- DEGRADED report render — partial-success state with gaps clearly flagged (renders P2's coded state).
- 429 quota-exhausted screen.
- Gate-3 critic-flag UI on the detail/review screen.
- Successful export/download surface.
- Stage-specific failure copy — a `synthesise`/`export` failure must not render the generic reading-failure headline (Reading failed / Drafting failed / Export failed).
- Holding-state routing — `DRAFT` + no job → route to `upload`, never an indefinite "reading" holding screen.
- Legacy-sentinel rows — hide or label legacy `__default__`/sentinel-template reports in the list. (Confirm with the owner whether a given "Draft ready" row is real or a legacy shell before filtering.)
- Upload-enqueue continuity — after enqueue, route to `/reports/{id}/reading`, not back to the list.

**Diagnosis (Ask Mode → Plan Mode `.md`, then STOP for approval).** Identify which of the above are produced by P2/P3 but have no rendered surface. Confirm the `error_code`-keyed copy mechanism and where new states plug in. Confirm no raw backend message, `job.error`, `section_key`, or sentinel reaches the user.

**Scope fence.** Status legibility only. The frontend renders the coded states P2/P3 produce; do not invent pipeline behaviour. No backend change beyond exposing existing states (D5 already fixed the source of truth to job state).

**Acceptance.** Each state above renders a friendly, actionable surface — never a frozen spinner or raw message. List chip and reading screen can never disagree. Tests/checks assert consistency and correct per-state rendering.

**STOP.** Any change that would ripple into the entitlement/quota or gate state machine → STOP and surface.

---

### P5 — Read more formats (extractor coverage) · 🟢 Green · independent (worktree-eligible with P1) · gated on D1

**Objective.** Broaden the extractors so the in-scope structured formats just work, shrinking how often P1's door has to reject. v1 target: `.docx` tables, `.csv`, `.xlsx` for `indicator_data`. Docling (committed) handles layout-aware table extraction.

**Diagnosis (Ask Mode).** Inventory the current extractor dispatch per classification and the formats handled today. Confirm what is available (Docling, openpyxl) and the gap to cover `.docx` tables + `.csv` + `.xlsx` reliably. Confirm the deferral boundary.

**Scope fence.** Coverage breadth for the in-scope structured formats only. As coverage expands, update the D1 matrix (P1) in lockstep so the door stops bouncing now-supported formats. Do not touch worker, quota, auth, or the degradation/liveness logic. **Images-of-tables and binary `.doc` are out of scope** (OCR/conversion, hallucination risk).

**Acceptance.** `.docx` tables, `.csv`, `.xlsx` reliably extracted for `indicator_data` (and any other tabular classification). Extraction remains zero-hallucination: values read, never inferred; unreadable regions become gaps, not guesses. P1 matrix updated. Tests assert correct extraction on representative real-world fixtures, including a messy one.

**STOP.** D1 is locked — update the P1 matrix when P5 expands indicator coverage. If reliable extraction of an in-scope format needs OCR/conversion with hallucination risk → STOP and reclassify as deferred. Any touch to degradation/liveness → out of scope, STOP.

---

### P6 — Document delete / replace · 🟢 Green · pairs with P1 · **deployed — do not rebuild**

**Objective.** Let the owner remove an uploaded document so the user can swap a bad file. "Start over" is live and functional (P6 shipped).

**Diagnosis (Ask Mode).** Trace how `uploaded_documents` rows attach to a report and where the pipeline reads them. Confirm the safe condition to allow delete (report not mid-pipeline). Confirm owner-scoping (404 on others' documents). Identify the upload-UI insertion point for delete/replace.

**Scope fence.** A new owner-scoped `DELETE /api/reports/{id}/documents/{doc_id}` (flagged contract addition) + the upload-UI affordance. Do not touch pipeline behaviour, quota, or auth beyond owner-scoping.

**Acceptance.** An owner can remove a specific uploaded document from a report that is not mid-pipeline; after removal + re-upload of a valid file, re-enqueue produces a clean run. Owner-scoped 404 on others' documents. Tests assert delete, owner-scoping, and the safe-state guard.

**STOP.** If delete cannot be made safe against an in-flight pipeline without touching the job state machine → STOP and surface.

---

### P7 — Report delete (optional hygiene) · 🟢 Green · independent · LOW

**Objective.** Owner-only delete of a report in `DRAFT` or `failed` state only.

**Scope fence.** A new owner-scoped `DELETE /api/reports/{id}` restricted to `DRAFT`/`failed` (flagged contract addition). Not required for the core journey.

**Acceptance.** Owner can delete a `DRAFT`/`failed` report; completed/in-flight reports cannot be deleted; owner-scoped. Tests assert the state restriction and scoping.

---

### P8 — Quota charge-point migration (create → first COMPLETE) · 🟠 Amber + 🔴 owner-triggered reconciliation · independent (worktree-eligible)

**Objective (D6 is locked).** Charge `REPORT_CREATE` **exactly once, at the moment a report first reaches `COMPLETE`.** A report that never completes is never charged. Attempt-count is irrelevant. **Remove** the create-time charge and **remove** the `REPORT_CREATE_REFUND` logic.

**Diagnosis (Ask Mode → Plan Mode `.md`, then STOP for approval).** Map every current call site touching `REPORT_CREATE` (the create-time `record_usage`) and the refund (`mark_job_failed` → `REPORT_CREATE_REFUND`). Identify the exact transition where a report first reaches `COMPLETE` (Gate 3 complete / `status: COMPLETE`) as the new charge point. Confirm an idempotency mechanism so the charge fires exactly once per report, even on re-completion or regeneration (a `version` bump must not re-charge). **Design the cutover order so that no report is double-charged (old create-charge + new complete-charge) and none escapes charge during the transition.** Quantify the current live ledger state (creates, refunds, completed-vs-not) to scope the one-off reconciliation. Confirm **exports remain unmetered** — do **not** touch export metering; if export *enforcement* exists that contradicts "exports unlimited," **surface it as separate drift and do not fix it here.**

**Scope fence.** The `REPORT_CREATE` charge point + removal of the refund + contract §12.8 and decision-log alignment. Do **not** touch export metering, the Impact limit *value*, the entitlements structure beyond charge timing, the pipeline, or auth.

**Acceptance.** A report is charged exactly once, at first `COMPLETE`. A report that never completes is never charged. A report that fails N times then completes is charged once. Re-completion/regeneration does not re-charge. The refund code and the create-time charge are both removed. §12.8 and the decision log reflect the new model. Tests assert: charge-once-at-complete, never-charged-if-never-complete, no-recharge-on-regeneration, idempotency. The cutover cannot double-charge or under-charge during transition.

**STOP / owner-trigger.** Any cutover design risking double-charge or charge-escape → STOP and surface. **The historical ledger reconciliation is owner-triggered:** propose the exact reconciliation operation and **STOP**. **Do not mutate the production ledger.** Any touch to export metering or the limit value → STOP.

---

## Validation (owner's step — not yours)

You cannot authenticate to the live app and cannot run the end-to-end walk. The owner performs that validation. Your responsibility for every package ends at: code, passing automated tests, and a short self-verification note describing what you tested and how. **Do not mark any package "validated"** on the basis of the walk — that is the owner's confirmation, not yours.

---

## Sequence

```
(Owner runs a clean end-to-end walk first — independent of you.)
        │
        ├── P1 (door) 🟢 ─┐   unblocked (D1 locked)
        │   P6 (doc delete) 🟢   deployed — do not rebuild
        ├── P5 (coverage) 🟢 ─┘  P1 + P5 worktree-parallel-eligible
        │
        │   P8 (quota: create→complete) 🟠/🔴   independent; own worktree; plan approved by owner;
        │                                        reconciliation run by owner
        ▼
   P3 (liveness/reaper) 🟠   → owner approves plan → build   (pre-check: is the worker up?)
        │  (coupled)
        ▼
   P2 (degradation) 🟠       → owner approves plan → build
        │  (coupled)
        ▼
   P4 (legibility remainder) 🟠 → owner approves plan → build
        │
        ▼
(Owner runs the deliberately-broken walk as the acceptance gate.)
        │
        └── P7 (report delete) 🟢   opportunistic, low
```

**Conditional:** if the owner's clean walk shows the worker dying on a clean run, the **P3 worker-stability pre-check moves to the front** ahead of everything else.

---

## Per-package execution checklist

1. **Confirm the repo root** (state which; confirm `package.json`/`app/`/git toplevel).
2. **Ask Mode read-only diagnosis** → findings note with an explicit stop condition. If the package is gated on an open decision (D1/D3/D4) and the owner has not provided it → STOP and request it.
3. **🟢 Green:** Plan Mode → Agent Mode build → tests → self-verification note.
   **🟠 Amber:** Plan Mode → save plan `.md` → **STOP for owner approval** → Agent Mode build → tests → self-verification note.
   **🔴 Owner-triggered:** propose the exact production operation → **STOP**; the owner runs it.
4. **Scoped commit** for that package only.
5. **STOP** before the next package.
