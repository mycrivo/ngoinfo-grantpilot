# INDEPENDENT AUDIT — Package 1 PRs (pre-merge, Layer 2 gate)

**Date:** 2026-07-19
**Auditor role:** Independent read-only auditor (Layer 2 merge gate). No fixes, no refactors, no product commits — findings only.
**Scope:**

- Backend: `mycrivo/ngoinfo-grantpilot` PR #10 (`feat/gate1-conflict-integrity`, head `46157ab`, base `9fa406d`, 16 files, +1001/−14)
- Frontend: `mycrivo/grantpilot-frontend` PR #3 — **not auditable from this session** (see verdict section)

**References audited against:** committed diagnostic report [`GATE1_CONFLICT_SAVE_AND_FACTS_PAYLOAD_DIAG_2026-07-19.md`](GATE1_CONFLICT_SAVE_AND_FACTS_PAYLOAD_DIAG_2026-07-19.md) and the plan-of-record. Note: no separate plan/approval file exists in the repo — the approved plan and the owner's five amendments exist in-repo only as the D-058–D-062 decision-log narrative added by this PR. That narrative was verified internally consistent with the amendment brief and used as the plan-of-record.

**Method:** full diff read; line-level tracing of every value path into the knowledge bank and resolutions; test-suite diffing (numstat, word-diff, skip/xfail sweep); local test execution at head and at the parent commit (red-run witness); full-suite head-vs-base differential; five auditor-constructed behavioral probes against the sibling-marking and invariant edge cases.

---

## VERDICT — Backend PR #10: **APPROVE WITH FIXES**

The moat holds on every path in the diff: no invention, no auto-resolution, no loosened guard, no repair-scope widening — none of the brief's BLOCKING triggers fired. The verdict is not plain APPROVE because three NON-BLOCKING findings (F1, F2, F3) sit against explicitly specified bounds of the approved plan — two against the D-061 repair evidence design, one against seam-level test coverage — so check 8 is not certified as fully met as shipped. **F1/F2 should be remediated before the post-deploy D-061 repair round executes; the product-code merge itself is safe.**

## VERDICT — Frontend PR #3: **CANNOT COMPLETE — NO VERDICT ISSUED**

The audit session's GitHub access is scoped to `mycrivo/ngoinfo-grantpilot` only; direct reads of `mycrivo/grantpilot-frontend` were denied and the scope-management tooling was unavailable. Not one line of the frontend diff was read. The following checks were **not performed and are explicitly not passed**: frontend halves of checks 2 and 3, check 5 (deterministic card explanation), check 6 (copy sweep, error-map coverage of the new domain code, copy-scan test coverage, shipped-vs-approved copy), check 7 (frontend test diffing), and the frontend portions of checks 9 and 11. The Layer 2 gate for PR #3 remains unsatisfied — it requires a re-scoped audit session. This report must not be treated as certifying PR #3.

---

## Findings — Backend PR #10

All findings NON-BLOCKING. Line numbers refer to PR head `46157ab`.

| # | File:line | Class | Finding |
|---|-----------|-------|---------|
| F1 | `scripts/audit/gate1_orphan_repair_cb090edb.py:118-131` | NON-BLOCKING | Dry-run does not produce an exact diff as the audited bounds specify — evidence carries pre/post SHA-256, repair records, and a facts-key preview, but no postimage or field-level diff, so the owner cannot inspect the exact stub contents before apply. |
| F2 | `scripts/audit/gate1_orphan_repair_cb090edb.py:104-116,150-156` | NON-BLOCKING | Apply-mode CAS anchors to the apply run's own pre-transaction read, not the dry-run invocation's snapshot; the STOP message "row changed since dry-run snapshot" overstates the guarantee — drift between dry-run and apply invocations is silently re-normalized (mitigated: `_prepare` re-runs all STOP checks at apply time). |
| F3 | `app/reports/services/knowledge_bank_reconciliation_service.py:77` | NON-BLOCKING | No test exercises orphan normalization through the actual persist seam (`reconcile_and_persist`); coverage is unit-level (normalizer function) and API-level (PATCH after manually calling the normalizer). The seam wiring executes only incidentally in `test_service_persists_complete` with a well-formed KB — a wiring regression would not be caught. |
| F4 | `app/reports/knowledge/conflict_integrity.py:18-31,113-126` | NON-BLOCKING | "Exact value" correspondence is normalization-based, not byte-exact: whitespace/number/boolean representation variants match (probe: sibling `"2025-10-14 "` was marked against candidate `"2025-10-14"`), and `None` collapses with blank strings, so a blank-string sibling can match a null candidate. Failure direction remains conservative (see check 4). |
| F5 | `app/reports/knowledge/conflict_integrity.py:149-151,183-185` | NON-BLOCKING | An empty-string conflict `fact_key` passes the invariant silently (skipped by both the repair loop and the post-condition). Unreachable at the product seam (`KnowledgeBankConflict.fact_key` has `min_length=1`); reachable only via the repair script's raw-DB preimage path. A whitespace-only key fails closed with `ValueError` (the reconcile run dies loudly rather than persisting). |
| F6 | `app/reports/knowledge/conflict_integrity.py:195-208` | NON-BLOCKING | Repair trace is recorded in `knowledge_bank_json.agent_trace.conflict_integrity_repairs`, not `report_jobs.agent_trace_json`. Matches the committed decision text, but diverges from the module's standard trace store, so cost/inspection tooling reading `report_jobs` will not see these events. |
| F7 | `scripts/audit/gate1_orphan_repair_cb090edb.py:30` (docstring L1-6) | NON-BLOCKING | The repair script does not verify the fleet scan ran GREEN first — the Phase A→B ordering is procedural only. Blast radius remains bounded to the constant report id regardless. |
| F8 | `app/reports/knowledge/conflict_integrity.py:75` | NON-BLOCKING | Stub fallback `source_document_id: "unresolved-conflict"` places a synthetic token in a field that otherwise carries real document ids (only when a conflict has no dict candidates); the display field is `source_label` ("Uploaded document"), so no user-facing leak observed. |
| F9 | PR head CI | NON-BLOCKING | No CI check runs are reported on head `46157ab` at audit time (`get_status`: 0 checks). The repo's own CI has not certified this head; the auditor's local run of the smoke selection is green (266 passed / 24 skipped) but does not substitute for CI. |

**Environment note (not a PR finding):** `tests/test_me_module_worker.py::test_outcome_1_concurrent_claim_only_one_wins` is flaky at **both** revisions in the audit environment (8/10 pass at head, 9/10 at base); it is outside the smoke selection and untouched by the diff.

---

## Check-by-check results — Backend PR #10

### 1. Moat — no invention: PASS

Every path by which a value can enter the KB or a resolution was traced. The seam normalizer's stub is `value: None`, `verification_status: "unverified"`, `confirmed/confirmed_by_user: False` (`conflict_integrity.py:84,92-96`); it copies only provenance metadata (source id/label/excerpt) from an anchor candidate, never a value, and never touches `conflict.resolved_value`. The repair script can only run that same normalizer and hard-STOPs if a value appears on the stub or `resolved_value` changes (`gate1_orphan_repair_cb090edb.py:59-69`) — no flag or input makes it write a resolution. Resolution requires an explicit human non-null, non-blank value (`knowledge_bank_patch_service.py:72-83`, called at `:93` as the first statement); the resolved canonical fact becomes citable only with `gate1_confirmed_at` set plus human confirmation flags (`confirmed_kb.py:34-46`), and Gate 1 confirm remains blocked while any conflict is unresolved (`knowledge_bank_reconciliation_v1.py`, `validate_gate1_knowledge_bank`, unchanged). No auto-resolve, default, or invention path exists in the diff.

### 2. Fail-closed guards unchanged: PASS

The `KB_PATCH_VALIDATION_FAILED` missing-fact guard has zero diff hunks touching it (`knowledge_bank_patch_service.py:100-126`) and its strictness is witnessed behaviorally: the PR's own guard test passes identically against the parent commit and head. The post-normalization invariant raises `ValueError` inside `ensure_conflicts_materializable` before the return value is assigned to `report.knowledge_bank_json` (`knowledge_bank_reconciliation_service.py:76-81`) — fails closed before DB assignment. Null AND blank-string (`""`, `"   "`) resolved values are rejected with the dedicated `KB_CONFLICT_RESOLUTION_VALUE_REQUIRED` 422 before any mutation; the PATCH operates on a deepcopy assigned only after all resolutions succeed (`:238,:258`), so the whole request is atomic.

### 3. Amendment 1 — loud normalization: PASS (backend)

Every repair appends a trace record carrying report id, conflict key, stub flag, and every provenance-only key (`conflict_integrity.py:195-208`) and emits a WARNING log with the same fields (`:210-217`). The product seam and the repair script both call with `emit_log=True`; the dry-run evidence also carries the trace. The caplog regression test asserts the WARNING (`tests/test_conflict_integrity.py:131`). No silent path exists in the diff. Frontend half: not verifiable (see PR #3 verdict).

### 4. Amendment 2 — conservative sibling marking: PASS (with F4 nuance)

Marking requires the key relationship (`conflict_key + "_"|"."` prefix, `conflict_integrity.py:44-47`) AND exactly one candidate matching on both value and `source_document_id` (`:113-126`); anything else is left unmarked. Failure direction verified three ways: the committed `test_inexact_sibling_not_marked`, plus two auditor probes — value-matches-but-source-differs → NOT marked; two identical candidates (ambiguous) → NOT marked. Uncertainty produces visible duplication, never de-citation.

### 5. Amendment 3 — the card keeps its story: CANNOT COMPLETE (frontend)

The rendering change is in PR #3. Backend-side: the deterministic humanized label (`conflict_integrity.py:34-46`, e.g. "Reporting period — End") contains no fact keys, gate numbers, agent names, or slugs; the raw annotation remains data-only in the payload, unrendered by anything in this diff.

### 6. Internal identifiers: backend PASS; frontend CANNOT COMPLETE

New backend user-visible strings — the humanized label, "Uploaded document", and the unresolved-conflict provenance excerpt — are clean plain English. `details.fact_key` on the new error continues the pre-existing error-details pattern and, per the diagnostic, unknown codes fall to the frontend's generic fallback string (not the server message), so no leak path was introduced. Whether the frontend error map covers `KB_CONFLICT_RESOLUTION_VALUE_REQUIRED`/`KB_PATCH_VALIDATION_FAILED`, the card/explicit-entry/disabled/saving copy, the copy-scan test's coverage, and shipped-vs-approved copy could not be verified.

### 7. Anti-bent-ruler: PASS

Numstat shows zero deletions across all four test files; the smoke workflow word-diff is a pure insertion of `tests/test_conflict_integrity.py`; no skip/xfail/marker appears in any added line; no assertion was weakened.

**Red-run witnessed against the parent commit (`9fa406d`):**

- `test_provenance_only_fact_not_citable` — fails red at base, passes at head (citability fence genuinely new)
- `test_null_and_blank_resolved_value_return_dedicated_code` — fails red at base, passes at head (dedicated 422 code genuinely new)
- `test_repaired_orphan_resolves_via_patch_candidate_and_explicit_entry` — fails red at base, passes at head
- `test_filter_exportable_facts_drops_provenance_only_siblings` — fails red at base, passes at head (export fence genuinely new)
- `test_unrepaired_orphan_still_strict_missing_fact` — **passes at both** base and head, proving the missing-fact guard unchanged

Full-suite differential head-vs-base: no pre-existing test outcome changed (smoke selection: 256 → 266 passed, identical 24 skips; the three new PATCH integration tests error in whole-suite mode exactly like their two pre-existing siblings do at base — a pre-existing cross-file fixture issue; they pass standalone).

**Test inventory** (matches the PR body's enumeration of four files):

| Test | Characterization |
|------|------------------|
| `test_conflict_integrity.py::test_orphan_shape_normalized_creates_stub_and_marks_exact_siblings` | Prod-shaped orphan → null/unverified/unconfirmed stub, both siblings marked, trace + WARNING (Amendment 1 emit regression) |
| `test_conflict_integrity.py::test_unrelated_fact_not_marked_provenance_only` | Key-relationship boundary — unrelated key never marked |
| `test_conflict_integrity.py::test_inexact_sibling_not_marked` | Amendment 2 failure direction — inexact value left unmarked |
| `test_conflict_integrity.py::test_repaired_orphan_resolves_concrete_and_explicit` | Candidate + owner-entered resolution; citability on canonical, off for sibling |
| `test_conflict_integrity.py::test_null_and_blank_resolved_value_rejected` | D-059 unit-level: None/""/"   " → dedicated 422 |
| `test_conflict_integrity.py::test_missing_fact_guard_still_strict_without_normalizer` | Anti-bent-ruler: unrepaired orphan still 422 `KB_PATCH_VALIDATION_FAILED` |
| `test_knowledge_bank_patch.py::test_repaired_orphan_resolves_via_patch_candidate_and_explicit_entry` | API-level: repaired orphan resolves via both branches |
| `test_knowledge_bank_patch.py::test_null_and_blank_resolved_value_return_dedicated_code` | API-level: null/blank → 422 `KB_CONFLICT_RESOLUTION_VALUE_REQUIRED` |
| `test_knowledge_bank_patch.py::test_unrepaired_orphan_still_strict_missing_fact` | API-level anti-bent-ruler: guard unchanged |
| `test_confirmed_kb.py::test_provenance_only_fact_not_citable` | Provenance-only sibling never citable; canonical citable |
| `test_docx_renderer.py::test_filter_exportable_facts_drops_provenance_only_siblings` | Export table input excludes provenance-only siblings |

Note: `test_docx_renderer.py` is listed in the PR's test plan but is not part of the smoke workflow line (it never was).

### 8. Repair and scan scripts: PASS with F1/F2/F7

The fleet scan performs one parameterized SELECT and no DB writes (`gate1_orphan_fleet_scan.py:52-66`), STOPs (exit 2) on any orphan outside the authorized id, on >1 orphan key, or on a set gate stamp (`:89,:97,:100`). The repair is hard-scoped to the constant `cb090edb-715b-41cb-b3be-61c006fbdb55` id (`:30`); argparse accepts only `--apply` — there is **no argument or environment variable that widens report scope**. It snapshots and SHA-256-hashes the preimage, aborts if `gate1_confirmed_at` is set, applies under `FOR UPDATE` with an in-transaction hash re-check and `rowcount==1` check inside a transaction (abort → rollback), and touches only `knowledge_bank_json` (+`updated_at`) on that one row — never candidate values, `resolved_value`, gate stamps, jobs, content, or templates (`_prepare` STOPs enforce this). The dry-run/CAS evidence gaps are F1/F2.

### 9. Scope discipline: PASS

No files under `app/reports/agents/` (reconciler prompt/model untouched); `tests/reconciliation_grading.py` diff is zero lines (E1 grader/answer key untouched); no alembic/migration files; synthesis, gap, and template code untouched — the fence lands solely via `confirmed_kb.py:37-40` and `docx_renderer.py:204-207`, exactly the citability and export fences the plan authorized (downstream consumers inherit it through existing `is_fact_citable`/`filter_citable_facts` calls without being edited); nothing touches auth, entitlements, or facts-screen code; the workflow change adds one test file.

### 10. Governance completeness: PASS

The decision-log table head at base is D-057 with zero pre-existing D-058+ occurrences; the PR appends D-058–D-062 with the Amendment 5 numbering note. The D-059 narrative quotes D-043's operative rule **verbatim** — compared word-for-word against the original D-043 row: identical. O-010 names `assert_no_spurious_conflicts` in `tests/reconciliation_grading.py` (exists at line 237, untouched) as the open grader-alignment follow-up, per Amendment 4. `API_CONTRACT.md` (PATCH rules + four error-table rows) and `DB_FIELD_CONTRACT_DONOR_REPORTS.md` (`provenance_only_for`, citability rule, D-058 invariant) are updated as promised.

### 11. Security pass: PASS

No route or authorization code changed; the PATCH path still resolves ownership via `get_owned_donor_report` (unchanged), and the new tests exercise the endpoint authenticated. Scripts use fully parameterized SQL with a constant id and take `DATABASE_URL` from env/Railway bootstrap — no secrets, tokens, or connection strings anywhere in the diff or evidence output. WARNING logs and trace records carry report id, fact keys, and booleans only — no document content or values. The repair's preimage evidence file does contain full KB content, which matches the repo's existing committed-evidence practice for this exact report (`GATE1_CONFLICT_SAVE_DIAG_DB_cb090edb.json`).

---

## Auditor probe evidence (Amendment 2 / invariant edges)

Probes run against PR head code, no repo files modified:

| Probe | Input | Result |
|-------|-------|--------|
| A | Sibling value matches candidate 1, source does NOT correspond | NOT marked (duplication, not de-citation) ✓ |
| B | Two candidates share the sibling's value+source (ambiguous) | NOT marked ✓ |
| C | Sibling `"2025-10-14 "` (trailing space) vs candidate `"2025-10-14"` | MARKED — normalization counts representation variants as exact (F4) |
| D | Whitespace-only conflict `fact_key` (`" "`) | `ValueError` — fails closed, reconcile run dies loudly ✓ |
| E | Empty-string conflict `fact_key` (`""`) | Passes silently, no stub created (F5; unreachable at product seam) |

---

## Disposition

- **PR #10:** APPROVE WITH FIXES. Merge of product code is safe. F1/F2 (repair-script evidence design) should be remediated in a separately scoped fix round **before** the post-deploy D-061 scan/repair executes; F3 (seam-level regression test) recommended in the same round. F4–F9 are informational for owner disposition.
- **PR #3:** no verdict — requires an audit session with `mycrivo/grantpilot-frontend` in scope before merge.

**STOP.** Findings only; remediation returns to the builder.
