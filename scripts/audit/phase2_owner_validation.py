#!/usr/bin/env python3
"""Phase 2 owner validation helper — count Gate 2 gaps after P2-2a/P2-2b deploy.

Usage:
  python scripts/audit/phase2_owner_validation.py --report-id <uuid> [--api-base URL]
  python scripts/audit/phase2_owner_validation.py --report-id <uuid> --fcdo-complete

Owner sign-off: one real FCDO run + one real NLCF run; inspect missing_items count.
Owner must execute prod funder-row deletion on template 55f891ac before validation walk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FCDO_EXPECTED_GAPS_PATH = (
    ROOT / "tests" / "fixtures" / "gap" / "fcdo_complete_3347590c_expected_gaps.json"
)


def fetch_gap_check(api_base: str, report_id: str, token: str | None) -> dict:
    url = f"{api_base.rstrip('/')}/api/reports/{report_id}/gap-check"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _load_fcdo_expected_refs() -> set[str]:
    sidecar = json.loads(FCDO_EXPECTED_GAPS_PATH.read_text(encoding="utf-8"))
    return set(sidecar.get("required_item_refs") or [])


def summarize(payload: dict) -> dict:
    items = payload.get("missing_items") or []
    funder_refs = [
        item.get("required_item_ref") or item.get("label")
        for item in items
        if item.get("owner") == "funder"
        or item.get("requirement_type") == "funder_supplied"
    ]
    gap_refs = {
        item.get("required_item_ref")
        for item in items
        if item.get("required_item_ref")
    }
    return {
        "open_items_count": payload.get("open_items_count"),
        "readiness_basis": payload.get("readiness_basis"),
        "readiness_message": payload.get("readiness_message"),
        "missing_count": len(items),
        "required_item_refs": sorted(gap_refs),
        "funder_side_leaks": funder_refs,
        "missing_items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 owner gap-wall validation")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--api-base", default=os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.getenv("OWNER_API_TOKEN"))
    parser.add_argument(
        "--fcdo-complete",
        action="store_true",
        help="Assert gap refs match distilled 3347590c expected set (FCDO BridgeLight walk)",
    )
    args = parser.parse_args()

    try:
        payload = fetch_gap_check(args.api_base, args.report_id, args.token)
    except urllib.error.HTTPError as exc:
        print(json.dumps({"error": exc.read().decode("utf-8", errors="replace")}, indent=2))
        return 1
    except OSError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 1

    summary = summarize(payload)
    print(json.dumps(summary, indent=2))
    exit_code = 0
    if summary["funder_side_leaks"]:
        print("FAIL: funder-side items surfaced to NGO", file=sys.stderr)
        exit_code = 2
    if args.fcdo_complete:
        expected = _load_fcdo_expected_refs()
        actual = set(summary["required_item_refs"])
        if actual != expected:
            print(
                f"FAIL: FCDO complete gap set mismatch expected={sorted(expected)} actual={sorted(actual)}",
                file=sys.stderr,
            )
            exit_code = 2
        if summary["open_items_count"] != len(expected):
            print(
                f"FAIL: open_items_count {summary['open_items_count']} != expected {len(expected)}",
                file=sys.stderr,
            )
            exit_code = 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
