# Audit 1603 — Profile Page Runtime Diagnosis

Date: 2026-03-16  
Scope: Frontend diagnosis + live Railway runtime capture (no code fixes applied)

## 1) Prior Code-Trace Findings (from static diagnosis)

### Profile page load sequence (`components/profile/ProfileForm.tsx`, `load()`)
1. `GET /api/ngo-profile` via `getNgoProfile()`
   - On success: code assumes `response.ngo_profile` exists and uses it to prefill form.
   - On error:
     - `404`: treated as create mode
     - non-`404`: bubbled to outer catch -> sets `error` -> `ErrorDisplay`
2. `GET /api/ngo-profile/completeness` via `getNgoProfileCompleteness()`
   - On success: updates completeness bar
   - On error: swallowed (`setCompleteness(null)`), does not trigger global error card

### Profile save sequence (`components/profile/ProfileForm.tsx`, `saveProfile()`)
1. `POST /api/ngo-profile` (create mode) or `PUT /api/ngo-profile` (edit mode)
2. `POST 409` fallback to `PUT` is present
3. `GET /api/ngo-profile/completeness` refresh after successful save
4. If from `/start` and completeness COMPLETE, redirects back to `/start?opportunity_id=...`

### API wrapper check (`lib/api-client.ts`)
- Base URL comes from `NEXT_PUBLIC_API_BASE_URL`
- Bearer token is attached from auth handlers
- Wrapper returns parsed JSON as-is; it does not unwrap nested envelopes

---

## 2) New Runtime Network Capture (live backend)

Base URL tested: `https://ngoinfo-grantpilot-production.up.railway.app`

### Test 1: `POST /api/auth/test-mode/mint`
- **Status:** `200`
- **Result:** access token minted successfully
- **Important:** response user is still `smoke-test@grantpilot.local` even when random email is sent

### Test 2: `GET /api/ngo-profile` (with minted Bearer token)
- **Status:** `200`
- **Body shape observed:** **top-level profile object**
  - Example keys: `organization_name`, `past_projects`, `profile_status`, `completeness_score`, etc.
  - **No `ngo_profile` envelope present**

### Test 3: `GET /api/ngo-profile/completeness`
- **Status:** `200`
- **Body shape observed:** `{ "profile_status", "completeness_score", "missing_fields" }`
- Matches frontend expectation for completeness shape

### Test 4: `PUT /api/ngo-profile` (valid canonical keys)
- **Status:** `200`
- **Body shape observed:** **top-level profile object**, not `{ "ngo_profile": ... }`

### Test 5: `PUT /api/ngo-profile` (legacy wrong keys)
- **Status:** `422`
- **Body:** `VALIDATION_ERROR` with `extra_forbidden` for:
  - `past_projects[].project_title`
  - `past_projects[].donor_funder`
  - `me_practices`
  - `previous_funders`

---

## 3) Consolidated Diagnosis

### Exact failing point
The likely failure is **not** an HTTP 500 from profile endpoints.  
It is a **frontend response-shape parsing error after a successful 200**:

- `ProfileForm.load()` reads `response.ngo_profile` after `GET /api/ngo-profile`
- Runtime backend returns a top-level profile object (no `ngo_profile` wrapper)
- Accessing/spreading `response.ngo_profile` therefore fails in UI code, causing the error state/card

### Why profile save appears broken
Same mismatch exists in save path:

- Save calls (`POST`/`PUT`) return top-level profile object
- Code expects `response.ngo_profile` and then dereferences it
- This can throw after successful network response, making save look failed in UI

---

## 4) Hypothesis Table

| Hypothesis | Evidence | Confidence |
|---|---|---|
| Frontend expects `response.ngo_profile`, backend returns top-level profile object | Live `GET`/`PUT /api/ngo-profile` both returned `200` with top-level object; frontend load/save code reads `response.ngo_profile` | HIGH |
| Visible error card is caused by client-side exception after successful response, not request URL/auth failure | Auth works (mint/token valid), profile endpoints return `200`; completeness call shape is fine; only profile object shape mismatches frontend expectation | HIGH |

---

## 5) Raw Capture Snippets (key)

- `GET /api/ngo-profile` -> `200`, body starts with:
  - `{ "organization_name": "...", "country_of_registration": "...", ... }`
- `PUT /api/ngo-profile` valid -> `200`, same top-level shape
- `PUT /api/ngo-profile` legacy keys -> `422` `extra_forbidden` (safety net works)

