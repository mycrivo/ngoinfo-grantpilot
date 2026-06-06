#!/usr/bin/env python3
import json
import shutil
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
RID = "1c9f7ffa-9853-40e7-86c2-5c9e41300be6"
railway = shutil.which("railway.cmd") or "railway"
pg = json.loads(
    subprocess.check_output(
        [railway, "variables", "--json", "--service", "Postgres"],
        cwd=REPO,
        text=True,
    )
)
engine = create_engine(pg["DATABASE_PUBLIC_URL"])
with engine.connect() as conn:
    report = conn.execute(
        text(
            """
            SELECT status,
                   knowledge_bank_json->>'gate1_confirmed_at' AS gate1
            FROM donor_reports
            WHERE id = CAST(:rid AS uuid)
            """
        ),
        {"rid": RID},
    ).mappings().first()
    jobs = conn.execute(
        text(
            """
            SELECT id, stage, status, error, started_at, finished_at
            FROM report_jobs
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at ASC NULLS LAST, id ASC
            """
        ),
        {"rid": RID},
    ).mappings().all()
print("report", dict(report) if report else None)
for j in jobs:
    print(dict(j))
