#!/usr/bin/env python3
"""Disposable Stage E prod smoke walk — orchestrates API only, no in-process agents."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_URL = os.environ.get(
    "BASE_URL", "https://ngoinfo-grantpilot-production.up.railway.app"
).rstrip("/")
FCDO_TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
DOC_DIR = (
    Path(__file__).resolve().parents[1]
    / "M_E_Module"
    / "Sample_docs"
    / "FCDO_Test_Set"
)
UPLOAD_FILES = [
    "01_FCDO_BridgeLight_Winning_Proposal.docx",
    "02_FCDO_BridgeLight_Award_Letter.docx",
    "03_FCDO_BridgeLight_Logframe_Data_Table.docx",
    "BridgeLight Logframe and Finance AR1 Export.xlsx",
]
POLL_SECONDS = 12
MAX_WAIT_GATE1 = 900
MAX_WAIT_POST_GATE1 = 600
MAX_WAIT_POST_GATE2 = 300


def _secret() -> str:
    secret = os.environ.get("TEST_MODE_SECRET", "").strip()
    if secret:
        return secret
    try:
        out = subprocess.check_output(
            ["railway", "variables", "--json"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
        )
        data = json.loads(out)
        return str(data.get("TEST_MODE_SECRET") or "")
    except Exception as exc:
        raise RuntimeError("TEST_MODE_SECRET not available") from exc


def mint_token(session: requests.Session, email: str) -> str:
    secret = _secret()
    r = session.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={"X-Test-Mode-Secret": secret, "Content-Type": "application/json"},
        json={"email": email, "full_name": "Stage E Smoke", "plan": "FREE"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"mint failed {r.status_code}: {r.text[:500]}")
    return r.json()["access_token"]


def poll_job(
    session: requests.Session,
    report_id: str,
    *,
    label: str,
    until_status: set[str] | None = None,
    until_stage: set[str] | None = None,
    max_seconds: int,
) -> dict:
    deadline = time.time() + max_seconds
    last: dict = {}
    seen_running = False
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        if st == "running":
            seen_running = True
        print(
            f"  [{label}] status={st} stage={stage} "
            f"error={last.get('error')!r} running_seen={seen_running}",
            flush=True,
        )
        if until_status and st in until_status:
            if until_stage is None or stage in until_stage:
                last["_seen_running"] = seen_running
                return last
        if st == "failed":
            last["_seen_running"] = seen_running
            return last
        time.sleep(POLL_SECONDS)
    last["_seen_running"] = seen_running
    last["_timeout"] = True
    return last


def fetch_gap_analysis_via_db(report_id: str) -> dict | None:
    """Read-only gap_analysis_json for the smoke report via Railway psql."""
    sql = (
        "SELECT gap_analysis_json FROM donor_reports "
        f"WHERE id = '{report_id}'::uuid;"
    )
    try:
        proc = subprocess.run(
            ["railway", "run", "--", "psql", "$DATABASE_URL", "-t", "-A", "-c", sql],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            print(f"  [db-read] psql failed: {proc.stderr[:300]}", flush=True)
            return None
        raw = proc.stdout.strip()
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:
        print(f"  [db-read] skipped: {exc}", flush=True)
        return None


def main() -> int:
    email = f"stage-e-smoke-{int(time.time())}@grantpilot-test.org"
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, email)}"

    print("=== Stage E prod smoke walk ===", flush=True)
    print(f"BASE_URL={BASE_URL}", flush=True)

    # Step 1 — create report
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
        print(f"STOP: create report failed {r.status_code} {r.text[:500]}")
        return 1
    report = r.json()
    report_id = report["id"]
    print(f"CREATE report_id={report_id} template={report.get('template_name')}", flush=True)

    # Step 2 — upload
    for name in UPLOAD_FILES:
        path = DOC_DIR / name
        if not path.exists():
            print(f"STOP: missing upload file {path}")
            return 1
        mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if name.endswith(".xlsx")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if name.endswith(".docx")
            else "application/octet-stream"
        )
        with path.open("rb") as fh:
            ur = session.post(
                f"{BASE_URL}/api/reports/{report_id}/documents",
                files={"file": (name, fh, mime)},
                timeout=120,
            )
        if ur.status_code != 200:
            print(f"STOP: upload {name} failed {ur.status_code} {ur.text[:300]}")
            return 1
        print(f"UPLOAD {name} -> {ur.json().get('id')}", flush=True)

    # Step 3 — enqueue + poll to Gate 1
    er = session.post(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
    er.raise_for_status()
    print(f"ENQUEUE job_id={er.json().get('job_id')}", flush=True)

    gate1_job = poll_job(
        session,
        report_id,
        label="to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_WAIT_GATE1,
    )
    print(f"GATE1_HALT {json.dumps({k: gate1_job.get(k) for k in ('status','stage','error')})}", flush=True)
    if gate1_job.get("status") == "failed":
        print("OVERALL FAIL at Gate 1 pipeline")
        return 1

    kb_r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb = kb_r.json().get("knowledge_bank_json") or kb_r.json()
    facts_count = len(kb.get("facts") or {})
    print(f"KB pre-gate1 facts={facts_count} reconciled={kb.get('reconciliation_outcome')}", flush=True)

    # Step 4 — Gate 1 confirm
    g1 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb_r.json().get("knowledge_bank_json") or kb},
        timeout=60,
    )
    if g1.status_code != 200:
        print(f"STOP: gate1 confirm failed {g1.status_code} {g1.text[:500]}")
        return 1
    print(f"GATE1_CONFIRM at={g1.json().get('gate1_confirmed_at')}", flush=True)

    # Beat 1 + 2 — post Gate 1 resume
    post_g1 = poll_job(
        session,
        report_id,
        label="post-gate1",
        until_status={"awaiting_human", "failed"},
        max_seconds=MAX_WAIT_POST_GATE1,
    )
    trace = post_g1.get("agent_trace_json") or {}
    gap_trace = (trace.get("stages") or {}).get("gap") or {}
    print(f"POST_GATE1_JOB {json.dumps({k: post_g1.get(k) for k in ('status','stage','error')})}", flush=True)
    print(f"GAP_TRACE {json.dumps(gap_trace)}", flush=True)

    gap_json = fetch_gap_analysis_via_db(report_id) or {}
    gaps = gap_json.get("gaps") or []
    readiness = gap_json.get("readiness_score")
    print(
        f"GAP_ANALYSIS readiness={readiness} gap_count={len(gaps)} "
        f"gap_agent={gap_json.get('gap_agent')!r}",
        flush=True,
    )
    if gaps:
        keys = [g.get("item_key") for g in gaps[:8]]
        print(f"GAP_KEYS_SAMPLE {keys}", flush=True)
        if len(gaps) > 8:
            print(f"GAP_KEYS_MORE count={len(gaps)-8}", flush=True)

    beat1_action = gap_trace.get("action")
    beat1_pass = beat1_action != "parked_at_gap_boundary" and gap_trace.get("gap_count") is not None
    beat2_pass = (
        post_g1.get("status") == "awaiting_human"
        and post_g1.get("stage") == "synthesise"
        and bool(gap_json.get("gap_agent"))
        and len(gaps) > 0
    )

    # Step 6 — Gate 2 full confirm (if gaps exist)
    gate2_pass = False
    if gaps:
        responses = {}
        for g in gaps:
            key = g["item_key"]
            responses[key] = {
                "disposition": "answered",
                "answer_text": f"Smoke answer for {g.get('required_item_ref', key)}.",
            }
        g2 = session.post(
            f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate2/gap-responses",
            json={"responses": responses},
            timeout=120,
        )
        print(f"GATE2_SUBMIT status={g2.status_code} body={g2.text[:400]}", flush=True)
        if g2.status_code == 200:
            body = g2.json()
            print(
                f"GATE2 unlocked={body.get('gate2_unlocked')} "
                f"confirmed_at={body.get('gate2_confirmed_at')}",
                flush=True,
            )
            if body.get("gate2_unlocked"):
                post_g2 = poll_job(
                    session,
                    report_id,
                    label="post-gate2",
                    until_status={"awaiting_human", "failed"},
                    max_seconds=MAX_WAIT_POST_GATE2,
                )
                synth_trace = (post_g2.get("agent_trace_json") or {}).get("stages", {}).get(
                    "synthesise"
                ) or {}
                print(
                    f"POST_GATE2_JOB {json.dumps({k: post_g2.get(k) for k in ('status','stage','error')})}",
                    flush=True,
                )
                print(f"SYNTH_TRACE {json.dumps(synth_trace)}", flush=True)
                gate2_pass = (
                    post_g2.get("status") == "awaiting_human"
                    and post_g2.get("stage") == "synthesise"
                    and synth_trace.get("action") == "parked_at_synthesise_boundary"
                )
    else:
        print("GATE2 skipped — no gaps persisted", flush=True)

    print("=== VERDICT ===", flush=True)
    print(f"report_id={report_id}", flush=True)
    print(f"BEAT1_gate1_resume_runs_e3={'PASS' if beat1_pass else 'FAIL'} action={beat1_action!r}", flush=True)
    print(f"BEAT2_e3_and_gate2_halt={'PASS' if beat2_pass else 'FAIL'}", flush=True)
    print(f"CLOSING_gate2_resume_park={'PASS' if gate2_pass else 'FAIL' if gaps else 'SKIP'}", flush=True)
    overall = beat1_pass and beat2_pass and (gate2_pass or not gaps)
    print(f"OVERALL={'PASS' if overall else 'FAIL'}", flush=True)
    return 0 if overall else 2


if __name__ == "__main__":
    sys.exit(main())
