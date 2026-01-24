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


def main() -> None:
    base_url = os.getenv("SMOKE_BASE_URL")
    test_secret = os.getenv("TEST_MODE_SECRET")
    if not base_url or not test_secret:
        print("Missing SMOKE_BASE_URL or TEST_MODE_SECRET")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    headers_base = {"x-request-id": str(uuid.uuid4())}

    with httpx.Client() as client:
        # Health check
        resp, latency = _request(client, "GET", f"{base_url}/health", headers=headers_base)
        _report("health", "GET", "/health", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("health", resp, latency)

        # Negative: protected endpoint without auth
        resp, latency = _request(client, "GET", f"{base_url}/ngo-profile", headers=headers_base)
        _report("ngo_profile_unauth", "GET", "/ngo-profile", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("ngo_profile_unauth", resp, latency)
        _assert_error_schema("ngo_profile_unauth", resp)

        # Mint test tokens
        headers = {
            "x-request-id": str(uuid.uuid4()),
            "x-test-mode-secret": test_secret,
        }
        resp, latency = _request(
            client, "POST", f"{base_url}/api/auth/test-mode/mint", headers=headers
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
        resp, latency = _request(client, "GET", f"{base_url}/ngo-profile", headers=auth_headers)
        _report("ngo_profile_get", "GET", "/ngo-profile", resp.status_code, latency)
        if resp.status_code == 404:
            payload = {
                "organization_name": "Smoke Test Org",
                "country_of_registration": "Kenya",
                "mission_statement": "Test mission statement",
                "focus_sectors": ["Health"],
                "geographic_areas_of_work": ["Nairobi"],
                "target_groups": ["Youth"],
                "past_projects": [{"title": "Pilot Project"}],
            }
            resp, latency = _request(
                client, "POST", f"{base_url}/ngo-profile", headers=auth_headers, json_body=payload
            )
            _report("ngo_profile_create", "POST", "/ngo-profile", resp.status_code, latency)
            if resp.status_code != 200 and resp.status_code != 201:
                _fail("ngo_profile_create", resp, latency)
        elif resp.status_code != 200:
            _fail("ngo_profile_get", resp, latency)

        # Update profile
        payload_update = {
            "organization_name": "Smoke Test Org Updated",
            "country_of_registration": "Kenya",
            "mission_statement": "Updated mission statement",
            "focus_sectors": ["Health", "Education"],
            "geographic_areas_of_work": ["Nairobi", "Kisumu"],
            "target_groups": ["Youth"],
            "past_projects": [{"title": "Pilot Project"}],
        }
        resp, latency = _request(
            client, "PUT", f"{base_url}/ngo-profile", headers=auth_headers, json_body=payload_update
        )
        _report("ngo_profile_update", "PUT", "/ngo-profile", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("ngo_profile_update", resp, latency)

        # Completeness
        resp, latency = _request(
            client, "GET", f"{base_url}/ngo-profile/completeness", headers=auth_headers
        )
        _report("ngo_profile_completeness", "GET", "/ngo-profile/completeness", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("ngo_profile_completeness", resp, latency)

        # Negative: invalid payload -> 422
        resp, latency = _request(
            client, "PUT", f"{base_url}/ngo-profile", headers=auth_headers, json_body={}
        )
        _report("ngo_profile_invalid", "PUT", "/ngo-profile", resp.status_code, latency)
        if resp.status_code != 422:
            _fail("ngo_profile_invalid", resp, latency)

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

        # Protected endpoint now returns 401 (no auth header)
        resp, latency = _request(client, "GET", f"{base_url}/ngo-profile", headers=headers_base)
        _report("ngo_profile_post_logout", "GET", "/ngo-profile", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("ngo_profile_post_logout", resp, latency)

    print(json.dumps({"result": "success"}))


if __name__ == "__main__":
    main()
