GP_U01_SYSTEM_PROMPT = """You are GrantPilot's input normalization layer.
You do not write proposal content.
You map user intent and the DB's requirements_json into a deterministic generation plan.
You must not invent requirements.
Output valid JSON only."""

GP_U01_USER_PROMPT_TEMPLATE = """Normalize user inputs and create a generation plan for this funding opportunity.

PROMPT INPUTS (AUTHORITATIVE):
{prompt_inputs_json}

TASK:

Select Variant (if not provided):

If prompt_inputs.user.selected_variant_id is provided and exists → use it

Else apply deterministic selection:
a. Prefer variant whose eligibility_rules.applicant_type matches prompt_inputs.ngo.organization_type
b. Prefer variant with matching geography (prompt_inputs.ngo.country in variant.eligibility_rules.eligible_countries)
c. If still ambiguous → select first variant and flag warning: "VARIANT_SELECTION_AMBIGUOUS"
Deterministic Selection (Tie-Breaking):
  1. Filter to variants where applicant_type matches
  2. From (1), filter to variants where ngo.country in geographies[]
  3. If multiple remain, select variant with lowest array index (first in list)

Map Submission Items:
For each submission_item in selected variant:

Determine if generation_allowed (based on item.type and item.generation_allowed field)

Identify missing NGO profile fields required for generation (from item.inputs_required)

Flag items that require upload

Summarize Required Documents:
From variant.required_documents, list status (PROVIDED/MISSING/UNKNOWN) based on prompt_inputs.user.uploaded_documents_index

Output ONLY valid JSON matching this schema:

{
  "selected_variant_id": "string",
  "generation_plan": {
    "items_to_generate": [
      {
        "item_id": "string",
        "type": "NARRATIVE|TABLE|UPLOAD|DECLARATION|PORTAL_FIELD|OTHER",
        "generation_allowed": true,
        "missing_ngo_fields": ["string"],
        "notes": "string"
      }
    ],
    "items_upload_required": [
      {
        "item_id": "string",
        "reason": "string"
      }
    ],
    "required_documents_summary": [
      {
        "doc_id": "string",
        "name": "string",
        "mandatory": true,
        "status": "PROVIDED|MISSING|UNKNOWN"
      }
    ]
  },
  "warnings": ["string"]
}
"""
