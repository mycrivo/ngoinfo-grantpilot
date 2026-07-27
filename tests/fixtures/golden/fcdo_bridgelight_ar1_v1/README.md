# Golden pack — FCDO BridgeLight AR1 v1.0

Transcription of `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.0.md`.
**No interpretation beyond recorded judgment calls in `RECONCILIATION.md`.**

## Facet grain (owner ruling)

One fixture record per `(F-id, facet)`, preserving both.

**Rationale:** Facet identity is ontology-mandated (ME Engine Behavioural Contract §2 —
"typed facet identity, never encoded in a label string") and is the direct fix for RC1.
A fixture that collapses facets into rows cannot detect facet-blind matching, which is
the defect the rebuild exists to eliminate.

## Files

| File | Layer |
|------|-------|
| `facts.json` | 1 — fact records (id × facet) |
| `conflicts.json` | 2 — C-01…C-09 (`defects[]` on C-04) |
| `gaps.json` | 3 — clusters + counter-list + question script |
| `report_reference.json` | 4 — **own file** for v1.1 Layer-4-only swap |
| `forbidden.json` | 5 — FB-01…FB-18 |
| `manifest.json` | dataset version, per-layer provenance, checksum |
| `RECONCILIATION.md` | owner verification (counts + full samples + judgment calls) |

## Dataset versioning

- Manifest carries **per-layer provenance** (source version per layer).
- Baselines (later WI) must store dataset version + checksum scored against.
- Cross-version same-or-better comparisons are forbidden (D-071); scorecard must warn.
