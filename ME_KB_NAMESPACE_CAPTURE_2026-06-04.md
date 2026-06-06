# M&E Knowledge-Bank Namespace Capture — Production

**Date:** 2026-06-04  
**Method:** Read-only `BEGIN READ ONLY` / `ROLLBACK` SELECT against Railway Postgres. No writes, no pipeline runs, no row edits.  
**Query tool:** One-off Python via `.venv` + `railway variables --service Postgres` (cmd.exe).

---

## Production target (confirmed)

| Field | Value |
|-------|--------|
| **Railway project** | NGOINfo-GrantPilot AI |
| **Environment** | **production** (`c139bc74-dd5e-47ed-ac75-85674599f22b`) |
| **Database service** | Postgres (EU West, online) |
| **FCDO template id** | `55f891ac-bb8b-4137-bc42-6de8ff935064` |
| **Backend URL** | `https://ngoinfo-grantpilot-production.up.railway.app` |

Confirmed via `railway status` (production) before any query.

---

## FCDO candidate reports (synthesise boundary and beyond)

Multiple FCDO rows reached Gate 2+ with synthesis content. **Namespace is not identical across rows** — reconciler output shape varies by walk/date.

| Report ID | Facts | Gap answers | Gate 1 | Gate 2 | Job stage | Sections | Notes |
|-----------|------:|------------:|:------:|:------:|-----------|----------:|-------|
| `fda69a23-7e31-4ff9-afaf-0b5486eac54b` | 74 | 41 | ✓ | ✓ | export | 8 | `financials.OP1_1.AR1_actual_spend` pattern |
| **`6643d922-150d-4000-b878-4025e7c9145a`** | **72** | 41 | ✓ | ✓ | export | 8 | **`financials.lines.op*.*.y1_*` — matches F1 emission code + F1 walk** |
| `5026ab66-9e30-413b-a823-7931c16fe435` | 71 | 41 | ✓ | ✓ | export | 8 | Prior planted-conflict walk |
| `b91ae3e0-92fb-430d-9feb-1dcd9b878b70` | 58 | 41 | ✓ | ✓ | export | 8 | `financials.lines.OP1.1.actual` (dotted OP ids) |
| `cabb8796-195b-4089-afab-94d6fe841d50` | 66 | 41 | ✓ | ✓ | critique | 8 | Mid-pipeline |
| **`fe6bf98b-70b7-46f2-9bc2-a1306546af18`** | **33** | 44 | ✓ | ✓ | critique | 8 | **Literal ~33-fact row; targets-only, no financial line facts** |
| `2c78550a-ed6b-4bb1-b6c4-058efd0a65f7` | 0 | 44 | ✓ | ✓ | synthesise | 0 | Empty `facts{}` — not usable |

### Source report used for namespace capture

**Primary (authoritative for Safe Schools seed):** `6643d922-150d-4000-b878-4025e7c9145a`

**Why not the 33-fact row alone:** `fe6bf98b` matches the “~33 facts at synthesise boundary” description (Gate 2 confirmed, job reached critique after synthesis, 8 sections), but its `facts{}` contains **proposal/target keys only** — **zero** `financials.*` or `.y1_actual` indicator actuals. A Stage F gate run on hand-confirmed Safe Schools data needs spend lines and AR1 actuals; `6643d922` is the most complete prod row whose key shapes match `F1_BLOCK_DECOMPOSITION_6643d922.md` and `emit_claim_granular_evidence()` (which binds `financials.lines.opN_N.y1_actual` / `.y1_budget`).

**Secondary reference (~33-fact row):** `fe6bf98b-70b7-46f2-9bc2-a1306546af18` — documented below for completeness.

---

## Top-level `knowledge_bank_json` structure (prod, verbatim keys)

From report **`6643d922`** (same top-level set on all reconciled rows inspected):

```
agent_trace
conflicts
facts
gap_answers
gate1_confirmed_at
gate2_confirmed_at
gate3_confirmed_at
reconciled_at
reconciler_agent
reconciliation_outcome
reconciliation_version
schema_version
unreadable_sources
```

**Reconciliation metadata (6643d922):**

| Field | Value |
|-------|--------|
| `schema_version` | `"1.0.0"` |
| `reconciliation_version` | `"1.0.0"` |
| `reconciler_agent` | `"knowledge_bank_reconciler"` |
| `reconciled_at` | `"2026-06-01T17:01:27.371862+00:00"` (ISO-8601; varies by row) |

---

## Gate-stamp representation (prod)

Stamps are **top-level ISO-8601 strings** on `knowledge_bank_json` (not nested).

**6643d922 (confirmed Gate 1 + Gate 2, pre–Gate 3 export confirm):**

```json
{
  "gate1_confirmed_at": "2026-06-01T18:37:57.940429+00:00",
  "gate2_confirmed_at": "2026-06-01T19:03:57.203042+00:00",
  "gate3_confirmed_at": null
}
```

**fe6bf98b (~33-fact row):**

```json
{
  "gate1_confirmed_at": "2026-05-31T22:18:22.219217+00:00",
  "gate2_confirmed_at": "2026-05-31T22:20:55.249108+00:00",
  "gate3_confirmed_at": null
}
```

**Seeded run must reproduce:** non-null `gate1_confirmed_at` and `gate2_confirmed_at` before synthesis; `gate3_confirmed_at` remains null until human Gate 3 confirm.

---

## Real `facts{}` key naming pattern (6643d922 — 72 keys)

E1 uses **reconciler-assigned dotted keys** (not template `item_key` strings inside `facts{}`).

### Pattern families (verbatim from prod)

| Family | Pattern | Examples (verbatim keys) |
|--------|---------|---------------------------|
| **Financial lines** | `financials.lines.op{N}_{N}.y1_actual` / `.y1_budget` | `financials.lines.op1_1.y1_actual`, `financials.lines.op2_1.y1_budget` |
| **Financial totals** | `financials.y1_actual.total`, `financials.y1_budget.total` | values `"920420"`, `"880000"` (GBP) |
| **Grant / award** | `grant.*` | `grant.award_budget.amount`, `grant.period.start`, `grant.funder` |
| **Outcome (OCM)** | `indicators.ocm{N}_*.proposal_endline_target` | `indicators.ocm1_attendance_80pct.proposal_endline_target` |
| **Output indicators** | `indicators.op{N}_{N}_*.y1_actual` / `.y1_target` / `.proposal_endline_target` | `indicators.op1_2_girls_attending_80pct.y1_actual` |
| **Objectives** | `objectives.*` | `objectives.imp1_girls_complete_basic_education` |
| **Reporting** | `reporting.*` | `reporting.annual_review_period_1.start`, `reporting.annual_review_pack_deadline`, `reporting.obligation.annual_review` |

**Not used in 6643d922 facts:** `fact:` prefix (prefix is F1/F2 citation only), `AR1_actual_spend`, `.ar1_actual`, `financials.lines.OP1.1.actual`.

### Representative facts (25 rows — keys and values verbatim from prod)

| # | Key | Value | Unit |
|---|-----|-------|------|
| 1 | `financials.lines.op1_1.y1_actual` | `174850` | GBP |
| 2 | `financials.lines.op1_1.y1_budget` | `162000` | GBP |
| 3 | `financials.lines.op1_2.y1_actual` | `98740` | GBP |
| 4 | `financials.lines.op1_2.y1_budget` | `94000` | GBP |
| 5 | `financials.lines.op2_1.y1_actual` | `148900` | GBP |
| 6 | `financials.lines.op2_1.y1_budget` | `121000` | GBP |
| 7 | `financials.lines.op3_3.y1_actual` | `24980` | GBP |
| 8 | `financials.lines.op4_3.y1_actual` | `58630` | GBP |
| 9 | `financials.y1_actual.total` | `920420` | GBP |
| 10 | `financials.y1_budget.total` | `880000` | GBP |
| 11 | `grant.award_budget.amount` | `1240000` | GBP |
| 12 | `grant.period.start` | `2024-10-15` | — |
| 13 | `grant.period.end` | `2026-10-14` | — |
| 14 | `indicators.ocm1_attendance_80pct.proposal_endline_target` | `70` | — |
| 15 | `indicators.op1_1_girls_reenrolled_retained.y1_actual` | `684` | — |
| 16 | `indicators.op1_1_girls_reenrolled_retained.y1_target` | `650` | — |
| 17 | `indicators.op1_2_girls_attending_80pct.y1_actual` | `472` | — |
| 18 | `indicators.op2_1_latrine_stances_functional.y1_actual` | `31` | — |
| 19 | `indicators.op3_3_hardship_households_followup.y1_actual` | `0.68` | — |
| 20 | `indicators.op4_3_actors_trained_reentry.y1_target` | `120` | — |
| 21 | `objectives.imp1_girls_complete_basic_education` | (text objective) | — |
| 22 | `reporting.annual_review_period_1.start` | `2024-10-15` | — |
| 23 | `reporting.annual_review_period_1.end` | `2025-10-14` | — |
| 24 | `reporting.annual_review_pack_deadline` | `2025-11-21` | — |
| 25 | `reporting.obligation.annual_review` | (obligation text) | — |

### Full fact object shape (one entry — prod)

Key `financials.lines.op1_1.y1_actual`:

```json
{
  "value": "174850",
  "unit": "GBP",
  "semantic_label": "OP1.1 Year 1 actual spend",
  "coverage": "single_source",
  "source_document_id": "3869398c-cd12-4212-94b1-90126c062aa6",
  "source_label": "BridgeLight Logframe and Finance AR1 Export.xlsx",
  "provenance": {
    "excerpt": "174850",
    "cell_ref": "Sheet1!W10",
    "section_label": null,
    "page": null,
    "char_start": null,
    "char_end": null
  },
  "interpretation_note": null,
  "confirmed": false,
  "confirmed_at": null,
  "confirmed_by_user": false
}
```

---

## Real `gap_answers{}` key naming pattern (6643d922)

Gap keys are **template item keys** — `{section_key}:{required_item_type}:{required_item_ref}`.

### Pattern

```
{section_key}:indicator:{indicator_ref}
{section_key}:table:{table_key}
```

### Representative answered gaps (verbatim keys + disposition)

| Key | disposition | source_label |
|-----|-------------|--------------|
| `summary_and_overview:indicator:overall_progress` | `answered` | `human_confirmed_gap_answer` |
| `detailed_output_scoring:indicator:output_scores` | `answered` | `human_confirmed_gap_answer` |
| `evidence_and_evaluation:indicator:data_quality_limitations` | `answered` | `human_confirmed_gap_answer` |
| `performance_and_conclusions:table:outcome_assessment` | `answered` | `human_confirmed_gap_answer` |
| `programme_management_delivery_commercial_financial:indicator:financial_delivery` | `answered` | `human_confirmed_gap_answer` |
| `risk_and_safeguarding:indicator:realised_assumptions` | `answered` | `human_confirmed_gap_answer` |
| `recommendations_and_actions:indicator:recommendations_from_current_review` | `answered` | `human_confirmed_gap_answer` |
| `value_for_money:indicator:economy` | `answered` | `human_confirmed_gap_answer` |

Skipped gaps use `"disposition": "skipped"` with `skip_reason` (e.g. `"not_applicable"`).

### Full answered gap object shape (prod)

```json
{
  "disposition": "answered",
  "answer_text": "Output scoring is populated from the BridgeLight AR1 export with proposed scores A–C and variance explanations per indicator row.",
  "responded_at": "2026-06-01T19:03:57.203042+00:00",
  "source_label": "human_confirmed_gap_answer",
  "source_document_id": null,
  "skip_reason": null,
  "provenance": {
    "source": "human_confirmed_gap_answer",
    "excerpt": "Output scoring is populated from the BridgeLight AR1 export with proposed scores A–C and variance explanations per indicator row."
  }
}
```

**F1/F2 citation form:** `gap:{item_key}` e.g. `gap:evidence_and_evaluation:indicator:data_quality_limitations` — prefix added at synthesis/critic time, **not** stored in `facts{}`.

---

## Namespace drift across prod rows (important)

Same FCDO template, **different reconciler key shapes** on different reports:

| Report | Financial key example | Indicator actual example |
|--------|----------------------|---------------------------|
| **6643d922** (use for seed) | `financials.lines.op1_1.y1_actual` | `indicators.op1_1_girls_reenrolled_retained.y1_actual` |
| fda69a23 | `financials.OP1_1.AR1_actual_spend` | `indicators.OP1_1_girls_reenrolled.AR1_actual` |
| b91ae3e0 | `financials.lines.OP1.1.actual` | `indicators.OP1.1.actual` |
| fe6bf98b (33 facts) | *(none in facts)* | `indicators.op1_1_girls_reenrolled_retained.target` only |

**Test/fixture shorthand NOT in 6643d922 prod facts:** `.ar1_actual`, `.actual`/`.target` only, `fcdo.summary.*`, `indicators.op2_1.ar1_target`.

---

## Code cross-check (live consumers)

**Source:** read-only inspection of `app/reports/services/report_inputs_builder.py` and `app/reports/agents/fact_safety_critic.py` (`resolve_cited_sources`).

| Consumer | Reads | Expectation vs 6643d922 prod |
|----------|--------|------------------------------|
| `build_knowledge_bank_inputs()` | Entire `facts{}` dict; `gap_answers{}` filtered to `disposition == "answered"` | **Match** — keys passed through unchanged |
| F1 prompt / hygiene | `fact:{key}` where `key` ∈ `facts` keys; `gap:{item_key}` where item_key ∈ answered gaps | **Match** when citations use 6643d922 key forms |
| `resolve_cited_sources()` | `facts[key].value` for `fact:` refs; `gap_answers[key].answer_text` for `gap:` refs | **Match** — no key transformation |
| `emit_claim_granular_evidence()` | Explicitly upgrades to `financials.lines.op*.*.y1_*` | **Match 6643d922**; **mismatch** fda69a23 `AR1_*` and fe6bf98b (no financial facts) |

**Mismatch flagged:** Unit tests in `test_synthesis_output_hygiene.py` / `test_synthesis_citation_emission.py` use overlapping but not identical key strings (e.g. `indicators.op2_1_latrine_stances_functional.y1_actual` vs prod `indicators.op2_1_latrine_stances_functional.y1_actual` — close; hygiene tests use `.ar1_actual` which **does not appear in 6643d922 prod**). Seeded Safe Schools KB must **not** copy test shorthand.

---

## Mapping note — Safe Schools golden fixture → real key patterns

| Safe Schools category | Seed using prod pattern (6643d922 family) |
|----------------------|-------------------------------------------|
| **Financials / spend lines** | `financials.lines.op{N}_{N}.y1_actual`, `.y1_budget`; totals `financials.y1_actual.total`, `.y1_budget.total` |
| **Outcome indicators (OCM1–3)** | `indicators.ocm1_attendance_80pct.proposal_endline_target` (+ `.y1_actual`/`.y1_target` when spreadsheet actuals exist) |
| **Output indicators (OP1–4)** | `indicators.op{N}_{N}_{slug}.y1_actual`, `.y1_target`, `.proposal_endline_target` |
| **Disaggregation / equity narrative** | `indicators.equity_support_reach.proposal_target` (or gap-only if no extract) |
| **Grant / award envelope** | `grant.award_budget.amount`, `grant.period.start/end`, `grant.funder` |
| **Reporting dates / obligations** | `reporting.annual_review_period_1.start/end`, `reporting.annual_review_pack_deadline`, `reporting.obligation.*` |
| **Narrative judgements (scores, VfM, risks)** | **`gap_answers`** at `{section}:indicator:{ref}` with `disposition: "answered"` — not `facts{}` |
| **Output scoring table (A++–C)** | `detailed_output_scoring:indicator:output_scores` (gap answer text) + optional indicator facts for numeric rows |
| **Answered gaps (Gate 2)** | Full template item_key; F1 cites as `gap:{item_key}` |

---

## Source attribution

| Claim | Source |
|-------|--------|
| Prod target / candidates | **Live DB** — read-only query 2026-06-04 |
| Representative keys & values | **Live DB** — report `6643d922` (primary), `fe6bf98b` (33-fact secondary) |
| Code consumer behaviour | **Live code** — `report_inputs_builder.py`, `fact_safety_critic.resolve_cited_sources` |
| Namespace drift table | **Live DB** — cross-report comparison |

---

## Verdict

**Namespace captured, ready to author seeded KB.**

Use report **`6643d922-150d-4000-b878-4025e7c9145a`** as the canonical prod namespace for Safe Schools seeding (`financials.lines.op*.*.y1_*`, `indicators.*.y1_actual`/`.y1_target`, `grant.*`, `reporting.*`, gap keys `{section}:indicator|table:{ref}`). Treat **`fe6bf98b`** as the historical ~33-fact synthesise-boundary row but **not** as the financial/actuals template — it lacks line facts and uses targets-only indicator keys.

---

*Read-only capture. Single deliverable. No DB writes, no seeding, no pipeline invocation.*
