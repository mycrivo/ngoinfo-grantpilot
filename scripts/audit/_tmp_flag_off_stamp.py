import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
raw = subprocess.check_output(
    ["cmd", "/c", "railway variables --json --service exemplary-encouragement"],
    cwd=str(REPO),
    text=True,
)
worker = json.loads(raw)
val = worker.get("ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE")
print("WORKER_FAULT_AFTER_UNSET=", val)

p = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_FLAG_WINDOW_2026-07-19.json")
d = json.loads(p.read_text(encoding="utf-8"))
end = datetime.now(timezone.utc)
d["window_end_utc"] = end.isoformat()
d["worker_flag_readback_end"] = val
start = datetime.fromisoformat(d["window_start_utc"])
d["window_duration_seconds"] = round((end - start).total_seconds(), 1)
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
print("WINDOW_END_UTC=", d["window_end_utc"])
print("WINDOW_DURATION_S=", d["window_duration_seconds"])
