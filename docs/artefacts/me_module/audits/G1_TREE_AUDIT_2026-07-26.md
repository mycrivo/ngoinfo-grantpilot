# G1 tree-wide governance audit (report-only)

Generated: 2026-07-27T12:24:52.845218+00:00

This job never blocks. Engine-path hits are the P1 decontamination worklist.
Harness hits are informational only (exempt from the string guard).

## Engine-path violations (26)

| Path | Count | Sample detail |
|------|------:|---------------|
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

### Full engine hit list

- `app/reports/agents/gap_compliance_agent.py` — anchored pattern 'logframe_row_template_form' — `as a gap using the supplied item_key and required_item_ref (logframe_row:opN_N). Name`
- `app/reports/agents/gap_compliance_agent.py` — anchored pattern 'op_dotted_indicator' — `the OP indicator id (e.g. OP2.3) in the question and rationale.`
- `app/reports/agents/grant_terms_extractor.py` — blocklisted token '15 October 2024 to 14 October 2025' — `8b. If the letter gives a contractual review period AND mentions an alternative period discussed (e.g. "October to September" in an inception call vs "15 October 2024 to 14 October 2025" in the letter`
- `app/reports/agents/indicator_data_extractor.py` — blocklisted token 'NLCF' — `Package A carrier: reads the funder's source-declared section column (e.g. NLCF`
- `app/reports/agents/indicator_data_extractor.py` — blocklisted token 'NLCF' — `"Section for NLCF update") verbatim. The LLM never authors section membership.`
- `app/reports/agents/proposal_extractor.py` — blocklisted token 'Expected objective count' — `- Expected objective count: 2 (one impact, one outcome). Set level to impact or outcome on each row.`
- `app/reports/agents/proposal_extractor.py` — blocklisted token 'girls with disabilities / ultra-poor / previously out-of-school' — `- Extract exactly ONE additional targetless indicator from Value for Money §8: the equity-assessment line only, as indicator_key equity_support_reach_qualitative with target.absent=true (share of supp`
- `app/reports/agents/proposal_extractor.py` — blocklisted token 'Expected total' — `- Expected total: 15 logframe indicators with targets + 1 targetless equity indicator = 16 indicators.`
- `app/reports/agents/proposal_extractor.py` — blocklisted token 'op1_1_girls_reenrolled' — `3. Use stable snake_case keys (e.g. ocm1_attendance_80pct, op1_1_girls_reenrolled, equity_support_reach_qualitative).`
- `app/reports/ai/prompts/synthesis.py` — blocklisted token '684 girls were re-enrolled against a target of 650' — `"text": "684 girls were re-enrolled against a target of 650.",`
- `app/reports/ai/prompts/synthesis.py` — blocklisted token 'fact:indicators.op1_1' — `"fact:indicators.op1_1.ar1_actual",`
- `app/reports/ai/prompts/synthesis.py` — blocklisted token 'fact:indicators.op1_1' — `"fact:indicators.op1_1.ar1_target"`
- `app/reports/ai/prompts/synthesis.py` — bare fixture number '684' in prompt-component path — `"text": "684 girls were re-enrolled against a target of 650.",`
- `app/reports/ai/prompts/synthesis.py` — bare fixture number '684' in prompt-component path — `"value_tokens": ["684", "650"]`
- `app/reports/extraction/spreadsheet_input.py` — blocklisted token 'NLCF' — `# (e.g. NLCF monitoring "Section for NLCF update"). Markdown-stripped, lower-cased,`
- `app/reports/gap/gap_question_copy.py` — blocklisted token 'FCDO' — `"""Logframe row ref question (FCDO-style OP1.1 actuals)."""`
- `app/reports/gap/gap_question_copy.py` — anchored pattern 'op_dotted_indicator' — `"""Logframe row ref question (FCDO-style OP1.1 actuals)."""`
- `app/reports/gap/logframe_completeness.py` — blocklisted token 'Detailed Output Scoring' — `return "detailed_output_scoring", "Detailed Output Scoring"`
- `app/reports/gap/requirement_metadata.py` — blocklisted token 'FCDO' — `"FCDO_management_actions",`
- `app/reports/gap/requirement_satisfaction.py` — blocklisted token 'progress_against_expected_results' — `"progress_against_expected_results": ["ar1_actual", "ar1_milestone_target"],`
- `app/reports/schemas/indicator_data_extraction_v1.py` — blocklisted token 'NLCF' — `# Package B: the row's evidence/note/commentary cell (e.g. NLCF monitoring column`
- `app/reports/schemas/indicator_data_extraction_v1.py` — blocklisted token 'NLCF' — `# assignment for this row (e.g. NLCF monitoring column "Section for NLCF update").`
- `app/reports/schemas/proposal_extraction_v1.py` — blocklisted token 'FCDO' — `Aligned with FCDO logframe columns: indicator, baseline, milestone, target.`
- `app/reports/services/report_inputs_builder.py` — blocklisted token 'FCDO' — `# fact_namespaces key at all (e.g. FCDO). A section that declares the key (even`
- `app/reports/services/report_inputs_builder.py` — blocklisted token 'FCDO' — `# fact_namespaces key (e.g. FCDO archetype-driven). Sections that declare the key`
- `app/reports/services/synthesis_citation_emission.py` — anchored pattern 'op_dotted_indicator' — `"""Split prose without breaking OP2.1-style dotted indicator ids."""`

## Harness informational (56) — not violations

| Path | Count | Sample token |
|------|------:|--------------|
| `app/reports/eval/fixtures.py` | 2 | `FCDO` |
| `app/reports/eval/gates.py` | 28 | `FCDO` |
| `app/reports/eval/offline_replay.py` | 21 | `fcdo` |
| `app/reports/eval/output_rubric.py` | 5 | `FCDO` |
