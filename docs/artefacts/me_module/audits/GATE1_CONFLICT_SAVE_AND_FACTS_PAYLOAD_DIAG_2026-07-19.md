# DIAGNOSTIC AUDIT — Gate 1 conflict-save failure + facts-screen payload shape

**Date:** 2026-07-19  
**Tier context:** AMBER (Gate 1 moat) — **this package is DIAGNOSIS-ONLY**  
**Report under study:** `cb090edb-715b-41cb-b3be-61c006fbdb55`  
**Incident window (owner):** ~10:30–10:45 UK / ~09:30–09:45 UTC  

**Invariants held:** no product code changes, no fixes, no test edits, no prod writes. Production access limited to Railway log read + one scoped SELECT.

---

## Problem 1 — Conflict resolution cannot be saved

### Stored conflict shape (read-only DB)

Evidence: [`GATE1_CONFLICT_SAVE_DIAG_DB_cb090edb.json`](GATE1_CONFLICT_SAVE_DIAG_DB_cb090edb.json)

| Field | Value |
|-------|--------|
| `conflicts[0].fact_key` | `reporting_period.end` |
| `conflict_type` | `VALUE_MISMATCH` |
| `resolved_value` / `resolved_at` | `null` / `null` |
| Candidate 1 | `value: "2025-10-14"`, source `c534314e-…` (award letter) |
| Candidate 2 | `value: null`, **same** `source_document_id` / filename |
| Annotation | Mentions `normalization_ambiguous=true` in prose; flag is **not** a structured field on the candidate object |
| Matching `facts["reporting_period.end"]` | **ABSENT** |
| Sibling facts present | `reporting_period.end_formal` (`2025-10-14`) and `reporting_period.end_inception_call` (`value: null`) — explains two Programme-summary rows |

`gate1_confirmed_at` is still null; reconciler present. Conflict remains unresolved in DB (no successful save).

### Production request log (web service)

Evidence: [`GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_2026-07-19.txt`](GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_2026-07-19.txt), filtered extract [`GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_FILTERED_2026-07-19.txt`](GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_FILTERED_2026-07-19.txt)

Immediately after successful `GET …/knowledge-bank` 200s:

```
PATCH /api/reports/cb090edb-715b-41cb-b3be-61c006fbdb55/knowledge-bank  422
PATCH /api/reports/cb090edb-715b-41cb-b3be-61c006fbdb55/knowledge-bank  422
PATCH /api/reports/cb090edb-715b-41cb-b3be-61c006fbdb55/knowledge-bank  422
```

Three PATCH failures match the three owner actions. Access log does not include response bodies; no stack traces around these lines. Earlier in the same log pull, some `GET …/cb090edb…` returned **401**, and several `POST /api/auth/refresh` returned **200** — see AUTH section below. The failing saves themselves are **422**, not 401/403.

### Frontend error mapping (why the generic banner)

| Step | Evidence |
|------|----------|
| Save path | `PATCH` via `patchKnowledgeBank` → `conflict_resolutions: [{ fact_key, resolved_value }]` — `facts/page.tsx` ~132–142; panel sends `option.value` (including `null`) — `Gate1ConflictPanel.tsx` ~23–34, ~71 |
| Banner | catch → `resolveFriendlyApiErrorMessage(…, "Failed to save conflict resolution.")` |
| `KB_PATCH_VALIDATION_FAILED` | **not** in `ME_ERROR_MESSAGE` (`me-error-messages.ts`) → falls through to that fallback |
| 401 | `api-client.ts` refreshes then usually `forceLoginRedirect()` — typically **no** save banner |

So a 422 with `KB_PATCH_VALIDATION_FAILED` is exactly what the user sees as the generic banner; 401 would more often eject the session.

### Local reproduction

1. **Null-candidate shape with matching fact entry** — all three actions succeed at `materialize_conflict_resolution` ([`GATE1_CONFLICT_SAVE_DIAG_LOCAL_REPRO.json`](GATE1_CONFLICT_SAVE_DIAG_LOCAL_REPRO.json)).  
   → Null candidate / same-source / ambiguity flag alone do **not** reject the materialize path.

2. **Prod orphan shape** — conflict on `reporting_period.end` while facts only have `…end_formal` / `…end_inception_call` ([`GATE1_CONFLICT_SAVE_DIAG_ORPHAN_REPRO.json`](GATE1_CONFLICT_SAVE_DIAG_ORPHAN_REPRO.json)):

```
KB_PATCH_VALIDATION_FAILED
"Conflict fact_key 'reporting_period.end' has no matching fact entry"
HTTP 422
```

for select-candidate-1, select-null, and enter-another — identical uniform failure.

Governing code: `knowledge_bank_patch_service.py` `materialize_conflict_resolution` requires `facts[fact_key]` to be a dict (`~103–110`).

### Hypothesis adjudication

| ID | Hypothesis | Verdict | Evidence chain |
|----|------------|---------|----------------|
| **H1 — auth** | Save failed 401/403; FE masks as generic banner | **RULED OUT** as cause of these three saves | Access log: three `PATCH …/knowledge-bank` → **422**, not 401/403. FE 401 path redirects rather than showing this banner. |
| **H2 — payload/validation** | Endpoint rejects constructed payload for this conflict shape | **CONFIRMED** (specific mechanism) | Orphan `fact_key` with no `facts` entry → `KB_PATCH_VALIDATION_FAILED` 422; FE maps that code to generic banner. Uniform failure across all three actions matches (same missing key every time). Null/same-source alone **ruled out** by local repro with matching fact entry. |
| **H3 — persistence/server** | Write fails (constraint/enum/transaction) regardless of payload | **RULED OUT** for this incident | Failure is pre-persist validation in `materialize_conflict_resolution`; no stack traces in window; orphan repro fails before DB write. |

### Named root cause

**Conflict `fact_key` `reporting_period.end` is orphaned:** the reconciler emitted a conflict under that key and left the two values as separate fact rows (`reporting_period.end_formal`, `reporting_period.end_inception_call`), but never created `facts["reporting_period.end"]`. Every Gate 1 resolution PATCH fails validation because materialization requires a fact row for the conflict key.

**Upstream inference (labelled inference):** reconciler split same-document ambiguous AR1 end into two fact keys + a third conflict key without a stub fact — novel relative to walks where conflict key == fact key.

### AUTH_REFRESH_DIAG / auth side-channel

| Signal | Result |
|--------|--------|
| Literal `AUTH_REFRESH_DIAG` lines in web logs | **0** — that print lives in audit-walk client (`scripts/audit/_common.py`), **not** in the production frontend |
| `POST /api/auth/refresh` in same log pull | Multiple **200 OK** (access log lines) — refresh endpoint was exercised successfully during the broader session |
| Relation to save failure | **Unrelated to the three 422s.** Auth expiry remains a live general concern (earlier 401 GETs exist) but is not the mechanism of this conflict-save failure |

---

## Problem 3 — Continuation with unresolved conflict

**Classification: BLOCKED before synthesis**

| Layer | Behavior | Citation |
|-------|----------|----------|
| UI | Continue control `disabled={hasUnresolvedConflicts \|\| !allClustersReviewed}` | `Gate1ReviewFacts.tsx` ~64–65, ~159–162; `Gate1StickyFooter.tsx` ~47 |
| Confirm API | Unresolved conflict (`resolved_value is None`) → validation error → 422 `GATE1_VALIDATION_FAILED` | `knowledge_bank_reconciliation_v1.py` ~147–150; `gate1_confirmation_service.py` ~167–174 |
| Downstream | Gap/synthesis require `gate1_confirmed_at` | `gate_preconditions.py` / synthesis guards (explored) |

Not carried as a disclosed gap; not silently resolved to a candidate.

**Owner observation note:** “Continue remains enabled” while “1 item needs your decision” — **INDETERMINATE vs UI perception/CSS**. Code wires `disabled` true when `unresolvedCount > 0`. Even if the button were clickable via a UI bug, confirm + preconditions still **BLOCK**. No production continue was attempted in this package.

---

## Problem 2 — Facts payload shape / matrix feasibility

Evidence: [`GATE1_FACTS_PAYLOAD_INVENTORY_cb090edb.json`](GATE1_FACTS_PAYLOAD_INVENTORY_cb090edb.json) (same SELECT as Problem 1).

### 1) Fields each fact carries

Observed non-null population (n=156 facts):

| Field | Count non-null |
|-------|----------------|
| `semantic_label`, `coverage`, `source_document_id`, `source_label`, `provenance`, `verification_status`, `confirmed`, `confirmed_by_user` | 156 |
| `value` | 155 (one null: inception-call end) |
| `unit` | 16 |
| `interpretation_note` | 4 |
| `parent_indicator`, `dimension`, `cohort`, `disaggregation` (as separate fields) | **0** |

API GET knowledge-bank passes `kb.facts` through without adding structured disaggregation metadata (`donor_report_lifecycle_service.get_knowledge_bank`).

Disaggregation identity on this report is carried as:
- a **composed** `semantic_label` string, and
- often a **path-like** `fact_key` (e.g. `indicators.OP1.1.disaggregation.male_6_11`),

not as separate parent / dimension / cohort fields.

### 2) Where the display label is composed

| Stage | Role |
|-------|------|
| Extraction / candidate build / reconciler (incl. degrade) | Compose `semantic_label` (and path keys); stored in KB |
| GET `/knowledge-bank` | Pass-through |
| Frontend | `label = fact.semantic_label ?? key`; `displayText = label + formatted value` (`knowledge-bank-view.ts` ~84–96) |

**Verdict:** labels are **stored composed** at extraction/reconciliation time, not recomposed at response/render time from structured parts.

### 3) Label inconsistency origin

Samples from this report include both short path-style labels (`OP1.1 actual disaggregation — Male age 6–11`) and long descriptive strings (`Number of girls… – Gender and Age Group – …`, `TOTAL disaggregation — …`, proposal-target wording). That variance is present in **persisted `semantic_label`**, so it originates **upstream of the UI** (extractor/reconciler/LLM/degrade composition), not from frontend formatting.

### 4) Frontend-only pivoted matrix — VERDICT

**NO**

A contract-grade indicators × cohorts matrix cannot be built from first-class structured fields in the current payload (those fields are absent). Heuristic parsing of `fact_key` / `semantic_label` is possible for many rows but is brittle and incomplete given inconsistent label composition and encoded multi-dimension tokens (e.g. `male_6_11`).

**Minimal backend change category (one line):** emit structured disaggregation metadata on each fact (parent indicator id/code, dimension type(s), cohort key/label, and actual/target role) in the knowledge-bank facts payload.

### 5) Inventory (this report)

| Group (key-prefix heuristic) | Count |
|------------------------------|------:|
| `indicators.*` | 144 |
| programme-ish | 5 |
| `reporting_period.*` | 3 |
| other / award_budget / reporting_obligations | 4 |
| **Total facts** | **156** |
| Disaggregation-like labels (heuristic) | 107 |

Consistently present: identity/source/provenance/verification/`semantic_label`.  
Consistently absent as structured fields: parent indicator, dimension, cohort, disaggregation object.

---

## Fix categories (no designs / no implementations)

| Finding | Fix CATEGORY | Suggested tier |
|---------|--------------|----------------|
| Orphan conflict key blocks all resolutions | Reconciler / KB integrity: conflict `fact_key` must have a materializable `facts` entry (or patch must resolve via candidate sources without requiring that stub) | **AMBER** |
| Generic banner hides `KB_PATCH_VALIDATION_FAILED` | FE error-map: surface domain code (or details.fact_key) on Gate 1 save | **GREEN** |
| Selecting null candidate would mark conflict “resolved” as still unresolved if fact existed | FE/BE semantics for null `resolved_value` / “—” candidate | **AMBER** (latent; not this incident’s blocker) |
| Label inconsistency / no matrix metadata | KB fact schema: structured disaggregation fields at emit time | **AMBER** |
| AUTH_REFRESH_DIAG not in prod FE; refresh 200s observed | Auth observability: prod-path diagnostics if still investigating session TTL | **GREEN** (observability) / separate auth track |
| Continue affordance vs unresolved conflict (perception) | FE disabled-state clarity only if repro shows clickable control | **GREEN** (UX) — API already BLOCKED |

---

## Evidence index

| Artefact | Role |
|----------|------|
| `GATE1_CONFLICT_SAVE_DIAG_DB_cb090edb.json` | Read-only conflict + periodish facts |
| `GATE1_FACTS_PAYLOAD_INVENTORY_cb090edb.json` | Fact field inventory |
| `GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_2026-07-19.txt` | Web access log pull |
| `GATE1_CONFLICT_SAVE_DIAG_WEB_LOGS_FILTERED_2026-07-19.txt` | Filtered lines |
| `GATE1_CONFLICT_SAVE_DIAG_LOCAL_REPRO.json` | Null-candidate materialize succeeds when fact exists |
| `GATE1_CONFLICT_SAVE_DIAG_ORPHAN_REPRO.json` | Orphan key → 422 for all three actions |

---

## STOP

Diagnosis complete. No fixes started.
