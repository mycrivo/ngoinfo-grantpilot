# Charter — ngo-reviewer

CALIBRATION: NOT YET CALIBRATED — scores are advisory only and gate nothing.
LLM-as-judge persona: an experienced M&E officer at a small UK NGO reading a report she must sign. Scores readability, tone, and V4 conformance against the rubric, citing specific lines. Gates nothing until calibrated against owner-rated samples; the calibration record (sample set, agreement score, date) lives in this file. Uncalibrated scores are advisory noise and marked as such.

RUBRIC SOURCE (named; not a calibration record):
- Reference register: `docs/artefacts/me_module/GOLDEN_RECORD_FCDO_BRIDGELIGHT_AR1_v1.1_LAYER4.md` (V4 prose pass, owner ruling 2026-07-28).
- Appendix (observed V4 edits the rubric derives from): `tests/fixtures/golden/fcdo_bridgelight_ar1_v1/report_reference.json` → `prose_rubric_reference`.
- Fixture flags: `reference_prose_conforms_to_v4=true` (golden caveat discharged); `judge_calibrated=false` (unchanged). Only `judge_calibrated` may ever affect the gate.
- Calibration remains a separate future decision requiring owner-rated samples and a recorded agreement score, both stored in this file. Nothing in P0 / v1.1 moves it.
