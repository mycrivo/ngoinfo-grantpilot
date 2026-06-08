import json
import os

from scripts.audit import _common as C

cap = C.db_capture("fa81b4e3-ff18-4410-ad4b-1512a661f4cc")
rep = cap["report"]
print("report.status =", rep.get("status"))
print("report.created_at =", rep.get("created_at"))
print("report.updated_at =", rep.get("updated_at"))
for j in cap["jobs"]:
    print("JOB stage=", j["stage"], "status=", j["status"])
    print("  error=", j["error"])
    print("  trace=", json.dumps(j.get("agent_trace_json") or {})[:800])
print("DOCS:")
for d in cap["documents"]:
    print("  ", d["original_filename"], "| class=", d["classification"],
          "| extraction_status=", d["extraction_status"])
C.write_artifact("degraded_failed_capture.json", cap)
