# P0 PR #15 — Independent review pass

**Package:** bundle export + scorecard emitter (D-083)
**Review target:** `engine/p0-bundle-export` @ `0489f58e0b0395e9019516ec4c43600b2314d5d2` — PR [#15](https://github.com/mycrivo/ngoinfo-grantpilot/pull/15) (draft)
**Base:** `main` @ `ef1f21a263c5ce7a7c1c6a7d6e9a9675648c6167` · 2 commits · 11 files · +37,348 / −0
**Reviewer:** Claude Code, independent pass. Read-only against the review target — no commits, branches or pushes to `engine/p0-bundle-export`; `0489f58` is unchanged. Execution for evidence was performed against a scratch extraction of the target tree, outside the repository working directory.
**Tier:** certification-adjacent, owner-triggered.
**Output discipline:** evidence only. No dispositions, no proposed changes. A finding without an evidence pointer does not enter the record.

CI on the review target: `governance-guards` **success**, `governance-tree-audit` **success**, `smoke` **success** (run 31251734256).

---

## STOP conditions

| Condition | Result |
|---|---|
| An expected figure appears in the package | **Not triggered.** No threshold, pass mark, expected value or prior-result comparison exists in `bundle_export.py`, `scorecard.py`, `bundle_export_run.py` or `scorecard_emit.py`. The only numeric comparison in the package is `len(families) > 1` (`bundle_export.py:237`), which triggers an observation string, not a judgement. Bounded note under Q3/Q4 on observed production values in the committed discovery artefact — those are observations, not expectations, and nothing compares against them. |
| The export writes to production | **Not triggered.** The library performs no I/O other than `git rev-parse HEAD`. The CLI opens the connection with `conn.set_session(readonly=True, autocommit=True)` and issues two `SELECT` statements; object storage is reached only via `get_object`. See Q4. |

Pass ran to completion.

---

## Part A — What was built

Two commits:

| Commit | Content |
|---|---|
| `6ca33fc` | Read-only discovery of persisted shapes for report `dfd17248` (script + JSON + MD artefact) |
| `0489f58` | `app/reports/eval/bundle_export.py`, `app/reports/eval/scorecard.py`, decision log D-083, smoke wiring |

The package adds two library modules and two owner-triggered CLIs. `export_scoreable_bundle()` maps an already-loaded `PersistedReportRecord` into the `ScoreableBundle` contract that PR #14 established; `emit_scorecard()` / `scorecard_to_dict()` run the existing five-layer assertion library over that bundle and format the results. The assertion library itself, the golden pack, `starvation.py` and `matching.py` are **unchanged** by this PR — `git diff` touches no file under `app/reports/eval/layers/`, `tests/fixtures/golden/`, `matching.py` or `starvation.py`.

Scope note used throughout: findings are marked **[package]** where they live in code this PR adds, and **[inherited]** where they live in PR #14 code that this package puts on the production data path.

---

## Q1 — Fidelity

**Finding: the export transcribes without renaming, aliasing or normalising.** Payloads reach the bundle through `copy.deepcopy` and nothing else — `knowledge_bank = _deep_copy(kb_raw)` (`bundle_export.py:232`), the same for `gap_analysis` (`:276`), `content_json` (`:297`) and `job_trace` (`:337`). No key is rewritten between source and bundle. Non-dict payloads are explicitly *not* coerced (`:229`, `:273`, `:294`, `:340`). Unobserved root keys are recorded and carried, not dropped (`_collect_unknown_keys`, `:127`).

Verified by execution against the target tree: mutating the exported bundle leaves the source record untouched, so the deep copy is real and not a shared reference.

```
source mutated? False | source now: {'facts': {'a.b': {'value': 1}}, 'schema_version': '1'}
```

**Places where two differently-named keys are treated as one.** None inside the export. Three on the package's data path:

1. **[inherited] `bundle_schema.py:49`** — `bundle_id=str(raw.get("bundle_id") or raw.get("report_id") or "unknown")`. Two differently-named keys resolve to one field. This is on the emitter's live path: `scorecard_emit.py` reloads the bundle file through `ScoreableBundle.from_dict` before scoring. Executed: `ScoreableBundle.from_dict({'report_id': 'RID-only'}).bundle_id` returns `RID-only`.
2. **[inherited] `matching.py:1–8, 65`** — the module docstring states the rule: *"Match by normalised value + source document — never by engine fact_key."* `_bank_match_candidates` (`l1_assertions.py:31`) drops the fact key entirely. At match time two differently-named keys carrying the same normalised value and source are interchangeable. This is a documented D-040/D-041 decision, not a defect introduced here, but it is the answer to the question as asked, and it acquires force from the finding below.
3. **[package, observational only] `_extract_model_config` (`bundle_export.py:139`)** flattens `model_used` from three locations into one dict. The keys are namespaced (`knowledge_bank.agent_trace.model_used`, `gap_analysis.agent_trace.model_used`, `agent_trace.stages.<name>.model_used`), so nothing merges, and the values remain in the deep copies as well.

**Related evidence — the persisted record carries two naming families for the same indicator set.** From the committed discovery artefact, `knowledge_bank_json.facts` is a flat object of 152 dotted keys carrying both:

```
indicators.OP1.1 … indicators.OP4.3                       (10 upper-dotted prefixes)
indicators.op1_1_girls_reenrolled … op4_3_actors_trained  (12 snake prefixes)
```

In this reference record the two families are complementary rather than duplicative — each indicator's `value` is populated under one style only (`OP1.2.actual='472'` with `op1_2_girls_attending_80pct.actual` absent; `op1_1_girls_reenrolled.actual=684` with `OP1.1.actual` absent) — so no collision is observed here. The export does not merge them; it transcribes both exactly.

**Gap in the export's own fidelity observation.** `_fact_key_prefix_families` (`bundle_export.py:110`) splits each key on the *first* `.` only. For this record every indicator key, in both naming styles, collapses to the single family `indicators`. The observation that the module emits to disclose naming heterogeneity therefore cannot surface the naming split that is actually present in the data. No test covers this.

---

## Q2 — No reconstruction

**Finding: nothing is inferred or defaulted in the library.** There is no fallback value, no `setdefault`, no derived field. Stages with nothing persisted are omitted from `stages_present` rather than coerced to empty containers — the docstring states the intent (`bundle_export.py:175`) and the four stage branches implement it.

**The empty collection is recorded as absent.** Confirmed by code and by test. `indicator_actuals_json` empty or null produces the observation

> `indicator_actuals_json: empty or null — recorded as absent; not populated, inferred, or reconstructed from any other collection`

and the `meta["indicator_actuals_json"]` key is **not written** (`bundle_export.py:315`, `:377`). `indicator_actuals` is not a `ScoreableBundle` stage, so it also never enters `stages_present`. Covered by `test_empty_indicator_actuals_recorded_as_absent_not_reconstructed`, which asserts both halves.

**Three places where absence is lossy:**

1. **[package] `_is_empty_json_value` (`bundle_export.py:96`) conflates a persisted NULL with a persisted `{}`.** Both produce byte-identical observation text, so the record cannot distinguish "column was NULL" from "column held an empty object". Executed:

```
NULL  obs: ['knowledge_bank: persisted payload absent or empty — stage omitted from stages_present']
EMPTY obs: ['knowledge_bank: persisted payload absent or empty — stage omitted from stages_present']
identical observation text: True
```

2. **[package] `bundle_export_run.py:106–107` invents a value on the production path.** The CLI builds the record with

```python
reporting_period_start=str(row.get("reporting_period_start")),
reporting_period_end=str(row.get("reporting_period_end")),
```

`str(None)` is `'None'`. A NULL reporting period is therefore transcribed into `meta["report_meta"]` as the four-character string `"None"` — a non-null value that was never persisted. This is the only place in the package where a value is created rather than carried. The two adjacent fields (`status`, `version`) are passed through unwrapped, so the coercion is not uniform. The CLI has no test.

3. **[inherited] `ScoreableBundle.from_dict` (`bundle_schema.py:50–55`)** rebuilds missing payloads as `{}` and missing `export_text` as `""`. On the `scorecard_emit.py` reload path absence survives only through `stages_present`, which is preserved verbatim.

---

## Q3 — No tuning

**Finding: the emitter reports and does not judge.** Exhaustive scan of the package for comparison and target vocabulary (`>=`, `<=`, `> N`, `< N`, `threshold`, `baseline`, `expected`, `pass_mark`, `ratchet`, `previous`, `prior`) returns:

- six matches in `bundle_export.py`, all inside f-strings for `unexpected type` observations, plus `len(families) > 1`;
- five matches in `scorecard.py`, all in prose or flags declaring the absence (`"no_threshold": True`, `"no_expected_comparison": True`, the Notes line);
- one match in `scorecard_emit.py`, in the module docstring.

No expected figure, no pass mark, no comparison to a prior result, no baseline, no ratchet.

**The emitter does not surface a certification.** `scorecard.py` imports `run_all_layers` but **not** `gate_verdict`, so `gate_pass`, `blocking_failures` and `demonstrated_safety_count` are never computed or printed. `test_scorecard_separates_judged_from_starvation_and_carries_provenance` asserts `"gate_pass" not in md`. The Notes block states that PASS-BY-STARVATION is not a demonstrated safety property and that ADVISORY outcomes are not certifications.

**Observation.** The non-judgement claims are asserted, not derived: the markdown prints the sentence *"No threshold, baseline, ratchet, or expected-result comparison is applied"* and the structured form emits `report_only: True`, `no_threshold: True`, `no_expected_comparison: True` as literals. A reader cannot distinguish a genuinely non-judging emitter from one carrying the flags. The distinction here rests on the code scan above, not on the artefact's self-description.

**Bounded note on figures in the tree.** The verdicts the scorecard reports are produced by the assertion library, which does hold the golden answer key and the eighteen deterministic forbidden-output patterns (`layers/l5_assertions.py:15–43`, unchanged by this PR). Separately, the committed discovery artefact carries observed production values that coincide with golden-record content for this case — `award_budget.amount = 1240000`, `op1_1_girls_reenrolled.actual = 684`, `.target = 1200`, `OP1.2.actual = '472'`, `OP3.1.actual = '392'`, `grant_reference = MWI-EDU-AR-4471` — because report `dfd17248` is a production run of the golden case. These are observations of what the engine persisted. No code in the package reads the discovery artefact at runtime; the mapping references it only as a provenance string in `meta["discovery_artefact"]`.

---

## Q4 — Read-only and safe

**No engine or model call.** A search of the entire `app/reports/eval/` package for `openai`, `prompt_runner`, `requests.`, `httpx`, `anthropic`, `.chat.` and client construction returns **zero matches**. `bundle_export.py` imports only `copy`, `subprocess`, `dataclasses`, `datetime`, `typing` and `bundle_schema`. `scorecard.py` imports only sibling eval modules. The Layer 4 prose arm is deterministic; nothing in the scoring path reaches a model.

The single subprocess in library code is `resolve_git_commit()` (`bundle_export.py:157`), `git rev-parse HEAD` with `stderr` suppressed and `""` on failure.

**No production write.**

- `bundle_export_run.py:_load_record` — `conn.set_session(readonly=True, autocommit=True)` (server-enforced `default_transaction_read_only`), then two `SELECT` statements (`donor_reports` by id; latest `report_jobs` row). No DML anywhere in the file.
- `_fetch_export_plaintext` — `DocumentStorageService().fetch_bytes(storage_ref)`, which is `client.get_object` (`document_storage_service.py:74`). The service's `upload_bytes` and `delete_object` are not referenced. The DOCX is read, never re-rendered or re-uploaded.
- `scorecard_emit.py` — reads a local file, writes local files. No database or storage import.
- Both CLIs write only to the owner-supplied `--out` / `--json-out` paths.

**Credential handling, for the record.** `--railway` shells out to `railway variables --json --service Postgres` and assigns `DATABASE_PUBLIC_URL` (falling back to `DATABASE_URL`) into `os.environ`. The read-only guarantee is a session attribute set by the client, not a read-only database role; the credential itself carries whatever rights the Postgres service grants.

**Identifiable organisation data.**

*In the bundle:* the bundle carries what the record carries — for this case, golden-case content. It is never committed; `bundle_export_run.py:157` prints `NOTE: do not commit this bundle file — it may contain identifiable organisation content.` That notice is advisory: no `.gitignore` entry, hook or path convention enforces it, and the default `--out` is owner-chosen with no constraint.

*In the committed discovery artefact* (`BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json`, 1.16 MB, +35,642 lines): the redaction is partial and the field name overstates it. Counted across the artefact:

```
string samples: fully disclosed (len<=48): 962; truncated prefixes: 172; path/identity redacted: 198
```

`_redact_scalar` (`bundle_export_discovery.py:80`) emits `prefix_redacted = value[:48]`, so for any string of 48 characters or fewer the field named `prefix_redacted` holds the **entire value**. Examples from the artefact: `report_meta.funder_name_redacted.prefix_redacted = "Foreign, Commonwealth & Development Office"` with `length: 42`; `facts.grant_reference.value → "MWI-EDU-AR-4471"`; `facts.funder.value → "FCDO"`. Numeric values bypass the redaction path entirely — 29 integers are emitted in full, including `award_budget.amount = 1240000`. Free-text keys leak 48-character prefixes: `conflicts[0].annotation` (length 597) begins `"The winning proposal (01) states a target of 1,2"`. Path-like and identity-bearing strings *are* replaced with `[redacted_path_or_identity]` (198 of them), and uploaded-document bodies are not dumped.

Measured against the question as asked — organisation data beyond what the golden record already contains — the organisation-identifying content in the artefact (funder, programme code, contract value, grant period, indicator values) is material the golden record already holds. What the artefact adds beyond the golden record is system data, not organisation data: production report/job/document UUIDs, a storage-ref digest, model identity (`claude-sonnet-4-6`), token counts and latency.

**Governance position of that artefact.** `.governance/blocklist.json` lists `docs/` under `path_scopes.guard_excluded_from_string_scan`, so `check_funder_fixture_lines` returns early for this path and the funder-identity token list (which contains `FCDO` and the full department name) was never applied to it. `group5_sealed_tokens` is empty, so the everywhere-blocked check finds nothing. The artefact's presence in the tree is permitted by configuration; `governance-guards` passing on this PR is consistent with that exclusion and is not an inspection of the artefact's contents.

---

## Q5 — Provenance and coverage

### Provenance carried

| Element | Present | Evidence |
|---|---|---|
| commit | yes, with caveat below | `scorecard.py:56–58, 68`; `git_commit` argument or `bundle.meta["git_commit"]`, rendered as `(unknown)` when empty |
| dataset version | yes | `scorecard.py:70` — `pack.dataset_version` |
| checksum | yes | `scorecard.py:71` — `pack.content_checksum` |
| run identity | yes | `scorecard.py:72–73` — `bundle_id` (= `report_id`) and `bundle.provenance` |
| exported_at, stages_present, model_config | yes | `scorecard.py:74–83` |

Both the markdown and `scorecard_to_dict` carry all five. `test_scorecard_separates_judged_from_starvation_and_carries_provenance` asserts commit, dataset version, checksum and run id.

**Caveat on `git_commit`.** The value is the HEAD of whatever working tree the exporting process runs in (`bundle_export.py:157`), captured at export time. It identifies the audit tooling, not the engine build that produced the persisted report — the report was written by a deployed worker at an earlier commit, and nothing in the persisted record supplies that commit. The scorecard labels the field `git_commit` without that distinction. If `git` is unavailable the field silently becomes `""` and prints as `(unknown)`; no test covers that path.

### Starvation shown separately

Yes. `_partition` (`scorecard.py:33`) splits on `Verdict.PASS_BY_STARVATION`; each layer prints a `### Judged` section and a `### Nothing to judge (stage absent / starvation)` section with per-layer counts, and `scorecard_to_dict` mirrors the split as `judged` / `nothing_to_judge`. The Notes block states that starvation is not a demonstrated safety property. Asserted by test on an all-starved bundle.

### All five layers have their inputs — **no, one gap**

Executed against the target tree, exporting the constructed record and scoring it:

```
stages_present: ['knowledge_bank', 'gaps', 'content', 'export']
export_text repr: ''
L1: judged=3  starved=0
L2: judged=3  starved=0
L3: judged=3  starved=0
L4: judged=4  starved=0
L5: judged=18 starved=0   verdicts={'PASS': 14, 'ADVISORY': 3, 'REVIEW-REQUIRED': 1}
```

Layers 1–4 receive their inputs from the transcribed payloads; the flat dotted `facts` object is handled by `_bank_facts` (`l1_assertions.py:14`), which materialises it to rows, so the production shape does reach Layer 1.

Layer 5 is the gap. `bundle_export.py:299–307` marks `STAGE_EXPORT` present from `content_json.export` **metadata alone**, while `export_text` remains `""` unless the owner passes `--fetch-export-text`. Layer 5's corpus is `export_text + str(content_json) + str(gap_analysis)` (`l5_assertions.py:49–54`). On the default export path the exported document's prose is absent from that corpus, yet all eighteen forbidden-output assertions are reported as **judged**, fourteen of them PASS, and none as starved.

Nothing marks the shortfall. `REQUIRED_STAGE_BY_FAMILY` declares `"l5_forbidden_export": STAGE_EXPORT` (`starvation.py:20`), but a search of `app/reports/eval/layers/` for `l5_forbidden_export` returns **no hits** — the family is never used, so the export stage's presence or absence can never produce a PASS-BY-STARVATION verdict. Layer 5 routes only to `l5_forbidden_content` and `l5_forbidden_gaps`.

The single disclosure is oblique: the export writes the observation `export_text: not supplied — left empty; mapping does not fetch or render DOCX` into `meta["observations"]`, and the scorecard does print the observations block. A reader who reaches that line can infer the gap; the layer's own counts state the opposite. `stages_present` in the provenance block lists `export`.

**[inherited] related.** The same corpus stringifies `content_json` and `gap_analysis` with `str()`, so Layer 5's deterministic patterns run against a Python repr including keys and punctuation rather than rendered prose. Unchanged by this PR; recorded because this package is what puts production payloads into that corpus.

### Tests

`tests/test_p0_bundle_export_scorecard.py`, 11 tests, wired into the `smoke` job (`smoke-test.yml:131–135`). Executed against the target tree: **11 passed, 0 failed**, matching the PR's claim.

| Test | Criterion covered |
|---|---|
| `test_export_transcribes_facts_object_keys_exactly` | keys transcribed exactly, source fields unaliased, family observation emitted |
| `test_export_carries_conflicts_and_gap_questions_intact` | conflicts and gap question/rationale intact; `gaps` not aliased to `questions` |
| `test_export_preserves_section_claims_and_bindings` | claim `bind_status`, `source_refs`, section text preserved |
| `test_empty_indicator_actuals_recorded_as_absent_not_reconstructed` | empty collection recorded as absent, meta key omitted |
| `test_absent_knowledge_bank_omits_stage` | absent stage omitted from `stages_present` |
| `test_export_stage_from_persisted_export_metadata` | export stage from metadata; `export_text` empty; observation emitted |
| `test_export_text_optional_owner_supplied` | owner-supplied plaintext path |
| `test_unobserved_root_key_recorded_and_transcribed` | unobserved key observed and carried, not dropped |
| `test_bundle_carries_report_identity_timestamp_commit` | report id, commit, timestamp, status, provenance, model_config |
| `test_scorecard_separates_judged_from_starvation_and_carries_provenance` | starvation split; commit/version/checksum/run id; `gate_pass` absent; no-threshold line |
| `test_scorecard_judged_section_populated_when_stages_present` | judged section populated when stages present |

**Acceptance criteria with no test.** Taken from the D-083 decision-log entry and the PR's stated invariants:

1. **"No production writes"** — no test. The read-only session, the SELECT-only queries and the absence of DML are established by inspection only.
2. **"Does not call the engine or any model"** — no test. Established by inspection only.
3. **Both CLIs** (`bundle_export_run.py`, `scorecard_emit.py`) — no test of any kind. This is the file containing the `str(None)` → `"None"` coercion in Q2, the readonly-session call, and the S3 fetch.
4. **"Report metadata transcribed without reconciling disagreements against the fact collection"** — no test; only `status` is asserted, in the identity test.
5. **Deep-copy isolation** (export does not mutate the source record) — no test; verified manually in this pass.
6. **`bundle_to_export_dict`** — no test, though it is the serialiser the export CLI writes through.
7. **`resolve_git_commit` failure path** (`""` → `(unknown)`) — no test.
8. **The four "unexpected type — not coerced" branches** (`kb`, `gaps`, `content`, `trace`) — no test; every test passes well-formed dicts.
9. **The `content_json.export` empty-object branch** ("export stage not added from metadata alone") — no test.
10. **Round-trip through `ScoreableBundle.from_dict`** — no test, although that is the emitter's actual input path in `scorecard_emit.py`, and the path carrying the `bundle_id`/`report_id` fallback from Q1 and the `{}` / `""` coercions from Q2.
11. **Export-stage coverage disclosure** — no test, and by Q5 no assertion is marked starved when `export_text` is empty.
12. **`_fact_key_prefix_families` depth** — no test; the single family test asserts only that *some* multi-family observation appears, on a fixture whose keys differ at the first segment.

---

## Summary of findings

| # | Question | Scope | Finding |
|---|---|---|---|
| 1 | Q1 | inherited | `bundle_schema.py:49` resolves `bundle_id` or `report_id` to one field, on the emitter's reload path |
| 2 | Q1 | inherited | `matching.py` discards the fact key by design; differently-named keys with equal normalised value+source are interchangeable at match time |
| 3 | Q1 | package | `_fact_key_prefix_families` splits on the first `.` only, so the two indicator naming families present in the persisted record collapse to one family in the observation |
| 4 | Q2 | package | `bundle_export_run.py:106–107` — `str(None)` writes `"None"` into `report_meta` for a NULL reporting period; the only invented value found |
| 5 | Q2 | package | `_is_empty_json_value` conflates persisted NULL with persisted `{}`; identical observation text for both |
| 6 | Q4 | package | Committed discovery artefact: 962 short strings fully disclosed under a field named `prefix_redacted`; 29 integers unredacted; 48-char free-text prefixes. Content is within golden-record scope; additions beyond it are system identifiers |
| 7 | Q4 | package | "Do not commit this bundle" is an advisory print with no `.gitignore`, hook or path constraint behind it |
| 8 | Q5 | package | `git_commit` is the exporter's HEAD, not the engine build that produced the persisted report |
| 9 | Q5 | package + inherited | Export stage marked present from metadata while `export_text` is empty; `l5_forbidden_export` is declared in the starvation map but referenced nowhere, so all 18 Layer 5 assertions report as judged without the exported document |
| 10 | Q5 | package | Twelve acceptance criteria with no test, including both CLIs, the no-write claim and the no-model-call claim |

Answers as asked: **Q1 yes** for the export itself, with three key-identity findings on its path. **Q2 yes** for the library, with one invented value in the CLI; the empty collection is recorded as absent. **Q3 yes** — the emitter reports and does not judge. **Q4 yes** — no engine or model call, no production write; the bundle carries no organisation data beyond the golden record's content. **Q5 partial** — provenance is complete with a commit-identity caveat, starvation is shown separately, but Layer 5 does not have its export input and the scorecard does not say so.
