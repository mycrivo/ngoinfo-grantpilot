# P0 — Layer 5 uncalibrated demotion and regression proofs: independent review

**Branch:** `engine/p0-harness`
**Review target:** `f1ff2e20eb48d1301d87a1e4d0a23cee5565d43e` (`f1ff2e2`)
**Comparison base:** `f27b51ce7f4e1ad69500202f0fff9de1c15b254e` (`f27b51c`) — reachable; `f27b51c` is a direct parent of `f1ff2e2`
**Diff scope:** one commit, nine files
**Tier:** certification-adjacent, owner-triggered, read-only
**Date:** 2026-08-08
**Method:** read-only. No repository file outside this artefact was modified. Verification was mechanical (AST extraction, blob-hash comparison, live execution of the pack loader and test suite in a detached worktree at `f1ff2e2`).

---

## STOP conditions

Four were specified. Three did not trigger. One did.

| Condition | Result |
|---|---|
| Any detector pattern, predicate, routing or identifier list differs | **Not triggered** — all identical (Q2) |
| Content checksum has moved | **Not triggered** — unchanged and self-consistent at both revisions (Q1) |
| Any layer payload digest has moved | **Not triggered** — L1/L2/L3/L4/L5 all unchanged (Q1) |
| An exception list survives in any form | **TRIGGERED** — see S-1 |

### S-1 — STOP: the exception list survives in the pack generator

`scripts/audit/_tmp_build_golden_v11_layer4.py` is unchanged by this commit (blob identical at both revisions) and still contains the complete six-entry exception list:

- **line 576:** `"l5_self_check_allowlist": [` — followed by all six `{id, rationale}` objects for FB-04, FB-05, FB-06, FB-09, FB-13, FB-14, byte-for-byte the list deleted from the manifest.
- **line 575 (comment):** `# while forbidding them. Unexpected hits outside this allowlist fail pack load.`
- **lines 366–369:** the script also emits, into `RECONCILIATION_V11_LAYER4.md`, the pre-demotion narrative: *"These hits are **allowlisted** in `manifest.l5_self_check_allowlist` … Pack load fails on any hit outside the allowlist, and on stale allowlist entries that no longer hit."*

This script writes `manifest.json` (line 621–622: `(OUT / "manifest.json").write_text(...)`) and `RECONCILIATION_V11_LAYER4.md` (line 391). Its manifest dict contains **no** `l5_deterministic_arm` key — grep for `l5_deterministic_arm|uncalibrated|gates_ignored` across the file returns zero hits.

Consequence, stated precisely: **running this script reverts the entire policy change.** It would restore the six-entry exception list to the manifest, delete the `l5_deterministic_arm` declaration (status, gates, fail_on_load, statement, reversion_condition), and overwrite the reconciliation text with the superseded "pack load fails" narrative — with no guard, no warning, and no decision-log entry.

Scope of the risk, stated fairly:
- The script is **not** wired into CI or any hook (`git grep 'scripts/audit' -- .github/ .githooks/ .cursor/ .claude/` returns only `full_walk.py`, `phase1_signoff_gate.py`, `b1_rollback_execute.py`, `offline_replay.py`).
- The **live** load path is clean: the loader ignores any allowlist, and the shipped manifest carries none.
- So this is a latent regeneration path, not an active gating path. It does not weaken the demotion as shipped. It does mean the deletion is not durable: the artefact that produces the manifest still encodes the deleted policy, and D-080's instruction "do not reintroduce an exception list" is contradicted by a script in the tree that reintroduces it on execution.

The package's own evidence document notes these `_tmp_` build scripts exist (`P0_PR14_INDEPENDENT_REVIEW_2026-07-28.md:218`) but does not identify that one of them carries the exception list.

No other surviving exception list was found. A full sweep for `allowlist|allow_list|allow_ids|whitelist|exception_list|exempt|waiver|suppress` across the tree, and for any `{id, rationale}` structure keyed by FB identifiers, returns nothing else. The pack's six JSON files contain zero `"rationale"` keys. The remaining `l5_self_check_allowlist` mentions are historical prose (decision log, prior review, reconciliation note recording the deletion) and two test assertions proving its absence.

---

## Q1 — Nothing in the answer key moved

**Confirmed. Nothing moved.**

Checksum recomputed from the shipped fixtures at each revision using the `f1ff2e2` algorithm (`compute_pack_checksum`, sha256 over canonical JSON: sorted keys, `ensure_ascii=False`, separators `(",",":")`).

| | `f27b51c` | `f1ff2e2` |
|---|---|---|
| `manifest.content_checksum` | `185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79` | *(identical)* |
| Recomputed from fixtures | `185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79` | *(identical)* |
| Declared == recomputed | yes | yes |
| `dataset_version` | `1.1` | `1.1` |

Both revisions are internally self-consistent, and the value is unchanged between them.

**Layer payload digests** (sha256 over canonical JSON of each layer file; raw-byte blob hashes were also compared and are likewise identical):

| Layer | File | `f27b51c` | `f1ff2e2` | |
|---|---|---|---|---|
| 1 | `facts.json` | `deaf3dd11006e4f2…` | `deaf3dd11006e4f2…` | unchanged |
| 2 | `conflicts.json` | `5f3b428c61ffe511…` | `5f3b428c61ffe511…` | unchanged |
| 3 | `gaps.json` | `fcd0c98207ac0204…` | `fcd0c98207ac0204…` | unchanged |
| 4 | `report_reference.json` | `401ed48f92199f29…` | `401ed48f92199f29…` | unchanged |
| 5 | `forbidden.json` | `95340e824deec32c…` | `95340e824deec32c…` | unchanged |

**Layer 4 reference content** — inner digests, unchanged at both revisions:

- `full_markdown` sha256 = `72c6c91d94a70393aa2979324f85b5971f91e6a0549b6a8cc7782399693bda6c`
- `prose_rubric_reference` sha256 = `ba5cac5e557bf621c0268ece9464a9e15a0f3bc89c3f421de21f7e7f43d00e72`
- `sections_present` canonical digest = `d65c855f66dadad6…`
- `reference_prose_conforms_to_v4` = `true`; `judge_calibrated` = `false`

---

## Q2 — No detector was touched

**Confirmed. No detector pattern, predicate, corpus-routing rule or identifier list differs — including whitespace and comments, except two docstring/comment additions recorded below.**

**Every location detectors appear.** 39 files across the tree contain FB identifiers or `re.compile`. Blob-hash comparison at both revisions: **34 identical**, 5 changed (`golden_pack.py`, `l5_assertions.py`, `manifest.json`, `README.md`, `RECONCILIATION_V11_LAYER4.md`), plus the test file. Every other detector-bearing module — including `l3_assertions.py`, `l4_assertions.py`, `matching.py`, `faithfulness_check.py`, `docx_export_assertions.py`, the agents, the hooks, `blocklist.json`, `forbidden.json` — is byte-identical.

**AST-level extraction** from the two changed modules at both revisions:

| Artefact | `l5_assertions.py` | `golden_pack.py` |
|---|---|---|
| All `re.compile` / `re.search` / `re.findall` literals (source order) | IDENTICAL | IDENTICAL |
| `_DETERMINISTIC_PATTERNS` table | IDENTICAL | — |
| `_DET_PATTERNS` table | — | IDENTICAL |
| String collections (routing sets, identifier lists) | IDENTICAL | IDENTICAL |
| FB identifier constants | IDENTICAL | IDENTICAL |
| Integer constants (heuristic thresholds, slice bounds) | IDENTICAL | IDENTICAL |
| `_corpus`, `_questions_corpus` | IDENTICAL | — |

**`evaluate_layer5`** — the one function whose body changed. Normalising the AST by replacing every `AssertionResult(...)` call with a bare marker yields **byte-identical source at both revisions**. Every branch test, every loop, every predicate and every assignment is unchanged; the differences live entirely inside `AssertionResult(...)` constructor arguments. Specifically unchanged: the `det_hit` pattern loop, the `qcorpus if fid in {"FB-14","FB-15"} else corpus` routing, the starvation family split, and the FB-05 predicates (`mentions_op23`, `mentions_op42`, `disclosed`, `det_omission`).

The only predicate-inventory delta is one ternary — `verdict = Verdict.FAIL if det_hit else Verdict.PASS` — which is the verdict selector itself, inside the constructor, removed because the verdict is now unconditionally `ADVISORY`. That is the demotion, not a detector change.

**`golden_pack.py`:**
- `scan_reference_against_forbidden` — **docstring-only change**. With docstrings stripped, byte-identical.
- `_DET_PATTERNS` — one comment line added (`# D-080: arm is uncalibrated; patterns must not be edited in builder packages.`). Table itself untouched.
- `load_golden_pack` — allowlist plumbing removed, replaced by a direct call to the unchanged scanner. Docstring added.
- `validate_l5_reference_self_check` — **deleted entirely** (the function that raised).

**Judged arm.** The `elif method == "judged":` block is **byte-identical** at both revisions, comments included: same `re.findall(r"[A-Za-z]{5,}", ...)`, same `keywords[:8]`, same `>= 3` threshold, same `Verdict.REVIEW_REQUIRED if heuristic else Verdict.PASS`, same `AssertionClass.INVARIANT`. Verified live: `test_l5_judged_never_auto_clears_moat_on_heuristic` passes, FB-10 returns REVIEW-REQUIRED. The dual-method judged fallback (`keywords[:6]`, `>= 4`) is likewise unchanged.

---

## Q3 — The demotion is real; the exception list is gone from the live path

### The self-check still executes, still records, and cannot fail the load

Verified by execution against the shipped pack at `f1ff2e2`:

```
load_golden_pack()                 -> SUCCEEDED (no raise)
l5_reference_self_hits recorded    -> ['FB-04','FB-05','FB-06','FB-09','FB-13','FB-14']  (6)
module exports validate_l5_reference_self_check ? NO — function deleted
```

**Adversarial probe.** A copy of the pack whose `full_markdown` was replaced with synthetic text engineered to trip **all ten** deterministic detectors was loaded with `verify_l5_self_check=True`:

```
hits recorded = ['FB-01','FB-02','FB-04','FB-05','FB-06','FB-09','FB-13','FB-14','FB-15','FB-18']
load          -> SUCCEEDED (no raise)
```

Fail-on-load is genuinely suspended: the maximal adverse observation does not fail the load. There is no remaining code path from an observation to an exception — the only `raise` in `load_golden_pack` is the checksum branch.

**Control.** Fail-closed power elsewhere in the loader is intact: the same mutated pack loaded with `verify_checksum=True` raises `ValueError: Golden pack checksum mismatch: …`. The suspension is scoped to the L5 self-check and did not weaken checksum verification.

### Where the six observations are recorded, and their legibility

| Site | Form | Legible to a person reading the pack? |
|---|---|---|
| `GoldenPack.l5_reference_self_hits` | in-memory tuple, populated on every load | **No** — runtime only; not persisted, not printed, not written to any file |
| `RECONCILIATION_V11_LAYER4.md:46` | static prose: *"Observed at v1.1 authorship: FB-04, FB-05, FB-06, FB-09, FB-13, FB-14."* | **Yes** — the only human-readable record |
| `manifest.l5_deterministic_arm` | policy block; carries `detectors_found_non_discriminating: true` | **No** — does not enumerate the six IDs |
| `tests/test_p0_assertion_library.py:50` | asserted set of six | Yes, but as a test fixture, not pack documentation |

Three observations on legibility:

1. The six IDs survive in exactly **one** pack-facing document, as a static snapshot ("Observed at v1.1 authorship"). It is not regenerated from the live scan, so it can silently drift from what the loader actually records.
2. The prior text named **which pattern fired** for each ID (e.g. `'FB-04:1[, ]?184[, ]?000'`, `'FB-13:life[- ]of[- ]programme|burn\s*rate|remaining budget'`). That detail is gone. A reader can no longer tell from the pack which regex produced which observation.
3. The six per-ID rationales — the reasoning that each hit was an honest disclosure rather than a forbidden claim — were deleted with the list and are **not preserved anywhere in the pack, manifest, or code**. They survive only in the stale generator script (S-1) and in the prior review document. This is defensible under D-080's logic (the rationales were the suppression mechanism), but it means the diagnostic reasoning is no longer available to whoever eventually calibrates these detectors.

### The manifest states both conditions

`tests/fixtures/golden/fcdo_bridgelight_ar1_v1/manifest.json`, key `l5_deterministic_arm`, replacing `l5_self_check_allowlist` (top-level key count unchanged at 21; this is a one-for-one substitution):

```json
"l5_deterministic_arm": {
  "status": "uncalibrated",
  "gates": false,
  "self_check": "runs_and_records",
  "fail_on_load": "suspended",
  "detectors_found_non_discriminating": true
}
```

**Uncalibrated condition, quoted verbatim:**

> "The Layer 5 deterministic arm is uncalibrated and gates nothing. Pack-load self-check runs against the pack's own reference text and records every observation; it does not fail the load on any observation. No exception list is carried."

**Reversion condition, quoted verbatim:**

> "Restore fail-on-load only when owner/CTO has authored and calibrated the detectors, recorded by a decision-log entry naming that calibration. Until then do not reintroduce an exception list. See D-080."

Both are mirrored in `README.md`, `RECONCILIATION_V11_LAYER4.md`, and the `load_golden_pack` docstring.

### The demotion gates nothing — structurally verified

`gate_verdict` (`run_assertions.py`, **unchanged by this commit**) excludes ADVISORY from `gate_pass`, collects it under `advisory_ignored_by_gate`, and `counts_as_demonstrated_safety` (`verdicts.py`, also unchanged) requires `verdict == PASS and assertion_class == INVARIANT` — which `ADVISORY`/`ADVISORY` fails on both conjuncts. The demotion reuses pre-existing, already-proven machinery rather than introducing new gate logic. That is the right shape.

---

## Q4 — The new proofs

| # | Acceptance criterion | Test | What it asserts | Verdict |
|---|---|---|---|---|
| 1 | Checksum stability | `test_pinned_content_checksum_and_layer_payload_digests`; also `test_golden_pack_loads_and_checksum_matches` | `pack.content_checksum == PINNED_CONTENT_CHECKSUM` and that `compute_pack_checksum` over the loaded fixtures recomputes to the same pinned constant | **Covered, passes** |
| 2 | Payload digest pinning | same test (second half) | raw `sha256` of `facts/conflicts/gaps/forbidden.json` equals four pinned constants | **Covered but RED** — see F-1 |
| 3 | Gate-verdict stability under inverted prose-conformance flag, all five layers + summary | `test_reference_prose_conforms_to_v4_cannot_affect_any_layer_or_gate` | `run_all_layers` verdict map identical before/after inversion, and all six `gate_verdict` summary keys identical | **Covered, passes — genuinely widened** |
| 4 | Fail-closed when calibration flag absent | `test_missing_judge_calibrated_flag_is_fail_closed` | with `judge_calibrated` popped, `pack.judge_calibrated is False` | **Covered, passes — narrow, see F-3** |
| 5 | `uncalibrated` / `gates_ignored` markers on deterministic arm | `test_l5_deterministic_arm_markers_and_excluded_from_demonstrated_safety`; `test_l5_dual_deterministic_arm_is_advisory_when_uncalibrated` | class and verdict are `ADVISORY`, both metrics `True`, id present in `advisory_ignored_by_gate` and absent from `blocking_failures` | **Covered for 2 of 3 emission sites — see F-2** |
| 6 | Exclusion from demonstrated-safety counts | both tests above, via `assert not r.counts_as_demonstrated_safety` | ADVISORY results never count as demonstrated safety | **Covered, passes** |

Full run at `f1ff2e2`: **16 passed, 1 failed.**

### F-1 — The payload-digest pin is red on every LF checkout

`test_pinned_content_checksum_and_layer_payload_digests` **fails** at `f1ff2e2`:

```
AssertionError: facts.json digest moved: b40ab555dc3775667e02b54588aa487de055103ab3b8b640fe02d21cb887cc11
  assert 'b40ab555dc37…' == 'b1f723252fed…'
```

Diagnosis, and the reason this is **not** a Q1 STOP condition: all four pinned constants are the sha256 of the **CRLF-normalised** file, not the committed bytes. Verified for each file at both revisions:

| File | Committed bytes (LF) | CRLF-normalised | Pinned constant |
|---|---|---|---|
| `facts.json` | `b40ab555dc…` | `b1f723252f…` | `b1f723252f…` ✓ |
| `conflicts.json` | `d46a81c95c…` | `0ba4701d17…` | `0ba4701d17…` ✓ |
| `gaps.json` | `f72b239eb6…` | `e595a26fdd…` | `e595a26fdd…` ✓ |
| `forbidden.json` | `9ef4fa1a33…` | `d1788cf372…` | `d1788cf372…` ✓ |

The CRLF variants match the pins **identically at both `f27b51c` and `f1ff2e2`** — so the payload content has not moved; the pins were computed on a Windows checkout with `core.autocrlf` translation. The repository has no `.gitattributes` and the checkout is LF, so the assertion compares a translated digest against untranslated bytes.

Two consequences:

- The regression proof for criterion 2 **does not currently execute successfully** on Linux, macOS, or CI. It is the one criterion the package added specifically to replace manual inspection, and in the shipped state it reports the answer key as moved when it has not.
- It is not caught, because `tests/test_p0_assertion_library.py` **is not on any CI allowlist**. `git grep 'test_p0_assertion_library' -- .github/ .githooks/ .cursor/` returns nothing. The entire assertion-library suite — including every D-080 proof in the table above — runs in no workflow. The green CI on PR #14 does not evidence any of these proofs.

The checksum half of the same test (criterion 1) is unaffected: it uses canonical-JSON hashing, which is line-ending independent, and passes.

### F-2 — One of the three demoted emission sites has no test

`evaluate_layer5` demotes at three sites. Branch coverage over the full test file (`coverage run --branch`):

| Site | Lines | Covered |
|---|---|---|
| `method == "deterministic"` | 159–181 | yes |
| `dual` + `det_hit` | 210–231 | yes |
| **FB-05 `dual` + `det_omission and disclosed`** | **135–157** | **no — 0 tests reach it** |

`l5_assertions.py` reports 92% line coverage with `135-157` and branch `111->159` missing. Reaching this branch requires a corpus that omits OP2.3/OP4.2 *and* contains a disclosure phrase (`unreported|not reported|reporting gap|absent from`); no test bundle satisfies both. It is exactly the honest-disclosure case that motivated the whole package — the shape the detectors provably cannot distinguish — and it is the one demotion the proofs do not exercise.

### F-3 — Two narrower gaps

- **The deleted negative test was not replaced with an equivalent.** `test_l5_self_check_rejects_unexpected_hit` (which proved the load *did* fail on an unexpected hit) was removed. Its replacement, `test_l5_self_check_records_hits_without_failing_load`, only reloads the *same* pack with its known six hits. No test injects a novel or unexpected hit to prove the load still does not fail. The property "cannot fail the load on **any** observation" is therefore asserted in the manifest and in D-080 but not proven by the suite. (This review proved it directly via the ten-detector probe above; the point is that the regression suite does not.) Correspondingly, `golden_pack.py` line 171 — the checksum `raise` — and the `verify_l5_self_check=False` path are both uncovered.
- **The fail-closed test bypasses the loader.** `test_missing_judge_calibrated_flag_is_fail_closed` constructs a `GoldenPack` dataclass directly rather than going through `load_golden_pack`, and asserts only the property getter. It does not assert the downstream consequence (that L4-PROSE stays ADVISORY and the gate verdict is unaffected) when the flag is absent.
- Minor: `det_results` in `test_l5_deterministic_arm_markers_and_excluded_from_demonstrated_safety` is computed and never used.

### The flag-inversion test was widened — confirmed

It was, materially. At `f27b51c` the test called `evaluate_layer4(bundle, pack)` only, on a `[STAGE_CONTENT]`-only bundle, and compared a Layer 4 verdict map. At `f1ff2e2` it calls `run_all_layers` on a `[KNOWLEDGE_BANK, GAPS, CONTENT]` bundle and additionally compares the gate summary.

Measured, not assumed — the widened bundle produces:

```
layer 1: 3    layer 2: 3    layer 3: 3    layer 4: 4    layer 5: 18    total: 31
pass-by-starvation: 0/31   (no layer is starved out of the comparison)
```

and the test compares all six summary keys (`gate_pass`, `blocking_failures`, `review_required`, `advisory_ignored_by_gate`, `pass_by_starvation`, `demonstrated_safety_count`). The observed summary is non-trivial — `gate_pass=False`, `review_required=['FB-05']`, `advisory_ignored_by_gate=['L4-PROSE','FB-04','FB-09','FB-13']`, `demonstrated_safety_count=16` — so the comparison has real content to protect rather than comparing two empty structures.

One brittleness: the flip is `not pack.reference_prose_conforms_to_v4` but the following assertion is hardcoded `is False`. If the pack's flag ever became `false`, the test would fail on its own setup rather than on the property. It fails loudly, so this is a note, not a defect.

---

## Q5 — Record integrity

**Decision ID collisions: none.** D-080 and D-081 are assigned by this package. At `f27b51c`, a tree-wide grep for `D-08[01]` returns **two lines, both in the D-079 entry**, and both are forward reservations rather than occupants:

- `ME_MODULE_DECISION_LOG.md:88` — *"P0 WI8 decision IDs shift to D-080/D-081."*
- `ME_MODULE_DECISION_LOG.md:582` — same sentence in the D-079 narrative block.

No other file, and no other decision-log row, held either ID. The IDs were reserved by the immediately preceding decision and consumed as reserved. Both are registered in all three places the log requires: the main table, the supersession table (D-080 only, superseding "D-079 (L5 allowlist only)"), and a dated narrative block.

**Override log: appended, not edited.** `.governance/override_log.jsonl`, 78 → 81 lines (15,744 → 17,248 bytes). The `f1ff2e2` blob **begins with the entire `f27b51c` byte sequence verbatim** — a pure append, zero prior bytes altered. All 78 prior entries parse and are present in the same order, unmodified. The three appended entries carry `"layer": "correction"`, each with a `corrects_timestamp` pointing at a real prior entry (`…19:55:55.263093+00:00` and `…19:55:55.268031+00:00`, both confirmed present in the prior set), a `correct_reason`, and an explicit `"Prior line not edited."` in the reason text. The correction discipline is sound: the mislabelled D-079 restages are corrected by superseding entries, not by rewriting history.

**Stored review findings: byte-identical.** `docs/artefacts/me_module/audits/P0_PR14_INDEPENDENT_REVIEW_2026-07-28.md` at `f1ff2e2` is blob `0c043fd31b4570971826f7569a480b8595567546` — the same blob produced by the preceding pass at `3541fa5` ("docs(p0): independent review pass of PR #14 golden v1.1 Layer 4 swap", authored by `Claude <noreply@anthropic.com>`, 2026-07-27). 236 lines, 22,313 bytes. `3541fa5` is **not** an ancestor of `f1ff2e2` — the file was carried across branches — so byte-identity here is a substantive check, and it holds. The findings were transcribed without alteration.

**Scope of the diff.** Nine files:

| File | Change | In scope? |
|---|---|---|
| `app/reports/eval/golden_pack.py` | fail-on-load removed; validator deleted | yes |
| `app/reports/eval/layers/l5_assertions.py` | three emission sites demoted to ADVISORY | yes |
| `tests/fixtures/…/manifest.json` | allowlist → `l5_deterministic_arm` | yes |
| `tests/fixtures/…/README.md` | one table cell + one bullet | yes |
| `tests/fixtures/…/RECONCILIATION_V11_LAYER4.md` | self-check section rewritten | yes |
| `tests/test_p0_assertion_library.py` | proofs added/rewritten | yes |
| `ME_MODULE_DECISION_LOG.md` | D-080 **and D-081** | D-080 yes; D-081 adjacent |
| `.governance/override_log.jsonl` | three D-079 mislabelling corrections | adjacent |
| `audits/P0_PR14_INDEPENDENT_REVIEW…md` | evidence artefact added | yes |

Two items travel with the package beyond the stated scope (demote the arm, delete the list, add proofs):

- **D-081**, a new standing rule — *"Builder implements measurements, never authors them"* — a general governance rule, not a Layer 5 change.
- **The three override-log corrections**, which fix D-079-era mislabelling and are unrelated to Layer 5.

Both are disclosed rather than smuggled: D-081 is a full decision-log entry, and the corrections are named in the commit trailer (`GOVERNANCE_OVERRIDE: D-080 override-log corrections for mislabeled D-079 restages`). Neither touches engine behaviour, detectors, fixtures, or gates. Recording them as scope facts, not as defects.

No unrelated source file, migration, route, service, or export path appears in the diff.

**No merge has occurred.** PR #14 (`P0 PR1 — golden pack + five-layer assertion library + Layer 4 v1.1 (draft)`) is **open**, `merged: false`, head `f1ff2e20eb48d1301d87a1e4d0a23cee5565d43e`, base `main` at `15b52583025f9c39b979ff78b5aea5ce172970a0`. `f1ff2e2` is the tip of `engine/p0-harness` and the sole commit beyond `f27b51c`.

---

## The `governance-tree-audit` job

**The premise does not hold at this revision: the job is not exiting non-zero.** It is green, and every step within it succeeded.

Evidence — job-level and step-level, from the two runs that matter:

| Run | Event | Head | Job conclusion | Steps |
|---|---|---|---|---|
| `30304950466`, job `90106788345` | `pull_request` (PR #14) | `f1ff2e2` — the review target | **success** | all 8 steps `success`, including "Comment tree audit on PR" |
| `31244525307`, job `93070801731` | `schedule` | `main` @ `15b5258` (latest, 2026-08-08 06:42Z) | **success** | all steps `success`; "Comment tree audit on PR" `skipped` |

So the question resolves to neither of the two offered alternatives — it is not a designed report-only non-zero exit, and it is not an unreviewed failure being tolerated. There is no non-zero exit.

The design is nevertheless worth stating, because it explains why a non-zero exit is not reachable from the audit itself:

1. `scripts/governance/tree_audit.py` **cannot** exit non-zero. `main()` ends with a hardcoded `return 0` under the comment `# Always exit 0 — report-only.` There is no threshold, no violation count, no failure branch. Report-only is enforced in the script, not in the workflow.
2. `continue-on-error: true` at the **job** level (`smoke-test.yml:78`) is therefore belt-and-braces. Given (1), the only steps that could fail are infrastructure — checkout, `setup-python`, `upload-artifact` — or the PR-comment step, which carries its own `continue-on-error: true` (line 97) and is gated `if: github.event_name == 'pull_request'` (line 96).

One structural observation, offered as fact rather than recommendation: because `continue-on-error: true` sits at job level and the script can never signal a finding, this job cannot fail for any reason — including a genuine infrastructure failure that silently produced no report. Its green status is not evidence that the tree audit ran or that its output was reviewed. In these two runs it demonstrably did run (the "Report-only tree audit" and "Upload tree-audit artifact" steps both succeeded, and the PR run posted its comment), so the audit output exists for PR #14; the observation concerns what the signal would be worth on a future run, not what happened here.

Separately, and relevant to the D-078 entry in this package's decision-log neighbourhood: the **`governance-guards`** job (the blocking one) has no `continue-on-error` and succeeded on both runs, with protected-file mode `blocking` on the PR event and `report` on schedule/push, as D-078 specifies.

---

## Summary

- **Q1 — clean.** Checksum unchanged and self-consistent at both revisions; dataset version unchanged; all five layer payloads unchanged; Layer 4 reference content unchanged. No STOP.
- **Q2 — clean.** Every detector pattern, predicate, corpus-routing rule and identifier list is identical, verified by AST extraction and blob comparison across all 39 detector-bearing files. The two source changes are a docstring and a comment. The judged arm is byte-identical and still returns REVIEW-REQUIRED. No STOP.
- **Q3 — the demotion is real; one STOP.** The self-check runs, records six observations, and provably cannot fail the load even on a maximal adverse input, while checksum fail-closure is retained. The manifest states both required conditions and quotes cleanly. **But** the pack generator (`scripts/audit/_tmp_build_golden_v11_layer4.py`) still carries the full six-entry exception list and, if run, would restore it and delete the `l5_deterministic_arm` declaration (**S-1**). The six observations are legible in exactly one static document, without the per-pattern detail or the per-ID rationales.
- **Q4 — five of six criteria proven; one red, one branch unproven.** The flag-inversion test was genuinely widened to all five layers plus the summary (31 assertions, none starved). But the payload-digest pin is **red on every LF checkout** because its four constants are CRLF digests (**F-1**) — and it is not caught, because the entire assertion-library suite is on no CI allowlist. The FB-05 honest-disclosure demotion branch — the exact case that motivated the package — has **no test** (**F-2**). The deleted fail-on-load negative test was not replaced with an equivalent (**F-3**).
- **Q5 — clean.** No decision-ID collision (D-080/D-081 were reserved by D-079 and consumed as reserved). The override log is a pure append with all 78 prior entries byte-intact. The stored review findings are the same blob the preceding pass produced. No merge has occurred. Two adjacent items (D-081, override-log corrections) travel with the package; both are disclosed, and neither touches engine behaviour.
- **`governance-tree-audit` — green, not failing.** Every step succeeded on both the review-target PR run and the latest main run. `tree_audit.py` hardcodes `return 0`; the job-level `continue-on-error` is redundant given that, and means the job cannot fail for any cause, including infrastructure.

*Read-only pass. No repository file other than this artefact was modified. Evidence only; no fixes and no recommendations.*
