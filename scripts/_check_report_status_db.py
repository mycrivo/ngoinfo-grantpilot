#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
railway = shutil.which("railway.cmd") or shutil.which("railway")
pg = json.loads(
    subprocess.check_output(
        [railway, "variables", "--json", "--service", "Postgres"],
        cwd=REPO,
        text=True,
    )
)
os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]
from sqlalchemy import create_engine, text

rid = sys.argv[1]
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as c:
    r = c.execute(
        text(
            """
            SELECT status,
                   knowledge_bank_json->>'gate1_confirmed_at' AS g1,
                   knowledge_bank_json->>'gate2_confirmed_at' AS g2,
                   knowledge_bank_json->>'gate3_confirmed_at' AS g3,
                   content_json->'generation_summary' AS gen_summary
            FROM donor_reports WHERE id = CAST(:rid AS uuid)
            """
        ),
        {"rid": rid},
    ).mappings().first()
    jobs = c.execute(
        text(
            """
            SELECT stage, status, error, finished_at
            FROM report_jobs WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at DESC NULLS LAST LIMIT 5
            """
        ),
        {"rid": rid},
    ).mappings().all()
    exports = c.execute(
        text(
            """
            SELECT id, export_format, created_at
            FROM report_exports WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY created_at DESC LIMIT 3
            """
        ),
        {"rid": rid},
    ).mappings().all()
print("report", dict(r) if r else None)
print("jobs", [dict(x) for x in jobs])
print("exports", [dict(x) for x in exports])
