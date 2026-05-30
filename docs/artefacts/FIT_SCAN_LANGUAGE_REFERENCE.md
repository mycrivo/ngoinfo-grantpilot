# Fit Scan Result — Human Language Reference

**Purpose:** Exact display copy for the Fit Scan result page, so the Cursor frontend change (part B) and the GP-F02 prompt rewrite (part A) have zero ambiguity.

**Scope:** Display labels + microcopy + prose principles. No scoring, schema, thresholds, or enum *values* change — only how they are shown to the user and how the model phrases free text.

**Audience:** A non-technical NGO manager. If a phrase would confuse someone who has never seen the database, it's wrong.

---

## A. Verdict badge (frontend label map)

Source field: `overall_recommendation`. Show **one** verdict. Hide the internal `model_rating` pill entirely (it duplicates the verdict in jargon).

| Enum value (do not change) | Display label | Accent |
|---|---|---|
| `RECOMMENDED` | Strong fit — worth applying | green |
| `APPLY_WITH_CAVEATS` | Worth applying — a few gaps to close first | amber |
| `NOT_RECOMMENDED` | Not a strong fit right now | red |

Fallback for any unexpected value: show "Assessment complete" in neutral grey (never show the raw enum).

---

## B. Score dimensions (frontend microcopy)

Keep the 0–100 numbers and bars exactly as they are. Add one plain-English line under each label.

| Label | One-line descriptor |
|---|---|
| Eligibility | Do you meet the funder's hard requirements? |
| Alignment | How well your mission and focus match this opportunity |
| Readiness | How prepared your application is right now |

(Colour thresholds on the bars are unchanged.)

---

## C. Risk flag type labels (frontend label map)

Source field: `risk_flags[].risk_type`. Map the raw type to a human title. The *description* text comes from the model (see Section E) — the frontend only relabels the type.

| Enum value (do not change) | Display title |
|---|---|
| `ELIGIBILITY` | Eligibility concern |
| `CAPACITY` | Grant size vs. your scale |
| `EVIDENCE` | Track record evidence |
| `PROCESS` | Application workload |
| `TIMING` | Deadline pressure |
| `MISSING_DATA` | Missing profile information |

Fallback for any unexpected type: "Point to review".

---

## D. Severity labels (frontend label map)

Source field: `risk_flags[].severity`. Title-case only; keep existing colour coding.

| Enum value (do not change) | Display label |
|---|---|
| `HIGH` | High |
| `MEDIUM` | Medium |
| `LOW` | Low |

---

## E. Prose fields (backend GP-F02 rewrite — model-generated text)

These fields are written by the model, not the frontend: `primary_rationale`, `risk_flags[].description`, `eligibility_check.notes`, `alignment_assessment.notes`, `readiness_assessment.notes`, `readiness_assessment.key_gaps[]`, `recommended_modifications[].recommendation`.

### Hard rules for all prose

1. Plain English for a non-technical NGO manager.
2. Address the reader as "you / your".
3. Refer to things by their real-world name, **never** by field path. No `prompt_inputs.*`, no JSON keys, no underscores-as-words, no `null`, no `=`, no `[...]`, no code-style identifiers.
4. Stay specific and grounded — name the actual country, sector, amount, count. Do not invent facts (fact-safety).
5. Where a risk or gap is fixable, say what to do about it.
6. Keep it concise and clinical — this is an assessment, not proposal prose. No filler, no hype, no probability language ("likely", "should be competitive").

### Translation principle (field → human)

The model must translate every data reference into how an NGO would describe it:

| Internal reference | How to say it to the user |
|---|---|
| `prompt_inputs.ngo.country` | your country / where you're based |
| `geographies=[...]` | the regions this fund covers |
| `prompt_inputs.ngo.focus_sectors` | your focus areas |
| `themes_required` | what this funder is looking for |
| `prompt_inputs.ngo.annual_budget_amount` | your annual budget |
| `full_time_staff` | your full-time staff count |
| `monitoring_and_evaluation_practices` | your monitoring & evaluation approach |
| `past_projects` | your past projects / track record |
| `uploaded_documents_index=[]` | the documents you haven't uploaded yet |
| `submission_items` | the items you'll need to submit |
| `total_funding_available` | the grant size |

### Before / after (grounded in the current screen)

**primary_rationale**

- Before: *"The NGO passes the framework's selected-variant eligibility checks because prompt_inputs.requirements.variants[0].eligibility_rules.applicant_type='MIXED', prompt_inputs.ngo.country='United Kingdom' is in geographies=['United Kingdom'], and prompt_inputs.ngo.focus_sectors includes 'EDUCATION'..."*
- After: *"You're eligible for this fund: you're based in the UK, which it covers, and your focus on education matches what the funder supports. Your alignment is strong on geography, organisation type, and sector. The main thing holding you back is readiness — several details needed to complete the budget and core narrative are still missing from your profile."*

**risk_flags[].description — MISSING_DATA**

- Before: *"Critical NGO fields are null or empty: prompt_inputs.ngo.annual_budget_amount=null, prompt_inputs.ngo.annual_budget_range=null, prompt_inputs.ngo.full_time_staff=null, prompt_inputs.ngo.monitoring_and_evaluation_practices=null, prompt_inputs.ngo.website=null."*
- After: *"A few key details are missing from your profile: annual budget, full-time staff count, your monitoring & evaluation approach, and your website. Add these so we can complete the budget and core narrative sections."*

**risk_flags[].description — EVIDENCE**

- Before: *"No past projects in prompt_inputs.ngo.past_projects clearly match the opportunity's required beneficiary group of disadvantaged children and young people aged 0–25 in the UK. The listed project has donor='test', title='test'..."*
- After: *"None of your listed past projects clearly match this funder's focus on disadvantaged children and young people aged 0–25 in the UK. Adding a relevant project would strengthen your application."*

**risk_flags[].description — PROCESS**

- Before: *"The selected variant contains 13 submission_items, which creates a comparatively heavy application process."*
- After: *"This is a heavier application — there are 13 separate items to prepare and submit."*

---

## F. Empty / edge states

- **No risk flags:** show a positive line, e.g. "No major risks flagged." Never show an empty section header alone.
- **Missing opportunity title:** "this opportunity" rather than a blank or `null`.
- **Any unmapped enum:** use the fallback labels above; never render the raw enum string to the user.

---

## G. What is explicitly NOT changing

- Subscore numbers and the 0–100 scale.
- Which risk flags fire and their severity logic.
- Enum *values* in the data and API (only their *display* changes).
- The rating → recommendation mapping.
- The JSON schema shape.

Only display labels, microcopy, and the model's phrasing of free-text fields change.
