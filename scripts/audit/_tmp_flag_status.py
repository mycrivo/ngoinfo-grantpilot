import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def rw_vars(service: str) -> dict:
    raw = subprocess.check_output(
        ["cmd", "/c", f"railway variables --json --service {service}"],
        cwd=str(REPO),
        text=True,
    )
    return json.loads(raw)


def rw_deps(service: str) -> list:
    raw = subprocess.check_output(
        ["cmd", "/c", f"railway deployment list --service {service} --json"],
        cwd=str(REPO),
        text=True,
    )
    return json.loads(raw)


worker = rw_vars("exemplary-encouragement")
web = rw_vars("ngoinfo-grantpilot")
deps = rw_deps("exemplary-encouragement")
top = deps[0]
print("WORKER_FAULT=", worker.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"))
print("WEB_HAS_FLAG_KEY=", "ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE" in web)
print("WEB_FAULT=", web.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"))
print(
    "WORKER_TOP_DEPLOY=",
    top.get("status"),
    (top.get("meta") or {}).get("commitHash", "")[:12],
)
print("STATUS_AT_UTC=", datetime.now(timezone.utc).isoformat())
