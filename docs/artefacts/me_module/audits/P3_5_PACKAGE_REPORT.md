# P3-5 package report — Contract re-sync (doc-only)

**Package:** P3-5  
**Status:** Shipped (pending CI run ID after push)  
**Plan:** Phase 3 Plan v2 · doc-only fence

## Shipped

| Deliverable | Action |
|-------------|--------|
| Unmetered exports | `API_CONTRACT.md` §4 `report_exports`, §12.13 — no `REPORT_EXPORT` charge; D6 `REPORT_CREATE` at first COMPLETE documented |
| COMPLETE semantics | §12.13 — export persist vs Gate 3 confirm distinguished |
| Canonical gap answers | New `GATE2_GAP_ANSWERS_FIELD_CONTRACT.md` from `gate2_gap_answers.py` / service |
| PATCH §12.7 | Marked provisional; points to §12.7a + field contract |
| P3 ID collision | `ME_MODULE_FOLLOWUP_BACKLOG.md` — renamed to `P-UX-*`; cross-link to Phase 3 `P3-*` packages |
| Code align backlog | `P-UX-11` — PATCH §12.7 implementation/removal |

## Not in scope (by fence)

- No gap-answers route or schema code changes
- No ENUM_REGISTRY edit (export unmetered aligns with existing D6 implementation)

## Exit checkpoint

- Doc diff only; smoke suite unchanged behaviour
- CI run ID: _(pending push)_
