#!/usr/bin/env python3
"""Restore Gate 1 if wiped, reclaim failed gap job, resume to Gate 2 halt."""

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
JOB_ID = "e9e8adaf-d72c-4fef-bba9-52769221dd70"
FIXTURE_EMAIL = "stage-f-validation-2026-06-05-1780657990@grantpilot-test.org"
POLL_SECONDS = 15
MAX_WAIT = 900

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
            resolved_log.append({"fact_key": key, "resolved_value": chosen})
        conflicts_out.append(c)
    out["conflicts"] = conflicts_out
    out.pop("gate1_confirmed_at", None)
    return out, resolved_log


def ensure_gate1_confirmed(session: requests.Session) -> dict:
    kb_r = session.get(
        f"{BASE_URL}/api/reports/{REPORT_ID}/knowledge-bank", timeout=60
    )
    kb_r.raise_for_status()
    kb_api = kb_r.json()
    kb = dict(kb_api.get("knowledge_bank_json") or kb_api)
    if kb.get("gate1_confirmed_at"):
        return {"skipped": True, "gate1_confirmed_at": kb["gate1_confirmed_at"]}

    resolved_kb, resolution_log = apply_resolutions(kb)
    endpoint = (
        f"{BASE_URL}/api/reports/donor-reports/{REPORT_ID}/knowledge-bank/gate1/confirm"
    )
    g1 = session.post(
        endpoint,
        json={"knowledge_bank_json": resolved_kb},
        timeout=120,
    )
    body = g1.json() if g1.headers.get("content-type", "").startswith("application/json") else {}
    return {
        "skipped": False,
        "status_code": g1.status_code,
        "resolution_log": resolution_log,
        "gate1_confirmed_at": body.get("gate1_confirmed_at"),
        "body": body,
    }


def poll_job(session: requests.Session) -> dict:
    deadline = time.time() + MAX_WAIT
    last: dict = {}
    while time.time() < deadline:
        r = session.get(
            f"{BASE_URL}/api/reports/{REPORT_ID}/job",
            params={"job_id": JOB_ID},
            timeout=60,
        )
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        print(json.dumps({"poll": {"status": st, "stage": stage, "error": last.get("error")}}), flush=True)
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
                       gap_analysis_json->>'readiness_score' AS readiness_score,
                       gap_analysis_json->'agent_trace'->>'attempt_count' AS gap_attempt_count,
                       jsonb_array_length(COALESCE(gap_analysis_json->'gaps', '[]'::jsonb)) AS gap_count,
                       gap_analysis_json->'gaps' AS gaps
                FROM donor_reports WHERE id = CAST(:rid AS uuid)
                """
            ),
            {"rid": REPORT_ID},
        ).mappings().first()
        jobs = conn.execute(
            text(
                """
                SELECT id, stage, status, error, started_at, finished_at,
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

    gate1_result = ensure_gate1_confirmed(session)
    print(json.dumps({"gate1_restore": gate1_result}, default=str), flush=True)
    if not gate1_result.get("skipped") and gate1_result.get("status_code") != 200:
        return 1

    enqueue = session.post(f"{BASE_URL}/api/reports/{REPORT_ID}/job", timeout=60)
    print(
        json.dumps(
            {
                "enqueue": {
                    "status_code": enqueue.status_code,
                    "body": enqueue.json()
                    if enqueue.headers.get("content-type", "").startswith("application/json")
                    else enqueue.text[:500],
                }
            },
            default=str,
        ),
        flush=True,
    )
    if enqueue.status_code != 200:
        return 2

    body = enqueue.json()
    if body.get("job_id") != JOB_ID:
        print(f"STOP: expected reclaimed job {JOB_ID}, got {body.get('job_id')}")
        return 3
    if body.get("stage") != "gap":
        print(f"STOP: expected stage=gap, got {body.get('stage')}")
        return 4

    post_job = poll_job(session)
    db_state = read_db_state()

    gaps = (db_state.get("donor_report") or {}).get("gaps") or []
    gap_summary = [
        {
            "item_key": g.get("item_key"),
            "section_label": g.get("section_label"),
            "question": g.get("question"),
            "rationale": g.get("rationale"),
        }
        for g in gaps
    ]

    out = {
        "report_id": REPORT_ID,
        "job_id": JOB_ID,
        "gate1_restore": gate1_result,
        "enqueue_response": body,
        "post_gap_job": post_job,
        "gap_summary": gap_summary,
        "db_state": db_state,
    }
    path = REPO / "M_E_Module" / "gate_run" / "STAGE_F_GAP_RESUME_RESULT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, indent=2, default=str))

    if post_job.get("status") == "failed":
        return 5
    ok = (
        post_job.get("status") == "awaiting_human"
        and post_job.get("stage") == "synthesise"
    )
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
