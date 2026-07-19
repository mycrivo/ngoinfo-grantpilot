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

email = sys.argv[1] if len(sys.argv) > 1 else "REDACTED_OWNER@example.invalid"
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as c:
    u = c.execute(
        text("SELECT id, email FROM users WHERE email = :email"),
        {"email": email},
    ).mappings().first()
    print("user", dict(u) if u else None)
    if not u:
        sys.exit(1)
    uid = str(u["id"])
    p = c.execute(
        text("SELECT plan_name FROM user_plans WHERE user_id = CAST(:uid AS uuid)"),
        {"uid": uid},
    ).scalar()
    q = c.execute(
        text(
            "SELECT reports_remaining FROM usage_ledger "
            "WHERE user_id = CAST(:uid AS uuid) ORDER BY updated_at DESC LIMIT 1"
        ),
        {"uid": uid},
    ).scalar()
    n = c.execute(
        text("SELECT count(*) FROM donor_reports WHERE user_id = CAST(:uid AS uuid)"),
        {"uid": uid},
    ).scalar()
    print("plan", p, "reports_remaining", q, "donor_reports", n)
