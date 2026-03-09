# GrantPilot Backend Smoke Test Diagnostic

Date: 2026-03-09  
Base URL: `https://ngoinfo-grantpilot-production.up.railway.app`  
Mode: Live API diagnostic via `curl` (no code changes)

## Test 0.1: Health check
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/health`  
**Payload:** none  
**Status:** `200`  
**Response:** `{"status":"ok","service":"grantpilot","version":"v1.0.0","time_utc":"2026-03-09T18:22:05.886801+00:00"}`  
**Assessment:** PASS  
**Notes:** API reachable.

## Test 0.2: OpenAPI discovery
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/openapi.json`  
**Payload:** none  
**Status:** `200`  
**Response:** full OpenAPI returned (saved locally during run).  
**Assessment:** PASS  
**Notes:** Extracted schema fields below from live OpenAPI.

### OpenAPI schema field extraction (live)

- **`NGOProfileCreate`**  
  `organization_name, country_of_registration, mission_statement, focus_sectors, geographic_areas_of_work, target_groups, past_projects, year_of_establishment, contact_person_name, contact_email, website, full_time_staff, annual_budget_amount, annual_budget_currency, monitoring_and_evaluation_practices, funders_worked_with_before`

- **`NGOProfileUpdate`**  
  `organization_name, country_of_registration, mission_statement, focus_sectors, geographic_areas_of_work, target_groups, past_projects, year_of_establishment, contact_person_name, contact_email, website, full_time_staff, annual_budget_amount, annual_budget_currency, monitoring_and_evaluation_practices, funders_worked_with_before`

- **`NGOProfileRead`**  
  `organization_name, country_of_registration, mission_statement, focus_sectors, geographic_areas_of_work, target_groups, past_projects, year_of_establishment, contact_person_name, contact_email, website, full_time_staff, annual_budget_amount, annual_budget_currency, monitoring_and_evaluation_practices, funders_worked_with_before, id, user_id, profile_status, completeness_score, missing_fields, created_at, updated_at, last_completed_at`

- **`PastProject`**  
  `title, donor, duration, location, summary`

- **`NGOProfileCompletenessResponse`**  
  `profile_status, completeness_score, missing_fields`

- **`FitScanCreateRequest`**  
  `funding_opportunity_id`

## Test 1.1: Mint test tokens
**Request:** `POST https://ngoinfo-grantpilot-production.up.railway.app/api/auth/test-mode/mint`  
**Payload:** `{"secret":"...","email":"smoke-test@grantpilot.local","full_name":"Smoke Test","plan":"FREE"}`  
**Status:** `200`  
**Response:**  
`{"access_token":"<jwt>","refresh_token":"<opaque>","token_type":"Bearer","expires_in":900,"user":{"id":"eb09c4f0-f0b3-4ce8-911c-5862d01014fd","email":"smoke-test@grantpilot.local","full_name":null,"plan":"FREE"}}`  
**Assessment:** PASS  
**Notes:** Mint works; response returned `user.full_name: null`.

## Test 1.2: Verify token via entitlements
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/me/entitlements`  
**Payload:** none  
**Status:** `200`  
**Response:**  
`{"plan":"FREE","entitlements":{"fit_scans":{"limit":1,"used":0,"remaining":1,"period":"LIFETIME","reset_at":null},"proposals":{"limit":1,"used":0,"remaining":1,"period":"LIFETIME","reset_at":null},"proposal_regenerations":{"limit_per_proposal":0}}}`  
**Assessment:** PASS  
**Notes:** Token valid; plan/quota shape present.

## Test 2.1: Check existing profile
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** none  
**Status:** `200`  
**Response:** existing profile returned; notable excerpt:  
`"past_projects":[{"title":null,"donor":null,"duration":null,"location":null,"summary":null}]` and `"profile_status":"COMPLETE","completeness_score":100`  
**Assessment:** UNEXPECTED  
**Notes:** Profile already existed; had null past project title/donor despite `COMPLETE`.

## Test 2.2: Completeness before profile operation
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile/completeness`  
**Payload:** none  
**Status:** `200`  
**Response:** `{"profile_status":"COMPLETE","completeness_score":100,"missing_fields":[]}`  
**Assessment:** PASS  
**Notes:** Uses `profile_status` + `completeness_score` (not `status` + `percent_complete`), no `required_fields`, no `updated_at`.

## Test 2.3a: Update profile with `project_title/donor_funder`, `me_practices`, `previous_funders`
**Request:** `PUT https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** full NGO payload using:
- `past_projects[].project_title`, `past_projects[].donor_funder`
- `me_practices`
- `previous_funders`  
**Status:** `200`  
**Response:** profile updated but key fields came back null/empty:
- `past_projects[].title: null`
- `past_projects[].donor: null`
- `monitoring_and_evaluation_practices: null`
- `funders_worked_with_before: []`  
**Assessment:** FAIL  
**Notes:** Endpoint accepted request but silently ignored mismatched field names.

## Test 2.3b: Update profile with `title/donor`, `monitoring_and_evaluation_practices`, `funders_worked_with_before`
**Request:** `PUT https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** same NGO payload but OpenAPI-style keys:
- `past_projects[].title`, `past_projects[].donor`
- `monitoring_and_evaluation_practices`
- `funders_worked_with_before`  
**Status:** `200`  
**Response:** fields persisted correctly:
- `past_projects` titles/donors populated
- `monitoring_and_evaluation_practices` populated
- `funders_worked_with_before` populated  
**Assessment:** PASS  
**Notes:** Confirms backend expects OpenAPI names, not contract/frontend names.

## Test 2.4: Read back profile after save
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** none  
**Status:** `200`  
**Response:** profile data includes populated:
- `past_projects` (2 entries with `title`/`donor`)
- `monitoring_and_evaluation_practices`
- `funders_worked_with_before`  
Also includes `profile_status:"COMPLETE"`, `completeness_score:100`.  
**Assessment:** PASS  
**Notes:** Data integrity is good when OpenAPI field names are used.

## Test 2.5: Completeness after save
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile/completeness`  
**Payload:** none  
**Status:** `200`  
**Response:** `{"profile_status":"COMPLETE","completeness_score":100,"missing_fields":[]}`  
**Assessment:** PASS  
**Notes:** Profile remains complete.

## Test 2.6: PUT update path with third project
**Request:** `PUT https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** same as 2.3b plus third `past_projects` item  
**Status:** `200`  
**Response:** returned profile includes all 3 project entries with `title`/`donor` values.  
**Assessment:** PASS  
**Notes:** Update path works.

## Test 2.7: POST create while profile exists
**Request:** `POST https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** same as 2.6  
**Status:** `409`  
**Response:** `{"error_code":"PROFILE_ALREADY_EXISTS","message":"Profile already exists"}`  
**Assessment:** PASS  
**Notes:** Correct conflict behavior.

## Test 3.1: Funding opportunities availability probe
**Request:** OpenAPI path discovery + list probes  
- Found only `GET /api/funding-opportunities/{opportunity_id}` in OpenAPI (no list endpoint).
- Also checked user lists for reusable IDs:
  - `GET /api/fit-scans?limit=5` -> `{"fit_scans":[]}` (`200`)
  - `GET /api/proposals?limit=5` -> `{"proposals":[]}` (`200`)  
**Payload:** none  
**Status:** `200`  
**Response:** no opportunity IDs discoverable from available endpoints/responses.  
**Assessment:** UNEXPECTED  
**Notes:** Cannot deterministically obtain a valid `funding_opportunity_id` via public API surface.

## Test 4.1: Create fit scan
**Request:** `POST /api/fit-scans`  
**Payload:** `{ "funding_opportunity_id": "{id}" }`  
**Status:** SKIPPED  
**Response:** SKIPPED  
**Assessment:** SKIPPED  
**Notes:** No valid opportunity ID available from Phase 3.

## Test 4.2: Get fit scan by ID
**Request:** `GET /api/fit-scans/{fit_scan_id}`  
**Payload:** none  
**Status:** SKIPPED  
**Response:** SKIPPED  
**Assessment:** SKIPPED  
**Notes:** Dependent on 4.1.

## Test 5.1: Token refresh
**Request:** `POST https://ngoinfo-grantpilot-production.up.railway.app/api/auth/refresh`  
**Payload:** `{"refresh_token":"<from 1.1>"}`  
**Status:** `200`  
**Response:** `{"access_token":"<new_jwt>","refresh_token":"<new_opaque>","token_type":"Bearer","expires_in":900}`  
**Assessment:** PASS  
**Notes:** Rotation works.

## Test 5.2: Use old access token after refresh
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** none  
**Status:** `200`  
**Response:** full profile payload returned.  
**Assessment:** PASS  
**Notes:** Old access token remained valid at test time (expected if not revoked and not expired).

## Test 5.3: Use new access token
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** none  
**Status:** `200`  
**Response:** full profile payload returned.  
**Assessment:** PASS  
**Notes:** New token valid.

## Test 5.4: Protected endpoint without auth
**Request:** `GET https://ngoinfo-grantpilot-production.up.railway.app/api/ngo-profile`  
**Payload:** none  
**Status:** `401`  
**Response:** `{"error_code":"UNAUTHORIZED","message":"Unauthorized"}`  
**Assessment:** PASS  
**Notes:** Correct error envelope shape.

## Summary Table

| Test | Status | Assessment | Issue |
|------|--------|------------|-------|
| 0.1 | 200 | PASS | None |
| 0.2 | 200 | PASS | OpenAPI shape differs from API_CONTRACT naming |
| 1.1 | 200 | PASS | None |
| 1.2 | 200 | PASS | None |
| 2.1 | 200 | UNEXPECTED | Existing profile had null past project fields but marked COMPLETE |
| 2.2 | 200 | PASS | Completeness fields are `profile_status/completeness_score` |
| 2.3a | 200 | FAIL | `project_title/donor_funder`, `me_practices`, `previous_funders` ignored |
| 2.3b | 200 | PASS | OpenAPI field names persisted correctly |
| 2.4 | 200 | PASS | Data integrity OK with OpenAPI keys |
| 2.5 | 200 | PASS | COMPLETE with empty missing_fields |
| 2.6 | 200 | PASS | PUT update path works |
| 2.7 | 409 | PASS | Correct `PROFILE_ALREADY_EXISTS` |
| 3.1 | 200 | UNEXPECTED | No funding-opportunity list path; no discoverable opportunity IDs |
| 4.1 | SKIPPED | SKIPPED | Blocked by missing valid opportunity ID |
| 4.2 | SKIPPED | SKIPPED | Dependent on 4.1 |
| 5.1 | 200 | PASS | Refresh rotation works |
| 5.2 | 200 | PASS | Old token still valid in window |
| 5.3 | 200 | PASS | New token valid |
| 5.4 | 401 | PASS | Proper unauth response |

## Critical Findings

1. **PastProject accepted fields:** `title` / `donor`  
   - `project_title` / `donor_funder` were silently ignored (2.3a).

2. **M&E accepted field:** `monitoring_and_evaluation_practices`  
   - `me_practices` ignored (2.3a).

3. **Funders accepted field:** `funders_worked_with_before`  
   - `previous_funders` ignored (2.3a).

4. **Exact completeness response shape:**  
   `{"profile_status": "...", "completeness_score": <int>, "missing_fields": [...]}`  
   - No `status`, no `percent_complete`, no `required_fields`, no `updated_at`.

5. **Complete profile reaches COMPLETE:** Yes (`profile_status: COMPLETE`, score `100`).

6. **PUT after POST/create-existing:** Yes, PUT works; POST on existing correctly returns 409.

7. **Seeded funding opportunities available:** Not determinable from exposed API.  
   - Only detail endpoint exists; no list endpoint; no IDs discoverable from user lists.

8. **Fit scan success against complete profile:** Not tested (blocked by missing opportunity ID).

## Recommended Fix Sequence

1. **Backend first: eliminate silent field-loss on profile write**  
   Accept alias keys (`project_title`, `donor_funder`, `me_practices`, `previous_funders`) or reject them with explicit 422 (preferred over silent null persistence).

2. **Backend first: align/decide canonical response shapes**  
   Completeness endpoint currently serves legacy shape (`profile_status/completeness_score`), conflicting with contract expecting (`status/percent_complete/...`). Pick one canonical and enforce.

3. **Backend first: provide opportunity discovery path for diagnostics**  
   Add a safe list endpoint or a test helper to obtain at least one valid funding opportunity ID for E2E smoke.

4. **Frontend alignment second**  
   Ensure frontend profile payload matches chosen backend schema exactly (current backend OpenAPI shape is `title/donor`, `monitoring_and_evaluation_practices`, `funders_worked_with_before`).

5. **Contract/OpenAPI reconciliation**  
   Update `API_CONTRACT.md` and OpenAPI to match actual accepted payload and completeness response (or vice versa), then regenerate smoke assertions from that canonical source.

