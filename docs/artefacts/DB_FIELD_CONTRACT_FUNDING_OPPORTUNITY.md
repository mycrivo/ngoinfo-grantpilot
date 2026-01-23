Status: Canonical (LOCKED FOR BUILD)
System of record: Railway Postgres (GrantPilot DB)
Applies to: funding_opportunities table, CSV imports, admin entry, proposal generation inputs
Renaming: structured_requirements → requirements_json (authoritative)

1) Canonical Table: funding_opportunities
1.1 Required columns (MVP)

Identity & timestamps

id (UUID) will be the primary key

created_at (timestamp, not null)

updated_at (timestamp, not null)

Provenance & URLs

source_url (text, not null) — canonical source page where details are described

application_url (text, not null) — canonical “apply” destination (can equal source_url)

Opportunity snapshot (list / search / filters)

title (text, not null)

donor_organization (text, not null)

funding_type (text, not null)

applicant_type (text enum, not null):
NGO | INDIVIDUAL | ACADEMIC_INSTITUTION | CONSORTIUM | MIXED

location_text (text, not null) — human-readable primary geography

focus_areas (text, not null) — comma-separated list for MVP (future: array)

deadline_type (text enum, not null):
FIXED | ROLLING | VARIES

application_deadline (date, nullable)

must be NOT NULL when deadline_type = FIXED

must be NULL allowed when ROLLING or VARIES

Amounts (nullable; unknown is valid)

currency (text, nullable; ISO recommended)

amount_min (numeric, nullable)

amount_max (numeric, nullable)

total_funding_available (numeric, nullable)

Publisher / UX text

short_summary (text, not null) — 1–2 lines for listing

overview_text (text, nullable) — longer narrative description

Eligibility & process (human-readable for MVP)

eligibility_criteria (text, nullable)

application_process (text, nullable)

Status

status (text enum, not null):
DRAFT | READY | PUBLISHED | ARCHIVED

is_active (boolean, not null, default true)

is_archived (boolean, not null, default false)

last_verified (date, nullable)

Authoritative requirements contract

requirements_json (JSONB, not null) — MUST conform to schema in Section 2

1.2 Optional columns (recommended but not required for MVP)

organization_types (text, nullable) — comma-separated list

geographic_focus (text, nullable) — comma-separated list for filtering

contact_information (text, nullable)

processing_status (text, nullable)

parsing_confidence (numeric, nullable) — manual or automated confidence

internal_notes (text, nullable)

2) Authoritative JSON Contract: requirements_json (JSONB)
2.1 Contract intent

requirements_json is the single source of truth for:

application variants/tracks

discrete submission requirements (“submission items”)

required documents/attachments classification

application process notes beyond the flat field

Proposal generation MUST be driven primarily by requirements_json.variants[*].submission_items.

2.2 Required top-level schema
{
  "version": "1.0",
  "opportunity_mode": "SINGLE" | "VARIANTS",
  "variants": [],
  "global_notes": {
    "review_criteria": [],
    "red_flags": [],
    "internal_curator_notes": ""
  }
}


Rules

version is required and must be "1.0" for MVP.

variants must contain:

exactly 1 variant when opportunity_mode = "SINGLE"

1+ variants when opportunity_mode = "VARIANTS"

2.3 Variant schema (required)

Each element of variants[] must conform to:

{
  "variant_id": "string",
  "variant_name": "string",
  "deadline_type": "FIXED|ROLLING|VARIES",
  "application_deadline": "YYYY-MM-DD or null",
  "eligibility_rules": {
    "applicant_type": "NGO|INDIVIDUAL|ACADEMIC_INSTITUTION|CONSORTIUM|MIXED",
    "geographies": ["string"],
    "org_types_allowed": ["string"],
    "org_types_excluded": ["string"],
    "themes_required": ["string"],
    "themes_excluded": ["string"],
    "notes": "string"
  },
  "submission_items": [],
  "required_documents": [],
  "process_notes": {
    "how_to_apply": "string",
    "portal_steps": ["string"],
    "special_conditions": ["string"]
  }
}


Rules

If deadline_type = FIXED, application_deadline must be non-null.

eligibility_rules.applicant_type must match the table-level applicant_type unless table-level is used as a broad umbrella; if mismatch, curator must explain in eligibility_rules.notes.

submission_items must be non-empty for READY opportunities.

2.4 Submission item schema (required)

Each element of submission_items[] must conform to:

{
  "item_id": "string",
  "label": "string",
  "type": "NARRATIVE|TABLE|UPLOAD|DECLARATION|PORTAL_FIELD|OTHER",
  "prompt_text": "string",
  "mandatory": true,
  "format_constraints": {
    "word_limit": 0,
    "page_limit": 0,
    "file_types": ["PDF","DOCX","XLSX"],
    "template_url": "string or null",
    "notes": "string"
  },
  "evaluation_hint": "string or null",
  "inputs_required": ["ngo_profile.<field_name>"],
  "generation_allowed": true
}


Rules

prompt_text must contain either:

the funder’s exact question/instruction, OR

a curator-authored faithful restatement (not speculation).

generation_allowed=false indicates the system must recommend upload/manual completion, not fabricate content.

inputs_required is advisory metadata; it must not block generation, but should be used to flag missing NGO profile fields.

2.5 Required document schema (required)

Each element of required_documents[] must conform to:

{
  "doc_id": "string",
  "name": "string",
  "mandatory": true,
  "type": "UPLOAD|TEMPLATE|EVIDENCE",
  "format": "PDF|DOCX|XLSX|OTHER",
  "notes": "string",
  "generation_allowed": false
}


Rules

generation_allowed defaults to false for documents unless explicitly approved.

Documents are distinct from submission items; documents represent attachments/evidence.

3) CSV Import Contract (MVP)
3.1 Required import support

CSV import must populate:

all required flat fields (Section 1.1)

requirements_json as a valid JSON string that conforms to Section 2

3.2 Minimum required CSV columns

title

donor_organization

funding_type

applicant_type

location_text

focus_areas

deadline_type

application_deadline

currency

amount_min

amount_max

total_funding_available

application_url

source_url

short_summary

overview_text

eligibility_criteria

application_process

requirements_json

status

is_active

is_archived

last_verified

4) Validation & Degradation Rules (implementation behaviour)
4.1 DB integrity validations (must enforce)

source_url, application_url, title, donor_organization, funding_type, applicant_type, location_text, focus_areas, deadline_type, short_summary, status, requirements_json must exist.

When deadline_type=FIXED, application_deadline must exist.

When status=READY, requirements_json.variants[*].submission_items must be non-empty.

4.2 Prompt engine dependency rules

Proposal generation MUST use:

requirements_json.variants[*].submission_items as the authoritative list of required outputs.

If requirements_json is missing/invalid OR submission_items empty:

Do not infer sections.

Return a degraded “missing requirements” response with required next actions for curator/admin.

5) Compatibility Note (ReqAgent later)

When ReqAgent is reintroduced:

It must output data that can be mapped into this contract without changing the prompt library behaviour.

requirements_json.version changes require explicit migrations and prompt version bumps.