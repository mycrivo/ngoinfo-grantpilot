# M&E Module — Cursor Dynamic (Behavioural) Audit — Findings Register

**Date:** 2026-06-08
**Scope:** Donor Report Writer engine (`app/reports/*`), run end-to-end against the live Railway **test** environment (`ngoinfo-grantpilot` backend + `exemplary-encouragement` worker + Postgres).
**Method:** HTTP API walks (test-mode mint, canonical `/api/reports/{id}/*` gate URLs) + read-only DB capture + isolated agent probes. Read-only on the engine — **no fixes**.
**Stance:** Adversarial. The auditor actively tried to break the zero-hallucination moat and the failure paths.

> Harness (audit tooling only, never engine code): `scripts/audit/*`. Evidence artifacts: `docs/artefacts/me_module/audits/dynamic_run/`.

---

## What was actually run (live LLM spend)

| Run | State | Outcome | Evidence |
|-----|-------|---------|----------|
| R1 FCDO | Happy path, classify→export | **COMPLETE**, 6 NGO-synthesizable sections, docx rendered | `walk_fcdo_full_3347590c.json`, `export_3347590c.docx`, `analysis_3347590c.json` |
| R2 NLCF | Generalisation, classify→Gate 2 | Clean: 0 conflicts, 18 gaps | `walk_nlcf_gen_e7fa9bee.json` |
| R3 Degraded | FCDO docx + image-only PDF | **Hard crash at classify** | `walk_degraded_fa81b4e3.json`, `degraded_failed_capture.json` |
| R5 (scoping) | FCDO docx + **text-layer** PDF | **Hard crash at classify** | `walk_pdf_textlayer_f7718831.json` |
| R6 Over-quota | IMPACT quota exhausted | 403 at charge point; no create pre-check | `quota_probe.json` |
| R7 Conflict | FCDO multi-doc | E1 surfaced 1 conflict; Gate 1 **blocked** | `walk_fcdo_full_3347590c.json` (Gate 1 422) |
| R8 Worker death | Reaper decision demo | Terminal reap, no re-queue, no auto-resume | (reaper functions, side-effect-free) |
| Moat F2 | Isolated false-negative probe | F2 catches uncited + tampered specifics | `f2_falseneg_probe.json` |
| Contracts | updated_at / metering / enums | confirmed | `contracts_probe.json` |
| Rubric | per-agent live traces | captured | `rubric_traces.json` |

Total live spend ≈ **$0.5–0.7** (two full Claude extract/reconcile/critique passes, one gpt-5.4 synthesis, F2 probe). Well under the approved ~$8–$20 ceiling — the resume harness and lighter state runs avoided redundant full runs.

---

## Findings register

Severity legend: **TOP** = threatens moat or hard-blocks the core flow · **HIGH** · **MEDIUM** · **LOW/cosmetic**. **AMBER** = moat/quota/auth/contract tier.

### DYN-01 — Every PDF upload hard-crashes the pipeline · **TOP · AMBER (moat/availability)**
- **What it means for the NGO:** If you upload *any* PDF — a scanned award letter, a funder's PDF guidance, a proposal saved as PDF — the whole report build dies with a cryptic error and your readable Word/Excel files are abandoned with it. PDF is one of the most common document formats funders use.
- **Behaviour observed:** Upload of a PDF is *accepted* (`200`, mime `application/pdf`), then the `classify` stage crashes: `libxcb.so.1: cannot open shared object file: No such file or directory`. The whole job → `failed`. Reproduced with **both** an image-only PDF (R3) **and** a freshly generated text-layer PDF (R5) → it is **all PDFs**, not just scans.
- **Blast radius:** In R3 the two perfectly readable `.docx` files were left `classification=None, extraction_status=PENDING` — **one bad input takes down the entire job; no per-document isolation at classify.**
- **Dishonest status:** After the hard failure the `donor_reports.status` stayed **`DRAFT`** — the report looks like a normal editable draft, not a failure. The user gets no honest "this failed" signal.
- **Dimension & cause:** Deployment/runtime — the worker container is missing the `libxcb.so.1` system library that Docling's PDF backend (pypdfium/render path) loads at import. Never caught because the FCDO/NLCF sample sets are all `.docx`/`.xlsx`; PDFs were never exercised end-to-end.
- **Fix cost:** Low for the crash (add the OS lib / proper Docling system deps to the worker image). Medium to add per-document isolation + honest status propagation so one bad doc degrades instead of killing the job.
- **Evidence:** `walk_degraded_fa81b4e3.json`, `degraded_failed_capture.json`, `walk_pdf_textlayer_f7718831.json`.

### DYN-02 — F2 fact-safety critic floods false-positive BLOCKs (verifies citations, not the KB) · **HIGH · AMBER (moat economics)**
- **What it means for the NGO:** On a clean, fully-sourced report the safety critic raised **6 BLOCK flags** — and **all 6 were on content that is genuinely in your confirmed data** (district names from the proposal, OP3.3 figures `0.68`/`0.75` that are real facts, a "sixteen records" count you typed in at Gate 2). To export you must clear every BLOCK. When the critic cries wolf 6 times on correct content, users learn to "accept everything" — which is exactly when a *real* fabrication would sail through.
- **Behaviour observed:** Real run produced 6 BLOCKs; tracing each: `Machinga`/`Mangochi` **are** in the KB (proposal facts); `0.68`/`0.75` **are** `indicators.OP3.3.ar1_actual`/`ar1_milestone_target`; "sixteen" came from a Gate-2 gap answer. Cause: F2 verifies prose only against the section's `evidence_used[]` citations, and the citation-emission/hygiene pipeline drops valid citations → the critic flags correctly-sourced specifics as "no cited source."
- **Isolated F2 probe (dangerous direction):** F2 itself is *accurate against its inputs* — given an uncited fabricated section it **BLOCKed all 4 invented specifics**; given a cited-but-wrong value (5,000 vs 684) it **BLOCKed the mismatch**; the supported control passed. So the weakness is **false positives from the citation feed, not false negatives in F2.**
- **Compounding factor:** see DYN-03 — there is no granular "reject this one flag" surface; acceptance is all-or-nothing via DB.
- **Dimension & cause:** Moat calibration / citation-resolution reliability. Fix cost: Medium — F2 should verify against the full confirmed KB (facts + gap_answers), not just the lossy `evidence_used`; and the evidence emission must stop dropping valid citations.
- **Evidence:** `analysis_3347590c.json` (6 block_flags), `f2_falseneg_probe.json`, district/figure trace in this report's notes.

### DYN-03 — No production API for the synthesis→export tail · **HIGH · AMBER (blocks core flow)**
- **What it means for the NGO:** After answering the Gate-2 questions there is **no API** to (a) run the safety critic, (b) review/accept sections, or (c) accept BLOCK flags. The only mounted report routes are create/upload/job/knowledge-bank/gate1/gap-check/gap-answers/gate2/gate3/export. A report **cannot be driven to a finished document through the API** — the audit had to advance it with direct DB writes (the `_accept_all_sections_for_gate3` test pattern), exactly as the prior gate-run notes did.
- **Behaviour observed:** `app/reports/router.py` mounts only `health, read, lifecycle, export, gate1, gate2, gate3`. `confirm_gate3` requires `critique_completed` + all sections `ACCEPTED` + all BLOCKs `accepted` — none of which any endpoint can set.
- **Dimension & cause:** Missing API surface for the human-review gate (Gate 3). Fix cost: Medium. Until then the moat's "human owns truth at gates" guarantee is only reachable via DB surgery.
- **Evidence:** route enumeration; harness `scripts/audit/_db_drive.py` had to simulate the missing UI.

### DYN-04 — Over-quota is enforced only at the very end; create has no pre-check · **MEDIUM · AMBER (quota)**
- **What it means for the NGO:** An IMPACT user (limit **2 reports/cycle**) can create a 3rd report, upload, run the full pipeline, answer all gates, and spend all the LLM cost — then be rejected **only when the report first reaches COMPLETE** at export. The work and spend are wasted.
- **Behaviour observed:** With quota exhausted, `POST /api/reports` still returns `200 DRAFT` (no pre-check). The charge point `charge_report_on_first_complete → enforce_report_create_quota` raises `ForbiddenError code=QUOTA_EXCEEDED status=403`.
- **Contract drift:** the audit plan/contract expected **429**; the engine returns **403 `QUOTA_EXCEEDED`**. `REPORT_CREATE` is charged **once** at first COMPLETE (verified: exactly one ledger row, idempotency key `report:create:<id>`).
- **Fix cost:** Low–Medium (add a create-time/Gate-aware pre-check + reconcile the documented status code).
- **Evidence:** `quota_probe.json`, `contracts_probe.json`.

### DYN-05 — The "gap wall": NGO is asked for data already in the bank and for funder-side fields · **MEDIUM (engine intelligence)**
- **What it means for the NGO:** On a complete FCDO set the engine raised **46 Gate-2 questions** (NLCF: 18). Most are answerable from data already extracted, are reviewer/funder fields the NGO shouldn't author, or are narrative the system should draft. It feels like the tool ignored the documents you gave it.
- **Resolved with numbers (FCDO, 46 gaps, 74 KB facts):**
  - **24 narrative/judgment** prompts (`overall_progress`, `main_issues`, `new_risks`, `key_recommendations`…) — should be synthesised or human-authored.
  - **11 data-backed-but-asked** (`actual_results`, `output_indicators`, `logframe_milestones`, `forecast_vs_actual_spend`, `financial_delivery`…) — the KB **holds** the matching `indicators.*.ar1_actual` / `financials.lines.*` facts, but the gap matcher uses naive substring token-matching of narrative prompt names against structured fact keys, which structurally cannot match. **→ agent/matching fix, not a parser fix.** (Of these, ~2 — `logframe_row:op2_3`, `op4_2` — are *genuine* missing AR1 actuals: only `proposal_target` present.)
  - **11 funder-side assessment** (`output_scores`, `impact_weightings`, `risk_ratings`, VfM `economy/efficiency/effectiveness/equity`, `vfm_measures`) — see DYN-06.
- **Cause:** Template `required_indicators` are *narrative/assessment content requirements* typed as `"indicator"`; `satisfaction.py` only matches them to facts by substring token overlap. Same pattern reproduced on NLCF (narrative prompts + spend totals), so it is **structural, not FCDO-specific.**
- **Fix cost:** Medium — map narrative requirements to a synthesis-from-facts path and/or semantic (not substring) satisfaction.
- **Evidence:** `analysis_3347590c.json` (`gap_categories`), fact-key vs gap-list dump, `walk_nlcf_gen_e7fa9bee.json`.

### DYN-06 — Template model has no "whose-field"; NGO is asked to author the funder's assessment · **MEDIUM (template model)**
- **What it means for the NGO:** FCDO Annual Reviews reserve **output scoring (A++/A/B/C)** and the **Value-for-Money 4E assessment** for the FCDO reviewer/delivery partner. The engine marks those sections `required` and asks the NGO to write them.
- **Behaviour observed:** All 8 FCDO template sections are `required=true`, including `detailed_output_scoring` (`ARCH_OUTPUT_SCORING_TABLE`) and `value_for_money` (`ARCH_VALUE_FOR_MONEY_4E`); `FUNDER_TEMPLATE_SCHEMA` / `template_requirements._section_visible` encode only `required` + `report_type=='final'` — **no NGO-vs-funder ownership flag.** (NLCF correctly uses `required=false`+conditional for `final_update_only`, so conditional logic exists; whose-field does not.)
- **Fix cost:** Medium (add a first-class `owner: ngo|funder` to the schema; suppress funder-side fields from Gate 2).
- **Evidence:** live template sections dump; the 11 funder-side gaps in DYN-05.

### DYN-07 — Worker death mid-stage loses the in-flight run (no resume, terminal reap, no heartbeat) · **MEDIUM (reliability)**
- **What it means for the NGO:** If the background worker dies while building your report, the job is stuck; when a worker returns it **fails** the job rather than resuming, and all the work/LLM spend so far is lost. Nothing auto-recovers it.
- **Behaviour observed:** `claim_next_job` only claims `status=QUEUED`, so a stuck `RUNNING` job is never re-claimed. The orphan reaper runs **only inside a live worker** (startup + idle cycles) and `mark_job_failed` is **terminal — no re-queue path.** `report_jobs` has **no lease/heartbeat/`updated_at`**. The 3600s wall-clock backstop is a `ThreadPoolExecutor` timeout that dies with the process; only the 7200s reaper remains, and only if a worker is alive. Reaper decision verified: a 3h-silent `running` extract/synthesise job → `should_reap=True` (terminal fail); a healthy 60s job → `False`.
- **Fix cost:** Medium (lease/heartbeat + re-queue-on-reap instead of terminal fail).
- **Evidence:** `orphan_reaper.py`, `job_runner.py`; side-effect-free reaper demonstration.
- *Note:* demonstrated via the reaper's own decision function rather than scaling the shared Railway worker to 0 (which would have killed concurrent audit jobs); the mechanism is identical.

### DYN-08 — `donor_reports.updated_at` never updates after creation · **LOW · AMBER (contract)**
- **What it means:** Any client/cache/sync relying on "last modified" gets the creation time forever, even on a COMPLETE report.
- **Behaviour observed (live):** Report `3347590c` went through KB writes, gap, content, 3 gate confirmations and `status=COMPLETE`, yet `created_at == updated_at` (both `19:45:47`). Model has `server_default now()` but **no `onupdate`**, and services don't set it.
- **Fix cost:** Trivial (`onupdate=func.now()`).
- **Evidence:** `contracts_probe.json`.

### DYN-09 — Export metering (`REPORT_EXPORT`) is never written; export is a GET with no enforcement · **LOW · AMBER (contract)**
- **What it means:** The `report_exports` entitlement always shows 0 used; downloads are unmetered and re-downloadable freely.
- **Behaviour observed (live):** Completed user's ledger holds exactly `{REPORT_CREATE: 1}` and **no `REPORT_EXPORT`**. `GET /api/reports/{id}/export` just streams bytes (no `record_usage`, no 429).
- **Fix cost:** Low (decide whether export is metered; if so, write the ledger row).
- **Evidence:** `contracts_probe.json`, `export.py`.

### DYN-10 — SDK extractors under-report input tokens → broken cost accounting · **CLOSED (P3-3)**
- **What it meant:** The spec requires per-agent token/cost accounting; the D2–D4 Claude-Agent-SDK extractors reported `input_tokens=16` flat from `ResultMessage.usage` (last-turn only), so trace-based cost was unreliable (audit's claude_input summed to 48 = 16×3).
- **Fix (P3-3):** `app/reports/agents/token_usage.py` — `SdkUsageAccumulator` sums `AssistantMessage.usage` across sub-turns; falls back to `ResultMessage.model_usage` then `ResultMessage.usage` with `estimated: true` when multi-turn and sub-turn data absent. D2/D3/D4 traces now carry `estimated` and optional `cost_usd` from `total_cost_usd`.
- **Evidence:** `tests/test_token_usage.py`; recorded fixtures tagged `estimated: true` for legacy 16-token captures.

### DYN-11 — Documented "5 known test failures" are stale: 3 reproduce, 2 now pass · **LOW (test debt)**
- **Reproduced:** `test_auth_account_linking` ×2 (`AttributeError: 'tuple' object has no attribute 'id'`, line 39 — test-harness bug, not engine, and outside M&E), `test_me_module_worker::test_worker_startup_path_registers_mappers_before_claim` (subprocess sqlite `no such table: report_jobs`).
- **Now passing:** `test_gate1_confirm_endpoint_404_when_module_disabled`, `test_outcome_1_concurrent_claim_only_one_wins`.
- **Fix cost:** Low. **Evidence:** pytest run.

### DYN-12 — Positives confirmed under live fire (moat-supporting)
- **E1 surfaces conflicts, never silently merges:** OP3.3 unit conflict (`85` vs `0.75`) surfaced with `resolved_value=null`; **Gate 1 correctly returned 422 and blocked confirmation** until resolved.
- **No numeric hallucination leaked into the rendered docx (happy path):** after normalising formatting, every substantive number in `export_3347590c.docx` traces to a KB fact or a Gate-2 answer (only 2 regex artifacts remained).
- **Charge-once works** (DYN-04); **deterministic E3 is robust** (46 gaps, no LLM, ~2s); **engine generalises to a 2nd funder** (NLCF clean to Gate 2); **D1 classifier enums correct** (`proposal`/`grant_letter`/`indicator_data`).

### DYN-13 — Test-mode mint cannot grant the IMPACT plan · **LOW (test tooling)**
- `POST /api/auth/test-mode/mint` ignores the `plan` field and never writes `user_plans`; minted users default to FREE and 403 on all M&E routes. The audit had to provision `user_plans` directly. Product impact: none; test-harness friction only.

---

## Agent verdict table

| Agent | Build | Input contract | Live job-performance (R1) | Robustness / stability | Moat exposure |
|-------|-------|----------------|---------------------------|------------------------|---------------|
| **D1 Classifier** | Anthropic Messages (haiku) | doc text | 3/3 correct enums (`proposal`,`grant_letter`,`indicator_data`); classify stage ~25s | **Crashes on PDF input (DYN-01)** | Low (labels only) |
| **D2 Proposal extractor** | Claude Agent SDK (haiku) | proposal text | complete, 66.7s, 12.3k out | sub-turn aggregation + `estimated` marker (DYN-10 closed) | Data into KB |
| **D3 Grant-terms extractor** | Claude Agent SDK (haiku) | award text | complete, 60.8s, 11.2k out | as above | Data into KB |
| **D4 Indicator extractor** | Claude Agent SDK (haiku) | xlsx | complete, 99.2s, 18.1k out, 1 attempt | as above | Actuals into KB |
| **E1 Reconciler** | Anthropic Messages (sonnet, 32768 out) | fact candidates | 74 facts, **1 conflict surfaced, not merged** | Robust; Gate 1 blocks unresolved | **Strong (surfaces, never resolves) ✓** |
| **E3 Gap/compliance** | **Deterministic** (no LLM) | KB + template | 46 gaps (FCDO)/18 (NLCF), ~2s | Robust, fail-safe | Over-asks (DYN-05/06) |
| **F1 Synthesis** | OpenAI gpt-5.4 | KB subset + answers | 6/6 NGO-synthesizable sections generated (0 failed), ~4min | Used real facts; citation emission lossy | Drove F2 false-positives (DYN-02) |
| **F2 Fact-safety critic** | Anthropic Messages (sonnet) | section + evidence_used | 6 BLOCK (all false-positive), verified 4/8 | **No false-negatives** in isolation (catches uncited+tampered) | **Mis-calibrated: verifies citations not KB (DYN-02)** |
| **Export** | python-docx | content_json | docx 44.6 KB, status→COMPLETE, charge-once | No metering (DYN-09) | Renders only accepted content |

---

## Moat verdict — per state

| State | Verdict | Basis |
|-------|---------|-------|
| **Happy path (FCDO, R1)** | **PASS at output, FRAGILE in process** | No specific leaked to the docx; every number traceable. But export required clearing 6 BLOCKs that were all false-positives — only luck (the flags were on *sourced* content) kept a leak out; the all-or-nothing accept (DYN-03) + false-positive flood (DYN-02) is a real path to rubber-stamping a future true fabrication. |
| **Generalisation (NLCF, R2)** | **PASS to Gate 2** | Clean reconcile (0 conflicts), gap-check works, no funder-overfit. |
| **Degraded (R3)** | **NOT EXERCISED** | The natural degrade trigger (PDF) **hard-crashes** before the degrade/fence logic engages (DYN-01). Degrade-fencing of `degraded_pass_through:*` in synthesis remains **unverified under live fire**. |
| **Conflict (R7)** | **PASS** | E1 surfaced the OP3.3 conflict; Gate 1 blocked confirmation (DYN-12). |
| **F2 isolated (dangerous direction)** | **PASS** | Catches uncited fabrications and cited-but-wrong values; supported control passes. |

**Bottom line:** the moat's *primitives* are sound (E1 surfaces, F2 detects against its inputs, Gate 1 enforces, no leak this run), but its *system-level reliability* is undermined by a lossy citation feed (DYN-02), a missing review API (DYN-03), and an untested degrade path (DYN-01).

---

## Cross-check note (likely divergences from an independent static read)

A static/code read would likely **over-state** safety and **mis-state** a few facts; the dynamic run corrects them:
1. **PDFs (DYN-01):** static read sees `application/pdf` accepted by upload validation and assumes PDFs work. **They hard-crash** — only a live run reveals it (sample sets hid it).
2. **F2 "catches hallucinations" (DYN-02):** static read sees a strict cardinal-fact prompt and concludes the critic protects the moat. Live, **6/6 BLOCKs were false positives** on sourced content because F2 checks `evidence_used`, not the KB. The risk inverts to alert-fatigue.
3. **Over-quota status code (DYN-04):** docs say **429**; the code raises **403 `QUOTA_EXCEEDED`**.
4. **Known test debt (DYN-11):** "5 failures" is stale — **3 reproduce, 2 pass**.
5. **Gate-3 completability (DYN-03):** a static read of `confirm_gate3` assumes a UI sets sections ACCEPTED; **no such endpoint exists** — only DB writes complete a report.
6. **Synthesis "invents specifics":** a static read of the BLOCK flags would conclude F1 hallucinated district names/counts; tracing shows those values **are in the KB / gap answers** — the fault is citation emission, not invention.

---

## Fences honoured
Read-only on the engine; no engine/schema/contract code changed. Harness/probes under `scripts/audit/` are tooling only. Minimal DB writes were limited to test-data setup (provisioning `user_plans`, resolving a Gate-1 conflict as the human would, the accept-all that substitutes for the missing Gate-3 UI, and synthetic quota ledger rows) on the disposable test dataset. Frontend was out of scope (noted: the gap-check redirect-loop fix is live and working — `GET /gap-check` returned 200 with 46/18 items). **No remediation performed — STOP.**
