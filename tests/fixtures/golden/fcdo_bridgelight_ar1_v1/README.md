# Golden pack — FCDO BridgeLight AR1 v1.1

Layers 1–3 and 5 transcribed from `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`.
Layer 4 from `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.1_LAYER4.md` (V4 prose pass, D-079).
**No interpretation beyond recorded judgment calls in `RECONCILIATION.md` / `RECONCILIATION_V11_LAYER4.md`.**

## Facet grain (owner ruling)

One fixture record per `(F-id, facet)`, preserving both.

**Rationale:** Facet identity is ontology-mandated (ME Engine Behavioural Contract §2 —
"typed facet identity, never encoded in a label string") and is the direct fix for RC1.
A fixture that collapses facets into rows cannot detect facet-blind matching, which is
the defect the rebuild exists to eliminate.

**Status is facet-scoped:** a golden Status that names a conflict or gap attaches only to
the facet that conflict/gap concerns; other facets of that fact are normally CONFIRMED.

**Absence is a state:** missing values use `value: null`, `source_document: null`, and
`absent: {reason, gap_id?}` — never the strings `NOT REPORTED` or `—`.

**reportable:** `false` on derived cross-indicator totals and TOTAL-row / vulnerability
aggregates (F-052…F-056, F-094…F-097); `true` elsewhere.

## Files

| File | Layer |
|------|-------|
| `facts.json` | 1 — fact records (id × facet) |
| `conflicts.json` | 2 — C-01…C-09 (`defects[]` on C-04) |
| `gaps.json` | 3 — clusters + counter-list + question script |
| `report_reference.json` | 4 — V4 prose; `reference_prose_conforms_to_v4` + `judge_calibrated`; appendix in `prose_rubric_reference` |
| `forbidden.json` | 5 — FB-01…FB-18 (`deterministic` / `judged` / `dual`) |
| `manifest.json` | dataset version 1.1, per-layer provenance, checksum, L5 self-check allowlist |
| `RECONCILIATION.md` | owner verification (layers 1–3, 5) |
| `RECONCILIATION_V11_LAYER4.md` | Layer 4 v1.1 prose-pass verification |

## Dataset versioning

- Manifest carries **per-layer provenance** (source version per layer).
- Dataset version **1.1** = Layer 4 V4 prose pass only; layers 1/2/3/5 source_version remain 1.0.
- Baselines (later WI) must store dataset version + checksum scored against.
- Cross-version same-or-better comparisons are forbidden (D-071); scorecard must warn.
- Gate reads `judge_calibrated` only; `reference_prose_conforms_to_v4` is metadata.
