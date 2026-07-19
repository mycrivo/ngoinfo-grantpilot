"""Poll until worker top deploy SUCCESS (flag redeploy)."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVICE = "exemplary-encouragement"


def list_deps() -> list[dict]:
    raw = subprocess.check_output(
        ["cmd", "/c", f"railway deployment list --service {SERVICE} --json"],
        cwd=str(REPO),
        text=True,
    )
    return json.loads(raw)


def main() -> None:
    deadline = time.time() + 900
    while time.time() < deadline:
        top = list_deps()[0]
        st = top.get("status")
        ch = (top.get("meta") or {}).get("commitHash", "")
        print(f"status={st} commit={ch[:12]}", flush=True)
        if st == "SUCCESS":
            # confirm flag still true
            raw = subprocess.check_output(
                [
                    "cmd",
                    "/c",
                    f"railway variables --json --service {SERVICE}",
                ],
                cwd=str(REPO),
                text=True,
            )
            d = json.loads(raw)
            print("FAULT=", d.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"), flush=True)
            if str(d.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE")).lower() not in (
                "true",
                "1",
                "yes",
            ):
                raise SystemExit("FLAG_LOST_AFTER_REDEPLOY")
            print("DEPLOY_OK", flush=True)
            return
        if st in ("FAILED", "CRASHED"):
            raise SystemExit(f"DEPLOY_FAILED {st}")
        time.sleep(15)
    raise SystemExit("TIMEOUT")


if __name__ == "__main__":
    main()
