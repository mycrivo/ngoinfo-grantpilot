#!/usr/bin/env python3
"""Stage F fixture — API-only walk to Gate 1 halt (no gate_run harness)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BASE_URL = "https://ngoinfo-grantpilot-production.up.railway.app"
FCDO_TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
DOC_DIR = REPO / "M_E_Module" / "Sample_docs" / "FCDO_Test_Set"
UPLOAD_FILES = [
    "01_FCDO_BridgeLight_Winning_Proposal.docx",
    "02_FCDO_BridgeLight_Award_Letter.docx",
    "03_FCDO_BridgeLight_Logframe_Data_Table.docx",
    "BridgeLight Logframe and Finance AR1 Export.xlsx",
]
FIXTURE_TAG = f"stage-f-validation-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
POLL_SECONDS = 15
MAX_WAIT_GATE1 = 1200


def _railway() -> str:
    import shutil

    return shutil.which("railway.cmd") or shutil.which("railway") or "railway"


def _secret() -> str:
    out = subprocess.check_output(
        [_railway(), "variables", "--json", "--service", "ngoinfo-grantpilot"],
        cwd=REPO,
        text=True,
    )
    return str(json.loads(out).get("TEST_MODE_SECRET") or "")


def mint_token(session: requests.Session) -> str:
    email = f"{FIXTURE_TAG}-{int(time.time())}@grantpilot-test.org"
    r = session.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={
            "X-Test-Mode-Secret": _secret(),
            "Content-Type": "application/json",
        },
        json={"email": email, "full_name": FIXTURE_TAG, "plan": "FREE"},
        timeout=60,
    )
    r.raise_for_status()
    session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return email


def poll_job(session: requests.Session, report_id: str) -> dict:
    deadline = time.time() + MAX_WAIT_GATE1
    last: dict = {}
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        print(json.dumps({"poll": {"status": st, "stage": stage, "error": last.get("error")}}), flush=True)
        if st == "failed":
            return last
        if st == "awaiting_human" and stage == "gap":
            return last
        time.sleep(POLL_SECONDS)
    last["_timeout"] = True
    return last


def read_db_state(report_id: str) -> dict:
    pg = json.loads(
        subprocess.check_output(
            [_railway(), "variables", "--json", "--service", "Postgres"],
            cwd=REPO,
            text=True,
        )
    )
    from sqlalchemy import create_engine, text

    engine = create_engine(pg["DATABASE_PUBLIC_URL"])
    with engine.connect() as conn:
        report = conn.execute(
            text(
                """
                SELECT id, status, updated_at, created_at,
                       funder_report_template_id::text AS template_id,
                       knowledge_bank_json
                FROM donor_reports WHERE id = CAST(:rid AS uuid)
                """
            ),
            {"rid": report_id},
        ).mappings().first()
        jobs = conn.execute(
            text(
                """
                SELECT id, stage, status, started_at, finished_at, agent_trace_json
                FROM report_jobs WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY started_at ASC NULLS LAST, id ASC
                """
            ),
            {"rid": report_id},
        ).mappings().all()
    return {
        "donor_report": dict(report) if report else None,
        "report_jobs": [dict(j) for j in jobs],
    }


def main() -> int:
    session = requests.Session()
    fixture_email = mint_token(session)
    print(json.dumps({"fixture_tag": FIXTURE_TAG, "fixture_email": fixture_email}), flush=True)

    r = session.post(
        f"{BASE_URL}/api/reports",
        json={
            "reporting_period_start": "2025-04-01",
            "reporting_period_end": "2026-03-31",
            "funder_report_template_id": FCDO_TEMPLATE_ID,
        },
        timeout=60,
    )
    if r.status_code != 200:
        print(f"STOP create: {r.status_code} {r.text[:500]}")
        return 1
    report = r.json()
    report_id = report["id"]
    print(json.dumps({"create": report}), flush=True)

    uploaded = []
    for name in UPLOAD_FILES:
        path = DOC_DIR / name
        if not path.exists():
            print(f"STOP missing file: {path}")
            return 1
        mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if name.endswith(".xlsx")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        with path.open("rb") as fh:
            ur = session.post(
                f"{BASE_URL}/api/reports/{report_id}/documents",
                files={"file": (name, fh, mime)},
                timeout=180,
            )
        if ur.status_code != 200:
            print(f"STOP upload {name}: {ur.status_code} {ur.text[:300]}")
            return 1
        uploaded.append({"filename": name, "document_id": ur.json().get("id")})
    print(json.dumps({"uploads": uploaded}), flush=True)

    er = session.post(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
    er.raise_for_status()
    print(json.dumps({"enqueue": er.json()}), flush=True)

    job = poll_job(session, report_id)
    print(json.dumps({"gate1_halt_job": job}, default=str), flush=True)

    kb_r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb_payload = kb_r.json()
    print(json.dumps({"knowledge_bank_api": kb_payload}, default=str), flush=True)

    db_state = read_db_state(report_id)
    print(json.dumps({"db_state": db_state}, default=str), flush=True)

    out = REPO / "M_E_Module" / "gate_run" / "STAGE_F_GATE1_FIXTURE_RESULT.json"
    out.write_text(
        json.dumps(
            {
                "fixture_tag": FIXTURE_TAG,
                "fixture_email": fixture_email,
                "report_id": report_id,
                "uploads": uploaded,
                "job_halt": job,
                "knowledge_bank": kb_payload,
                "db_state": db_state,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return 0 if job.get("status") == "awaiting_human" and job.get("stage") == "gap" else 2


if __name__ == "__main__":
    sys.exit(main())
