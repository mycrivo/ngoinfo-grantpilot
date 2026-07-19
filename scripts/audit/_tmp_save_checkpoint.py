import json
import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
raw = subprocess.check_output(
    ["cmd", "/c", "railway variables --json --service Postgres"],
    cwd=str(REPO),
    text=True,
)
os.environ["DATABASE_URL"] = json.loads(raw)["DATABASE_PUBLIC_URL"]
engine = create_engine(os.environ["DATABASE_URL"])
rid = "b007f125-cf33-4bba-8acf-6eccde27d063"
with engine.connect() as c:
    job = c.execute(
        text(
            """
            SELECT agent_trace_json->'stages'->'extract' AS extract_stage
            FROM report_jobs
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at DESC NULLS LAST LIMIT 1
            """
        ),
        {"rid": rid},
    ).scalar()
out = Path(
    "docs/artefacts/me_module/audits/TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json"
)
out.write_text(json.dumps(job, indent=2, default=str) + "\n", encoding="utf-8")
print("WROTE", out)
