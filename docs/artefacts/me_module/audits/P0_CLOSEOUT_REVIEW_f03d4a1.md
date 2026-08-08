# P0 close-out (D-082): independent review

**Branch:** `engine/p0-harness`
**Review target:** `f03d4a18d84a353d1fbf09ff53d999e7893efffd` (`f03d4a1`)
**Comparison base:** `f1ff2e20eb48d1301d87a1e4d0a23cee5565d43e` (`f1ff2e2`) — direct ancestor
**Range:** three commits — `5ce9ca2` (close-out), `63275b9` (planted CI failure), `f03d4a1` (revert)
**Diff scope:** eight paths; two file deletions
**Tier:** certification-adjacent, owner-triggered, read-only
**Date:** 2026-08-08
**Method:** read-only. No repository file outside this artefact was modified. Verification was mechanical: independent digest recomputation, a materialised CRLF checkout, deliberate payload mutation, direct line-tracing of the interpreter, and retrieval of GitHub Actions job logs.

---

## STOP conditions

Four were specified. **None triggered.**

| Condition | Result |
|---|---|
| Content checksum or any layer payload digest has moved | Not triggered — all six digests unchanged (Q1) |
| Any detector differs | Not triggered — no file under `app/` changed at all (Q1) |
| Digest pin recomputed rather than made content-derived | Not triggered — fixed at the root, proven under three line-ending conventions (Q2) |
| CI does not explicitly select the suite, or the planted failure cannot be evidenced | Not triggered — dedicated named step; observed red at `63275b9` with logs (Q3) |

---

## Q1 — The answer key and the arm are unmoved

**Confirmed on every element.**

Checksum recomputed from the shipped fixtures at each revision (canonical JSON: sorted keys, `ensure_ascii=False`, separators `(",",":")`):

| | `f1ff2e2` | `f03d4a1` |
|---|---|---|
| `manifest.content_checksum` | `185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79` | *(identical)* |
| Recomputed from fixtures | same | same |
| Declared == recomputed | yes | yes |
| `dataset_version` | `1.1` | `1.1` |

**Layer payload digests** (canonical JSON per layer file):

| Layer | File | `f1ff2e2` → `f03d4a1` | |
|---|---|---|---|
| 1 | `facts.json` | `deaf3dd11006e4f2…` → same | unchanged |
| 2 | `conflicts.json` | `5f3b428c61ffe511…` → same | unchanged |
| 3 | `gaps.json` | `fcd0c98207ac0204…` → same | unchanged |
| 4 | `report_reference.json` | `401ed48f92199f29…` → same | unchanged |
| 5 | `forbidden.json` | `95340e824deec32c…` → same | unchanged |

**Layer 4 reference content and calibration state**, unchanged at both revisions: `full_markdown` sha256 `72c6c91d94a70393aa2979324f85b5971f91e6a0549b6a8cc7782399693bda6c`; `prose_rubric_reference` sha256 `ba5cac5e557bf621…`; `sections_present` canonical digest `d65c855f66dadad6…`; `reference_prose_conforms_to_v4 = true`; `judge_calibrated = false`.

**Uncalibrated arm declaration.** `manifest.l5_deterministic_arm` carries the same seven keys at both revisions — `status`, `gates`, `self_check`, `fail_on_load`, `statement`, `reversion_condition`, `detectors_found_non_discriminating` — and every shared value is byte-equal. The demotion and its reversion condition are untouched.

**Detectors.** The strongest available evidence: **no file under `app/` changed at all** across the whole range. `git diff --name-only f1ff2e2 f03d4a1 -- app/` returns empty. Explicitly confirmed by blob identity:

| File | Blob at both revisions |
|---|---|
| `app/reports/eval/golden_pack.py` | `0e48c983088c39ec8a715a52f7010086ac2a34f0` |
| `app/reports/eval/layers/l5_assertions.py` | `fb39c2f885d416db1221513634640916c31f90c0` |
| `app/reports/eval/verdicts.py` | `8dc6998fe5a880a11bf1d7e5460821c227e8464f` |
| `app/reports/eval/run_assertions.py` | `062b45ba5aced2df6c48e82a52471bef41734fa6` |
| `tests/fixtures/.../forbidden.json` | `503ee25f94308447f5010f127b2b317447779915` |

Both pattern tables (`_DET_PATTERNS`, `_DETERMINISTIC_PATTERNS`), every predicate, the corpus-routing rule and every identifier list live exclusively in those two unchanged modules. No detector could have moved.

The manifest change is additive metadata only (`l5_reference_self_check_observations`, +5 lines) and lies outside the checksum scope — which is why the checksum is unmoved despite the manifest edit.

---

## Q2 — The digest pin is content-derived, not re-pinned

**Fixed at the root. Stated plainly: this is not a recomputation on Linux.**

The change is to the derivation, not the constants:

| | `f1ff2e2` (defective) | `f03d4a1` |
|---|---|---|
| Constant name | `PINNED_PAYLOAD_SHA256` | `PINNED_PAYLOAD_CONTENT_SHA256` |
| Derivation | `hashlib.sha256(path.read_bytes())` | `_sha256_canonical(json.loads(path.read_text(encoding="utf-8")))` |
| Input | raw file bytes | parsed object → sorted canonical JSON dump |
| Depends on line endings | **yes** | **no** |

`_sha256_canonical` is imported from `app.reports.eval.golden_pack` — the *same* helper the production `compute_pack_checksum` uses. The test no longer defines its own hashing; it reuses the engine's canonicalisation. That is the structural reason the fragility cannot point the other way.

**Proof 1 — the constants are invariant under every line-ending convention.** Recomputed independently by this review from the `f03d4a1` blobs, not read from the test file:

| File | Pin | LF | CRLF | CR | Invariant |
|---|---|---|---|---|---|
| `facts.json` | `deaf3dd11006e4f2…` | match | match | match | YES |
| `conflicts.json` | `5f3b428c61ffe511…` | match | match | match | YES |
| `gaps.json` | `fcd0c98207ac0204…` | match | match | match | YES |
| `forbidden.json` | `95340e824deec32c…` | match | match | match | YES |

These are the same values this review computed independently in Q1 as the per-layer canonical digests. The pins are the content digests, not a snapshot of one machine's checkout.

**Proof 2 — the suite yields the same verdict on a real CRLF checkout.** A full working copy of `f03d4a1` was materialised and every pack JSON converted to CRLF (`facts.json` 2500 CRLF terminators, 0 bare LF; all six files converted, 0 bare LF remaining):

```
CRLF checkout : 20 passed
LF   checkout : 20 passed
```

Identical verdict. Under the old raw-byte derivation the same conversion moves every digest:

| File | raw sha256 (LF) | raw sha256 (CRLF) |
|---|---|---|
| `facts.json` | `b40ab555dc377566…` | `b1f723252fedfd9b…` |
| `conflicts.json` | `d46a81c95ccd3b2e…` | `0ba4701d17f446db…` |
| `gaps.json` | `f72b239eb6770732…` | `e595a26fddca525c…` |
| `forbidden.json` | `9ef4fa1a33a895f4…` | `d1788cf37227d613…` |

`b1f723252fedfd9b…` is exactly the D-080 pin for `facts.json` — the defect the previous review identified, reproduced here and now structurally unreachable.

**Proof 3 — the mutate-fails demonstration exists and altering a payload really does fail.**

`test_layer_payload_content_digest_fails_when_payload_altered` (new in this package) appends a record to the facts payload and asserts both that the layer content digest and the pack checksum diverge from their pins. It is a demonstration inside the suite rather than narration.

Verified independently against real on-disk mutations:

- **Appending one record to `facts.json`** (242 → 243 records) → load fails at the pack fixture: `ValueError: Golden pack checksum mismatch: expected 185223373f…, got 3cf3d7b73da2fbde…`.
- **Mutating `gaps.question_script_prose`** — a field *outside* the content-checksum scope (the checksum covers only `clusters`, `counter_list`, `target_note`) → the checksum is blind, and the per-layer pin catches it: `AssertionError: gaps.json content digest moved: dfcf8039638757127e…`.

The second case matters: it shows the per-layer pin is not redundant with the checksum. It guards payload content the checksum does not reach.

---

## Q3 — CI genuinely selects the suite, and the failure is real

**Selection is explicit, and the suite is blocking.**

`.github/workflows/smoke-test.yml`, added to the `smoke` job as its own named step (step 6), immediately after the P0 M&E unit smoke:

```yaml
# Full assertion-library suite — verbose so the job log proves every test EXECUTES by name (D-082).
- name: P0 assertion library suite
  env:
    PYTHONPATH: ${{ github.workspace }}
  run: pytest tests/test_p0_assertion_library.py -v --tb=short
```

Explicit on three counts: it names the file directly (not a glob, not a directory sweep, not `-k` matching); it is a dedicated step, so its result is attributable in the job's step list rather than buried in a 35-file `-q` invocation; and it carries **no** `continue-on-error`, and the `smoke` job itself carries none — so a failure fails the job and the workflow.

**Execution by name with a count, at the review head.** Run `31247644356` (event `pull_request`, head `f03d4a1`), job `smoke` `93078739475`, step "P0 assertion library suite" — conclusion `success`. Log:

```
Run pytest tests/test_p0_assertion_library.py -v --tb=short
collected 20 items
tests/test_p0_assertion_library.py::test_golden_pack_loads_and_checksum_matches PASSED [  5%]
… all 20 named individually …
tests/test_p0_assertion_library.py::test_run_all_layers_smoke PASSED     [100%]
============================== 20 passed in 0.15s ==============================
```

**The planted failure, evidenced as an observed CI red.**

What was broken (`5ce9ca2` → `63275b9`): a single line inserted as the first statement of the digest test —

```python
assert False, "D-082 planted CI failure — revert after observed red"
```

CI reported failure on that head. Run `31247490457` (head `63275b9`), **conclusion `failure`**, job `smoke` `93078360388`:

```
collected 20 items
tests/test_p0_assertion_library.py::test_pinned_content_checksum_and_layer_payload_digests FAILED [ 10%]
tests/test_p0_assertion_library.py:96: in test_pinned_content_checksum_and_layer_payload_digests
    assert False, "D-082 planted CI failure — revert after observed red"
E   AssertionError: D-082 planted CI failure — revert after observed red
========================= 1 failed, 19 passed in 0.17s =========================
##[error]Process completed with exit code 1.
```

This proves more than selection: the failure propagated to a non-zero exit and a failed job. The suite is enforcing, not merely observed.

**The revert is complete, with no residue.** `f03d4a1` removes exactly that one line and nothing else. Decisive check: the tree hash of `5ce9ca2` (pre-plant) equals the tree hash of `f03d4a1` (post-revert) — `1ac402f6b59daf69f714a513d7143d5b22b0adb3`. The plant/revert pair leaves the tree bit-for-bit as it stood before the plant. A residue sweep for `planted` / `assert False` across `tests/`, `app/` and `.github/` returns only pre-existing, unrelated usages (governance-guard fixtures, extractor answer keys, critic tests).

**CI is green on the review head, and its green now covers the harness.** All three jobs on run `31247644356` are `success`: `governance-guards` (blocking, protected-file mode `blocking` on the PR event), `governance-tree-audit`, and `smoke`. The distinction matters: at `f1ff2e2` the assertion-library suite ran in **no** workflow, so a green smoke result said nothing about the harness. The observed red at `63275b9` is the proof that the green at `f03d4a1` is now load-bearing for these 20 tests.

Run history on the branch, for the record:

| Run | Head | Event | Conclusion |
|---|---|---|---|
| `31247644356` | `f03d4a1` | pull_request | **success** |
| `31247490457` | `63275b9` | pull_request | **failure** (planted) |
| `30304950466` | `f1ff2e2` | pull_request | success |
| `30301465495` | `f27b51c` | pull_request | success |

---

## Q4 — Retirement lost nothing and reintroduces nothing

**Both generators are absent.** `scripts/audit/_tmp_build_golden_v11_layer4.py` (661 lines) and `scripts/audit/_tmp_build_golden_wi1.py` (1193 lines) are deleted at `f03d4a1`. No golden-pack builder remains under `scripts/`.

**Did either hold anything unique?** Assessed by category:

| Category | Held by the scripts? | Survives where |
|---|---|---|
| Detector patterns | **No** — `re.compile` count is **0** in both files | `golden_pack.py`, `l5_assertions.py` (unchanged) |
| Pack payloads (L1/L2/L3/L5) | outputs only | all nine pack files present in the tree |
| Layer 4 reference + provenance | outputs only | `report_reference.json`, `manifest.json` |
| Source text | read, not authored | `GOLDEN_RECORD…v1.0.md` (683 lines), `…v1.1_LAYER4.md` (287 lines) — both present |
| Judgment calls | **no** — explicitly delegated | `RECONCILIATION.md` (789 lines), `RECONCILIATION_V11_LAYER4.md` (66 lines) |
| Transcription/derivation code | **yes — this is what was retired** | nowhere in the tree; retrievable from git history |
| Six exception-list rationales | yes | analytically superseded; verbatim text only in git history |

The `wi1` script's own docstring settles the intent question:

> "One-shot WI1 builder: transcribe GOLDEN_RECORD v1.0 into typed fixtures. **Transcription only. Judgment calls are recorded in `RECONCILIATION.md`.** Not part of the runtime harness — **delete or keep as rebuild aid after owner verify.**"

It described itself as transcription-only, pointed judgment at a document that is present and 789 lines long, and anticipated its own deletion. Retirement executed the script's own stated disposal path.

Two things are genuinely no longer in the working tree, stated without softening:

1. **The derivation code itself.** The pack can no longer be regenerated by executing anything in the repository. That is the intended effect (D-082: "the golden pack is hand-authored ground truth; an executable that can regenerate it … is a hazard"), and it is also the cost — a future rebuild from the source documents would be manual.
2. **The verbatim six rationale strings.** Probing five distinctive rationale phrases against `f03d4a1`: two return zero files. Their *analytical* content is not lost but superseded in richer form (below); the literal text remains retrievable from git history at `f27b51c` and from the retired blobs.

**No executable artefact can now restore the exception list, remove the arm declaration, or overwrite the reconciliation narrative.** Verified:

- No golden-pack builder remains under `scripts/`.
- Every remaining `.py` that mentions `manifest.json` / `RECONCILIATION` / `l5_deterministic_arm` was checked: `app/reports/eval/golden_pack.py` has **0** write calls (read-only loader); `scripts/indicator_data_gate.py`, `scripts/knowledge_bank_reconciler_gate.py` and `scripts/audit/build_fcdo_post_deletion_template.py` have **0** references to `fcdo_bridgelight_ar1_v1` or `fixtures/golden`.
- The single `write_text` in `tests/test_p0_assertion_library.py` targets `dst / "report_reference.json"` inside a `shutil.copytree` copy under pytest's `tmp_path` — never the shipped pack.

**The new pack observation pointer resolves and carries real diagnostic detail.** `manifest.l5_reference_self_check_observations`:

```json
{
  "recorded_ids": ["FB-04","FB-05","FB-06","FB-09","FB-13","FB-14"],
  "per_detector_diagnostics": "docs/artefacts/me_module/audits/P0_PR14_INDEPENDENT_REVIEW_2026-07-28.md",
  "note": "IDs observed at v1.1 authorship against the pack's own reference text. Per-detector pattern, matched text, and classification live in the diagnostics document (Part B / Q3). Not an exception list — load never fails on these while fail-on-load is suspended (D-080)."
}
```

The target exists (236 lines). Its Part B / Q3 carries, for each of the six: the pattern as written, the matched text, the reference line with surrounding claim, and a per-ID classification of *why* the detector fired (pattern failing to distinguish assertion from mention; over-breadth via unbounded `.*`; presence-matching an absence predicate; corpus mismatch between scorer and self-check). This is materially more diagnostic than the deleted `{id, rationale}` pairs, which asserted the hits were benign without showing the mechanism. The six recorded IDs match the six the loader actually records — verified live in the previous pass and again here.

The `RECONCILIATION_V11_LAYER4.md` narrative was also corrected in the same commit: its "Fixture byte-identity" heading became "Fixture content-identity", and the body now describes canonical-JSON digests as "a property of content, not of checkout line endings (D-082)". The stale byte-identity claim is gone.

---

## Q5 — The new tests reach what they claim

### Honest-disclosure test — the previously unreached branch is now reached

`test_fb05_honest_disclosure_is_advisory_and_gates_nothing`.

Branch coverage of `app/reports/eval/layers/l5_assertions.py` under the full suite:

| | `f1ff2e2` | `f03d4a1` |
|---|---|---|
| Statements missed | **3** | **0** |
| Coverage | 92% | **98%** |
| Missing regions | `111->159`, **`135-157`** | `111->159`, `135->159` |

Lines 135–157 — the FB-05 `det_omission and disclosed` demotion site, unreached by any test at `f1ff2e2` — are no longer missing.

Confirmed independently by tracing the interpreter directly (`sys.settrace`, filtered to the module) over the test's own bundle:

```
lines executed in 135..157 : [135, 138, 139, 140, 141, 142, 143, 144, 146, 149, 150, 151, 152, 153, 157]
branch REACHED             : YES
```

What it asserts, verified by executing the same path:

| Property | Observed |
|---|---|
| `assertion_class` | `ADVISORY` |
| `verdict` | `ADVISORY` |
| `metrics["uncalibrated"]` | `True` |
| `metrics["gates_ignored"]` | `True` |
| `counts_as_demonstrated_safety` | `False` — excluded |
| in `advisory_ignored_by_gate` | `True` |
| in `blocking_failures` | `False` |
| detail | "Indicators unreported but disclosure phrase present (deterministic arm uncalibrated; gates nothing)" |

The bundle is constructed correctly for the case it claims: prose that omits OP2.3/OP4.2 and their aliases while carrying a disclosure phrase ("were not reported", "reporting gap"). This is the honest-disclosure shape the detectors provably cannot distinguish — the motivating case for the whole demotion — and it now has a test proving it gates nothing.

### Novel-observation test — genuinely novel, not a reload

`test_novel_self_check_observation_does_not_fail_load` copies the pack to `tmp_path` and appends `"Probe phrase: total row."` to the Layer 4 reference text, tripping the FB-01 fingerprint. Verified by execution:

```
recorded_ids in manifest        : ['FB-04','FB-05','FB-06','FB-09','FB-13','FB-14']
baseline hits on unmodified pack: ['FB-04','FB-05','FB-06','FB-09','FB-13','FB-14']
hits after injection            : ['FB-01','FB-04','FB-05','FB-06','FB-09','FB-13','FB-14']
NEW observation(s)              : ['FB-01']
new id absent from recorded_ids : True
load raised?                    : NO
```

FB-01 is absent from both the baseline hit set and the manifest's recorded six. The test injects a genuinely new observation and proves the load still does not fail — closing the gap the previous review recorded, where the only self-check test reloaded the known set.

### Full suite at the review head

20 tests, all passing, on both LF and CRLF checkouts and in CI:

| # | Test | |
|---|---|---|
| 1 | `test_golden_pack_loads_and_checksum_matches` | PASSED |
| 2 | `test_pinned_content_checksum_and_layer_payload_digests` | PASSED |
| 3 | `test_layer_payload_content_digest_fails_when_payload_altered` | PASSED *(new)* |
| 4 | `test_l5_self_check_records_hits_without_failing_load` | PASSED |
| 5 | `test_novel_self_check_observation_does_not_fail_load` | PASSED *(new)* |
| 6 | `test_fb05_honest_disclosure_is_advisory_and_gates_nothing` | PASSED *(new)* |
| 7 | `test_fb05_is_dual` | PASSED |
| 8 | `test_f043_caveat_names_inclusion_basis` | PASSED |
| 9 | `test_starvation_when_stage_absent` | PASSED |
| 10 | `test_pass_by_starvation_excluded_from_demonstrated_safety` | PASSED |
| 11 | `test_l1_fabrications_are_review_required_not_fail` | PASSED |
| 12 | `test_l1_recall_matches_on_value_and_source_not_fact_key` | PASSED |
| 13 | `test_l4_prose_is_advisory_and_ignored_by_gate` | PASSED |
| 14 | `test_reference_prose_conforms_to_v4_cannot_affect_any_layer_or_gate` | PASSED |
| 15 | `test_missing_judge_calibrated_flag_is_fail_closed` | PASSED |
| 16 | `test_l4_uses_report_reference_file_not_inline` | PASSED |
| 17 | `test_l5_judged_never_auto_clears_moat_on_heuristic` | PASSED |
| 18 | `test_l5_dual_deterministic_arm_is_advisory_when_uncalibrated` | PASSED |
| 19 | `test_l5_deterministic_arm_markers_and_excluded_from_demonstrated_safety` | PASSED |
| 20 | `test_run_all_layers_smoke` | PASSED |

### Acceptance criteria versus tests

| Criterion | Test | |
|---|---|---|
| Content-derived digest pins | #2 | covered |
| Mutation is demonstrated, not narrated | #3 | covered |
| Pack observation pointer present and correct | #1 (asserts the six IDs and the filename suffix) | covered |
| Honest-disclosure branch reached, ADVISORY, gates nothing, excluded from demonstrated safety | #6 | covered |
| Novel observation does not fail the load | #5 | covered |
| Assertion suite runs in CI | not a unit test — proved by workflow config plus the planted-failure/revert pair | covered by design |
| **Generator retirement** | **none** | **no test** |

**The one criterion with no test is generator retirement.** Nothing in the suite asserts that `scripts/audit/_tmp_build_golden_*.py` are absent, and nothing asserts that no executable in the tree can write the pack. The property holds today — verified above by inspection — but it is guarded by review only, so a future package could reintroduce a generator without any test going red. Recording this as a fact about coverage, not as a defect in what was built.

Two minor coverage residues, unchanged from the previous pass and outside this package's stated criteria: `golden_pack.py:171` (the checksum `raise`) and the `verify_l5_self_check=False` path remain unexercised by the suite. This review exercised the checksum raise directly (Q2, Proof 3).

### Decision entry

**D-082 exists and collides with nothing.** A tree-wide grep for `D-082` at `f1ff2e2` returns **zero** occurrences — the ID was entirely free, not even reserved. At `f03d4a1` it is registered in the main decision table (row dated 2026-08-08) and in a dated narrative block. No supersession-table row, which is correct: D-082 supersedes nothing; it discharges review findings against D-080's implementation.

`.governance/override_log.jsonl` grew 81 → 82 lines (17,248 → 17,538 bytes) as a **pure append** — the `f03d4a1` blob begins with the entire `f1ff2e2` byte sequence, and all 81 prior entries are present in order, unmodified. The single new entry records the `.github/workflows/smoke-test.yml` edit under D-082 at the `pre-commit` layer.

---

## Summary

- **Q1 — clean.** Content checksum, all five layer payload digests, dataset version, Layer 4 reference content, calibration state and the seven-key uncalibrated-arm declaration are all unchanged and self-consistent. No file under `app/` changed at all, so no detector pattern, predicate, corpus-routing rule or identifier list could have moved. No STOP.
- **Q2 — fixed at the root.** The pin derivation changed from raw file bytes to `_sha256_canonical(json.loads(...))`, reusing the engine's own canonicalisation. Proven three ways: the constants are invariant under LF, CRLF and CR by independent recomputation; the full suite returns 20 passed on a genuinely materialised CRLF checkout as well as LF; and raw-byte digests still visibly move under the same conversion, with the old D-080 pin reproduced exactly as the CRLF artefact. This is not a Linux recomputation — the fragility is eliminated, not reversed. The mutate-fails demonstration exists and real mutations fail: a facts append trips the checksum, and a mutation to a field *outside* checksum scope trips the per-layer pin, showing the two guards are complementary. No STOP.
- **Q3 — explicit and enforcing.** A dedicated `P0 assertion library suite` step names the file directly, with no `continue-on-error` on step or job. The green run at `f03d4a1` shows `collected 20 items`, all 20 named, `20 passed in 0.15s`. The planted failure at `63275b9` produced an observed CI **failure** with the exact assertion in the log and `exit code 1`; `f03d4a1` reverts it to a tree hash identical to the pre-plant commit, with no residue. All three jobs green on the review head, and the green now genuinely covers the harness. No STOP.
- **Q4 — retirement is clean.** Both generators absent; neither contained any detector pattern (`re.compile` count zero in both). Every output, the source documents, and the 789-line reconciliation record remain — and the retired script's own docstring delegated judgment there and anticipated its deletion. What is genuinely gone from the tree: the derivation code (intended) and the verbatim rationale strings (analytically superseded by a richer per-detector diagnostics table, and still in git history). No remaining executable can write the pack. The new manifest pointer resolves to a real 236-line document carrying all six IDs with pattern, matched text, reference line and per-ID classification.
- **Q5 — the tests reach what they claim.** The FB-05 honest-disclosure branch went from unreached to executed — statement misses 3 → 0, coverage 92% → 98%, confirmed by direct interpreter tracing of lines 135–157 — and asserts ADVISORY class and verdict, both markers, exclusion from demonstrated safety, presence in `advisory_ignored_by_gate` and absence from `blocking_failures`. The novel-observation test injects FB-01, absent from both the baseline hits and the recorded six, and proves the load still does not fail. D-082 collides with nothing and the override log is a pure append. **One criterion has no test: generator retirement is guarded by review only.**

*Read-only pass. No repository file other than this artefact was modified. Evidence only; no fixes and no recommendations.*
