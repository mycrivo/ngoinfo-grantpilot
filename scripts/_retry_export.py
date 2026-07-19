#!/usr/bin/env python3
"""Re-queue failed export stage and poll until done."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
BASE = os.environ.get(
    "BASE_URL", "https://ngoinfo-grantpilot-production.up.railway.app"
).rstrip("/")

railway = shutil.which("railway.cmd") or shutil.which("railway")
pg = json.loads(
    subprocess.check_output(
        [railway, "variables", "--json", "--service", "Postgres"],
        cwd=REPO,
        text=True,
    )
)
backend = json.loads(
    subprocess.check_output(
        [railway, "variables", "--json", "--service", "ngoinfo-grantpilot"],
        cwd=REPO,
        text=True,
    )
)
os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]
secret = backend.get("TEST_MODE_SECRET", "")

report_id = sys.argv[1]
job_id = sys.argv[2] if len(sys.argv) > 2 else None
email = sys.argv[3] if len(sys.argv) > 3 else "REDACTED_OWNER@example.invalid"

engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as conn:
    if job_id:
        conn.execute(
            text(
                """
                UPDATE report_jobs
                SET status = 'queued', stage = 'export', error = NULL, finished_at = NULL
                WHERE id = CAST(:jid AS uuid)
                """
            ),
            {"jid": job_id},
        )
    conn.execute(
        text(
            """
            UPDATE donor_reports SET status = 'GENERATING'
            WHERE id = CAST(:rid AS uuid)
            """
        ),
        {"rid": report_id},
    )
print("re-queued export")

mint = requests.post(
    f"{BASE}/api/auth/test-mode/mint",
    headers={"X-Test-Mode-Secret": secret, "Content-Type": "application/json"},
    json={"email": email, "full_name": "Export retry", "plan": "IMPACT"},
    timeout=60,
)
mint.raise_for_status()
token = mint.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

for i in range(60):
    job = requests.get(
        f"{BASE}/api/reports/{report_id}/job", headers=headers, timeout=60
    ).json()
    print(
        f"poll {i}: status={job.get('status')} stage={job.get('stage')} "
        f"error={job.get('error')!r}",
        flush=True,
    )
    if job.get("status") == "done":
        exp = requests.get(
            f"{BASE}/api/reports/{report_id}/export", headers=headers, timeout=120
        )
        print(
            f"export status={exp.status_code} type={exp.headers.get('content-type')} "
            f"bytes={len(exp.content)}",
            flush=True,
        )
        if exp.status_code == 200:
            out = REPO / f"FCDO_EXPORT_{report_id[:8]}.docx"
            out.write_bytes(exp.content)
            print(f"saved {out}", flush=True)
        sys.exit(0)
    if job.get("status") == "failed":
        sys.exit(1)
    time.sleep(12)
print("timeout")
sys.exit(1)
