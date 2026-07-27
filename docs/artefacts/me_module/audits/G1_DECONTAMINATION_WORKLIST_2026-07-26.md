# G1 decontamination worklist (P1) — engine-path hits

Source: `G1_TREE_AUDIT_2026-07-26.md` (regenerated 2026-07-27 after indicator-id pattern seed). Report-only; not fixed in G1.
Harness hits are excluded (informational only per D-076).

**Authoritative count:** this regenerated audit is authoritative. The earlier planned "~32" was a hand-count estimate (finding 5); no reconciliation work is required against that estimate. This list is a floor, not a boundary.

This list is a floor, not a boundary. The audit finds only what the blocklist knows; P1 additionally requires a reading pass over every prompt-component file for funder-specific coaching that no token matches.

| Path | Hits | Sample |
|------|-----:|--------|
| `app/reports/agents/gap_compliance_agent.py` | 2 | anchored pattern 'logframe_row_template_form' |
| `app/reports/agents/grant_terms_extractor.py` | 1 | blocklisted token '15 October 2024 to 14 October 2025' |
| `app/reports/agents/indicator_data_extractor.py` | 2 | blocklisted token 'NLCF' |
| `app/reports/agents/proposal_extractor.py` | 4 | blocklisted token 'Expected objective count' |
| `app/reports/ai/prompts/synthesis.py` | 5 | blocklisted token '684 girls were re-enrolled against a target of 650' |
| `app/reports/extraction/spreadsheet_input.py` | 1 | blocklisted token 'NLCF' |
| `app/reports/gap/gap_question_copy.py` | 2 | blocklisted token 'FCDO' |
| `app/reports/gap/logframe_completeness.py` | 1 | blocklisted token 'Detailed Output Scoring' |
| `app/reports/gap/requirement_metadata.py` | 1 | blocklisted token 'FCDO' |
| `app/reports/gap/requirement_satisfaction.py` | 1 | blocklisted token 'progress_against_expected_results' |
| `app/reports/schemas/indicator_data_extraction_v1.py` | 2 | blocklisted token 'NLCF' |
| `app/reports/schemas/proposal_extraction_v1.py` | 1 | blocklisted token 'FCDO' |
| `app/reports/services/report_inputs_builder.py` | 2 | blocklisted token 'FCDO' |
| `app/reports/services/synthesis_citation_emission.py` | 1 | anchored pattern 'op_dotted_indicator' |

**Total: 26 engine-path hits across 14 files.**

Required inclusions verified:
- `app/reports/agents/gap_compliance_agent.py` (logframe_row:opN_N + OP2.3)
- `app/reports/services/synthesis_citation_emission.py:28` (OP2.1)

Group 4 bare-number exclusions remain as recorded in `.governance/blocklist.json` notes (`group4_flag_fatigue`).
