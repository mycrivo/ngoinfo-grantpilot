
Layer 1: Eligibility (Deterministic)

Geography

Legal status

Sector

Budget range

Exclusions

Layer 2: Alignment

Mission alignment

Beneficiary match

Thematic relevance

Layer 3: Readiness

Past projects

Evidence availability

Capacity indicators

Layer 4: Risk Signals

Competitive funder

Size mismatch

First-time applicant

Each criterion must list:

Data source

Evaluation method

Output label

**Criterion: Geography**
- Data source: opportunity.eligible_countries, ngo_profile.country
- Method: Exact match
- Failure type: Hard block
- Output label:
  - Pass: “Eligible in {country}”
  - Fail: “Not eligible due to geography”
