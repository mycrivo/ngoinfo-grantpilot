#!/usr/bin/env python3
"""Shared helpers for the Cursor dynamic (behavioural) audit.

AUDIT TOOLING ONLY — drives the live engine over HTTP + read-only DB reads.
Canonical gate URLs (no stale /donor-reports/ segment). No engine mutation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

REPO = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get(
    "BASE_URL", "https://ngoinfo-grantpilot-production.up.railway.app"
).rstrip("/")
ARTIFACT_DIR = REPO / "docs" / "artefacts" / "me_module" / "audits" / "dynamic_run"

FCDO_TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
NLCF_TEMPLATE_ID = "2d5d75b7-12f5-46b5-adaa-d5939a5249a8"

DOC_ROOT = REPO / "M_E_Module" / "Sample_docs"
FCDO_DIR = DOC_ROOT / "FCDO_Test_Set"
NLCF_DIR = DOC_ROOT / "NLCF_Test_Set"

# Rough list pricing for token->USD estimates (cost accounting only).
OPENAI_INPUT_USD_PER_1M = 2.50
OPENAI_OUTPUT_USD_PER_1M = 10.00
CLAUDE_INPUT_USD_PER_1M = 1.00
CLAUDE_OUTPUT_USD_PER_1M = 5.00

POLL_SECONDS = 12

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def mime_for(name: str) -> str:
    if name.lower().endswith(".xlsx"):
        return _XLSX_MIME
    if name.lower().endswith(".pdf"):
        return "application/pdf"
    if name.lower().endswith(".csv"):
        return "text/csv"
    return _DOCX_MIME


def _railway() -> str:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found")
    return railway


def railway_vars(*extra: str) -> dict:
    out = subprocess.check_output(
        [_railway(), "variables", "--json", *extra], cwd=REPO, text=True
    )
    return json.loads(out)


def bootstrap_db_env() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    pg = railway_vars("--service", "Postgres")
    os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]


BACKEND_SERVICE = os.environ.get("BACKEND_SERVICE", "ngoinfo-grantpilot")


def test_mode_secret() -> str:
    if os.environ.get("TEST_MODE_SECRET"):
        return os.environ["TEST_MODE_SECRET"]
    return str(railway_vars("--service", BACKEND_SERVICE).get("TEST_MODE_SECRET") or "")


def ensure_plan(user_id: str, plan_name: str = "IMPACT") -> None:
    """Upsert a user_plans row (test-data setup; mint endpoint cannot grant plans)."""
    bootstrap_db_env()
    import app.models  # noqa: F401
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as c:
        c.execute(text(
            """
            INSERT INTO user_plans (user_id, plan_name, plan_activated_at)
            VALUES (CAST(:uid AS uuid), :plan, now())
            ON CONFLICT (user_id) DO UPDATE SET plan_name = EXCLUDED.plan_name,
                                                updated_at = now()
            """), {"uid": user_id, "plan": plan_name})


def mint_session(email: str, *, plan: str = "IMPACT", full_name: str = "Audit Walk") -> requests.Session:
    session = requests.Session()
    r = session.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={"X-Test-Mode-Secret": test_mode_secret(), "Content-Type": "application/json"},
        json={"email": email, "full_name": full_name, "plan": plan},
        timeout=60,
    )
    r.raise_for_status()
    body = r.json()
    session.headers["Authorization"] = f"Bearer {body['access_token']}"
    session.user_id = body["user"]["id"]  # type: ignore[attr-defined]
    session.user_email = body["user"]["email"]  # type: ignore[attr-defined]
    if plan and os.environ.get("DATABASE_URL"):
        ensure_plan(body["user"]["id"], plan)
    return session


def create_report(session: requests.Session, *, template_id: str,
                  start: str = "2025-04-01", end: str = "2026-03-31") -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports",
        json={
            "reporting_period_start": start,
            "reporting_period_end": end,
            "funder_report_template_id": template_id,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def upload(session: requests.Session, report_id: str, path: Path) -> dict:
    with path.open("rb") as fh:
        r = session.post(
            f"{BASE_URL}/api/reports/{report_id}/documents",
            files={"file": (path.name, fh, mime_for(path.name))},
            timeout=180,
        )
    if r.status_code >= 400:
        detail = _safe_json(r)
        raise requests.HTTPError(
            f"{r.status_code} uploading {path.name}: {detail}",
            response=r,
        )
    return r.json()


def enqueue(session: requests.Session, report_id: str) -> dict:
    r = session.post(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
    return {"status_code": r.status_code, "body": _safe_json(r)}


def _safe_json(r: requests.Response) -> Any:
    try:
        return r.json()
    except Exception:
        return r.text[:500]


def poll_job(session: requests.Session, report_id: str, *, label: str,
             until_status: set[str] | None = None, until_stage: set[str] | None = None,
             max_seconds: int) -> dict:
    deadline = time.time() + max_seconds
    last: dict = {}
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        print(f"  [{label}] status={st} stage={stage} error={last.get('error')!r}", flush=True)
        if st == "failed":
            return last
        if until_status and st in until_status:
            if until_stage is None or stage in until_stage:
                return last
        time.sleep(POLL_SECONDS)
    last["_timeout"] = True
    return last


def get_kb(session: requests.Session, report_id: str) -> dict:
    r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    r.raise_for_status()
    body = r.json()
    return body.get("knowledge_bank_json") or body


def resolve_conflicts(kb: dict) -> int:
    """Human Gate-1 action: set resolved_value on each unresolved conflict.

    Picks the first candidate value (a deliberate, recorded human choice). Does
    not invent a value outside the surfaced candidates.
    """
    from datetime import datetime, timezone

    resolved = 0
    for cf in kb.get("conflicts") or []:
        if cf.get("resolved_value") is None:
            vals = cf.get("values") or []
            if vals and isinstance(vals[0], dict):
                cf["resolved_value"] = vals[0].get("value")
                cf["resolved_at"] = datetime.now(timezone.utc).isoformat()
                resolved += 1
    return resolved


def owner_email_for_report(report_id: str) -> str:
    bootstrap_db_env()
    import app.models  # noqa: F401
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as c:
        row = c.execute(text(
            """
            SELECT u.email FROM donor_reports d JOIN users u ON u.id = d.user_id
            WHERE d.id = CAST(:rid AS uuid)
            """), {"rid": report_id}).mappings().first()
    if not row:
        raise RuntimeError(f"no owner for report {report_id}")
    return str(row["email"])


def confirm_gate1(session: requests.Session, report_id: str, kb: dict) -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb}, timeout=60,
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def gap_check(session: requests.Session, report_id: str) -> dict:
    r = session.get(f"{BASE_URL}/api/reports/{report_id}/gap-check", timeout=60)
    return {"status_code": r.status_code, "body": _safe_json(r)}


def submit_gate2(session: requests.Session, report_id: str, responses: dict) -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports/{report_id}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses}, timeout=180,
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def resume_critique(session: requests.Session, report_id: str) -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports/{report_id}/job/resume-critique",
        json={},
        timeout=60,
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def accept_all_sections(session: requests.Session, report_id: str) -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports/{report_id}/sections/accept-all",
        json={},
        timeout=60,
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def confirm_gate3(session: requests.Session, report_id: str) -> dict:
    r = session.post(
        f"{BASE_URL}/api/reports/{report_id}/knowledge-bank/gate3/confirm",
        json={}, timeout=60,
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def download_export(session: requests.Session, report_id: str) -> dict:
    r = session.get(f"{BASE_URL}/api/reports/{report_id}/export", timeout=120)
    info = {"status_code": r.status_code,
            "content_type": r.headers.get("content-type"),
            "content_length": len(r.content) if r.status_code == 200 else 0}
    if r.status_code == 200:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        out = ARTIFACT_DIR / f"export_{report_id[:8]}.docx"
        out.write_bytes(r.content)
        info["saved"] = str(out)
    else:
        info["body"] = _safe_json(r)
    return info


def report_detail(session: requests.Session, report_id: str) -> dict:
    r = session.get(f"{BASE_URL}/api/reports/{report_id}", timeout=60)
    return {"status_code": r.status_code, "body": _safe_json(r)}


def db_capture(report_id: str) -> dict:
    """Read-only snapshot of all engine-owned rows for a report."""
    if not os.environ.get("DATABASE_URL"):
        try:
            bootstrap_db_env()
        except Exception:
            return {"report_id": report_id, "db_capture": "skipped_no_database_url"}
    if not os.environ.get("DATABASE_URL"):
        return {"report_id": report_id, "db_capture": "skipped_no_database_url"}
    import app.models  # noqa: F401
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as c:
        docs = c.execute(text(
            """
            SELECT id, original_filename, mime_type, classification,
                   extraction_status, extracted_json
            FROM uploaded_documents
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY created_at
            """), {"rid": report_id}).mappings().all()
        report = c.execute(text(
            """
            SELECT id, user_id, status, version, created_at, updated_at,
                   knowledge_bank_json, gap_analysis_json, content_json
            FROM donor_reports WHERE id = CAST(:rid AS uuid)
            """), {"rid": report_id}).mappings().first()
        jobs = c.execute(text(
            """
            SELECT id, stage, status, error, started_at, finished_at, agent_trace_json
            FROM report_jobs WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at DESC NULLS LAST
            """), {"rid": report_id}).mappings().all()
        ledger = []
        if report:
            ledger = c.execute(text(
                """
                SELECT action_type, idempotency_key, created_at
                FROM usage_ledger WHERE user_id = CAST(:uid AS uuid)
                ORDER BY created_at DESC LIMIT 50
                """), {"uid": str(report["user_id"])}).mappings().all()
    return {
        "documents": [dict(d) for d in docs],
        "report": dict(report) if report else {},
        "jobs": [dict(j) for j in jobs],
        "usage_ledger": [dict(x) for x in ledger],
    }


def collect_claude_tokens(capture: dict) -> tuple[int, int]:
    inp = out = 0

    def _walk(obj: object) -> None:
        nonlocal inp, out
        if isinstance(obj, dict):
            if obj.get("input_tokens") is not None:
                inp += int(obj["input_tokens"])
            if obj.get("output_tokens") is not None:
                out += int(obj["output_tokens"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    for job in capture.get("jobs") or []:
        _walk(job.get("agent_trace_json"))
    for doc in capture.get("documents") or []:
        _walk(doc.get("extracted_json"))
    return inp, out


def collect_openai_tokens(capture: dict) -> tuple[int, int]:
    inp = out = 0
    for job in capture.get("jobs") or []:
        synth = ((job.get("agent_trace_json") or {}).get("stages") or {}).get("synthesise", {})
        inp += int(synth.get("openai_input_tokens") or 0)
        out += int(synth.get("openai_output_tokens") or 0)
    return inp, out


def cost_summary(capture: dict) -> dict:
    ci, co = collect_claude_tokens(capture)
    oi, oo = collect_openai_tokens(capture)
    claude_usd = ci * CLAUDE_INPUT_USD_PER_1M / 1e6 + co * CLAUDE_OUTPUT_USD_PER_1M / 1e6
    oai_usd = oi * OPENAI_INPUT_USD_PER_1M / 1e6 + oo * OPENAI_OUTPUT_USD_PER_1M / 1e6
    return {
        "claude_input_tokens": ci, "claude_output_tokens": co, "claude_usd": round(claude_usd, 4),
        "openai_input_tokens": oi, "openai_output_tokens": oo, "openai_usd": round(oai_usd, 4),
        "total_usd": round(claude_usd + oai_usd, 4),
    }


def write_artifact(name: str, payload: dict) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out = ARTIFACT_DIR / name
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out}", flush=True)
    return out
