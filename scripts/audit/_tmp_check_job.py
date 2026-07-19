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
pg = json.loads(raw)
os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]
engine = create_engine(os.environ["DATABASE_URL"])
rid = "b007f125-cf33-4bba-8acf-6eccde27d063"
with engine.connect() as c:
    job = c.execute(
        text(
            """
            SELECT id, stage, status, error,
                   agent_trace_json->'stages'->'extract' AS extract_stage
            FROM report_jobs
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at DESC NULLS LAST
            LIMIT 1
            """
        ),
        {"rid": rid},
    ).mappings().first()
    docs = c.execute(
        text(
            """
            SELECT original_filename, classification, extraction_status,
                   extracted_json->'structured'->>'extraction_outcome' AS outcome,
                   extracted_json->'agent_trace'->>'fault_injected' AS fault_injected,
                   extracted_json->'agent_trace'->>'fault_flag' AS fault_flag,
                   extracted_json->'agent_trace'->>'degraded_code' AS degraded_code
            FROM uploaded_documents
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY created_at
            """
        ),
        {"rid": rid},
    ).mappings().all()
print("JOB", dict(job) if job else None)
print("DOCS")
for d in docs:
    print(dict(d))
