# Pre-launch Smoke Report (Phase F-1)

Date: 2026-02-24 (UTC)

## Environment Details

- Frontend URL: `https://grantpilot.ngoinfo.org`
- Backend URL under test: `https://ngoinfo-grantpilot-production.up.railway.app`
- Frontend commit hash: `9ae22b4`
- Backend commit hash: `8197616`

## Smoke Harness Summary

- Primary runner: `scripts/smoke_test.py`
  - Track A (unauth/public + contract envelope checks)
  - Track B (authenticated checks via test-mode mint when `TEST_MODE_SECRET` is present)
- Secondary runner: `scripts/e2e_auth_profile_test.py`
  - Authenticated auth/profile lifecycle checks
- CI wiring: `.github/workflows/smoke-test.yml`
  - `python scripts/smoke_test.py`
  - `python scripts/e2e_auth_profile_test.py` (optional, `continue-on-error`)
- Execution command used:
  - `python scripts/smoke_test.py`
  - `python scripts/e2e_auth_profile_test.py`
- Required env vars confirmed in harness/workflow:
  - `SMOKE_BASE_URL`
  - `TEST_MODE_SECRET` (for authenticated test mode path)

## Smoke Test Audit Notes (Before Full Run)

### Drift found and fixed

1. `scripts/e2e_auth_profile_test.py` used deprecated paths:
   - `GET/POST/PUT /ngo-profile` -> corrected to `GET/POST/PUT /api/ngo-profile` (API_CONTRACT Section 6.1/6.2/6.3).
   - `GET /ngo-profile/completeness` -> corrected to `GET /api/ngo-profile/completeness` (Section 6.4).

2. `scripts/e2e_auth_profile_test.py` used stale profile payload keys/values:
   - `past_projects[].title` -> corrected to `past_projects[].project_title` (Section 6.1 schema).
   - sector values normalized to contract enum style (`HEALTH`, `EDUCATION`) (Section 6.1).

3. `scripts/e2e_auth_profile_test.py` refresh/logout flow drift:
   - After `POST /api/auth/refresh` (Section 3.6), script was logging out with stale refresh token.
   - Updated to use rotated `refresh_token` from refresh response before `POST /api/auth/logout` (Section 3.7).

4. `scripts/smoke_test.py` strengthened contract assertions:
   - Added `opportunity_title` presence checks on non-empty Fit Scan and Proposal list items (Sections 8.3, 9.3).
   - Added proposal status guard on list items (`DRAFT`/`DEGRADED`) (Section 9 status values).
   - Kept test-mode mint compatibility behavior: sends both body `secret` and `x-test-mode-secret` header due deployed backend behavior, while noting contract body requirement (Section 3.8).

### Contract mapping of asserted endpoints

- `GET /health` -> Section 2
- `POST /api/auth/exchange` -> Section 3.3
- `POST /api/auth/refresh` -> Section 3.6
- `POST /api/auth/logout` -> Section 3.7
- `POST /api/auth/test-mode/mint` -> Section 3.8
- `GET /api/me/entitlements` -> Section 4
- `GET /api/ngo-profile` -> Section 6.1
- `POST /api/ngo-profile` -> Section 6.2
- `PUT /api/ngo-profile` -> Section 6.3
- `GET /api/ngo-profile/completeness` -> Section 6.4
- `GET /api/funding-opportunities/{id}` -> Section 7.1
- `GET /api/fit-scans` -> Section 8.3
- `GET /api/proposals` -> Section 9.3
- Standard Error envelope assertions (`error_code`, `message`) -> Section 1
- Proposal status enum assertions -> Section 9 (status values table)
- Operational check (non-contract endpoint): `GET /openapi.json` (kept as deployment/spec availability check)

## Results Table

| Check | Contract reference | Result | Notes / remediation |
|---|---|---|---|
| Track A: `GET /health` | Section 2 | PASS | 200 |
| Track A: unauth `GET /api/ngo-profile` | Section 6.1 + Section 1 | PASS | 401 + standard envelope |
| Track A: unauth `GET /api/ngo-profile/completeness` | Section 6.4 + Section 1 | PASS | 401 + standard envelope |
| Track A: unauth `GET /api/fit-scans` | Section 8.3 + Section 1 | PASS | 401 + standard envelope |
| Track A: unauth `GET /api/proposals` | Section 9.3 + Section 1 | PASS | 401 + standard envelope |
| Track A: invalid `POST /api/auth/exchange` | Section 3.3 + Section 1 | PASS | 401 + standard envelope |
| Track A: invalid `POST /api/auth/refresh` | Section 3.6 + Section 1 | PASS | 401 + standard envelope |
| Track B: `POST /api/auth/test-mode/mint` | Section 3.8 | PASS | 200 |
| Track B: `GET /api/me/entitlements` | Section 4 | PASS | 200 |
| Track B: `GET /api/fit-scans` list shape | Section 8.3 | PASS | 200 + `fit_scans` array (+ `opportunity_title` key check when items present) |
| Track B: `GET /api/proposals` list shape + status | Section 9.3 + Section 9 status values | PASS | 200 + `proposals` array (+ `opportunity_title`, status guard when items present) |
| Track B: `GET /api/funding-opportunities/{id}` | Section 7.1 | PASS | 404 accepted as valid non-500 outcome in smoke harness |
| Extended e2e: profile read/create/update/completeness | Sections 6.1-6.4 | PASS | All calls 200 after path/payload fixes |
| Extended e2e: refresh + logout + post-logout protection | Sections 3.6, 3.7, 6.1 | PASS | Refresh rotation handled; logout 200; post-logout profile 401 |
| F-1 matrix coverage for J2/J3/J4/J5/J6/J7 proposal-generation/export flows | Phase F-1 checklist + Sections 9.1/9.2/9.4/9.5 | FAIL (not covered by current harness) | Add manual checklist evidence or extend harness in a follow-up smoke-only task before launch sign-off |

## Final Recommendation

**NO-GO (checklist incomplete), with API smoke stability confirmed.**

- API smoke harness itself is now contract-aligned for the endpoints it covers, and all executed checks passed in production.
- However, the current automated suite does not cover all Phase F-1 launch-journey checks (notably proposal generation/regeneration/export and broader J1-J7 end-to-end checklist evidence).
- To move to GO:
  1. Run and document the remaining Phase F-1 checklist items manually, or
  2. Add smoke-only checks for missing journey steps in the existing harness, then re-run.

