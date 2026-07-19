"""Inspect Railway services / deploy SHA for Phase 2 preflight."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = "67f94ca"


def run(args: list[str]) -> str:
    return subprocess.check_output(
        ["cmd", "/c", " ".join(args)],
        cwd=str(REPO),
        text=True,
        stderr=subprocess.STDOUT,
    )


def vars_for(service: str) -> dict:
    raw = subprocess.check_output(
        ["cmd", "/c", f"railway variables --json --service {service}"],
        cwd=str(REPO),
        text=True,
    )
    return json.loads(raw)


def main() -> None:
    print("=== railway status ===")
    print(run(["railway", "status"]))
    for svc in ("exemplary-encouragement", "ngoinfo-grantpilot", "Postgres"):
        print(f"\n=== service {svc} ===")
        try:
            d = vars_for(svc)
        except Exception as e:
            print("ERR", e)
            continue
        commit_keys = [
            k
            for k in d
            if "COMMIT" in k.upper() or "GIT" in k.upper() or "SHA" in k.upper()
        ]
        print("commit-ish keys:", {k: d.get(k) for k in commit_keys})
        print("ME_MODULE_ENABLED=", d.get("ME_MODULE_ENABLED"))
        print(
            "ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE=",
            d.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"),
        )
        print("has_ANTHROPIC=", "ANTHROPIC_API_KEY" in d)
        # Heuristic: worker has no PORT public web typically; both may have ME
        print(
            "sample keys:",
            [k for k in sorted(d) if k.startswith("ME_") or k in ("PORT", "WEB_CONCURRENCY")],
        )


if __name__ == "__main__":
    main()
