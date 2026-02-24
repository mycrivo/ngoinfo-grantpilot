import json
import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

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


def _extract_token_payload(payload: Dict[str, Any]) -> Optional[str]:
    token = payload.get("access_token")
    return token if isinstance(token, str) and token else None


def main() -> None:
    base_url = os.getenv("SMOKE_BASE_URL")
    if not base_url:
        print("Missing SMOKE_BASE_URL")
        sys.exit(1)

    base_url = base_url.rstrip("/")
    headers_base = {"x-request-id": str(uuid.uuid4())}

    with httpx.Client() as client:
        # Track A: unauthenticated smoke checks (release-blocking).
        resp, latency = _request(client, "GET", f"{base_url}/health", headers=headers_base)
        _report("health", "GET", "/health", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("health", resp, latency)

        # Protected endpoints must reject missing bearer auth with standard envelope.
        resp, latency = _request(client, "GET", f"{base_url}/api/ngo-profile", headers=headers_base)
        _report("ngo_profile_unauth", "GET", "/api/ngo-profile", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("ngo_profile_unauth", resp, latency)
        _assert_error_schema("ngo_profile_unauth", resp)

        resp, latency = _request(
            client,
            "GET",
            f"{base_url}/api/ngo-profile/completeness",
            headers={"x-request-id": str(uuid.uuid4())},
        )
        _report(
            "ngo_profile_completeness_unauth",
            "GET",
            "/api/ngo-profile/completeness",
            resp.status_code,
            latency,
        )
        if resp.status_code != 401:
            _fail("ngo_profile_completeness_unauth", resp, latency)
        _assert_error_schema("ngo_profile_completeness_unauth", resp)

        resp, latency = _request(
            client, "GET", f"{base_url}/api/fit-scans", headers={"x-request-id": str(uuid.uuid4())}
        )
        _report("fit_scans_list_unauth", "GET", "/api/fit-scans", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("fit_scans_list_unauth", resp, latency)
        _assert_error_schema("fit_scans_list_unauth", resp)

        resp, latency = _request(
            client, "GET", f"{base_url}/api/proposals", headers={"x-request-id": str(uuid.uuid4())}
        )
        _report("proposals_list_unauth", "GET", "/api/proposals", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("proposals_list_unauth", resp, latency)
        _assert_error_schema("proposals_list_unauth", resp)

        # OpenAPI
        resp, latency = _request(client, "GET", f"{base_url}/openapi.json", headers=headers_base)
        _report("openapi", "GET", "/openapi.json", resp.status_code, latency)
        if resp.status_code != 200:
            _fail("openapi", resp, latency)

        # OAuth exchange invalid code should be rejected
        resp, latency = _request(
            client,
            "POST",
            f"{base_url}/api/auth/exchange",
            headers={"x-request-id": str(uuid.uuid4())},
            json_body={"code": "invalid"},
        )
        _report("oauth_exchange_invalid", "POST", "/api/auth/exchange", resp.status_code, latency)
        if resp.status_code != 401:
            _fail("oauth_exchange_invalid", resp, latency)
        _assert_error_schema("oauth_exchange_invalid", resp)

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

        # Track B: authenticated checks via test-mode mint (optional).
        # Canonical contract describes secret in request JSON, but backend currently
        # requires x-test-mode-secret header. Keep header for compatibility.
        test_mode_secret = os.getenv("TEST_MODE_SECRET") or os.getenv("SMOKE_TEST_MODE_SECRET")
        if test_mode_secret:
            smoke_email = os.getenv("SMOKE_TEST_EMAIL", "smoke-test@grantpilot.local")
            smoke_name = os.getenv("SMOKE_TEST_FULL_NAME", "Smoke Test")
            smoke_plan = os.getenv("SMOKE_TEST_PLAN", "FREE")
            mint_headers = {
                "x-request-id": str(uuid.uuid4()),
                "x-test-mode-secret": test_mode_secret,
            }
            resp, latency = _request(
                client,
                "POST",
                f"{base_url}/api/auth/test-mode/mint",
                headers=mint_headers,
                json_body={
                    "secret": test_mode_secret,
                    "email": smoke_email,
                    "full_name": smoke_name,
                    "plan": smoke_plan,
                },
            )
            _report("test_mode_mint", "POST", "/api/auth/test-mode/mint", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("test_mode_mint", resp, latency)
            token = _extract_token_payload(_safe_json(resp))
            if not token:
                _fail("test_mode_mint", resp, latency)
            protected_headers = {
                "x-request-id": str(uuid.uuid4()),
                "Authorization": f"Bearer {token}",
            }
            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/me/entitlements",
                headers=protected_headers,
            )
            _report(
                "entitlements_with_token",
                "GET",
                "/api/me/entitlements",
                resp.status_code,
                latency,
            )
            if resp.status_code != 200:
                _fail("entitlements_with_token", resp, latency)

            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/fit-scans",
                headers={"x-request-id": str(uuid.uuid4()), "Authorization": f"Bearer {token}"},
            )
            _report("fit_scans_list_with_token", "GET", "/api/fit-scans", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("fit_scans_list_with_token", resp, latency)
            payload = _safe_json(resp)
            fit_scan_items = payload.get("fit_scans")
            if not isinstance(fit_scan_items, list):
                _fail("fit_scans_list_with_token", resp, latency)
            if fit_scan_items and isinstance(fit_scan_items[0], dict):
                if "opportunity_title" not in fit_scan_items[0]:
                    _fail("fit_scans_list_with_token", resp, latency)

            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/proposals",
                headers={"x-request-id": str(uuid.uuid4()), "Authorization": f"Bearer {token}"},
            )
            _report("proposals_list_with_token", "GET", "/api/proposals", resp.status_code, latency)
            if resp.status_code != 200:
                _fail("proposals_list_with_token", resp, latency)
            payload = _safe_json(resp)
            proposal_items = payload.get("proposals")
            if not isinstance(proposal_items, list):
                _fail("proposals_list_with_token", resp, latency)
            if proposal_items and isinstance(proposal_items[0], dict):
                if "opportunity_title" not in proposal_items[0]:
                    _fail("proposals_list_with_token", resp, latency)
                if proposal_items[0].get("status") not in ("DRAFT", "DEGRADED"):
                    _fail("proposals_list_with_token", resp, latency)

            known_opp_id = os.getenv("SMOKE_FUNDING_OPPORTUNITY_ID")
            if not known_opp_id:
                proposals = payload.get("proposals", [])
                if proposals and isinstance(proposals[0], dict):
                    maybe_id = proposals[0].get("funding_opportunity_id")
                    if isinstance(maybe_id, str) and maybe_id:
                        known_opp_id = maybe_id
            if not known_opp_id:
                known_opp_id = "00000000-0000-0000-0000-000000000000"

            resp, latency = _request(
                client,
                "GET",
                f"{base_url}/api/funding-opportunities/{known_opp_id}",
                headers={"x-request-id": str(uuid.uuid4()), "Authorization": f"Bearer {token}"},
            )
            _report(
                "funding_opportunity_detail_with_token",
                "GET",
                "/api/funding-opportunities/{id}",
                resp.status_code,
                latency,
            )
            if resp.status_code not in (200, 404):
                _fail("funding_opportunity_detail_with_token", resp, latency)
            if resp.status_code == 404:
                _assert_error_schema("funding_opportunity_detail_with_token", resp)
        else:
            print(json.dumps({"track_b": "skipped", "reason": "TEST_MODE_SECRET missing"}))

    print(json.dumps({"result": "success"}))


if __name__ == "__main__":
    main()
