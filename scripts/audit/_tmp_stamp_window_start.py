import json
from datetime import datetime, timezone
from pathlib import Path

p = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_FLAG_WINDOW_2026-07-19.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["window_start_utc"] = datetime.now(timezone.utc).isoformat()
p.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
print("WINDOW_START_UTC=", d["window_start_utc"])
