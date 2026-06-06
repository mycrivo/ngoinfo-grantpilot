#!/usr/bin/env python3
"""Stage F step 2 — Gate 1 confirm via real API only."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BASE_URL = "https://ngoinfo-grantpilot-production.up.railway.app"
REPORT_ID = "1c9f7ffa-9853-40e7-86c2-5c9e41300be6"
FIXTURE_EMAIL = "stage-f-validation-2026-06-05-1780657990@grantpilot-test.org"
POLL_SECONDS = 15
MAX_WAIT_POST_GATE1 = 900

# fact_key -> chosen resolved_value (AR1 XLSX / formal period per Pranab rulings)
RESOLUTIONS: dict[str, object] = {
    "indicators.OP1.1.target": 650,
    "indicators.OP1.2.target": 500,
    "indicators.OP1.3.target": 420,
    "indicators.OP2.1.target": 24,
    "indicators.OP2.2.target": 20,
    "indicators.OP3.1.target": 400,
    "indicators.OP3.2.target": 550,
    "indicators.OP3.3.target": 0.75,
    "indicators.OP4.1.target": 4,
    "indicators.OP4.3.target": 120,
    "grant.reporting_cycle_convention": "2024-10-15 to 2025-10-14",
}


def _railway() -> str:
    return shutil.which("railway.cmd") or shutil.which("railway") or "railway"


def _secret() -> str:
    out = subprocess.check_output(
        [_railway(), "variables", "--json", "--service", "ngoinfo-grantpilot"],
        cwd=REPO,
        text=True,
    )
    return str(json.loads(out).get("TEST_MODE_SECRET") or "")


def mint_token(session: requests.Session) -> None:
    r = session.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={
            "X-Test-Mode-Secret": _secret(),
            "Content-Type": "application/json",
        },
        json={
            "email": FIXTURE_EMAIL,
            "full_name": "stage-f-validation-2026-06-05",
            "plan": "FREE",
        },
        timeout=60,
    )
    r.raise_for_status()
    session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"


def apply_resolutions(kb: dict) -> tuple[dict, list[dict]]:
    out = dict(kb)
    resolved_log: list[dict] = []
    conflicts_out = []
    for conflict in kb.get("conflicts") or []:
        c = dict(conflict)
        key = c.get("fact_key")
        if key in RESOLUTIONS:
            chosen = RESOLUTIONS[key]
            c["resolved_value"] = chosen
            c["resolved_at"] = datetime.now(timezone.utc).isoformat()
            resolved_log.append(
                {
                    "fact_key": key,
                    "resolved_value": chosen,
                    "values_preserved": c.get("values"),
                }
            )
        conflicts_out.append(c)
    out["conflicts"] = conflicts_out
    out.pop("gate1_confirmed_at", None)
    return out, resolved_log


def poll_post_gate1(session: requests.Session) -> dict:
    deadline = time.time() + MAX_WAIT_POST_GATE1
    last: dict = {}
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}/api/reports/{REPORT_ID}/job", timeout=60)
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        print(json.dumps({"poll": {"status": st, "stage": stage}}), flush=True)
        if st == "failed":
            return last
        if st == "awaiting_human" and stage == "synthesise":
            return last
        time.sleep(POLL_SECONDS)
    last["_timeout"] = True
    return last


def read_db_state() -> dict:
    from sqlalchemy import create_engine, text

    pg = json.loads(
        subprocess.check_output(
            [_railway(), "variables", "--json", "--service", "Postgres"],
            cwd=REPO,
            text=True,
        )
    )
    engine = create_engine(pg["DATABASE_PUBLIC_URL"])
    with engine.connect() as conn:
        report = conn.execute(
            text(
                """
                SELECT id, status, updated_at,
                       knowledge_bank_json->>'gate1_confirmed_at' AS gate1,
                       knowledge_bank_json->>'gate2_confirmed_at' AS gate2
                FROM donor_reports WHERE id = CAST(:rid AS uuid)
                """
            ),
            {"rid": REPORT_ID},
        ).mappings().first()
        jobs = conn.execute(
            text(
                """
                SELECT id, stage, status, started_at, finished_at,
                       agent_trace_json->'stages'->'gap' AS gap_trace
                FROM report_jobs
                WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY started_at ASC NULLS LAST, id ASC
                """
            ),
            {"rid": REPORT_ID},
        ).mappings().all()
    return {
        "donor_report": dict(report) if report else None,
        "report_jobs": [dict(j) for j in jobs],
    }


def main() -> int:
    session = requests.Session()
    mint_token(session)

    kb_r = session.get(
        f"{BASE_URL}/api/reports/{REPORT_ID}/knowledge-bank", timeout=60
    )
    kb_r.raise_for_status()
    kb_api = kb_r.json()
    kb = dict(kb_api.get("knowledge_bank_json") or kb_api)
    pre_conflicts = len(kb.get("conflicts") or [])
    unresolved = [
        c.get("fact_key")
        for c in (kb.get("conflicts") or [])
        if c.get("resolved_value") is None
    ]
    print(
        json.dumps(
            {
                "pre_confirm": {
                    "conflicts_count": pre_conflicts,
                    "unresolved_keys": unresolved,
                }
            }
        ),
        flush=True,
    )

    resolved_kb, resolution_log = apply_resolutions(kb)
    if len(resolution_log) != 11:
        print(f"STOP: expected 11 resolutions, got {len(resolution_log)}")
        return 1

    endpoint = (
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate1/confirm"
    )
    g1 = session.post(
        endpoint,
        json={"knowledge_bank_json": resolved_kb},
        timeout=120,
    )
    print(
        json.dumps(
            {
                "gate1_confirm": {
                    "endpoint": endpoint,
                    "status_code": g1.status_code,
                    "body": g1.json() if g1.headers.get("content-type", "").startswith("application/json") else g1.text[:500],
                }
            },
            default=str,
        ),
        flush=True,
    )
    if g1.status_code != 200:
        return 2

    post_job = poll_post_gate1(session)
    db_state = read_db_state()

    out = {
        "report_id": REPORT_ID,
        "resolution_log": resolution_log,
        "gate1_response_gate1_confirmed_at": g1.json().get("gate1_confirmed_at"),
        "post_gate1_job": post_job,
        "db_state": db_state,
    }
    path = REPO / "M_E_Module" / "gate_run" / "STAGE_F_GATE1_CONFIRM_RESULT.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))
    ok = (
        g1.status_code == 200
        and post_job.get("status") == "awaiting_human"
        and post_job.get("stage") == "synthesise"
    )
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
