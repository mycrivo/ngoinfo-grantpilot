#!/usr/bin/env python3
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
RID = "1c9f7ffa-9853-40e7-86c2-5c9e41300be6"
JID = "1f26c2dc-02d4-4dda-8af5-4fce7bf57e82"
railway = shutil.which("railway.cmd") or "railway"
pg = json.loads(
    subprocess.check_output(
        [railway, "variables", "--json", "--service", "Postgres"],
        cwd=REPO,
        text=True,
    )
)
engine = create_engine(pg["DATABASE_PUBLIC_URL"])
now = datetime.now(timezone.utc)
with engine.begin() as conn:
    row = conn.execute(
        text("SELECT status, stage FROM report_jobs WHERE id = CAST(:jid AS uuid)"),
        {"jid": JID},
    ).mappings().first()
    print("before", dict(row) if row else None)
    if row and row["status"] not in ("done", "failed"):
        conn.execute(
            text(
                """
                UPDATE report_jobs
                SET status = 'failed',
                    error = 'aborted: accidental enqueue before failed-job reclaim deploy',
                    finished_at = :now
                WHERE id = CAST(:jid AS uuid)
                """
            ),
            {"jid": JID, "now": now},
        )
        print("marked failed")
    after = conn.execute(
        text("SELECT status, stage, error FROM report_jobs WHERE id = CAST(:jid AS uuid)"),
        {"jid": JID},
    ).mappings().first()
    print("after", dict(after))
    gate1 = conn.execute(
        text(
            """
            SELECT knowledge_bank_json->>'gate1_confirmed_at' AS g1
            FROM donor_reports
            WHERE id = CAST(:rid AS uuid)
            """
        ),
        {"rid": RID},
    ).scalar()
    print("gate1", gate1)
