from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.core.errors import DomainError
from app.integrations.openai_client import OpenAIClient, OpenAIServiceError

PROMPT_LIBRARY_VERSION = "1.1.0"

SYSTEM_PROMPT = (
    "You are GrantPilot, a consultant-grade fit assessment system.\n"
    "You evaluate eligibility, alignment, readiness and risk using only provided inputs.\n"
    "You do not use probabilistic language and do not invent facts.\n"
    "You do not refuse generation, but you surface weaknesses clearly.\n"
    "All human-readable output fields must be plain English for NGO managers — "
    "addressed to the reader as you/your, naming real-world things, never citing internal field paths or JSON structure.\n"
    "Output valid JSON only."
)

USER_PROMPT_TEMPLATE = """
Evaluate this NGO's fit for this funding opportunity using the deterministic 4-layer assessment framework.

PROMPT INPUTS (AUTHORITATIVE):
{prompt_inputs_json}

SELECTED VARIANT: {selected_variant_id}

ASSESSMENT FRAMEWORK (Apply Deterministically)
Layer 1: ELIGIBILITY (0 or 100)

Use:
prompt_inputs.requirements.variants[*].eligibility_rules
prompt_inputs.ngo
prompt_inputs.derived.applicant_type (MVP constant = "NGO")

Checks (selected variant only):
applicant_type:
PASS if variant eligibility_rules.applicant_type is "NGO" or "MIXED"
FAIL otherwise

geography:
PASS if prompt_inputs.ngo.country is in eligibility_rules.geographies

thematic eligibility:
PASS if overlap exists between:
prompt_inputs.ngo.focus_sectors
and eligibility_rules.themes_required

exclusions:
FAIL if overlap exists between prompt_inputs.ngo.focus_sectors and eligibility_rules.themes_excluded

Scoring:
If ANY hard fail → eligibility subscore = 0, overall_fit_rating = WEAK
If all pass → eligibility subscore = 100

Layer 2: ALIGNMENT (0-100)

Start at 0, add points:
+40 if ≥1 match between prompt_inputs.ngo.focus_sectors and (eligibility_rules.themes_required OR prompt_inputs.opportunity.focus_areas)
+30 if prompt_inputs.ngo.geographic_areas_of_work overlaps (eligibility_rules.geographies OR prompt_inputs.opportunity.location_text)
+30 if applicant type alignment exists (variant applicant_type is NGO or MIXED)

Cap at 100.

Qualitative Labels:
80-100 = STRONG
50-79 = MODERATE
<50 = WEAK

Layer 3: READINESS (0-100)

Start at 100, subtract points:
−15 for EACH mandatory submission_item whose inputs_required fields are missing in prompt_inputs.ngo (cap total deduction at −60)
−20 if ≥2 mandatory upload items have status=MISSING/UNKNOWN in prompt_inputs.user.uploaded_documents_index
−20 if deadline_type is FIXED and <14 days from today AND key gaps exist

Floor at 0.

Qualitative Labels:
70-100 = HIGH
40-69 = MEDIUM
<40 = LOW

Layer 4: RISK FLAGS (Do not affect overall_fit_rating)
Identify risks (do not affect overall_fit_rating):

CAPACITY (deterministic):
If total_funding_available is specified and NGO annual budget is specified, compute a ratio and flag capacity risk.

Inputs:
Grant pool amount: prompt_inputs.opportunity.total_funding_available
Grant currency: prompt_inputs.opportunity.currency
NGO annual budget: prompt_inputs.ngo.annual_budget_amount
NGO budget currency: prompt_inputs.ngo.annual_budget_currency
Display helpers: prompt_inputs.derived.grant_amount_display (if present)

Currency handling (deterministic, no FX inference):
If any required currency field is missing → flag MISSING_DATA (severity=MEDIUM) and do not compute ratio.
If currencies do not match (opportunity.currency != ngo.annual_budget_currency) → flag MISSING_DATA (severity=MEDIUM) with description CURRENCY_MISMATCH_NO_FX, and do not compute ratio.
Only compute ratio when currencies match.

Ratio computation:
ratio = total_funding_available / annual_budget_amount

If annual_budget_amount is null/0/negative → flag MISSING_DATA (severity=MEDIUM) and do not compute ratio.

Thresholds (deterministic):
If ratio ≥ 2.00 → CAPACITY severity=HIGH
If 1.00 ≤ ratio < 2.00 → CAPACITY severity=MEDIUM
If 0.50 ≤ ratio < 1.00 → CAPACITY severity=LOW
If ratio < 0.50 → do not raise CAPACITY

EVIDENCE: No past projects in prompt_inputs.ngo.past_projects matching this thematic area (severity=MEDIUM)
TIMING: Deadline <30 days from today (severity=HIGH if <14 days)
PROCESS: Variant has >10 submission_items (severity=LOW)
MISSING_DATA: Critical NGO fields null/empty (e.g., annual_budget_amount, past_projects) (severity=MEDIUM)

OVERALL FIT RATING CALCULATION
If eligibility subscore = 0 → WEAK
Else if alignment ≥70 AND readiness ≥70 → STRONG
Else if alignment ≥40 AND readiness ≥40 → MODERATE
Else → WEAK

CRITICAL RULES
If data missing, flag in risk_flags as MISSING_DATA (severity per Layer 4 rules above).
Never use probability language: "likely", "probably", "should be competitive", "chances", "competitive".

OUTPUT LANGUAGE (all model-generated free text)
Applies to: primary_rationale, risk_flags[].description, eligibility_check.notes, eligibility_check.hard_fails, alignment_assessment.notes, readiness_assessment.notes, readiness_assessment.key_gaps[], recommended_modifications[].area, recommended_modifications[].recommendation, proceed_advice.conditions[].

Hard rules:
1. Plain English for a non-technical NGO manager.
2. Address the reader as "you / your".
3. Refer to things by their real-world name — never by field path. No prompt_inputs.*, no JSON keys, no underscores-as-words, no "null", no "=", no "[...]", no code-style identifiers. Internal codes (e.g. CURRENCY_MISMATCH_NO_FX) must never appear in free-text output.
4. Stay specific and grounded — name the actual country, sector, amount, count. Do not invent facts.
5. Where a risk or gap is fixable, say what to do about it.
6. Keep it concise and clinical — this is an assessment, not proposal prose. No filler, no hype, no probability language.

Translation principle (translate every data reference into how an NGO would describe it):
- prompt_inputs.ngo.country → your country / where you're based
- geographies=[...] → the regions this fund covers
- prompt_inputs.ngo.focus_sectors → your focus areas
- themes_required → what this funder is looking for
- prompt_inputs.ngo.annual_budget_amount → your annual budget
- full_time_staff → your full-time staff count
- monitoring_and_evaluation_practices → your monitoring & evaluation approach
- past_projects → your past projects / track record
- uploaded_documents_index=[] → the documents you haven't uploaded yet
- submission_items → the items you'll need to submit
- total_funding_available → the grant size

FACT PRESERVATION (downstream proposal generator consumes this output):
Preserve every substantive fact exactly — countries, sectors, amounts, currencies, counts, dates, which eligibility checks pass or fail, which risk flags fire and their severity. Only change phrasing for readability; do not omit, soften, or invent facts.

Examples (bad → good):

primary_rationale:
- BAD: "The NGO passes the framework's selected-variant eligibility checks because prompt_inputs.requirements.variants[0].eligibility_rules.applicant_type='MIXED', prompt_inputs.ngo.country='United Kingdom' is in geographies=['United Kingdom'], and prompt_inputs.ngo.focus_sectors includes 'EDUCATION'..."
- GOOD: "You're eligible for this fund: you're based in the UK, which it covers, and your focus on education matches what the funder supports. Your alignment is strong on geography, organisation type, and sector. The main thing holding you back is readiness — several details needed to complete the budget and core narrative are still missing from your profile."

risk_flags[].description — MISSING_DATA:
- BAD: "Critical NGO fields are null or empty: prompt_inputs.ngo.annual_budget_amount=null, prompt_inputs.ngo.annual_budget_range=null, prompt_inputs.ngo.full_time_staff=null..."
- GOOD: "A few key details are missing from your profile: annual budget, full-time staff count, your monitoring & evaluation approach, and your website. Add these so we can complete the budget and core narrative sections."

risk_flags[].description — EVIDENCE:
- BAD: "No past projects in prompt_inputs.ngo.past_projects clearly match the opportunity's required beneficiary group..."
- GOOD: "None of your listed past projects clearly match this funder's focus on disadvantaged children and young people aged 0–25 in the UK. Adding a relevant project would strengthen your application."

risk_flags[].description — PROCESS:
- BAD: "The selected variant contains 13 submission_items, which creates a comparatively heavy application process."
- GOOD: "This is a heavier application — there are 13 separate items to prepare and submit."

primary_rationale must be 2-4 sentences explaining the rating (specific alignment or gap, plain English per rules above).

Output ONLY valid JSON matching this schema:
{
  "fit_summary": {
    "overall_fit_rating": "STRONG|MODERATE|WEAK",
    "subscores": {
      "eligibility": 0-100,
      "alignment": 0-100,
      "readiness": 0-100
    },
    "primary_rationale": "string (2-4 sentences)"
  },
  "eligibility_check": {
    "eligible": true,
    "hard_fails": ["string"],
    "notes": "string"
  },
  "alignment_assessment": {
    "thematic_alignment": "STRONG|MODERATE|WEAK",
    "geographic_alignment": "STRONG|MODERATE|WEAK",
    "applicant_type_alignment": "STRONG|MODERATE|WEAK",
    "notes": "string"
  },
  "readiness_assessment": {
    "documentation_readiness": "HIGH|MEDIUM|LOW",
    "evidence_strength": "HIGH|MEDIUM|LOW",
    "key_gaps": ["string"],
    "notes": "string"
  },
  "risk_flags": [
    {
      "risk_type": "ELIGIBILITY|CAPACITY|EVIDENCE|PROCESS|TIMING|MISSING_DATA",
      "severity": "LOW|MEDIUM|HIGH",
      "description": "string"
    }
  ],
  "recommended_modifications": [
    {
      "area": "string",
      "recommendation": "string"
    }
  ],
  "proceed_advice": {
    "recommended": true,
    "conditions": ["string"]
  }
}
"""


class FitScanExecutor:
    def __init__(self, client: OpenAIClient | None = None) -> None:
        self._client = client or OpenAIClient()

    def execute(
        self, prompt_inputs: dict, *, feature: str = "fit_scan", user_id: str | None = None
    ) -> dict[str, Any]:
        settings = get_settings()
        prompt_inputs_json = json.dumps(prompt_inputs, separators=(",", ":"), ensure_ascii=False)
        selected_variant_id = (
            prompt_inputs.get("prompt_inputs", {})
            .get("derived", {})
            .get("selected_variant_id")
        )
        selected_variant_id = selected_variant_id or ""

        user_prompt = (
            USER_PROMPT_TEMPLATE.replace("{prompt_inputs_json}", prompt_inputs_json)
            .replace("{selected_variant_id}", selected_variant_id)
        )

        try:
            response = self._client.create_chat_completion(
                model=settings.OPENAI_MODEL_PRIMARY,
                fallback_model=settings.OPENAI_MODEL_FALLBACK,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=2000,
                feature=feature,
                user_id=user_id,
            )
        except OpenAIServiceError as exc:
            raise DomainError(
                error_code="FIT_SCAN_FAILED",
                message="AI service unavailable",
                status_code=500,
                details={
                    "reason": exc.category,
                    "retry_attempted": exc.retry_attempted,
                },
            ) from exc
        payload = _extract_json_payload(response)
        _validate_fit_scan_payload(payload)
        return payload


def _extract_json_payload(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as exc:  # pragma: no cover - runtime safeguard
        _raise_fit_scan_failed("Invalid Fit Scan response payload", reason="AI_OUTPUT_INVALID")


def _validate_fit_scan_payload(payload: dict[str, Any]) -> None:
    fit_summary = payload.get("fit_summary")
    if not isinstance(fit_summary, dict):
        _raise_fit_scan_failed("Missing fit_summary")

    overall = fit_summary.get("overall_fit_rating")
    if overall not in {"STRONG", "MODERATE", "WEAK"}:
        _raise_fit_scan_failed("Invalid overall_fit_rating")

    subscores = fit_summary.get("subscores")
    if not isinstance(subscores, dict):
        _raise_fit_scan_failed("Missing subscores")

    for key in ("eligibility", "alignment", "readiness"):
        value = subscores.get(key)
        if not isinstance(value, int) or value < 0 or value > 100:
            _raise_fit_scan_failed(f"Invalid subscore {key}")

    primary_rationale = fit_summary.get("primary_rationale")
    if not isinstance(primary_rationale, str) or not primary_rationale.strip():
        _raise_fit_scan_failed("Missing primary_rationale")


def _raise_fit_scan_failed(message: str, *, reason: str = "AI_OUTPUT_INVALID") -> None:
    raise DomainError(
        error_code="FIT_SCAN_FAILED",
        message=message,
        status_code=500,
        details={"reason": reason},
    )
