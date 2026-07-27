# P0 — Layer 5 uncalibrated demotion and regression proofs — independent review pass

**Branch:** `engine/p0-harness`
**Review target SHA:** `f1ff2e2` — *fix(p0): D-080 L5 deterministic arm uncalibrated; delete exception list*
**Comparison base SHA:** `f27b51c` — *feat(p0): golden Layer 4 v1.1 V4 prose pass (D-079)* (reachable; unchanged)
**Diff:** single commit, 9 files, +451 / −129. Not merged; `f1ff2e2` reachable only from `origin/engine/p0-harness`.
**Reviewer:** Claude Code, independent pass. Read-only — no commits, branches or pushes to `engine/p0-harness`.
**Tier:** certification-adjacent, owner-triggered.
**Output discipline:** evidence only. No dispositions, no recommendations, no fixes.

---

## Pass outcome: STOPPED

**A STOP condition fired. The pass was halted at Q3 and Q4/Q5 were not performed.**

| STOP condition | Result |
|---|---|
| Detector pattern, predicate, routing or identifier list differs between revisions | **Not triggered.** All seven artefacts byte-identical. Q2. |
| Content checksum moved | **Not triggered.** Identical at both revisions, recomputed. Q1. |
| Any layer payload digest moved | **Not triggered.** L1/L2/L3/L4/L5 all byte-identical. Q1. |
| **An exception list survives in any form** | **TRIGGERED.** See below. |

### The STOP — an exception list survives in the pack's own generator

`scripts/audit/_tmp_build_golden_v11_layer4.py:576–619` still carries a live `"l5_self_check_allowlist"` key with all six original entries — FB-04, FB-05, FB-06, FB-09, FB-13, FB-14.

It is **not dead code**. The literal sits inside the `manifest = {` dict opened at line 483, which is written to the pack manifest at lines 621–622:

```python
(OUT / "manifest.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
)
```

The comment immediately above the surviving list still states the deleted policy verbatim:

```python
# Standing L5 self-check: reference prose discusses some forbidden patterns
# while forbidding them. Unexpected hits outside this allowlist fail pack load.
```

A second instance at line 366 writes the same framing into the generated reconciliation document:

```python
"- These hits are **allowlisted** in `manifest.l5_self_check_allowlist` with "
```

**`f1ff2e2` touched no file under `scripts/`.** `git diff --name-only f27b51c f1ff2e2 -- scripts/` returns empty. The generator was left at its pre-D-080 state.

**Consequence, stated as fact, not disposition:** the manifest at `f1ff2e2` carries no exception list, and the loader at `f1ff2e2` no longer reads the key — so the list is inert against *current* load behaviour. But the script that produces `manifest.json` for this pack still emits it. Re-running the generator regenerates the manifest with the exception list restored and the reconciliation document re-asserting the fail-on-load framing that D-080 suspends.

**Reachability of the generator:** no inbound references. `git grep -n "_tmp_build_golden" f1ff2e2` returns only a mention inside the prior review document. Not wired to CI, not invoked by any test. The second generator, `scripts/audit/_tmp_build_golden_wi1.py`, does **not** contain the key.

Because the STOP fired, **Q4 (new proofs) and Q5 (record integrity) were not performed**, and the governance-tree-audit exit-behaviour question was not investigated. Q1 and Q2 completed before the STOP and are recorded in full below; Q3 is recorded partially.

---

## Q1 — Nothing in the answer key moved *(completed, clean)*

**Payload digests — sha256 of file bytes at each revision:**

| Payload | `f27b51c` | `f1ff2e2` | |
|---|---|---|---|
| `facts.json` (L1) | `b40ab555dc3775667e02b54588aa487de055103ab3b8b640fe02d21cb887cc11` | same | **identical** |
| `conflicts.json` (L2) | `d46a81c95ccd3b2ec3a8ccb92d3d5cb9f0fbcf0456238a20d0a3ef293d3662ef` | same | **identical** |
| `gaps.json` (L3) | `f72b239eb6770732626ad59aa203e7822d5fc40b56d424e6385471b4bca4870a` | same | **identical** |
| `forbidden.json` (L5) | `9ef4fa1a33a895f4d22c4158f0094e72c5cae16f3824cfdd7ad2cc9d8b27e9f3` | same | **identical** |
| `report_reference.json` (L4) | `5f8d30c4df372df5df98a66c70dc07f039d805e62af3f1dfaa947825a563acc0` | same | **identical** |
| `manifest.json` | `c0735804feaee0cb98a7192f1b7e8d8f593deb2c02e039986e0bf970f7c3a140` | `35f02ec7de2e2afc13a397f51e667a978f588ff7cf679ef433ce28cc4149d9ce` | changed — declared scope |

The manifest is not a layer payload and is not inside the checksum scope. Its change is the exception-list deletion plus the new `l5_deterministic_arm` block (quoted under Q3).

**Content checksum — recomputed at both revisions** by executing each revision's own `compute_pack_checksum` over its own shipped fixtures:

```
f27b51c  declared = 185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79
f27b51c  recomputed = 185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79   match
f1ff2e2  declared = 185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79
f1ff2e2  recomputed = 185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79   match
```

Checksum unmoved across the package and self-consistent at each revision. `checksum_scope` string identical at both.

**Dataset version:** `1.1` at both revisions.

**Layer 4 reference content:** `report_reference.json → full_markdown` hashes to `72c6c91d94a70393aa2979324f85b5971f91e6a0549b6a8cc7782399693bda6c` at both revisions. Flags unchanged at both: `reference_prose_conforms_to_v4: True`, `judge_calibrated: False`. The v1.1 source document `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.1_LAYER4.md` is byte-identical (`7287f1e370511cb26312e0c5c474f3d2…`).

## Q2 — No detector was touched *(completed, clean)*

Each artefact was extracted verbatim from both revisions and byte-compared, including whitespace and comments. Not inferred from the diff.

| Artefact | Location | Length | Result |
|---|---|---:|---|
| `_DET_PATTERNS` table body | `app/reports/eval/golden_pack.py` | 1086 B | **identical** |
| `_DETERMINISTIC_PATTERNS` table body | `app/reports/eval/layers/l5_assertions.py` | 1096 B | **identical** |
| `scan_reference_against_forbidden` match loop | `golden_pack.py` | 207 B | **identical** |
| `_corpus` + `_questions_corpus` | `l5_assertions.py` | 363 B | **identical** |
| starvation-family routing + `target =` corpus routing + `det_hit` loop | `l5_assertions.py` | 928 B | **identical** |
| FB-05 predicate (`mentions_op23`, `mentions_op42`, `disclosed`, `det_omission`) | `l5_assertions.py` | 519 B | **identical** |
| judged arm (`elif method == "judged"` block) | `l5_assertions.py` | 1410 B | **identical** |

**No detector pattern, predicate, corpus routing or identifier list differs between the two revisions.** The identifier sets `{"FB-14", "FB-15"}` used for both starvation-family and corpus routing are unchanged in both locations.

**Judged arm confirmed unchanged and still review-required.** The block is byte-identical; its heuristic still yields `Verdict.REVIEW_REQUIRED` when triggered and `Verdict.PASS` otherwise, with `assertion_class=AssertionClass.INVARIANT` retained. The demotion did not reach it.

**What did change in those two modules** (comments, docstrings and verdict construction only):

- `golden_pack.py:19` — comment added: *"D-080: arm is uncalibrated; patterns must not be edited in builder packages."*
- `golden_pack.py` — `validate_l5_reference_self_check` deleted in full (former lines 134–161).
- `golden_pack.py` — `load_golden_pack` gains a docstring; the allowlist read and validator call replaced by a bare `scan_reference_against_forbidden(report_reference["full_markdown"])` under the comment *"Record-only while uncalibrated — never raise on observations (D-080)."*
- `l5_assertions.py` — three result-construction sites demoted from `AssertionClass.INVARIANT` / `Verdict.FAIL`\|`PASS` to `AssertionClass.ADVISORY` / `Verdict.ADVISORY`, each gaining `"uncalibrated": True` and `"gates_ignored": True` metrics: the FB-05 `det_omission and disclosed` branch, the `method == "deterministic"` branch, and the `dual` + `det_hit` branch. The `dual` no-hit branch and the FB-05 `not disclosed` REVIEW-REQUIRED branch are unchanged. `"deterministic_arm"` metric value changed from `"FAIL"` to `"hit"`.

## Q3 — Demotion and exception list *(partial — halted at the STOP)*

**Self-check still executes at load.** `load_golden_pack` retains the `verify_l5_self_check: bool = True` parameter and, when true, calls `scan_reference_against_forbidden(report_reference["full_markdown"])`.

**It cannot fail the load on any observation.** The only two raise sites in the former path — unexpected-hit and stale-allowlist — lived inside `validate_l5_reference_self_check`, which is deleted. No `raise` remains on the self-check path. The observations are assigned to `hits` and carried onto `GoldenPack.l5_reference_self_hits`.

**No exception list in the pack or the manifest.** `l5_self_check_allowlist` is absent from `manifest.json` at `f1ff2e2`; `validate_l5_reference_self_check` is absent tree-wide. Surviving textual occurrences are: this and the prior audit document (historical record), `RECONCILIATION_V11_LAYER4.md:47` (a note recording the deletion), the D-080 decision-log entries, two test assertions of the form `assert "l5_self_check_allowlist" not in pack.manifest`, and **the generator described in the STOP above**.

**Manifest states the uncalibrated condition and the reversion condition.** The deleted six-entry array is replaced by `l5_deterministic_arm`, quoted in full:

```json
"l5_deterministic_arm": {
  "status": "uncalibrated",
  "gates": false,
  "self_check": "runs_and_records",
  "fail_on_load": "suspended",
  "statement": "The Layer 5 deterministic arm is uncalibrated and gates nothing. Pack-load self-check runs against the pack's own reference text and records every observation; it does not fail the load on any observation. No exception list is carried.",
  "reversion_condition": "Restore fail-on-load only when owner/CTO has authored and calibrated the detectors, recorded by a decision-log entry naming that calibration. Until then do not reintroduce an exception list. See D-080.",
  "detectors_found_non_discriminating": true
}
```

**Where the six observations are now recorded — partially established.** They are carried in-process on `GoldenPack.l5_reference_self_hits` as a tuple of IDs, computed at load. Whether they are additionally rendered anywhere legible to a person reading the pack — and whether the per-ID rationales that the deleted allowlist carried survive in any human-readable form — **was not established**; the pass halted before completing this sub-question.

## Q4 — New proofs *(not performed)*

Halted by the STOP. No acceptance criterion was verified. The observable facts recorded incidentally before the halt: `tests/test_p0_assertion_library.py` grew from 282 to ~462 lines (+180) in this commit, and contains at least two assertions of the form `assert "l5_self_check_allowlist" not in pack.manifest` at lines 50 and 95. Nothing about coverage, naming or assertion content is claimed.

## Q5 — Record integrity *(not performed)*

Halted by the STOP. Recorded incidentally: the diff touches `.governance/override_log.jsonl` (+3), `ME_MODULE_DECISION_LOG.md` (+11) with a D-080 table row at line 89 and a narrative at line 589, and adds the prior review document at `docs/artefacts/me_module/audits/P0_PR14_INDEPENDENT_REVIEW_2026-07-28.md` (+236). No collision check, no byte-comparison of the stored review findings, no scope check and no merge check were performed.

## governance-tree-audit exit behaviour *(not investigated)*

Halted by the STOP.

---

## Method

- Detached worktrees at `f27b51c` and `f1ff2e2`; all comparisons run against working trees, not against diff output.
- `compute_pack_checksum` executed from each revision's own source over that revision's own fixtures.
- All six fixture files hashed at both revisions via `git show <sha>:<path> | sha256sum`.
- Detector artefacts extracted by anchored regex from each revision's source and compared by exact string equality and sha256, with lengths recorded.
- Exception-list survival established by `grep -rniE "allowlist|allow_list|allowed_ids|exception_list|exempt|suppress|whitelist|waiver|ignore_list"` across `app/reports/eval/`, `tests/fixtures/golden/` and the test file, then `git grep` for the specific key across the whole tree at `f1ff2e2`.
- Generator liveness established by locating the enclosing `def`, the opening `manifest = {` at line 483, the literal at 576–619, and the `manifest.json` write at 621–622, and confirming the literal falls between the dict opening and the write.

**Not established:** anything under Q4, Q5, or the CI job question. The pass stopped where it was instructed to stop.
