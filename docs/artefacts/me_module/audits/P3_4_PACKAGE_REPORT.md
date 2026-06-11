# P3-4 package report — Output quality (AMBER)

**Package:** P3-4  
**Status:** Shipped (pending CI run ID after push)  
**Plan:** Phase 3 Plan v2 · CP serial after P3-3

## Shipped

- **Proposal context:** `linked_proposal_summary` in `report_inputs.derived` via `report_inputs_builder.py`; synthesis user prompt background block (non-citable)
- **Humaniser:** `detect_humaniser_violations()` in `synthesis_output_hygiene.py`; violations logged on legacy citation path; detection-only (no prose rewrite — preserves faithfulness)
- **Funder tone:** Section `tone`, `narrative_constraints`, `terminology_map` wired into synthesis user prompt
- **Hard red:** `tests/test_p3_4_output_quality.py` — `@pytest.mark.hard_red` faithfulness / unmatched_numbers gates
- **Tests:** `tests/test_p3_4_output_quality.py`, humaniser unit in `tests/test_synthesis_output_hygiene.py`

## Fence judgments

- Humaniser is detect-and-log only; structured bind path unchanged
- Proposal context explicitly non-authoritative for numbers (prompt + field mapping parity)
- P3-1 G-faithfulness must stay green — hard-red tests enforce

## Exit checkpoint

- Local: `pytest tests/test_p3_4_output_quality.py tests/test_p3_eval_harness.py::test_g_faithfulness_zero_unmatched_on_clean tests/test_p1_phase1_faithfulness.py -q`
- CI run ID: _(pending push)_
