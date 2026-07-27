# P0 PR #14 — Independent review pass

**Package:** golden pack (WI1) + five-layer assertion library (WI2) + golden Layer 4 v1.1 V4 prose pass (D-079)
**Review target:** `engine/p0-harness` @ `f27b51c` — PR [#14](https://github.com/mycrivo/ngoinfo-grantpilot/pull/14) (draft)
**Base:** `main` @ `15b5258` · 4 commits · 30 files · +7898 / −1
**Reviewer:** Claude Code, independent pass. Read-only against the review target — no commits, branches or pushes to `engine/p0-harness`; `f27b51c` is unchanged.
**Tier:** certification-adjacent, owner-triggered.
**Output discipline:** evidence only. No dispositions, no proposed changes. A finding without an evidence pointer does not enter the record.

---

## STOP conditions

| Condition | Result |
|---|---|
| Allowlist reachable from a candidate-scoring path | **Not triggered.** Traced exhaustively; not reachable. See Q1. |
| Layer 1, 2, 3 or 5 payload hash moved | **Not triggered.** All four byte-identical across the swap. See Q4. |

Pass ran to completion.

---

## Part A — What was built (orientation for the CTO)

Four commits, in order:

| Commit | Work item | Content |
|---|---|---|
| `43e806c` | WI1 | Golden pack transcription + reconciliation (STOP) |
| `01ee715` | WI1 | Verification corrections (findings 1–5) |
| `1215fed` | WI2 | Five-layer assertion library + pack close-out |
| `f27b51c` | D-079 | Golden Layer 4 v1.1 V4 prose pass |

**1. The golden pack becomes machine-readable.** Before this branch, the golden record existed only as prose: `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`, with the eighteen forbidden outputs as rows in a markdown table. WI1 transcribes it into typed fixtures under `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/` — `facts.json`, `conflicts.json`, `gaps.json`, `forbidden.json`, `report_reference.json`, `manifest.json`, plus `RECONCILIATION.md` documenting the transcription.

**2. The assertion library scores bundles, not runs.** WI2 adds `app/reports/eval/`: `golden_pack.py` (load + checksum + validation), `bundle_schema.py` (`ScoreableBundle`), `starvation.py`, `verdicts.py`, `matching.py`, `run_assertions.py`, and `layers/l1..l5_assertions.py`. The design point stated in `app/reports/eval/__init__.py`: *"the harness scores persisted run bundles; it does not execute the pipeline."*

Verdict vocabulary (`verdicts.py`, surfaced via `run_assertions.gate_verdict`): `PASS`, `FAIL`, `REVIEW_REQUIRED`, `ADVISORY`, `PASS_BY_STARVATION`. Starvation results are excluded from demonstrated-safety counts, per the contract's invariant/baselined split.

**3. Layer 4 swapped to v1.1.** D-079 replaces the Layer 4 reference prose with a V4-conformant pass, and splits the single `prose_uncalibrated` flag into two: `reference_prose_conforms_to_v4` (golden caveat discharged — true) and `judge_calibrated` (unchanged — false). **The gate reads `judge_calibrated` only.** A standing Layer 5 self-check now runs at pack load, matching the deterministic forbidden-output patterns against the golden's own reference text.

**4. The open governance question.** Six forbidden outputs — FB-04, FB-05, FB-06, FB-09, FB-13, FB-14 — hit that self-check against the golden's own text and are allowlisted in `manifest.l5_self_check_allowlist`. The PR discloses this as unresolved and awaiting owner disposition. Establishing the facts about that allowlist was the priority question of this pass.

---

## Part B — Findings

### Q1 — Allowlist scope and blast radius *(priority)*

**Location and form.** `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/manifest.json:114`, key `l5_self_check_allowlist`. Pack-local JSON data: an array of six `{id, rationale}` objects.

**Every code path that reads it.** `grep -rn "l5_self_check_allowlist\|l5_reference_self_hits\|scan_reference_against_forbidden\|validate_l5_reference_self_check" app/ tests/` returns eleven lines, and only these:

| Site | Role |
|---|---|
| `app/reports/eval/golden_pack.py:195` | **sole read of the manifest key**, inside `load_golden_pack` |
| `app/reports/eval/golden_pack.py:197–199` | normalises entries to IDs (accepts `str` or `{id,…}`) |
| `app/reports/eval/golden_pack.py:200–203` | passes IDs to `validate_l5_reference_self_check` |
| `app/reports/eval/golden_pack.py:134–161` | the validator; raises on unexpected hit or stale entry |
| `app/reports/eval/golden_pack.py:123–131` | `scan_reference_against_forbidden`, called only from the validator |
| `app/reports/eval/golden_pack.py:72`, `:213` | writes `GoldenPack.l5_reference_self_hits` |
| `tests/test_p0_assertion_library.py:46`, `:183`, `:213` | test-only reads |

**Definitive answer: the allowlist is consulted only during golden pack load validation. No scoring path can reach it.**

The load-time chain is closed: `load_golden_pack` (`golden_pack.py:164`) → `validate_l5_reference_self_check` (`:200`) → `scan_reference_against_forbidden` (`:146`) → raise or return. It runs against `report_reference["full_markdown"]` (`:201`) — the golden's own reference text — and never against a candidate.

The scoring path is disjoint. `run_all_layers` (`run_assertions.py:19–30`) calls `evaluate_layer1…5(bundle, pack)`. `evaluate_layer5` (`l5_assertions.py:63–229`) reads `pack.forbidden` and matches against `_corpus(bundle)` / `_questions_corpus(bundle)` (`:49–60`) using its **own** module-level `_DETERMINISTIC_PATTERNS` (`:14–46`). It never reads `pack.manifest`, never reads `pack.l5_reference_self_hits`, and imports nothing from the self-check group. `gate_verdict` (`run_assertions.py:33–59`) reads only `AssertionResult` fields.

One structural note, recorded as fact: `GoldenPack.l5_reference_self_hits` is a field on the object passed to every scorer, so the self-check result is *available* on a scoring path. No scorer dereferences it. That is adjacency, not a live path.

**Guarded by test.** `tests/test_p0_assertion_library.py:195–216` empties the allowlist in a temp pack copy and asserts `load_golden_pack` raises `ValueError` matching `"L5 reference self-check failed"`. Verified passing.

### Q2 — Allowlist portability

**The allowlist is pack-local data. The patterns it excuses are shared validator logic.** A second golden pack for an unseen funder cannot be loaded without code changes.

Hardcoded, FCDO/BridgeLight-specific, outside the pack:

| File:line | What is hardcoded |
|---|---|
| `app/reports/eval/golden_pack.py:19–51` | `_DET_PATTERNS` — 17 regexes across 10 FB ids, containing `1[, ]?944`, `2[, ]?376`, `472\s*/\s*684`, `ocm1\s*=\s*69`, `1[, ]?184[, ]?000`, `op2\.?3`, `op4\.?2`, `392.*male`, `devtracker`, `vfm scoring rubric` |
| `app/reports/eval/layers/l5_assertions.py:14–46` | `_DETERMINISTIC_PATTERNS` — a **second copy** of the same 17 regexes (verified byte-equal at `f27b51c`) |
| `app/reports/eval/layers/l5_assertions.py:75–78` | starvation-family routing keyed on literal ids `{"FB-14","FB-15"}` |
| `app/reports/eval/layers/l5_assertions.py:96` | corpus routing keyed on literal ids `{"FB-14","FB-15"}` |
| `app/reports/eval/layers/l5_assertions.py:103–147` | FB-05-specific branch with `safeguarding referral` / `learning brief` literals |
| `app/reports/eval/golden_pack.py:12–15` | `DEFAULT_PACK_DIR` pinned to `tests/fixtures/golden/fcdo_bridgelight_ar1_v1` |

**Files that would have to change to load a second pack with its own forbidden-output set:** `app/reports/eval/golden_pack.py` (pattern table, default pack dir) and `app/reports/eval/layers/l5_assertions.py` (pattern table, both id-keyed routing sets, the FB-05 branch). The pack directory and `manifest.l5_self_check_allowlist` are already per-pack; nothing else is.

The two pattern tables are kept in sync by comment only — `golden_pack.py:17`, *"kept in sync with layers.l5_assertions._DETERMINISTIC_PATTERNS"*. No test asserts equality.

### Q3 — Pattern discriminability

Patterns as written in `golden_pack.py`. Matched text extracted from `report_reference.json → full_markdown`; line numbers are within that reference document.

| ID | Method | Pattern | Matched text | Reference line and surrounding claim |
|---|---|---|---|---|
| **FB-04** | deterministic | `1[, ]?184[, ]?000` | `1,184,000` | L186 — "…calculated on the proposal budget of £1,184,000 and a target of 1,200 girls. **That budget was superseded at award**" |
| **FB-05** | dual | `op2\.?3\|op2_3` / `op4\.?2\|op4_2` | `OP2.3` / `OP4.2` | L53 — "The **unreported** OP2.3 indicator matters out of proportion…"; L91 — "…their production is the **unreported** OP4.2 indicator" |
| **FB-06** | dual | `392.*male` and `all\s+392.*male` | `all 392 recipients are recorded as male` | L59 — "…all 392 recipients are recorded as male and spread across age bands of 6–11, 12–17 and 18–24 — **which cannot be credible**" |
| **FB-09** | deterministic | `aggregat\w+.*output.?score\|output.?score.*aggregat` | 150-char span: `aggregated figures don't reconcile to headline totals in three places, and the caregiver breakdown isn't credible on its face. And the proposed output score` | L23 — two unrelated clauses in one sentence, bridged by unbounded `.*` |
| **FB-13** | deterministic | `life[- ]of[- ]programme\|burn\s*rate\|remaining budget` | `life-of-programme` | L184 — "…so **no** life-of-programme burn position **can be derived** from it" |
| **FB-14** | dual | `previous recommendations` (hit); `impact weightings` (no match) | `previous recommendations` | L236 — "**Updates on previous recommendations.** Not applicable. This is the first Annual Review…" |

**Classification, per ID:**

- **FB-04, FB-06, FB-13 — pattern failing to distinguish assertion from mention.** Each matched string sits inside an explicit negation or disclosure in the same sentence ("was superseded at award", "which cannot be credible", "no … can be derived"). The patterns are literal fingerprints with no negation, scope or polarity handling. The forbidden output is stateable deterministically; these three patterns are not written to detect it.
- **FB-09 — pattern failing to distinguish, by over-breadth.** The unbounded `.*` bridges two clauses that are individually innocuous. The match is not a mention of the forbidden thing at all; it is an artefact of the alternation spanning a sentence. The manifest rationale itself labels it *"False-positive surface"*.
- **FB-05 — inherently not detectable by the pattern as written, for a structural reason.** The forbidden output is *omitting* OP2.3/OP4.2 *without flagging*. The self-check pattern matches the **presence** of the token, which is evidence of the opposite condition. Presence-matching cannot express an absence-plus-missing-disclosure predicate. Note that the scoring path implements a different, inverted predicate for the same ID — `l5_assertions.py:103–110`, `det_omission = not (mentions_op23 and mentions_op42)` plus a `disclosed` check. Scorer and self-check therefore apply opposite semantics to the same ID under the same regexes.
- **FB-14 — pattern failing to distinguish, compounded by a corpus mismatch.** The forbidden output is *asking the NGO* for prior recommendations. The match is a template section heading in report prose, answered "Not applicable". Separately: the scorer restricts FB-14/FB-15 to the questions corpus (`l5_assertions.py:96` — `target = qcorpus if fid in {"FB-14","FB-15"} else corpus`), whereas the self-check applies all patterns to the full report markdown with no such routing (`golden_pack.py:126–131`). FB-14's allowlist entry exists only because the self-check scans a corpus the scorer would never scan for that ID.

The second FB-14 arm, `impact weightings`, does not match. Staleness is checked at ID granularity (`golden_pack.py:155–160`), not per pattern, so a non-firing arm inside a firing ID raises nothing.

### Q4 — Regression proof and integrity

**Observed counts** — recounted from the fixtures, not read from the manifest:

| Metric | Manifest | Observed | |
|---|---:|---:|---|
| fact records (facet-grained) | 242 | 242 | match |
| distinct fact IDs | 106 | 106 | match |
| conflicts | 9 | 9 | match |
| gap clusters | 10 | 10 | match |
| counter-list entries | 15 | 15 | match |
| forbidden outputs | 18 | 18 | match |
| non-reportable records | 9 | 9 | match |
| absent records | 9 | **0 by `absent is True`** | see note |

*Note:* `absent_records: 9` does not reconcile against any `absent == True` field — zero records carry it. Records instead encode absence through `status` strings (`"Gap G-01"` ×3, `"Gap G-02"`, `"Gap G-03"`), and the `absent` key appears in the key union without a `True` value. The 9 non-reportable records reconcile exactly via `reportable == False`. Recorded as observed; not dispositioned.

**Payload hashes, WI2 (`1215fed`) → v1.1 (`f27b51c`)** — sha256 of file bytes:

| Payload | WI2 | v1.1 | |
|---|---|---|---|
| `facts.json` (L1) | `b40ab555dc377566` | `b40ab555dc377566` | **identical** |
| `conflicts.json` (L2) | `d46a81c95ccd3b2e` | `d46a81c95ccd3b2e` | **identical** |
| `gaps.json` (L3) | `f72b239eb6770732` | `f72b239eb6770732` | **identical** |
| `forbidden.json` (L5) | `9ef4fa1a33a895f4` | `9ef4fa1a33a895f4` | **identical** |
| `report_reference.json` (L4) | `8866daf91bbcc699` | `5f8d30c4df372df5` | changed — declared scope |
| `manifest.json` | `f87d39a26cd9fe83` | `c0735804feaee0cb` | changed — declared scope |

Layers 1, 2, 3 and 5 unmoved. STOP not triggered.

**Checksum scope extended and recomputed — verified.** `manifest.checksum_scope` reads `facts + conflicts + gaps(clusters,counter_list,target_note) + forbidden + report_reference(reference_prose_conforms_to_v4, judge_calibrated, full_markdown_sha256, prose_rubric_reference_sha256, sections_present)`. Both new flags and the new `prose_rubric_reference_sha256` are inside the scope (`golden_pack.py:110–117`). Independently recomputing `compute_pack_checksum` over the shipped fixtures yields:

```
185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79
```

— matching `manifest.content_checksum` exactly.

**Superseded Layer 4 hash recorded and correct.** `manifest.superseded_layer_4_sha256 = 866a51298324c32e55239756c7d39d8ce6ffdfc0ed21c5169baf3350074e070c`. Hashing the WI2 `report_reference.json → full_markdown` at `1215fed` yields the same value. The current markdown hashes to `72c6c91d94a70393aa2979324f85b5971f91e6a0549b6a8cc7782399693bda6c`.

`layer_provenance` records `source_version: "1.0"` for layers 1/2/3/5 and `"1.1"` for layer 4, with `layer_4_change_scope: "prose only; no fact, conflict, gap or forbidden-output content altered"`.

### Q5 — Gate wiring and test inventory

**Guard test exists.** `test_reference_prose_conforms_to_v4_cannot_affect_gate` (`tests/test_p0_assertion_library.py:160–192`) constructs a `GoldenPack` with `reference_prose_conforms_to_v4` flipped to `False`, re-runs, and asserts `base_verdicts == alt_verdicts`.

**Scope limit, stated as fact:** it calls `evaluate_layer4` only (`:170`, `:187`), not `run_all_layers` or `gate_verdict`. It proves the flag cannot alter Layer 4 verdicts; it does not exercise the other four layers or the gate summary.

**Uncalibrated default when the flag is absent — implemented, not tested.** `golden_pack.py:88–90`: `return bool(self.report_reference.get("judge_calibrated", False))`, commented *"Fail-closed: absent → not calibrated"*. `l4_assertions.py:146–149` reads `pack.judge_calibrated` and nothing else. No test constructs a `report_reference` without the key; the three `judge_calibrated` assertions (`:35`, `:152`, `:186`) all run against a fixture where the key is present and `False`.

**P0 suite — 14 tests, all passing.** Verified locally at `f27b51c`: `14 passed`.

| Test | Asserts |
|---|---|
| `test_golden_pack_loads_and_checksum_matches` | version 1.1; 242/9/10/15/18 counts; `reference_prose_conforms_to_v4 is True`; `judge_calibrated is False`; `prose_uncalibrated` absent; appendix separate from scored markdown; self-check hits == the six allowlisted IDs |
| `test_fb05_is_dual` | FB-05 `detection_method == "dual"` |
| `test_f043_caveat_names_inclusion_basis` | F-043 achieved is CAVEATED with `caveat.uncertain == "inclusion_basis"`; baseline CONFIRMED |
| `test_starvation_when_stage_absent` | `is_starved` true for absent stages, false for present |
| `test_pass_by_starvation_excluded_from_demonstrated_safety` | starvation verdicts present; `demonstrated_safety_count == 0` |
| `test_l1_fabrications_are_review_required_not_fail` | fabrication → REVIEW_REQUIRED, counted separately from recall |
| `test_l1_recall_matches_on_value_and_source_not_fact_key` | recall matches on value+source, not engine fact key |
| `test_l4_prose_is_advisory_and_ignored_by_gate` | L4-PROSE is ADVISORY, `gates_ignored is True`, listed in `advisory_ignored_by_gate` |
| `test_reference_prose_conforms_to_v4_cannot_affect_gate` | flag flip leaves Layer 4 verdicts unchanged |
| `test_l5_self_check_rejects_unexpected_hit` | emptied allowlist → `ValueError` on load |
| `test_l4_uses_report_reference_file_not_inline` | L4 reads `pack.report_markdown` from fixture |
| `test_l5_judged_never_auto_clears_moat_on_heuristic` | judged FB-10 → REVIEW_REQUIRED |
| `test_l5_dual_deterministic_arm_fails_on_named_instance` | FB-01 deterministic arm → FAIL |
| `test_run_all_layers_smoke` | ≥18 results; layers `{1,2,3,4,5}` present |

**D-079 required additions with no corresponding test.** Requirements taken from the D-079 decision-log entry (`ME_MODULE_DECISION_LOG.md:88` and `:121`):

| Required addition | Test coverage |
|---|---|
| Prose-flag split (`prose_uncalibrated` → two flags) | covered — `:34–36` |
| Gate reads `judge_calibrated` only | partial — Layer 4 only, per the scope limit above |
| Fail-closed when `judge_calibrated` absent | **none** |
| Standing L5 self-check with allowlist | covered — `:45–53`, `:195–216` |
| ngo-reviewer stays NOT YET CALIBRATED with RUBRIC SOURCE pointer | **none** — charter content is not asserted by any test |
| Calibration not moved | **none** — no test pins calibration state across revisions |
| Layers 1/2/3/5 unchanged by the swap | **none** — no test asserts payload stability; verified here by hash comparison only |

---

## Part C — WI2 ordering, CI, and protected-path overrides

**WI2 closed and green before v1.1 — with one qualification.** `1215fed` (WI2 close-out, 2026-07-27T20:30:11+01:00) precedes `f27b51c` (v1.1, 20:55:54+01:00). Running the P0 suite at `1215fed`: **12 passed**. At `f27b51c`: **14 passed**.

The qualification: **`f27b51c` did modify the assertion layer.** `git diff --name-only 1215fed f27b51c -- app/reports/eval/` returns `golden_pack.py` (+125), `layers/l4_assertions.py` (+64), `matching.py` (+3). WI2 was closed and green first, but the v1.1 commit subsequently changed three assertion-layer modules rather than touching fixtures alone. No CI run exists for `1215fed` — PR #14 was opened at `f27b51c`, so the only CI evidence is the run below.

**CI on the head SHA — confirmed green.** Run [`30301465495`](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/30301465495), event `pull_request`, head `f27b51c`, conclusion `success`, 2026-07-27T20:10:44Z → 20:13:13Z. Jobs: `governance-guards`, `governance-tree-audit`, `smoke`.

**Protected-path overrides are logged and visible in the diff.** Six new lines in `.governance/override_log.jsonl` (entries 73–78) covering `GOLDEN_RECORD_..._v1.0.md`, `GOLDEN_RECORD_..._v1.1_LAYER4.md` and `.claude/agents/ngo-reviewer.md`. Override tokens in commit messages: `43e806c` ✓, `1215fed` ✓, `f27b51c` ✓. `01ee715` carries none and touches no protected path. The four PR-declared override paths all appear in the diff and reconcile against the log.

**Two recording anomalies in the override log, stated as observed:**

1. Entries 76–78 carry `reason: "P0 WI2: assertion library + golden pack FB-05/C-07 close"` and timestamp `19:55:55Z` — one second after `f27b51c`'s commit timestamp (`19:55:54Z`) and ~26 minutes after the WI2 commit (`19:30:11Z`). They were written during the v1.1 commit but labelled with the WI2 reason.
2. Those same WI2-labelled entries name `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.1_LAYER4.md`, which does not exist at `1215fed` — verified: `git cat-file -e 1215fed:<path>` fails.

---

## Part D — Additional facts observed, outside the five questions

- `.claude/agents/ngo-reviewer.md` retains `CALIBRATION: NOT YET CALIBRATED` unchanged; the diff is purely additive (six lines of RUBRIC SOURCE pointers). Calibration state is unmoved, as claimed.
- Two build scripts ship in the package under `scripts/audit/` with `_tmp_` name prefixes: `_tmp_build_golden_wi1.py` (1193 lines) and `_tmp_build_golden_v11_layer4.py` (661 lines).
- `manifest.layer_provenance.layer_4_report` carries `vfm_section_f_workaround: true` and `vfm_amendment_when: "P1 restores VfM section (D-069) → Layer 4 requires golden amendment"` — a recorded forward dependency between this pack and D-069.

---

## Method and scope of verification

Everything above was verified by execution or direct inspection against `f27b51c`, not read from the PR body:

- Detached worktrees at `f27b51c` and `1215fed`; P0 suite executed at both.
- `compute_pack_checksum` re-executed over the shipped fixtures and compared to `manifest.content_checksum`.
- All six fixture payload files hashed at both revisions and compared.
- `superseded_layer_4_sha256` compared against the actual WI2 `full_markdown`.
- Counts recomputed from `facts.json` / `conflicts.json` / `gaps.json` / `forbidden.json`.
- Matched text for each of the six allowlisted IDs extracted by re-running `_DET_PATTERNS` against the reference markdown and resolving line numbers.
- Reachability established by exhaustive grep across `app/` and `tests/` for all four self-check symbols, then by reading every call site.
- CI conclusion read from the GitHub Actions API for run `30301465495`.

**Not established:** whether the allowlist is *correct* as a governance matter. This pass establishes what it is, where it lives, what it excuses and what reaches it. The disposition is the owner's.
