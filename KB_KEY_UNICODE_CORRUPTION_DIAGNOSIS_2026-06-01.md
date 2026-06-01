# KB key Unicode corruption — read-only diagnosis

**Reports:** `5026ab66-9e30-413b-a823-7931c16fe435` (planted-conflict F2 walk), `cabb8796-195b-4089-afab-94d6fe841d50` (earlier clean D4+F1 walk)  
**Date:** 2026-06-01  
**Scope:** Diagnosis only — no code, pipeline, or model runs.

---

## Verdict (3 lines)

1. **Entry point:** Non-ASCII digit corruption is **not** present in D4 `extracted_json`, openpyxl parser output, reconciliation, or persisted `knowledge_bank_json.facts{}` keys. It is introduced in **F1 synthesis** (`report_synthesis_service` → OpenAI gpt-5.4) in `content_json.sections[].content.evidence_used[]`, concentrated in **`detailed_output_scoring`** on walk `5026ab66`.
2. **Keys vs values:** Corruption is confined to **F1 `evidence_used` identifier strings** (fact paths). Persisted **KB fact keys and all KB numeric values are clean ASCII**; prose **numbers** (684, 24, 392, 0.68, etc.) are correct, though prose may contain unrelated **control characters** (see §4).
3. **Fix class:** **(a) LLM generating malformed keys** in F1 — direction: stop free-form key invention; validate or deterministically assign `evidence_used[]` against the KB key allowlist (structured outputs / post-synthesis normalization).

---

## 1. Entry point — trace backwards from a corrupt key

### Canonical corrupt example (planted walk)

Section `detailed_output_scoring`, persisted `content_json`:

```json
"fact:indicators.op2_\u09e7.ar\u0967_target"
```

(unescaped: `indicators.op2_১.ar१_target`)

| Stage | Sample key fragment | Non-ASCII digit code points | Corrupt? |
|-------|---------------------|----------------------------|----------|
| **F1 `evidence_used` (5026ab66 DB)** | `indicators.op2_১.ar१_target` | `১` **U+09E7** (Bengali ONE), `१` **U+0967** (Devanagari ONE) | **Yes — origin** |
| **Persisted KB `facts{}` keys (5026ab66 DB)** | `indicators.op2_1.ar1_target` | none (ASCII `1` = U+0031) | **No** |
| **D4 `uploaded_documents.extracted_json` (xlsx doc)** | `row_id`: `OP2.1` | none | **No** |
| **Reconciliation candidates (`input_builder`)** | `field_path`: `indicators.OP2.1.target` | none | **No** |
| **E1 reconciler output → KB** | `fact_key`: `indicators.op2_1.ar1_target` | none | **No** |

Additional scripts observed in the same section’s `evidence_used[]`:

| Corrupt key | Code points |
|-------------|-------------|
| `indicators.op2_2.ar১_actual` | U+09E7 |
| `indicators.op3_१.ar১_actual` | U+0967, U+09E7 |
| `indicators.op3_3.ar૧_target` | U+0AE7 (Gujarati ONE) |
| `indicators.op4_3.ar૧_actual` | U+0AE7 |

**Conclusion:** Corruption appears **only after F1 synthesis**. It is **not** introduced by reconciliation assembly, JSON DB persistence, or serialization boundaries (PostgreSQL JSONB stores the corrupt strings exactly as the synthesis model emitted them in `evidence_used`; KB keys remain ASCII in the same row).

### Code path (read-only)

```
openpyxl → spreadsheet_input.parse_xlsx_workbook
  → indicator_data_extractor (D4, Claude Haiku) → extracted_json  [clean]
  → input_builder._flatten_indicator_data → fact_candidates.field_path  [clean]
  → knowledge_bank_reconciler (E1) → facts{fact_key}  [clean ASCII keys]
  → report_inputs_builder → report_inputs.knowledge_bank.facts  [clean keys passed to F1]
  → report_synthesis_service._call_openai_section → generated_content.evidence_used  [corrupt in one section]
  → content_json persisted
  → fact_safety_critic.resolve_cited_sources (exact key lookup)  [fails on corrupt keys]
```

Relevant persistence seam — synthesis copies model output verbatim:

```169:177:app/reports/services/report_synthesis_service.py
    generated = raw.get("generated_content") or {}
    ...
    return build_generated_section(
        ...
        evidence_used=list(generated.get("evidence_used") or []),
```

Critic resolution is exact-match only:

```143:147:app/reports/agents/fact_safety_critic.py
        if ref.startswith("fact:"):
            key = ref.removeprefix("fact:")
            fact = facts.get(key)
            if isinstance(fact, dict):
                resolved[ref] = fact.get("value")
```

---

## 2. Keys vs values

| Location | Keys | Values |
|----------|------|--------|
| `knowledge_bank_json.facts{}` (5026ab66) | **71 keys, 0 with non-ASCII digits** | **0 values with non-ASCII digits**; numerics are ASCII (`684`, `24`, `392`, `571`, `0.68`, …) |
| `uploaded_documents.extracted_json` (xlsx, 5026ab66) | N/A (structured rows) | **0 Bengali/other-script digits** in indicator rows; `row_id` values `OP1.1` … `OP4.3` are ASCII |
| F1 `content_json` prose `text` (5026ab66) | N/A | Numeric claims use **correct ASCII digits**; no U+0010 control chars in this walk’s DB prose |
| F1 `evidence_used[]` (5026ab66) | **13 of 44 fact keys** contain non-ASCII digits; **15 fact keys total do not exist in KB** | N/A (identifiers only) |

**Note on user context:** The visible failure (“Bengali/mixed digit keys like `fact:indicators.op2_1.ar1_target`”) manifests in **F1 `evidence_used[]` and critic reasoning**, not in persisted KB storage. On `5026ab66`, KB stores the ASCII key `indicators.op2_1.ar1_target` with value `"24"`.

---

## 3. Parser vs model

| Input to model | Non-ASCII digits? |
|----------------|-------------------|
| openpyxl-parsed workbook (`spreadsheet_input.py` → `_normalize_xlsx_value`) | **No** — D4 sample `row_id='OP1.1'`, 10 indicator rows, zero Bengali-digit hits in full `extracted_json` tree |
| D4 LLM `extracted_json` output | **No** — same as above |
| F1 synthesis prompt input (`report_inputs.knowledge_bank.facts`) | Keys are **ASCII**; model receives correct keys but **re-emits corrupted variants** in `evidence_used` for `detailed_output_scoring` |

**Conclusion:** Parser/encoding path is clean. Corruption is an **LLM-generation bug** in F1 (gpt-5.4), not openpyxl or D4 Haiku output.

**Section asymmetry (5026ab66):** In `detailed_output_scoring`, `op1_*` keys in `evidence_used` are ASCII-clean; corruption begins at `op2_*` onward (see artifact lines 943–962 in `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json`). Other sections on the same report (`summary_and_overview`, `performance_and_conclusions`, …) use **ASCII** `indicators.opN_N.ar1_*` keys.

---

## 4. Prose corruption link (`Year` + U+0010, `GBP121,000`)

| Walk | Prose control chars | Key corruption |
|------|---------------------|----------------|
| **cabb8796** (DB + `FCDO_D4_F1_WALK_cabb8796.json`) | **Yes** — U+0010 (DLE) inserted in “Year\u0010 milestone” (4× in `summary_and_overview`); U+0013 in “Term \u0013 attendance”; missing space `GBP121,000` vs `GBP 121,000` | **No non-ASCII digits** in `evidence_used`; instead **wrong key shapes** (`indicators.OP1.x.actual`, wildcards) — 8 keys not in KB |
| **5026ab66** (DB) | **No** U+0010 in persisted prose | **Yes** — mixed-script digits in `detailed_output_scoring` `evidence_used` only |

**Conclusion:** **Same broad class, different surface form** — both are **F1 synthesis (OpenAI) emitting stray Unicode** in unstructured text fields. Prose corruption = control characters / spacing collapse in `generated_content.text`. Key corruption = Indic-script digits substituted for ASCII `1` in identifier paths. **Not** caused by spreadsheet parser or KB/reconciliation. **Not** the same bug instance on every walk (5026ab66 has keys corrupt, prose clean; cabb8796 has prose corrupt, keys wrong-format but ASCII).

---

## 5. Blast radius

### Reconciliation conflict matching — **not broken by Unicode keys on these walks**

- `5026ab66`: `conflicts_pre_gate1: []` (artifact `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json`).
- KB keys are ASCII; E1 would match conflicts on `fact_key` normally.
- Empty conflicts on the planted walk are **explained separately**: E1 did not surface planted VALUE_MISMATCH pairs (e.g. missing 612 extraction, semantic disambiguation), **not** because KB keys contain Bengali digits.

### Critic key-resolution — **broken**

- `resolve_cited_sources()` does `facts.get(key)` with **no normalization**.
- 15 `evidence_used` fact keys on `5026ab66` are absent from KB (13 due to non-ASCII digits; 2 malformed ASCII: `indicators.op4_0?ar?_target`, `indicators.op4_1.ar11_actual`).
- Normalizing Indic digits → ASCII would map many to valid KB keys (e.g. `indicators.op2_2.ar১_actual` → `indicators.op2_2.ar1_actual` → value `17`), but the pipeline **does not** do this today.
- **55 critic BLOCK flags** on `5026ab66` — mix of:
  - **Key-resolution failures** from corrupt/missing `evidence_used` (critic messages explicitly cite “Bengali digit variant key” / “no resolved value in cited_sources”).
  - **Missing financial fact citations** (totals and line-level GBP figures not listed in `evidence_used` even when KB has them).
  - **Gap-answer verification gaps** (claims not supported by cited gap text).

Unicode key corruption is a **primary driver** of critic BLOCKs for indicator milestone/target claims in `detailed_output_scoring`; it is **not** the cause of `conflicts_pre_gate1: []`.

---

## 6. Fix class

| Class | Applies? | Rationale |
|-------|----------|-----------|
| **(a) LLM malformed key generation** | **Yes — primary** | Corruption appears only in F1 `evidence_used[]`; upstream artifacts clean |
| (b) Parser/encoding normalization gap | **No** | openpyxl + D4 output contain no non-ASCII digits |
| (c) Serialization boundary | **No** | DB stores synthesis output faithfully; KB keys unchanged |
| (d) Other | **Partial — related F1 prose hygiene** | U+0010 / spacing issues same synthesis stage, different field |

**One-line fix direction:** After F1 (or via constrained generation), **bind `evidence_used[]` to the exact KB key set** already passed in `report_inputs.knowledge_bank.facts` — reject or auto-correct any key not in that allowlist; optionally apply NFKC + ASCII-digit normalization on identifiers only. Do **not** rely on the synthesis model to transcribe fact paths from memory.

---

## Evidence index

| Artifact | Finding |
|----------|---------|
| Prod DB `donor_reports` `5026ab66` | KB: 71 ASCII keys; `detailed_output_scoring` `evidence_used` contains U+09E7/U+0967/U+0AE7 |
| Prod DB `donor_reports` `cabb8796` | KB: 66 ASCII keys; prose U+0010/U+0013; `evidence_used` wrong-format ASCII keys only |
| `uploaded_documents.extracted_json` (xlsx, both walks) | 10 rows, `row_id` ASCII, 0 Bengali digits |
| `FCDO_PLANTED_CONFLICT_WALK_5026ab66.json` | `\u09e7`/`\u0967`/`\u0ae7` in `detailed_output_scoring` `evidence_used`; critic BLOCK reasons; `conflicts_pre_gate1: []` |
| `FCDO_D4_F1_WALK_cabb8796.json` | U+0010 in summary prose; `GBP121,000` spacing defect |
| Code | `report_synthesis_service.py` (verbatim `evidence_used`); `fact_safety_critic.resolve_cited_sources` (exact lookup); `input_builder._flatten_indicator_data` (deterministic ASCII `field_path`) |

---

**STOP** — diagnosis complete; no fix proposed beyond fix-class direction above.
