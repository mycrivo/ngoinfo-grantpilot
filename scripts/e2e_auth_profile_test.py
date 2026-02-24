import json
import os
import sys
import time
import uuid
from typing import Any, Dict

import httpx


def _request(
    client: httpx.Client,
    method: str,
    url: str,
    headers: Dict[str, str] | None = None,
    json_body: Any | None = None,
) -> tuple[httpx.Response, float]:
    start = time.time()
    response = client.request(method, url, headers=headers, json=json_body, timeout=20.0)
    latency_ms = round((time.time() - start) * 1000, 2)
    return response, latency_ms


def _report(step: str, method: str, url: str, status: int, latency_ms: float) -> None:
    print(
        json.dumps(
            {
                "step": step,
                "method": method,
                "url": url,
                "status": status,
                "latency_ms": latency_ms,
            }
        )
    )


def _fail(step: str, response: httpx.Response, latency_ms: float) -> None:
    try:
        body = response.json()
    except Exception:
        body = response.text[:500]
    request_id = response.headers.get("x-request-id") or body.get("request_id") if isinstance(body, dict) else None
    print(
        json.dumps(
            {
                "step": step,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "response_excerpt": body,
                "request_id": request_id,
                "headers": dict(response.headers),
            }
        )
    )
    sys.exit(1)


def _assert_error_schema(step: str, response: httpx.Response) -> None:
    try:
        payload = response.json()
    except Exception:
        _fail(step, response, 0)
    if not isinstance(payload, dict):
        _fail(step, response, 0)
    if "error_code" not in payload or "message" not in payload:
        _fail(step, response, 0)


def _safe_json(response: httpx.Response) -> Dict[str, Any]:
    try:
        payload = response.json()
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> None:
    base_url = os.getenv("SMOKE_BASE_URL")
    test_secret = os.getenv("TEST_MODE_SECRET")
    if not base_url or not test_secret:
        print("Missing SMOKE_BASE_URL or TEST_MODE_SECRET")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    headers_base = {"x-request-id": str(uuid.uuid4())}

    with httpx.Client() as client:
        # Mint test tokens
        smoke_email = os.getenv("SMOKE_TEST_EMAIL")
        if not smoke_email:
            smoke_email = f"smoke-e2e-{int(time.time())}@grantpilot.local"
        smoke_name = os.getenv("SMOKE_TEST_FULL_NAME", "Smoke E2E Test")
        smoke_plan = os.getenv("SMOKE_TEST_PLAN", "IMPACT")
        headers = {
            "x-request-id": str(uuid.uuid4()),
            "x-test-mode-secret": test_secret,
        }
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/test-mode/mint",
            headers=headers,
            json_body={
                "secret": test_secret,
                "email": smoke_email,
                "full_name": smoke_name,
                "plan": smoke_plan,
            },
        )
        _report("test_mode_mint", "POST", "/api/auth/test-mode/mint", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("test_mode_mint", resp, latency)
        token_payload = resp.json()
        access_token = token_payload["access_token"]
        refresh_token = token_payload["refresh_token"]

        auth_headers = {
            "authorization": f"Bearer {access_token}",
            "x-request-id": str(uuid.uuid4()),
        }

        # Get profile or create if missing
        resp, latency = _request(client, "GET", f"{base_url}/api/ngo-profile", headers=auth_headers)
        _report("ngo_profile_get", "GET", "/api/ngo-profile", resp.status_code, latency)
        if resp.status_code == 404:
            payload = {
                "organization_name": "Smoke Test Org",
                "country_of_registration": "Kenya",
                "mission_statement": "Test mission statement",
                "focus_sectors": ["HEALTH"],
                "geographic_areas_of_work": ["Nairobi"],
                "target_groups": ["Youth"],
                "past_projects": [{"project_title": "Pilot Project"}],
            }
            resp, latency = _request(
                client, "POST", f"{base_url}/api/ngo-profile", headers=auth_headers, json_body=payload
            )
            _report("ngo_profile_create", "POST", "/api/ngo-profile", resp.status_code, latency)
            if resp.status_code != 200 and resp.status_code != 201:
                _fail("ngo_profile_create", resp, latency)
        elif resp.status_code != 200:
            _fail("ngo_profile_get", resp, latency)

        # Update profile
        payload_update = {
            "organization_name": "Smoke Test Org Updated",
            "country_of_registration": "Kenya",
            "mission_statement": "Updated mission statement",
            "focus_sectors": ["HEALTH", "EDUCATION"],
            "geographic_areas_of_work": ["Nairobi", "Kisumu"],
            "target_groups": ["Youth"],
            "past_projects": [{"project_title": "Pilot Project"}],
        }
        resp, latency = _request(
            client, "PUT", f"{base_url}/api/ngo-profile", headers=auth_headers, json_body=payload_update
        )
        _report("ngo_profile_update", "PUT", "/api/ngo-profile", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("ngo_profile_update", resp, latency)

        # Completeness
        resp, latency = _request(
            client, "GET", f"{base_url}/api/ngo-profile/completeness", headers=auth_headers
        )
        _report("ngo_profile_completeness", "GET", "/api/ngo-profile/completeness", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("ngo_profile_completeness", resp, latency)

        # F-1 missing journey checks: funding opportunity -> fit scan -> proposal lifecycle.
        resp, latency = _request(client, "GET", f"{base_url}/api/fit-scans?limit=5", headers=auth_headers)
        _report("fit_scans_list", "GET", "/api/fit-scans?limit=5", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("fit_scans_list", resp, latency)
        fit_scans_payload = _safe_json(resp)
        fit_scans = fit_scans_payload.get("fit_scans")
        if not isinstance(fit_scans, list):
            _fail("fit_scans_list", resp, latency)

        resp, latency = _request(client, "GET", f"{base_url}/api/proposals?limit=5", headers=auth_headers)
        _report("proposals_list", "GET", "/api/proposals?limit=5", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("proposals_list", resp, latency)
        proposals_payload = _safe_json(resp)
        proposals = proposals_payload.get("proposals")
        if not isinstance(proposals, list):
            _fail("proposals_list", resp, latency)

        known_opp_id = os.getenv("SMOKE_FUNDING_OPPORTUNITY_ID")
        if not known_opp_id and proposals and isinstance(proposals[0], dict):
            maybe_opp = proposals[0].get("funding_opportunity_id")
            if isinstance(maybe_opp, str) and maybe_opp:
                known_opp_id = maybe_opp
        if not known_opp_id and fit_scans and isinstance(fit_scans[0], dict):
            maybe_opp = fit_scans[0].get("funding_opportunity_id")
            if isinstance(maybe_opp, str) and maybe_opp:
                known_opp_id = maybe_opp

        if known_opp_id:
            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/funding-opportunities/{known_opp_id}",
                headers=auth_headers,
            )
            _report(
                "funding_opportunity_detail",
                "GET",
                "/api/funding-opportunities/{id}",
                resp.status_code,
                latency,
            )
            if resp.status_code != 200:
                _fail("funding_opportunity_detail", resp, latency)

            resp, latency = _request(
                client,
                "POST",
                f"{base_url}/api/fit-scans",
                headers=auth_headers,
                json_body={"funding_opportunity_id": known_opp_id},
            )
            _report("fit_scan_create", "POST", "/api/fit-scans", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("fit_scan_create", resp, latency)
            fit_scan_payload = _safe_json(resp).get("fit_scan")
            if not isinstance(fit_scan_payload, dict):
                _fail("fit_scan_create", resp, latency)
            fit_scan_id = fit_scan_payload.get("id")
            if not isinstance(fit_scan_id, str) or not fit_scan_id:
                _fail("fit_scan_create", resp, latency)

            resp, latency = _request(
                client,
                "POST",
                f"{base_url}/api/proposals",
                headers=auth_headers,
                json_body={
                    "funding_opportunity_id": known_opp_id,
                    "fit_scan_id": fit_scan_id,
                },
            )
            _report("proposal_create", "POST", "/api/proposals", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("proposal_create", resp, latency)
            proposal_create_payload = _safe_json(resp)
            proposal_id = proposal_create_payload.get("id")
            if not isinstance(proposal_id, str) or not proposal_id:
                _fail("proposal_create", resp, latency)
            if proposal_create_payload.get("status") not in ("DRAFT", "DEGRADED"):
                _fail("proposal_create", resp, latency)

            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/proposals/{proposal_id}",
                headers=auth_headers,
            )
            _report("proposal_detail", "GET", "/api/proposals/{id}", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("proposal_detail", resp, latency)
            proposal_detail_payload = _safe_json(resp)
            content_json = proposal_detail_payload.get("content_json")
            if not isinstance(content_json, dict):
                _fail("proposal_detail", resp, latency)
            if not isinstance(content_json.get("sections"), list):
                _fail("proposal_detail", resp, latency)

            resp, latency = _request(
                client,
                "POST",
                f"{base_url}/api/proposals/{proposal_id}/regenerate",
                headers=auth_headers,
                json_body={"mode": "FULL"},
            )
            _report(
                "proposal_regenerate_full",
                "POST",
                "/api/proposals/{id}/regenerate",
                resp.status_code,
                latency,
            )
            if resp.status_code != 200:
                _fail("proposal_regenerate_full", resp, latency)

            resp, latency = _request(
                client,
                "POST",
                f"{base_url}/api/proposals/{proposal_id}/export",
                headers=auth_headers,
                json_body={"format": "DOCX"},
            )
            _report("proposal_export_docx", "POST", "/api/proposals/{id}/export", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("proposal_export_docx", resp, latency)
            content_type = resp.headers.get("content-type", "")
            content_disposition = resp.headers.get("content-disposition", "")
            if not content_type.startswith(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ):
                _fail("proposal_export_docx", resp, latency)
            if "attachment;" not in content_disposition.lower():
                _fail("proposal_export_docx", resp, latency)
        else:
            print(
                json.dumps(
                    {
                        "extended_journey_checks": "skipped",
                        "reason": "SMOKE_FUNDING_OPPORTUNITY_ID missing and no reusable funding_opportunity_id found",
                    }
                )
            )

        # Refresh
        refresh_headers = {"x-request-id": str(uuid.uuid4())}
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/refresh",
            headers=refresh_headers,
            json_body={"refresh_token": refresh_token},
        )
        _report("auth_refresh", "POST", "/api/auth/refresh", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("auth_refresh", resp, latency)
        refresh_payload = resp.json()
        rotated_refresh_token = refresh_payload.get("refresh_token")
        if isinstance(rotated_refresh_token, str) and rotated_refresh_token:
            refresh_token = rotated_refresh_token

        # Logout
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/logout",
            headers=refresh_headers,
            json_body={"refresh_token": refresh_token},
        )
        _report("auth_logout", "POST", "/api/auth/logout", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("auth_logout", resp, latency)

        # Protected endpoint now returns 401
        resp, latency = _request(client, "GET", f"{base_url}/api/ngo-profile", headers=headers_base)
        _report("ngo_profile_post_logout", "GET", "/api/ngo-profile", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("ngo_profile_post_logout", resp, latency)
        _assert_error_schema("ngo_profile_post_logout", resp)

    print(json.dumps({"result": "success"}))


if __name__ == "__main__":
    main()
