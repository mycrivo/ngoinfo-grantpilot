# M&E Module — State Reconciliation (read-only)

**Date:** 2026-07-05
**Author:** Claude Code (read-only memory-refresh audit)
**Repo state at audit:** branch `claude/me-module-state-audit-kwteok` @ `5014348`; GitHub `main` @ `5014348`
**Sources of truth consulted:** `ME_MODULE_DECISION_LOG.md`, `audits/ME_MODULE_KB_STARVATION_DIAGNOSIS_2026-06-14.md`, `audits/P3_9_SYNTHESIS_RELIABILITY_DIAGNOSIS.md`, git history + GitHub API, merged code, `.github/workflows/smoke-test.yml`

> Scope: factual reconciliation of what was planned vs. what actually shipped/merged, and what remains open. No quality audit, no new findings, no recommendations, no code changes.

---

## 1. Where the module actually stands (60-second orientation)

Every remediation package from the KB-starvation cluster and the preceding Phase-3 work is **built, tested, and merged to `main`** — including **Package B, which is finished, not mid-build**. On GitHub, `main`'s tip is `5014348` ("Packages B, C, D…", 2026-07-05), which sits directly on top of Package A (`79b7b89`); all of C.1, Package 1, Package 2, Package A, and the KB-cluster C/D are in the linear history below it, and every package's proving tests are wired onto the CI "P0 M&E" smoke allowlist. The engine work is effectively complete **with one exception**: the **A-JSON synthesis JSON-parse freeze fix was never started** (deliberately deferred — the code still does a bare `json.loads` with no repair/retry), and it remains the last open reliability blocker. Beyond that, what's left is **not builder work**: the owner-triggered live template re-seed and the consolidated end-to-end re-walk on both funders are still pending, plus a short list of logged post-launch polish. Net: the code is landed; the module is gated on the A-JSON fix (build) and the owner's live validation (walk).

> **Merge-state caveat:** a purely local `git log origin/main..HEAD` will falsely show `5014348` as "unmerged" because this container's `origin/main` tracking ref is one fetch stale (`79b7b89`). The GitHub API (`main` = `5014348`) is authoritative: it is merged.

---

## 2. Package-by-package status

| Package | Status | Evidence |
|---|---|---|
| **P3-7** — synthesis prose + export fidelity, honesty gates, KB table render | **Merged** | `d78a628`, `b7d8447`, `a3c396b`; re-walk `1beb588b` (FCDO completed); on `main` |
| **P3-8** — forbidden-ref reclassification + `insufficient_data` empty-section policy | **Merged** | `d15c97c`; on `main` |
| **P3-9** — synthesis reliability diagnosis | **Merged (read-only doc; no engine change by design)** | `893672c`; `audits/P3_9_SYNTHESIS_RELIABILITY_DIAGNOSIS.md` |
| **Package D — gap-check 500 fix** (P3-9 Cluster D `NameError`) | **Merged** | `a5e5256`; `GapCheckMissingItemResponse` now imported at `gap_check_service.py:15`; `tests/test_gap_check_routes.py` on CI allowlist |
| **Package C.1** — sparse-section routing → honest `insufficient_data` preflight | **Merged** | `e475c7b` (fix) + `9531d2f`/`ca1e57d` (evidence); `tests/test_section_insufficiency.py` on allowlist; owner re-walk `d8e7518b` = **completed** |
| **Package 1** — NGO identifier redaction chokepoint + export tripwire | **Merged** | `91bdc3a`; `app/reports/services/ngo_text_redaction.py` added; `tests/test_export_identifier_leak.py` on allowlist; live re-walk `bc8fa94` |
| **Package 2** — template-driven funder table rendering | **Merged** | `92442a5`; `kb_table_renderer.py` rewritten (hardcoded `FCDO_LOGFRAME_OPS` deleted, dispatch on real `indicators.*`/`financials.*` namespaces); `tests/test_funder_table_rendering.py` on allowlist; live re-walk `bc8fa94`. *Also the fix path for P3-9 Cluster B (logframe key mismatch) — renderer now consumes real `.actual` facts.* |
| **Package A** — section-scoped visibility + remit-scoped caveats | **Merged** (was the prior `main` tip) | `79b7b89`; `app/reports/services/remit_disclosure.py` added; NLCF template JSON updated with `source_section_labels`/`fact_namespaces`; `tests/test_section_visibility.py` (16 tests) on allowlist |
| **Package C** (KB-cluster) — demographic disaggregation promotion | **Merged** | part of `5014348`; `input_builder._flatten_indicator_data` promotes `disaggregation` bands; `tests/test_disaggregation_promotion.py` on allowlist |
| **Package D** (KB-cluster) — clean budget-identity cells + widened leak tripwire (PL-a/PL-b) | **Merged** | part of `5014348`; `_strip_facet_prefix` + widened `_LEAK_PATTERNS`; `tests/test_export_identifier_leak.py` + `test_funder_table_rendering.py` extended |
| **Package B** — capture partners + consultation + monitoring notes *(highest-priority reconciliation point)* | **Merged — built, 16 tests, NOT mid-build** | `5014348`; `ExtractedPartner`/`ExtractedEngagement` on `proposal_extraction_v1`, `note` on `ExtractedIndicatorRow`; `tests/test_proposal_content_capture.py` (7) + `tests/test_monitoring_notes_capture.py` (9) on allowlist |

**Disambiguation:** there are **two "Package D"s** — the Phase-3 **gap-check 500 fix** (`a5e5256`) and the KB-cluster **render-label + tripwire** work (in `5014348`). Both are merged.

---

## 3. Open-items ledger (priority order)

### A. Build items still open

1. **A-JSON / synthesis JSON-parse freeze fix — NOT STARTED (confirmed still open).** `report_synthesis_service._extract_json_payload` (line 110) is still a bare `json.loads(content)` with no repair, no re-prompt, no partial-claim fallback; a malformed/truncated JSON body still fails the section terminally and freezes Gate-3 accept-all. Explicitly deferred in the C.1 decision ("A-JSON untouched… JSON-parse FAILED stays FAILED") and confirmed unfixed by P3-9 §A.4. This was flagged as the last reliability blocker and remains it. *(Note: the related A-MODEL refusal path was mitigated by C.1's preflight routing; the A-JSON parse path itself was not.)*
2. **No other build items open** — every other cluster package is merged.

### B. Owner-triggered items (no builder closes these)

3. **Live NLCF (+FCDO) template re-seed — PENDING.** Package A's shipped `TEMPLATE_INSTANCE_NLCF.json` adds `source_section_labels`/`fact_namespaces`; the live template DB copies must be re-seeded to match the shipped JSON before routing behaves as built. (FCDO template was deliberately left on the archetype fallback by Package A.)
4. **Consolidated owner re-walk on both funders — PENDING.** Named as "the real gate" in the STOP notes of Packages A, C+D, and B ("consolidated re-walk after B"). No post-B live re-walk evidence is committed; the only live walks on record are Package 1+2 (`bc8fa94`) and the C.1 NLCF walk (`d8e7518b`), both pre-B.

### C. Logged-but-deferred polish (post-launch, non-blocking)

5. **C.2 phrasing** — whether programme-level `objectives.*` facts alone should unlock narrative sections (self-contradiction follow-up). Logged as "C.2 candidate," not built.
6. **budget-vs-actual typing parity** — "Typing parity queued: `budget_vs_actual` table vs indicator typing not enforced in pin gate until follow-up" (NLCF regression-pin decision, 2026-06-11).
7. **FCDO output/outcome table split** — deliberately not implemented in Package 2 ("revisit only if FCDO reviewers require the split"; splitting would invent an undeclared indicator-type classification).
8. **Red-font gap-review treatment** — listed as deferred polish, but **not found anywhere in the repo** (see drift flag 4).

---

## 4. Drift flags

1. **The two named "source of truth" plan files do not exist.** There is no `kb_starvation_remediation` consolidated plan and no `ME_ENGINE_REMEDIATION_MASTER_PLAN` in the repo. The consolidated remediation record is actually **distributed** across `ME_MODULE_DECISION_LOG.md` (the as-shipped package spine), `audits/ME_MODULE_KB_STARVATION_DIAGNOSIS_2026-06-14.md` (the six losses / four fault-classes), and `audits/P3_9_SYNTHESIS_RELIABILITY_DIAGNOSIS.md` (Clusters A–D).
2. **Local `origin/main` is stale vs live `main`.** The container's tracking ref points at `79b7b89` (Package A) while GitHub `main` is at `5014348` (Packages B/C/D). Local git commands will misreport B/C/D as unmerged; they are on remote `main`. A `git fetch` reconciles this.
3. **The Package B decision-log STOP note is now stale.** It reads "owner audit before push," but B was subsequently committed and pushed to `main` (`5014348`). The log entry was not updated after the push — the only place the record lags reality.
4. **"Red-font gap-review treatment" has no repo footprint.** The string appears nowhere in the M&E documents. It was either never captured in-repo or lived only in the missing consolidated plan — unverifiable against the code.
5. **No false-done and no undocumented code found (otherwise clean).** Every merged commit maps to a decision-log entry, and every decision-log "shipped" claim is backed by code + an allowlisted test. Notably, the log does **not** falsely claim the A-JSON fix — it correctly records "A-JSON untouched." The older governance docs (`ME_MODULE_PROJECT_PLAN.md`, `ME_MODULE_MASTER_MEMORY.md`) are Stage A–L project plans that predate this cluster and do not track the remediation packages — stale for remediation purposes, but not contradicting the code.

---

*Read-only reconciliation. No engine changes made or proposed.*
