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
    kb = conn.execute(
        text("SELECT knowledge_bank_json FROM donor_reports WHERE id = CAST(:rid AS uuid)"),
        {"rid": RID},
    ).scalar()
    print("gate1", (kb or {}).get("gate1_confirmed_at"))
    print("recon", (kb or {}).get("reconciliation_outcome"))
    print("conflicts", len((kb or {}).get("conflicts") or []))
    print("facts", len((kb or {}).get("facts") or {}))
