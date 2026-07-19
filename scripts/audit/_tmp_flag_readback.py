import json
from datetime import datetime, timezone
from pathlib import Path

worker = json.loads(Path(".git/rw_worker_vars.json").read_text(encoding="utf-8"))
web = json.loads(Path(".git/rw_web_vars.json").read_text(encoding="utf-8"))
print("WORKER_FAULT=", worker.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"))
print("WEB_HAS_FLAG_KEY=", "ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE" in web)
print("WEB_FAULT=", web.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE"))
print("WINDOW_START_UTC=", datetime.now(timezone.utc).isoformat())
