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
    if not base_url:
        print("Missing SMOKE_BASE_URL")
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

        # Magic link request (dummy email)
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/magic-link/request",
            headers={"x-request-id": str(uuid.uuid4())},
            json_body={"email": "smoke-test@grantpilot.local"},
        )
        _report("magic_link_request", "POST", "/api/auth/magic-link/request", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("magic_link_request", resp, latency)

        # OpenAPI
        resp, latency = _request(client, "GET", f"{base_url}/openapi.json", headers=headers_base)
        _report("openapi", "GET", "/openapi.json", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("openapi", resp, latency)

        # Negative: invalid refresh token
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/refresh",
            headers={"x-request-id": str(uuid.uuid4())},
            json_body={"refresh_token": "invalid"},
        )
        _report("refresh_invalid", "POST", "/api/auth/refresh", resp.status_code, latency)
        if resp.status_code not in (401, 422):
            _fail("refresh_invalid", resp, latency)
        _assert_error_schema("refresh_invalid", resp)

    print(json.dumps({"result": "success"}))


if __name__ == "__main__":
    main()
