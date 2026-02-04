# FUNDING_OPPORTUNITY_GOLDEN_RULES.md

**Status:** Canonical (LOCKED)  
**Version:** 1.0  
**Scope:** All GrantPilot funding opportunity seed records  
**Authority:** This document governs how funding opportunities are authored for the GrantPilot database. Any seed record that violates these rules is not production-ready.

---

## Golden Record Creation Rules

### 1. submission_items are mandatory and explicit
No opportunity may be considered seed-ready without structured `submission_items`.  

If the funder does not publish application requirements:
- Mark `status` as `DRAFT` (not `READY` or `PUBLISHED`)
- Flag in `internal_curator_notes`: "Submission requirements not publicly available from source"

---

### 2. Variants only reflect real evaluation forks
Use `VARIANTS` only when evaluation reality materially differs:
- Separate evaluation panels
- Different thematic eligibility rules
- Different submission requirements or deadlines
- Different applicant types

Do NOT create variants for:
- Multiple themes under one evaluation process
- Cosmetic differences in funder language
- Different funding amounts within the same track

---

### 3. AI affordance is declared per submission item
Explicitly state `generation_allowed: true | false` for each submission item.

**`generation_allowed: true`** when:
- AI can generate substantive content (narrative sections, problem statements, budget narratives, M&E plans)
- Content is based on NGO profile data + opportunity requirements

**`generation_allowed: false`** when:
- Requires upload (CVs, audited financials, registration certificates)
- Generated through funder portal (SNSF CV format, agency-specific forms)
- Legal/institutional documents (collaboration agreements, letters of support)
- Factual records AI cannot fabricate (research output lists, past performance data)

**Default:** When uncertain, set to `false` and require upload/manual completion.

---

### 4. Red flags must be explicit
Rejection conditions are first-class data in `red_flags[]`, not buried in prose.

Examples:
- ✅ "Current graduate students as main applicants"
- ✅ "Proposals outside defined thematic areas"
- ✅ "Organisations lacking audited accounts for past 2 years"
- ❌ "May not be suitable for early-stage organisations" (too vague)

---

### 5. Distinguish primary applicant from permitted partner roles
Eligibility must clearly separate:
- Who can be the **lead/main applicant** (primary ownership, legal responsibility)
- Who can be **co-applicants** or **project partners** (contributory roles, funding share)
- Who is **explicitly excluded**

Document this in:
- `eligibility_rules.applicant_type` (lead applicant constraint)
- `eligibility_rules.org_types_allowed` and `org_types_excluded`
- `eligibility_criteria` (narrative explanation)
- `notes` field within `eligibility_rules`

---

### 6. Advisory intelligence is labeled as non-deterministic
**Qualitative descriptors are allowed:**
- "Competitive evaluation"
- "Selective programme"
- "Historically demanding"

**Quantitative probabilities are PROHIBITED unless explicitly stated in source:**
- ❌ "15-20% success rate" (unless source says this)
- ❌ "Typically funds 1 in 8 applications" (unless source says this)
- ✅ "17% approval rate (11 of 66 proposals approved, 2014 call)" (if source provides numerator and denominator)

---

### 7. Quantitative claims require explicit source evidence
Page limits, budgets, word counts, timelines, and success rates must be **traceable to source text**.

If you cannot find explicit evidence:
- ✅ "Budget limits not specified in call document"
- ✅ "Evaluation timeline not published"
- ❌ "Typically 6-8 weeks for decision" (unless stated)

Otherwise, remain qualitative:
- "Decisions communicated within a reasonable timeframe"
- "Budget should reflect realistic project costs"

---

### 8. Eligibility, evaluation, and advice are conceptually separated
They may coexist in `requirements_json`, but must not be conflated.

**Eligibility** = hard gates (pass/fail):
- Geographic restrictions
- Applicant type requirements
- Thematic scope boundaries
- Mandatory documents

**Evaluation** = comparative assessment (scored/ranked):
- Review criteria
- Weighting factors
- Evaluation methodology

**Advice** = curator intelligence (non-deterministic):
- Risk signals
- Strategic recommendations
- Competitive positioning insights

---

### 9. If a rule cannot be satisfied from the source, degrade—do not invent
Absence of evidence leads to:
- Conservative phrasing ("not specified", "details not available")
- Marking fields as `null` or empty arrays `[]`
- Flagging gaps in `internal_curator_notes`

Never leads to:
- Fabricated page limits
- Assumed deadlines
- Invented budget ranges
- Speculative eligibility rules

---

### 10. Output Validation Before Finalization
Before delivering the CSV row, validate:

- [ ] All quantitative claims trace to specific source sentences
- [ ] No `submission_item` has `generation_allowed=true` for upload-only content (CVs, legal docs, certificates)
- [ ] `red_flags[]` contains explicit conditions, not vague advisory warnings
- [ ] `applicant_type` eligibility distinguishes lead applicant vs. partner roles
- [ ] `status` is `READY` only if `submission_items[]` is non-empty
- [ ] No invented facts remain (re-read `internal_curator_notes` for speculation)
- [ ] All URLs are correct and accessible
- [ ] `requirements_json` is valid JSON and conforms to schema

---

### 11. Scope Discipline: One Opportunity Per Seed
If a funder operates multiple distinct programmes, create **one seed per programme**, not a mega-seed.

**Exception:** Use `VARIANTS` only when a **single published call** explicitly offers multiple tracks with materially different submission/evaluation rules.

Examples:
- ❌ SNSF as one mega-opportunity covering all 20+ funding schemes
- ✅ Indo-Swiss Joint Research Programme 2026 with MoES and ICSSR as separate variants (single call, two evaluation panels)
- ✅ Wellcome Trust Discovery Awards (single scheme, no variants)

Accepted ingestion formats:

UTF-8

UTF-8 with BOM

Rejected formats:

Windows-1252

ISO-8859-1

“ANSI” (Excel default on Windows)

---

## Self-Audit Requirement (Mandatory)

Before producing the final CSV row:

1. **Re-read the opportunity source** and confirm every field is grounded
2. **Validate against Golden Rules 1-11** above
3. **Remove or rephrase** any quantitative claim that cannot be traced to source text
4. **Confirm** that no invented facts remain in any field
5. **Mark DRAFT** if submission requirements are incomplete or unavailable

**Proceed only once all rules are satisfied.**

---

## Enforcement

Any seed record submitted to GrantPilot production that violates these rules will be **rejected** and returned for revision.

Curators (human or AI) are responsible for validating their own work before submission.

---

**END OF DOCUMENT**