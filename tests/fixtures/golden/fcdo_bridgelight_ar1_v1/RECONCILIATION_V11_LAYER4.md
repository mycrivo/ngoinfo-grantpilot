# RECONCILIATION — Golden Layer 4 v1.1 (V4 prose pass)

Owner ruling 2026-07-28. Change scope: prose only.

## Provenance

- Source document: `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.1_LAYER4.md`
- Dataset version: `1.1`
- Pack content_checksum: `185223373f46afa85e47562c82d7b6a5494858482aa7c9f9afe7f448869eca79`
- superseded_layer_4_sha256 (v1.0 full_markdown): `866a51298324c32e55239756c7d39d8ce6ffdfc0ed21c5169baf3350074e070c`
- v1.1 full_markdown_sha256: `72c6c91d94a70393aa2979324f85b5971f91e6a0549b6a8cc7782399693bda6c`

## Owner-corrected divergences

1. **Recommendations word-limit (Correction 1).** Supplied text said `*[Word count: 419 of 900]*`. Corrected to `*[Word count: 419, no limit]*` before transcription. v1.0 asserted no limit; word limits are template data and a prose pass must not introduce one. Live template `recommendations_and_actions.word_limit` is `null`.
2. **Dash typography (Correction 2).** Numeric ranges normalised to en dashes (`6–11`, `12–17`, `18–24`, `10–19`) matching v1.0. Recorded as normalised, not as a cosmetic divergence. B6: typography must never decide a match.

## Judgment calls (confirmed)

- Preamble → manifest metadata (not inside `full_markdown`).
- Appendix → `prose_rubric_reference`, excluded from coverage and claim-map scoring.
- Section word counts moving (758→743, 872→869, 604→597, 604→592, 664→656, 431→419) expected; recorded, not flagged.

## Word-limit reconciliation (report only)

Compare every limit the golden asserts against the live FCDO template. Change nothing on a mismatch — owner bins as golden amendment or template-data defect.

| Golden section | Golden word count | Golden asserted limit | Template `word_limit` | Match? |
|---|---:|---:|---:|---|
| A | 743 | 900 | 900 | MATCH |
| B | 869 | 1200 | 1200 | MATCH |
| Evidence | 597 | 900 | 900 | MATCH |
| Risk | 592 | 900 | 900 | MATCH |
| F | 656 | 1200 | 1200 | MATCH |
| Recommendations | 419 | no limit | null | MATCH |

## Token-set diff (numbers, currency, dates, claim-map IDs)

- Tokens only in v1.0 Layer 4: (none)
- Tokens only in v1.1 Layer 4: (none)

Recomputed from git HEAD v1.0 `full_markdown` vs v1.1 fixture. Section word-count integers (758→743, 872→869, 604→597, 604→592, 664→656, 431→419) differ by design and are excluded from this defect bar. No factual divergence in numbers, currency figures, dates, or claim-map IDs.

## Layer 5 self-consistency (standing pack check)

- Deterministic-arm hits against v1.1 reference text: ['FB-04:1[, ]?184[, ]?000', 'FB-05:op2\\.?3|op2_3', 'FB-06:392.*male', 'FB-09:aggregat\\w+.*output.?score|output.?score.*aggregat', 'FB-13:life[- ]of[- ]programme|burn\\s*rate|remaining budget', 'FB-14:previous recommendations']
- This check is standing: `load_golden_pack` validates every pack's reference text against its own forbidden-output deterministic patterns.

## Prose edit classes (from appendix — rubric derivation)

See `report_reference.prose_rubric_reference` for the full appendix. Classes observed:

- Structure: opens at pressure points (period offset + missing outcome).
- Contractions and register: cannot→can't, does not→doesn't; tables stay terse.
- Rhythm: short declaratives carry findings.
- Removed constructions: 'It should be noted that'; intensifier 'Significant'; forced transitions.
- Sector vocabulary: unique beneficiaries → individual girls and households supported.
- Position and demand: findings carry judgment and the ask.
- Asymmetry: outcome finding gets more space.

## Fixture byte-identity (layers 1/2/3/5)

Verified at build time: `facts.json`, `conflicts.json`, `gaps.json`, `forbidden.json` unchanged from pre-swap SHA-256.
