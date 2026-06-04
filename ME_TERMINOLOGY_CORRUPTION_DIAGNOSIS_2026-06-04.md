# Terminology-substitution corruption — read-only diagnosis

**Report:** `6643d922-150d-4000-b878-4025e7c9145a` (FCDO / BridgeLight gate-run export)  
**Date:** 2026-06-04  
**Scope:** Diagnosis only — no code changes, no re-render, no pipeline re-run.

**Sources used (read-only):**
- Production `donor_reports.content_json` for `6643d922` (Postgres, 2026-06-04)
- Rendered artifact `M_E_Module/gate_run/6643d922_export.docx`
- Code: `app/reports/export/docx_renderer.py`, `app/reports/services/report_export_service.py`
- Hygiene (confirmed not involved): `app/reports/services/synthesis_output_hygiene.py`, `app/reports/services/report_synthesis_service.py`
- FCDO template: `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json` (`terminology_map_json.canonical_to_funder`)

---

## Executive verdict

**Corruption is introduced at RENDER time (export stage), not at F1 generation or hygiene.**

Stored `content_json` section prose is natural English with correct words (`risk management`, `did not report`, `budget`, `milestone`, `limitations`). The same passages in the exported `.docx` contain funder-label phrases, dropped words, and stray `[ [` bracket runs. Applying the export renderer’s `_strip_internal_tokens` + `_apply_terminology` functions to the stored text reproduces the docx corruption exactly (verified on `risk_and_safeguarding` and `summary_and_overview`).

F1 synthesis and `sanitize_generated_content` do **not** reference `terminology_map_json` or `canonical_to_funder`.

---

## Decisive check: stored prose vs rendered docx

### Side-by-side evidence (same passages)

| # | Stored `content_json` (clean) | Rendered `.docx` (corrupt) | Corruption type |
|---|------------------------------|----------------------------|-----------------|
| 1 | `Risk management remained broadly stable during the reporting period.` | `Risk rating / assumptions / controls management remained broadly stable during the reporting period.` | Terminology replace |
| 2 | `Year 1 monitoring returns did not report any major incident trend.` | `Year 1 monitoring returns did not Annual Review any major incident trend.` | Terminology replace |
| 3 | `actual spend reached GBP 174,850 against a budget of GBP 162,000` | `actual spend reached GBP 174,850 against a Budget / forecast and actual costs of GBP 162,000` | Terminology replace |
| 4 | `Financial delivery ran ahead of the Year 1 budget allocation recorded in the AR1 export.` | `Financial delivery ran ahead of the Year 1 Budget / forecast and actual costs allocation recorded in the AR1 export.` | Terminology replace |
| 5 | `A smaller set of indicators fell below milestone.` | `A smaller set of Indicators fell below .` | Word deleted (strip pass) |
| 6 | `exceeding the planned Year 1 milestone.` | `exceeding the planned Year 1 .` | Word deleted (strip pass) |
| 7 | `there were, however, clear limitations that affected confidence in some results.` | `there were, however, clear that affected confidence in some results.` | Word deleted (strip pass) |

### Boolean proof (automated compare, prod DB + repo docx)

For phrases that indicate corruption:

| Phrase | In stored `risk_and_safeguarding`? | In rendered docx only? |
|--------|-----------------------------------|------------------------|
| `Risk rating / assumptions` | **No** | **Yes** |
| `Budget / forecast and actual costs` | **No** | **Yes** |
| `did not Annual Review` (verb corruption) | **No** (stored has `did not report`) | **Yes** |

Stored prose **already** contains legitimate funder phrasing where the model wrote it intentionally (e.g. `the first Annual Review period`) — those are **not** corruption. Corruption is where ordinary words (`report` as verb, `risk` in `risk management`, `budget` as noun) are replaced.

### Simulation confirmation

Running export renderer helpers on stored `risk_and_safeguarding` text:

- `_apply_terminology` alone on the opening sentence converts `Risk management` → `Risk rating / assumptions / controls management`.
- Full `_strip_internal_tokens` → `_apply_terminology` pipeline on stored text: `matches_docx: true`, `sim_has_brackets: true`.

---

## Layer responsible

| Layer | Role | Applies `canonical_to_funder`? | Strips words from prose? |
|-------|------|-------------------------------|--------------------------|
| F1 synthesis (`report_synthesis_service.py`) | Generate section text | **No** | **No** |
| Hygiene (`synthesis_output_hygiene.py`) | Citation binding, control-char strip | **No** | **No** (only `fact:`/`gap:` in evidence_used, not prose) |
| **Export renderer (`docx_renderer.py`)** | **Build `.docx` from stored `content_json`** | **Yes — on full section body** | **Yes — template keys as `\bword\b` deletes** |

**Call chain:** `report_export_service.export_and_persist` → `render_donor_report_docx` → `_render_section_body` (for each section with prose).

---

## Exact substitution mechanism

### Function 1: `_terminology_substitutions` + `_apply_terminology`

**File:** `app/reports/export/docx_renderer.py` (lines 42–72, 115, 211, 218, 237–242)

**Input operated on (wrongly):** entire section body string `content_json.sections[].content.text`, after an internal-token strip pass.

**Mechanism:**
1. Read `terminology_map_json["canonical_to_funder"]`.
2. For each `(canonical, funder_label)` pair, build `re.compile(rf"\b{re.escape(canonical)}\b", re.IGNORECASE)`.
3. Sequentially `pattern.sub(funder_label, text)` on the full prose.

This is **whole-word, case-insensitive regex replacement** across free narrative — not scoped to structured label fields.

**Also applied to:** section H1 headings (`template_section.label`) — line 218. That heading use is **legitimate**.

**Not applied to:** table sub-headings (`table_def.label`) — those are written raw at lines 223–225.

### Function 2: `_strip_internal_tokens` (dropped words + brackets)

**File:** `app/reports/export/docx_renderer.py` (lines 53–65, 114)

**Input operated on:** same section body prose, **before** terminology substitution.

**Mechanism (three passes):**
1. `_FACT_GAP_RE = r"\b(?:fact|gap):[^\s,;]+"` — removes `fact:…` / `gap:…` tokens **inside** citation brackets, leaving orphan `[` `]`.
2. `_ARCHETYPE_RE` — removes `ARCH_*` tokens.
3. For every `section_key` and template `indicator_key` / `table_key` / `column_key` with **`len(key) > 8`**, `re.sub(rf"\b{re.escape(key)}\b", "", text)` — deletes any matching **English word** in prose.

**Dropped-word examples (confirmed by before/after strip on stored text):**

| Deleted word | Template key source | Stored context | After strip |
|--------------|--------------------|--------------------|-------------|
| `milestone` | `column_key: "milestone"` (output score table) | `fell below milestone` | `fell below .` |
| `milestone` | same | `planned Year 1 milestone` | `planned Year 1 .` |
| `limitations` | `column_key: "limitations"` (evidence matrix) | `clear limitations that affected` | `clear that affected` |

Other template keys with `len > 8` that are common English words and therefore dangerous in prose include: `indicator`, `assessment`, `mitigation`, `recommendation`, `evidence`, `commentary`, etc. (full set derived from `TEMPLATE_INSTANCE_FCDO.json` via `_indicator_keys_from_template`).

---

## Offending `canonical_to_funder` entries (FCDO)

From `docs/artefacts/me_module/TEMPLATE_INSTANCE_FCDO.json`:

```json
"report": "Annual Review",
"budget": "Budget / forecast and actual costs",
"risk": "Risk rating / assumptions / controls",
"indicators": "Indicators",
"milestones": "Milestones",
"outputs": "Outputs",
"outcomes": "Outcome",
"value_for_money": "Value for Money / VfM",
"results_framework": "Results framework / logframe",
"project": "programme / project",
"funder": "FCDO",
"review_system": "AMP / DevTracker publication context"
```

**Entries that explain observed corruption:**

| Canonical key | Funder label | Observed false match in prose |
|---------------|--------------|------------------------------|
| `"risk"` | `"Risk rating / assumptions / controls"` | `Risk management` → corrupted heading clause |
| `"report"` | `"Annual Review"` | `did not **report** any` → `did not **Annual Review** any` |
| `"budget"` | `"Budget / forecast and actual costs"` | `against a **budget** of` / `Year 1 **budget** allocation` |
| `"indicators"` | `"Indicators"` | capitalisation change (`indicators` → `Indicators`) — minor but shows blind pass |

The map keys are **short English tokens**, not namespaced canonical identifiers. Used as `\b`-bounded replacements in narrative, they inevitably match incidental word use.

**Contract note:** `FUNDER_TEMPLATE_SCHEMA.md` §4.1 describes `canonical_to_funder` as “Replace labels in synthesis output”. Synthesis does not implement this; the export renderer applies it to stored prose instead.

---

## Dropped words: same pass or separate?

**Same render function, separate sub-mechanism — not caused by `canonical_to_funder`.**

- **Not** empty replacement values in the terminology map.
- **Not** F1/hygiene.
- **Yes** `_strip_internal_tokens` deleting template `column_key` / `indicator_key` strings that coincide with ordinary English words (`milestone`, `limitations`, …).

Terminology substitution runs **after** the strip pass in `_render_section_body`, so the user sees both artifact types in one export, but they have two distinct causes inside `docx_renderer.py`.

---

## Bracket artifacts `[ [ [`: same root cause?

**Same render stage, different sub-mechanism — not terminology substitution.**

- Stored `risk_and_safeguarding` prose contains inline citation markers, e.g.  
  `[gap:risk_and_safeguarding:indicator:new_risks]`, `[fact:financials.lines.op1_1.y1_actual]`.
- Stored text has **no** `[ [` runs (`stored_has_bracket_runs: false`).
- Rendered docx has multiple `[ [` runs (`rendered_has_bracket_runs: true`).

**Cause:** `_FACT_GAP_RE` removes only the `fact:…` / `gap:…` substring, not the surrounding square brackets. Example:

```
Before:  ...shortfall on OP2.2. [gap:risk_and_safeguarding:indicator:climate_environment_risk] Climate...
After:   ...shortfall on OP2.2. [ ] Climate...   → consecutive markers become [ [ [ [
```

This is a **citation-marker cleanup bug** in `_strip_internal_tokens`, not table-cell rendering and not the terminology map.

---

## What should vs should not receive funder-surface terms

| Field / surface | Should receive `canonical_to_funder`? | Current behaviour |
|-----------------|--------------------------------------|-------------------|
| Template section H1 (`report_sections_json[].label`) | **Yes** | Applied (correct) |
| Template table H2 (`required_tables[].label`) | **Yes** (label only) | **Not** applied today |
| Structured table column headers at render | **Yes** | N/A for from_scratch prose export |
| Gap question labels / checklist labels (gap agent) | **Yes** (prompt context only) | Separate path; not this bug |
| **`content_json.sections[].content.text` (F1 narrative prose)** | **No** — model already writes natural language; critic reviewed this text | **Incorrectly substituted and stripped today** |
| Document title / funder name / reporting period lines | Partially (title from format_rules) | Title raw; period lines raw |

---

## Recommended fix shape (describe only — do not implement)

1. **Remove terminology substitution from narrative prose.** In `_render_section_body`, delete the `_apply_terminology` call on section body text (line 115). Keep it **only** for template-derived labels (section headings; optionally add table sub-headings if desired).

2. **Stop using template schema keys as prose word blacklist.** `_strip_internal_tokens` should not iterate `column_key` / `indicator_key` / `table_key` values with `\b…\b` deletion against narrative. If internal tokens must be removed from prose, use a **citation-marker-aware** remover that deletes entire `[fact:…]` / `[gap:…]` bracket groups (or leave prose unchanged and rely on F1 hygiene, which already does not leave bare brackets).

3. **Re-scope FCDO `canonical_to_funder` keys** (data/contract follow-up, separate from renderer fix): short English keys like `risk`, `report`, `budget` are unsafe for global word replacement; prefer namespaced canonical labels or restrict map use to explicit label fields only.

4. **No F1/hygiene change required** for this defect class — stored `content_json` is already clean.

---

## Verification checklist (completed)

- [x] Side-by-side comparison of prod `content_json` vs repo docx (not inferred from code alone)
- [x] Corruption phrases absent from stored text, present only after render
- [x] Renderer simulation reproduces docx corruption
- [x] F1/hygiene path confirmed free of `canonical_to_funder`
- [x] Bracket artifact traced to `_FACT_GAP_RE` partial deletion

---

**Root cause confirmed at export render layer (`docx_renderer._render_section_body`), fix is: apply `canonical_to_funder` only to template labels, not section body prose, and replace `_strip_internal_tokens` prose logic with whole-marker citation removal that does not delete ordinary English words matching template column keys.**
