MVP Fit Scan Criteria — Authoritative (v1)

Status: MVP-Minimal (Locked)
Applies to: Fit Scan v1 only

For MVP, the Fit Scan criteria are deterministic, non-probabilistic, and conservative.

The Fit Scan is implemented exactly as defined in:

OPENAI_PROMPTS_LIBRARY.md — GP-F02 (authoritative logic)

requirements_json (authoritative eligibility source)

ngo_profiles DB contract (authoritative NGO data source)

This document is a human-readable specification, not an expansion of scope.

No additional criteria, inference, or scoring logic may be introduced.

Rating Normalisation Rule (Authoritative)

Model-level ratings are mapped to product-level recommendations as follows:

Model Rating	Product Recommendation
STRONG	RECOMMENDED
MODERATE	APPLY_WITH_CAVEATS
WEAK	NOT_RECOMMENDED

Both values MUST be persisted in Fit Scan results.

Layer 1: Eligibility (Hard Gates)

Eligibility is binary and deterministic.

If any eligibility check fails, the Fit Scan result MUST be:
NOT_RECOMMENDED.

Eligibility Criteria
Geography

Does the NGO operate in at least one eligible geography?

Applicant Type (MVP Rule)

F### Applicant type (MVP Rule)
For MVP:
- PASS if `variant.eligibility_rules.applicant_type` is `NGO` or `MIXED`
- FAIL otherwise

NGO applicant type is treated as constant = "NGO" via `prompt_inputs.derived.applicant_type`.

Sector / Thematic Eligibility

Is there overlap between NGO focus sectors and required themes?

Explicit Exclusions

Is the NGO excluded by any rule?

### Eligibility Data Sources (Authoritative)

- `prompt_inputs.requirements.variants[*].eligibility_rules`
  - `geographies`
  - `themes_required`
  - `themes_excluded`
  - `org_types_allowed`
  - `org_types_excluded`
  - `applicant_type`
- `prompt_inputs.ngo.country`
- `prompt_inputs.ngo.focus_sectors`

No other fields may be used.

Eligibility Output

Pass → eligible = true

Fail → eligible = false (hard block)

Layer 2: Alignment (Scored 0–100)

Measures how well the NGO matches the opportunity (not whether it is allowed).

Alignment Criteria

Thematic overlap (NGO focus sectors vs required themes)

Geographic relevance

Mission relevance (high-level only)

Alignment Data Sources

ngo_profile.focus_sectors

ngo_profile.geographic_areas_of_work

requirements_json.variants[*].eligibility_rules.themes_required

Alignment Method

Deterministic weighted overlap

No probabilistic language

No learned scoring

Alignment Output Labels

STRONG | MODERATE | WEAK

Layer 3: Readiness (Scored 0–100)

Measures application preparedness, not organisational quality.

Readiness Criteria

Presence of past projects

Evidence availability

Capacity signals

Deadline proximity

Readiness Data Sources

ngo_profile.past_projects

requirements_json.variants[*].submission_items

application_deadline, deadline_type

Readiness Method

Penalise missing mandatory inputs

Penalise late deadlines (<14 days)

Floor score at 0

Readiness Output (Internal)

HIGH | MEDIUM | LOW
(Contributes to overall model rating)

Layer 4: Risk Signals (Informational Only)

Risk signals do not change eligibility.

They must always be surfaced if present.

Risk Signals

Capacity mismatch

First-time applicant

Short submission window

Process complexity

Missing critical data

Risk Output

Array of flags with severity:
LOW | MEDIUM | HIGH

Important Constraints

No predictions

No probabilities

No “chance of success”

All outputs must be explainable and traceable to stated data sources



MVP Fit Scan Criteria — Authoritative (v1)

Status: MVP-Minimal (Locked)
Applies to: Fit Scan v1 only

For MVP, the Fit Scan criteria are deterministic and limited.
They are implemented exactly as defined in:

OPENAI_PROMPTS_LIBRARY.md — GP-F02

This document serves as a human-readable reference, not an expansion of scope.

No additional criteria may be inferred or introduced.

Rating Normalisation Rule (Authoritative)

Model-level ratings are mapped to product recommendations as follows:

Model Rating	Product Recommendation
STRONG	RECOMMENDED
MODERATE	APPLY_WITH_CAVEATS
WEAK	NOT_RECOMMENDED

Both values MUST be persisted.

Layer 1: Eligibility (Hard Gates)

If any eligibility criterion fails, the Fit Scan result MUST be NOT_RECOMMENDED.

Criteria

Geography

Applicant type (NGO only, MVP)

Sector / thematic eligibility

Explicit exclusions

Data sources

requirements_json.variants[*].eligibility_rules

ngo_profile.country

ngo_profile.focus_sectors

Method

Exact match against eligibility rules

No fuzzy matching

No inference

Output

Pass → eligible = true

Fail → eligible = false (hard block)

Layer 2: Alignment (Scored 0–100)
Criteria

Thematic overlap (focus sectors vs required themes)

Geographic relevance

Mission relevance (high-level)

Data sources

ngo_profile.focus_sectors

ngo_profile.geographic_areas_of_work

requirements_json.variants[*].eligibility_rules.themes_required

Method

Weighted overlap scoring

No probabilistic language

Deterministic calculation only

Output labels

STRONG / MODERATE / WEAK

Layer 3: Readiness (Scored 0–100)
Criteria

Presence of past projects

Evidence availability

Capacity signals

Deadline proximity

Data sources

ngo_profile.past_projects

requirements_json.variants[*].submission_items

deadline_type, application_deadline

Method

Penalise missing required inputs

Penalise late deadlines (<14 days)

Floor at 0

Output labels

HIGH / MEDIUM / LOW (internal)

Contributes to overall model rating

Layer 4: Risk Signals (Informational Only)

Risk signals do not change eligibility but MUST be surfaced.

Signals

Capacity mismatch (grant size vs NGO scale)

First-time applicant

Short submission window

Process complexity

Missing critical data

Data sources

ngo_profile

requirements_json

Funding metadata

Output

Array of risk flags with severity:

Risk Type | HIGH | MEDIUM | LOW
  CAPACITY | ratio ≥ 2.0 | 1.0 ≤ ratio < 2.0 | 0.5 ≤ ratio < 1.0
  EVIDENCE | No past projects + missing M&E | No past projects OR missing M&E | Weak past projects
  TIMING | <14 days | 14-30 days | 30-60 days
  PROCESS | >15 items | 10-15 items | <10 items
  MISSING_DATA | Critical field (budget, mission) | Important field (staff, M&E) | Optional field

Important

No predictions, probabilities, or “chance of success” language is permitted.

All outputs must be explainable and traceable to data sources above.