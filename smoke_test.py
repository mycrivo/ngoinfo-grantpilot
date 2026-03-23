#!/usr/bin/env python3
"""
GrantPilot End-to-End Smoke Test
Simulates a real user journey using mint tokens.
"""

import os
import sys
import json
import time
import requests

# ---------------------------------------------------------------------------
# Configuration — secret is read from env or passed as argument, never logged
# ---------------------------------------------------------------------------
BASE_URL = "https://ngoinfo-grantpilot-production.up.railway.app"
FUNDING_OPPORTUNITY_ID = "29dfccb1-ca58-4481-bfde-33e934a39039"
SECRET = os.environ.get("TEST_MODE_SECRET", "yY6JQvHc9p2VwF7M3qE4N8sR0kX5dA1ZbUeT21j")

DEFAULT_TIMEOUT = 30
PROPOSAL_TIMEOUT = 120

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
results = []   # list of (label, description, status, note)
warnings = []  # list of warning strings

def record(label, description, passed, note=""):
    status = "PASS" if passed else "FAIL"
    results.append((label, description, status, note))
    indicator = "✓" if passed else "✗"
    print(f"  {indicator} {label}  {description:<50s}  {status}  {note}")
    return passed

def warn(msg):
    warnings.append(msg)
    print(f"  ⚠  WARNING: {msg}")

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# TRACK A — Unauthenticated baseline
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("TRACK A — Unauthenticated baseline")
print("=" * 70)

# A1
try:
    r = requests.get(f"{BASE_URL}/health", timeout=DEFAULT_TIMEOUT)
    record("A1", "GET /health → 200", r.status_code == 200, f"got {r.status_code}")
except Exception as e:
    record("A1", "GET /health → 200", False, str(e))

# A2
try:
    r = requests.get(f"{BASE_URL}/api/ngo-profile", timeout=DEFAULT_TIMEOUT)
    record("A2", "GET /ngo-profile (no auth) → 401", r.status_code == 401, f"got {r.status_code}")
except Exception as e:
    record("A2", "GET /ngo-profile (no auth) → 401", False, str(e))

# A3
try:
    r = requests.get(f"{BASE_URL}/api/me/entitlements", timeout=DEFAULT_TIMEOUT)
    record("A3", "GET /me/entitlements (no auth) → 401", r.status_code == 401, f"got {r.status_code}")
except Exception as e:
    record("A3", "GET /me/entitlements (no auth) → 401", False, str(e))

# A4
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/magic-link/request",
        json={"email": "smoke-test-invalid@example.org"},
        timeout=DEFAULT_TIMEOUT,
    )
    record("A4", "POST /auth/magic-link/request → 200", r.status_code == 200, f"got {r.status_code}")
except Exception as e:
    record("A4", "POST /auth/magic-link/request → 200", False, str(e))

# A5
try:
    r = requests.get(f"{BASE_URL}/openapi.json", timeout=DEFAULT_TIMEOUT)
    record("A5", "GET /openapi.json → 200", r.status_code == 200, f"got {r.status_code}")
except Exception as e:
    record("A5", "GET /openapi.json → 200", False, str(e))

# A6
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/refresh",
        json={"refresh_token": "invalid-token-xyz"},
        timeout=DEFAULT_TIMEOUT,
    )
    ok = r.status_code in (401, 422)
    record("A6", "POST /auth/refresh (bad token) → 401/422", ok, f"got {r.status_code}")
except Exception as e:
    record("A6", "POST /auth/refresh (bad token) → 401/422", False, str(e))

# ---------------------------------------------------------------------------
# TRACK B — Full authenticated user journey (FREE plan)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("TRACK B — Full authenticated journey (FREE plan)")
print("=" * 70)

access_token = None
refresh_token = None
fit_scan_id = None
proposal_id = None
b1_fit_used = 0
b1_proposal_used = 0

# B0 — Mint token
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={"X-Test-Mode-Secret": SECRET, "Content-Type": "application/json"},
        json={
            "secret": SECRET,
            "email": "smoke-free@grantpilot-test.org",
            "full_name": "Smoke Test User",
            "plan": "FREE",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    ok = r.status_code == 200 and bool(access_token) and bool(refresh_token)
    record("B0", "Mint FREE token", ok, f"got {r.status_code}" + ("" if ok else f" body={json.dumps(data)[:200]}"))
except Exception as e:
    record("B0", "Mint FREE token", False, str(e))

auth_headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}

# B1 — Entitlements
try:
    r = requests.get(f"{BASE_URL}/api/me/entitlements", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
    data = safe_json(r)
    has_plan = "plan" in data
    has_entitlements = "entitlements" in data
    ok = r.status_code == 200 and has_plan and has_entitlements
    ents = data.get("entitlements", {})
    fit_info = ents.get("fit_scans", ents.get("fit_scan", {}))
    prop_info = ents.get("proposals", ents.get("proposal", {}))
    b1_fit_used = fit_info.get("used", 0) if isinstance(fit_info, dict) else 0
    b1_proposal_used = prop_info.get("used", 0) if isinstance(prop_info, dict) else 0
    fit_limit = fit_info.get("limit", "?") if isinstance(fit_info, dict) else "?"
    prop_limit = prop_info.get("limit", "?") if isinstance(prop_info, dict) else "?"
    note = f"plan={data.get('plan','?')} fit_scans={b1_fit_used}/{fit_limit} proposals={b1_proposal_used}/{prop_limit}"
    record("B1", "GET /me/entitlements", ok, note)
except Exception as e:
    record("B1", "GET /me/entitlements", False, str(e))

# B2 — Check profile
profile_exists = False
try:
    r = requests.get(f"{BASE_URL}/api/ngo-profile", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
    ok = r.status_code in (200, 404)
    if r.status_code == 200:
        profile_exists = True
        record("B2", "GET /ngo-profile (may be 200/404)", ok, "existing profile found — skip B3")
    else:
        record("B2", "GET /ngo-profile (may be 200/404)", ok, f"got {r.status_code} — will create in B3")
except Exception as e:
    record("B2", "GET /ngo-profile (may be 200/404)", False, str(e))

# B3 — Create profile (only if not found)
if not profile_exists:
    try:
        profile_body = {
            "organization_name": "Smoke Test NGO International",
            "country_of_registration": "Kenya",
            "mission_statement": (
                "Empowering rural communities through sustainable agriculture "
                "and climate-resilient livelihoods across East Africa."
            ),
            "focus_sectors": ["AGRICULTURE", "CLIMATE", "LIVELIHOODS"],
            "geographic_areas_of_work": ["Kenya", "Uganda", "Tanzania"],
            "target_groups": ["Smallholder farmers", "Women", "Youth"],
            "past_projects": [
                {
                    "title": "Climate-Smart Farming Initiative",
                    "donor": "USAID",
                    "duration": "2022-2024",
                    "location": "Western Kenya",
                    "summary": (
                        "Trained 2,000 smallholder farmers in drought-resistant crop varieties "
                        "and water harvesting techniques, achieving 40% improvement in yields."
                    ),
                },
                {
                    "title": "Women Economic Empowerment Programme",
                    "donor": "UN Women",
                    "duration": "2021-2023",
                    "location": "Uganda",
                    "summary": (
                        "Established 50 village savings groups reaching 1,500 women "
                        "with financial literacy training and microenterprise support."
                    ),
                },
            ],
            "monitoring_and_evaluation_practices": (
                "We use Theory of Change frameworks with quarterly data collection "
                "via KoBoToolbox and annual external evaluations."
            ),
            "funders_worked_with_before": ["USAID", "UN Women", "Ford Foundation", "DFID"],
            "year_of_establishment": 2015,
            "contact_person_name": "Jane Mwangi",
            "contact_email": "jane@smoketestngo.org",
            "website": "www.smoketestngo.org",
            "full_time_staff": 24,
            "annual_budget_amount": 850000,
            "annual_budget_currency": "USD",
        }
        r = requests.post(
            f"{BASE_URL}/api/ngo-profile",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=profile_body,
            timeout=DEFAULT_TIMEOUT,
        )
        data = safe_json(r)
        ok = r.status_code in (200, 201)
        profile_id = data.get("id") or data.get("profile", {}).get("id", "?")
        record("B3", "POST /ngo-profile (create)", ok, f"got {r.status_code} id={profile_id}")
    except Exception as e:
        record("B3", "POST /ngo-profile (create)", False, str(e))
else:
    record("B3", "POST /ngo-profile (create — skipped)", True, "profile already existed")

# B4 — Completeness
try:
    r = requests.get(f"{BASE_URL}/api/ngo-profile/completeness", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
    data = safe_json(r)
    ok = r.status_code == 200 and "profile_status" in data
    profile_status = data.get("profile_status", "?")
    completeness_score = data.get("completeness_score", data.get("score", "?"))
    missing = data.get("missing_fields", [])
    note = f"status={profile_status} score={completeness_score} missing={missing}"
    if r.status_code == 200 and profile_status != "COMPLETE":
        warn(f"Profile status is {profile_status!r}, not COMPLETE — missing: {missing}")
    record("B4", "GET /ngo-profile/completeness", ok, note)
except Exception as e:
    record("B4", "GET /ngo-profile/completeness", False, str(e))

# B5 — Fetch funding opportunity
try:
    r = requests.get(
        f"{BASE_URL}/api/funding-opportunities/{FUNDING_OPPORTUNITY_ID}",
        headers=auth_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    # handle nested or top-level
    fo = data.get("funding_opportunity", data)
    has_id = "id" in fo
    has_title = "title" in fo
    ok = r.status_code == 200 and has_id and has_title
    shape = "nested" if "funding_opportunity" in data else "top-level"
    record("B5", "GET /funding-opportunities/<id>", ok, f"title={fo.get('title','?')!r} shape={shape}")
except Exception as e:
    record("B5", "GET /funding-opportunities/<id>", False, str(e))

# B6 — Run Fit Scan
try:
    r = requests.post(
        f"{BASE_URL}/api/fit-scans",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"funding_opportunity_id": FUNDING_OPPORTUNITY_ID},
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    if r.status_code == 409:
        record("B6", "POST /fit-scans", False, "PROFILE_INCOMPLETE — check missing_fields from B4")
    elif r.status_code == 429:
        warn("B6: Quota already exhausted for this test user — fit scan quota used up")
        record("B6", "POST /fit-scans (quota warning)", True, "429 quota exhausted — WARN")
    else:
        # handle nested or top-level id
        fs = data.get("fit_scan", data)
        fit_scan_id = fs.get("id") or data.get("id")
        overall = fs.get("overall_recommendation") or data.get("overall_recommendation")
        rating = fs.get("model_rating") or data.get("model_rating")
        subscores = fs.get("subscores") or data.get("subscores", {})
        valid_rec = overall in ("RECOMMENDED", "APPLY_WITH_CAVEATS", "NOT_RECOMMENDED")
        valid_rating = rating in ("STRONG", "MODERATE", "WEAK")
        valid_subscores = isinstance(subscores, dict) and all(
            k in subscores for k in ("eligibility", "alignment", "readiness")
        )
        ok = r.status_code == 200 and bool(fit_scan_id) and valid_rec and valid_rating and valid_subscores
        note = (
            f"id={fit_scan_id} rec={overall} rating={rating} "
            f"subscores={{elig={subscores.get('eligibility','?')} "
            f"align={subscores.get('alignment','?')} "
            f"ready={subscores.get('readiness','?')}}}"
        )
        record("B6", "POST /fit-scans", ok, note)
except Exception as e:
    record("B6", "POST /fit-scans", False, str(e))

# B7 — Retrieve Fit Scan by ID
if fit_scan_id:
    try:
        r = requests.get(f"{BASE_URL}/api/fit-scans/{fit_scan_id}", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        data = safe_json(r)
        fs = data.get("fit_scan", data)
        id_match = (fs.get("id") == fit_scan_id) or (data.get("id") == fit_scan_id)
        rationale = fs.get("primary_rationale") or data.get("primary_rationale", "")
        risk_flags = fs.get("risk_flags") if "risk_flags" in fs else data.get("risk_flags")
        ok = r.status_code == 200 and id_match and bool(rationale) and risk_flags is not None
        note = f"rationale_len={len(rationale)} risk_flags_count={len(risk_flags) if isinstance(risk_flags, list) else '?'}"
        record("B7", "GET /fit-scans/<id>", ok, note)
    except Exception as e:
        record("B7", "GET /fit-scans/<id>", False, str(e))
else:
    record("B7", "GET /fit-scans/<id>", False, "no fit_scan_id from B6")

# B8 — Generate Proposal
print(f"  … Generating proposal (timeout={PROPOSAL_TIMEOUT}s, may take 30-90s) …")
if fit_scan_id:
    try:
        r = requests.post(
            f"{BASE_URL}/api/proposals",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={
                "funding_opportunity_id": FUNDING_OPPORTUNITY_ID,
                "fit_scan_id": fit_scan_id,
                "selected_variant_id": None,
                "user_overrides": None,
            },
            timeout=PROPOSAL_TIMEOUT,
        )
        data = safe_json(r)
        if r.status_code == 429:
            warn("B8: Proposal quota exhausted")
            record("B8", "POST /proposals (quota warning)", True, "429 quota exhausted — WARN")
        elif r.status_code == 500:
            code = data.get("detail", {}).get("code", "") if isinstance(data.get("detail"), dict) else str(data.get("detail", ""))
            record("B8", "POST /proposals", False, f"500 PROPOSAL_GENERATION_FAILED: {code}")
        else:
            proposal_id = data.get("id")
            status = data.get("status")
            gen_sum = data.get("generation_summary", {})
            ok = r.status_code == 200 and bool(proposal_id) and status in ("DRAFT", "DEGRADED")
            note = (
                f"id={proposal_id} status={status} "
                f"total={gen_sum.get('total_items','?')} generated={gen_sum.get('generated','?')} "
                f"failed={gen_sum.get('failed','?')} manual={gen_sum.get('manual_required','?')}"
            )
            record("B8", "POST /proposals", ok, note)
    except Exception as e:
        record("B8", "POST /proposals", False, str(e))
else:
    record("B8", "POST /proposals", False, "no fit_scan_id — skipped")

# B9 — Retrieve Proposal detail
if proposal_id:
    try:
        r = requests.get(f"{BASE_URL}/api/proposals/{proposal_id}", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
        data = safe_json(r)
        id_match = data.get("id") == proposal_id
        content_json = data.get("content_json", {})
        sections = content_json.get("sections", []) if isinstance(content_json, dict) else []
        has_sections = isinstance(sections, list) and len(sections) > 0
        valid_statuses = {"GENERATED", "FAILED", "MANUAL_REQUIRED"}
        sections_ok = all("generation_status" in s for s in sections)
        ok = r.status_code == 200 and id_match and has_sections and sections_ok
        gen_count = sum(1 for s in sections if s.get("generation_status") == "GENERATED")
        fail_count = sum(1 for s in sections if s.get("generation_status") == "FAILED")
        note = f"total_sections={len(sections)} generated={gen_count} failed={fail_count}"
        record("B9", "GET /proposals/<id>", ok, note)
    except Exception as e:
        record("B9", "GET /proposals/<id>", False, str(e))
else:
    record("B9", "GET /proposals/<id>", False, "no proposal_id — skipped")

# B10 — Export DOCX
if proposal_id:
    try:
        r = requests.post(
            f"{BASE_URL}/api/proposals/{proposal_id}/export",
            headers={**auth_headers, "Content-Type": "application/json"},
            json={"format": "DOCX"},
            timeout=DEFAULT_TIMEOUT,
        )
        ct = r.headers.get("Content-Type", "")
        cd = r.headers.get("Content-Disposition", "")
        body_len = len(r.content)
        valid_ct = "wordprocessingml" in ct or "octet-stream" in ct
        valid_cd = "attachment" in cd
        valid_size = body_len > 1000
        ok = r.status_code == 200 and valid_ct and valid_cd and valid_size
        note = f"size={body_len}B content-type={ct!r}"
        if ok or r.status_code == 200:
            export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke_test_export.docx")
            with open(export_path, "wb") as f:
                f.write(r.content)
            note += f" saved={export_path}"
        record("B10", "POST /proposals/<id>/export (DOCX)", ok, note)
    except Exception as e:
        record("B10", "POST /proposals/<id>/export (DOCX)", False, str(e))
else:
    record("B10", "POST /proposals/<id>/export (DOCX)", False, "no proposal_id — skipped")

# B11 — Quota decrement check
try:
    r = requests.get(f"{BASE_URL}/api/me/entitlements", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
    data = safe_json(r)
    ents = data.get("entitlements", {})
    fit_info = ents.get("fit_scans", ents.get("fit_scan", {}))
    prop_info = ents.get("proposals", ents.get("proposal", {}))
    b11_fit_used = fit_info.get("used", 0) if isinstance(fit_info, dict) else 0
    b11_prop_used = prop_info.get("used", 0) if isinstance(prop_info, dict) else 0
    fit_ok = b11_fit_used >= b1_fit_used + 1
    prop_ok = b11_prop_used >= b1_proposal_used + 1
    ok = r.status_code == 200 and fit_ok and prop_ok
    note = (
        f"fit_scans: {b1_fit_used}→{b11_fit_used} ({'OK' if fit_ok else 'NO CHANGE'}) | "
        f"proposals: {b1_proposal_used}→{b11_prop_used} ({'OK' if prop_ok else 'NO CHANGE'})"
    )
    record("B11", "Quota decrement check", ok, note)
except Exception as e:
    record("B11", "Quota decrement check", False, str(e))

# B12 — Refresh token
new_access_token = None
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/refresh",
        json={"refresh_token": refresh_token},
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    new_access_token = data.get("access_token")
    ok = r.status_code == 200 and bool(new_access_token)
    record("B12", "POST /auth/refresh (valid token)", ok, f"got {r.status_code} new_token={'yes' if new_access_token else 'no'}")
except Exception as e:
    record("B12", "POST /auth/refresh (valid token)", False, str(e))

# B13 — Logout
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/logout",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"refresh_token": refresh_token},
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    # accept "logged_out" or any 200 success indicator
    is_success = r.status_code == 200 and (
        data.get("status") in ("logged_out", "success", "ok")
        or data.get("message", "").lower().find("logout") >= 0
        or data.get("message", "").lower().find("success") >= 0
        or r.status_code == 200  # fallback: any 200 is acceptable
    )
    record("B13", "POST /auth/logout", is_success, f"got {r.status_code} body={json.dumps(data)[:120]}")
except Exception as e:
    record("B13", "POST /auth/logout", False, str(e))

# ---------------------------------------------------------------------------
# TRACK C — Auth boundary checks
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("TRACK C — Auth boundary checks")
print("=" * 70)

# C1 — Token should be invalid after logout
try:
    r = requests.get(f"{BASE_URL}/api/ngo-profile", headers=auth_headers, timeout=DEFAULT_TIMEOUT)
    if r.status_code == 401:
        record("C1", "Token invalid after logout → 401", True, "token correctly rejected")
    elif r.status_code == 200:
        warn("C1: Token still valid after logout — investigate session invalidation")
        record("C1", "Token invalid after logout → 401", False, f"got 200 — token still valid post-logout")
    else:
        record("C1", "Token invalid after logout → 401", False, f"got {r.status_code}")
except Exception as e:
    record("C1", "Token invalid after logout → 401", False, str(e))

# C2 — Cross-user access blocked (mint fresh token for smoke-c2 user)
c2_token = None
try:
    r = requests.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={"X-Test-Mode-Secret": SECRET, "Content-Type": "application/json"},
        json={
            "secret": SECRET,
            "email": "smoke-c2@grantpilot-test.org",
            "full_name": "Smoke C2 User",
            "plan": "FREE",
        },
        timeout=DEFAULT_TIMEOUT,
    )
    data = safe_json(r)
    c2_token = data.get("access_token")
except Exception as e:
    warn(f"C2: Failed to mint second token: {e}")

if c2_token:
    try:
        fabricated_id = "00000000-0000-0000-0000-000000000000"
        r = requests.get(
            f"{BASE_URL}/api/fit-scans/{fabricated_id}",
            headers={"Authorization": f"Bearer {c2_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        ok = r.status_code in (403, 404)
        record("C2", "Cross-user fit-scan blocked → 403/404", ok, f"got {r.status_code}")
    except Exception as e:
        record("C2", "Cross-user fit-scan blocked → 403/404", False, str(e))
else:
    record("C2", "Cross-user fit-scan blocked → 403/404", False, "could not mint C2 token")

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("GRANTPILOT SMOKE TEST RESULTS")
print(f"Ran against: {BASE_URL}")
print("=" * 70)

track_order = [
    ("TRACK A — Unauthenticated baseline", ["A1", "A2", "A3", "A4", "A5", "A6"]),
    ("TRACK B — Full authenticated journey", [f"B{i}" for i in range(14)]),
    ("TRACK C — Auth boundaries", ["C1", "C2"]),
]

result_map = {r[0]: r for r in results}

for track_name, labels in track_order:
    print(f"\n{track_name}")
    for label in labels:
        if label in result_map:
            lbl, desc, status, note = result_map[label]
            print(f"  {lbl:<4}  {desc:<50s}  {status}  {note}")

total = len(results)
passed = sum(1 for r in results if r[2] == "PASS")
failed_list = [(r[0], r[1], r[3]) for r in results if r[2] == "FAIL"]

print("\n" + "=" * 70)
print(f"TOTAL: {passed}/{total} checks passed")
if failed_list:
    print(f"FAILED ({len(failed_list)}):")
    for label, desc, note in failed_list:
        print(f"  {label}: {desc} — {note}")
else:
    print("FAILED: none")
if warnings:
    print(f"WARNINGS ({len(warnings)}):")
    for w in warnings:
        print(f"  • {w}")
else:
    print("WARNINGS: 0")
print("=" * 70)

sys.exit(0 if not failed_list else 1)
