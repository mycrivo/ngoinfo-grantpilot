#!/usr/bin/env python3
"""Fresh FCDO BridgeLight prod walk — D4 actuals + F1 synthesis (throwaway)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get(
    "BASE_URL", "https://ngoinfo-grantpilot-production.up.railway.app"
).rstrip("/")
FCDO_TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
DOC_DIR = REPO / "M_E_Module" / "Sample_docs" / "FCDO_Test_Set"
UPLOAD_FILES = [
    "01_FCDO_BridgeLight_Winning_Proposal.docx",
    "02_FCDO_BridgeLight_Award_Letter.docx",
    "BridgeLight Logframe and Finance AR1 Export.xlsx",
]
XLSX_NAME = "BridgeLight Logframe and Finance AR1 Export.xlsx"
EXPECTED_DEPLOY_SHA = "98d7512"
POLL_SECONDS = 12
MAX_WAIT_GATE1 = 1200
MAX_WAIT_POST_GATE1 = 900
MAX_WAIT_POST_GATE2 = 2400

OPENAI_INPUT_USD_PER_1M = 2.50
OPENAI_OUTPUT_USD_PER_1M = 10.00
# Claude Haiku/Opus rough list pricing for cost estimate from trace tokens
CLAUDE_INPUT_USD_PER_1M = 1.00
CLAUDE_OUTPUT_USD_PER_1M = 5.00


def _railway() -> str:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found")
    return railway


def _railway_vars(*extra: str) -> dict:
    out = subprocess.check_output(
        [_railway(), "variables", "--json", *extra],
        cwd=REPO,
        text=True,
    )
    return json.loads(out)


def _bootstrap_db_env() -> None:
    pg = _railway_vars("--service", "Postgres")
    os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]


def _secret() -> str:
    return str(_railway_vars().get("TEST_MODE_SECRET") or "")


def _verify_precondition() -> dict:
    gh = subprocess.check_output(
        ["gh", "api", "repos/mycrivo/ngoinfo-grantpilot/commits/main", "--jq", ".sha"],
        cwd=REPO,
        text=True,
    ).strip()
    local = subprocess.check_output(
        ["git", "show", "HEAD:app/reports/agents/indicator_data_extractor.py"],
        cwd=REPO,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    d4_ok = (
        'ME_CLASSIFIER_TIMEOUT_SECONDS", "180")' in local
        and "MAX_EXTRACTION_ATTEMPTS = 1" in local
    )
    health = requests.get(f"{BASE_URL}/health", timeout=30)
    return {
        "github_main_sha": gh,
        "github_main_prefix": gh[:7],
        "d4_constants_in_main": d4_ok,
        "health_status": health.status_code,
        "precondition_pass": gh.startswith(EXPECTED_DEPLOY_SHA) and d4_ok,
    }


def mint_token(session: requests.Session, email: str) -> str:
    r = session.post(
        f"{BASE_URL}/api/auth/test-mode/mint",
        headers={"X-Test-Mode-Secret": _secret(), "Content-Type": "application/json"},
        json={"email": email, "full_name": "FCDO D4 F1 Walk", "plan": "FREE"},
        timeout=60,
    )
    r.raise_for_status()
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
    while time.time() < deadline:
        r = session.get(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60)
        r.raise_for_status()
        last = r.json()
        st, stage = last.get("status"), last.get("stage")
        print(
            f"  [{label}] status={st} stage={stage} error={last.get('error')!r}",
            flush=True,
        )
        if until_status and st in until_status:
            if until_stage is None or stage in until_stage:
                return last
        if st == "failed":
            return last
        time.sleep(POLL_SECONDS)
    last["_timeout"] = True
    return last


def _db_read(report_id: str) -> dict:
    _bootstrap_db_env()
    import app.models  # noqa: F401
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    rid = report_id
    with engine.connect() as c:
        docs = c.execute(
            text(
                """
                SELECT id, original_filename, classification, extraction_status, extracted_json
                FROM uploaded_documents
                WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY created_at
                """
            ),
            {"rid": rid},
        ).mappings().all()
        report = c.execute(
            text(
                """
                SELECT knowledge_bank_json, gap_analysis_json, content_json
                FROM donor_reports WHERE id = CAST(:rid AS uuid)
                """
            ),
            {"rid": rid},
        ).mappings().first()
        job = c.execute(
            text(
                """
                SELECT stage, status, agent_trace_json
                FROM report_jobs
                WHERE donor_report_id = CAST(:rid AS uuid)
                ORDER BY started_at DESC NULLS LAST LIMIT 1
                """
            ),
            {"rid": rid},
        ).mappings().first()
    return {
        "documents": [dict(d) for d in docs],
        "report": dict(report) if report else {},
        "job": dict(job) if job else {},
    }


def _substantive_gap_answer(gap: dict) -> dict:
    """Answer from BridgeLight document content or skip honestly."""
    ref = (gap.get("required_item_ref") or "").lower()
    section = gap.get("section_key") or ""
    item_type = gap.get("required_item_type") or ""

    snippets: dict[str, str] = {
        "overall_progress": (
            "Year 1 delivery remained broadly on track. OP1.1 achieved 684 girls "
            "re-enrolled against a Year 1 target of 650 (score A). OP1.2 attendance "
            "at 80%+ reached 472 against target 500 (score B). OP2.1 delivered 31 "
            "latrine stances against target 24 (score A)."
        ),
        "outcome_assessment": (
            "Outcome monitoring used term attendance registers and school safeguarding "
            "pathway checks. Supported girls' attendance and retention improved against "
            "Year 1 milestones, with variance notes recorded in the AR1 export."
        ),
        "new_evidence": (
            "Evidence includes school registers, re-entry club forms, WASH engineer "
            "certificates, mobile-money hardship grant lists, and district validation samples."
        ),
        "evaluation_progress": (
            "No standalone external evaluation was commissioned in Year 1; monitoring "
            "relied on termly indicator returns and partner spot checks."
        ),
        "evidence_base_strength": (
            "Indicator actuals are drawn from the BridgeLight AR1 export with source "
            "notes per output; attendance and financial lines include variance explanations."
        ),
        "data_quality_limitations": (
            "Review period in partner returns uses 01-Oct-24 to 30-Sep-25 while the award "
            "letter cites 15-Oct to 14-Oct; finance has not recut. Four schools submitted "
            "attendance registers late, affecting OP1.2."
        ),
        "new_risks": (
            "No new material risks beyond those in the grant risk register; menstrual "
            "health supply delays affected OP2.2 (17/20 schools)."
        ),
        "realised_assumptions": (
            "Assumption that community focal teachers would be available held in most schools; "
            "three schools lacked a female focal teacher for menstrual health training."
        ),
        "funds_not_used_as_intended_risk": (
            "No evidence of funds not used as intended; hardship grants deduplicated 16 "
            "caregiver records before payment."
        ),
        "climate_environment_risk": (
            "Lake-shore transport costs increased for OP1.1; no major climate shock "
            "stopped delivery in Year 1."
        ),
        "safeguarding_risk_where_relevant": (
            "Safeguarding referral pathways were tested in supported schools; no major "
            "incident trend reported in Year 1 monitoring returns."
        ),
        "recommendations_from_current_review": (
            "Recut finance to FCDO 15-Oct–14-Oct review window; complete menstrual health "
            "training in three remaining schools; submit late attendance registers."
        ),
        "updates_on_previous_recommendations": (
            "Previous review actions on register cleaning were partially complete; "
            "September deduplication removed double-count risk on OP1.1."
        ),
        "priorities_for_next_period": (
            "Close OP2.2 gap (17/20 schools); complete disposal bins at four latrine units; "
            "align reporting period labelling with award letter."
        ),
        "recommendations_action_plan": (
            "Owner: Programme Manager — recut AR1 period by Q1 next period; Owner: M&E — "
            "chase four schools for Term 3 registers; Owner: WASH — finish disposal bins."
        ),
        "partner_performance": (
            "District validation samples confirmed re-entry figures; late register "
            "submission from four schools affected attendance reporting."
        ),
        "supplier_consultant_performance": (
            "WASH engineer certificates received for 31 latrine stances; cement and "
            "transport over budget on OP2.1."
        ),
        "financial_delivery": (
            "Year 1 actual spend on outputs totalled GBP 694,860 against forecast "
            "GBP 653,000 across sampled lines in the AR1 export."
        ),
        "commercial_issues": (
            "Menstrual health supplies procured late, contributing to OP2.2 below milestone."
        ),
        "management_actions": (
            "FCDO review pack due per award letter; partner held district learning "
            "meetings with documented action points."
        ),
    }

    for key, text in snippets.items():
        if key in ref or key in section:
            return {"disposition": "answered", "answer_text": text}

    if item_type == "table":
        return {
            "disposition": "skipped",
            "skip_reason": "cannot_provide",
        }

    if "score" in ref or "output" in ref:
        return {
            "disposition": "answered",
            "answer_text": (
                "Output scoring is populated from the BridgeLight AR1 export with "
                "proposed scores A–C and variance explanations per indicator row."
            ),
        }

    return {
        "disposition": "skipped",
        "skip_reason": "not_applicable",
    }


def _collect_claude_tokens(payload: dict) -> tuple[int, int]:
    inp = out = 0

    def _walk(obj: object) -> None:
        nonlocal inp, out
        if isinstance(obj, dict):
            if "input_tokens" in obj and obj["input_tokens"] is not None:
                inp += int(obj["input_tokens"])
            if "output_tokens" in obj and obj["output_tokens"] is not None:
                out += int(obj["output_tokens"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(payload.get("job", {}).get("agent_trace_json"))
    for doc in payload.get("documents") or []:
        _walk(doc.get("extracted_json"))
    return inp, out


def _openai_synth_tokens(trace: dict) -> tuple[int, int]:
    synth = (trace or {}).get("stages", {}).get("synthesise", {})
    inp = int(synth.get("openai_input_tokens") or 0)
    out = int(synth.get("openai_output_tokens") or 0)
    return inp, out


def main() -> int:
    print("=== FCDO D4+F1 fresh prod walk ===", flush=True)

    pre = _verify_precondition()
    print(f"PRECONDITION {json.dumps(pre)}", flush=True)
    if not pre["precondition_pass"]:
        print("STOP: D4 fix not confirmed live on main / constants missing")
        return 1

    email = f"fcdo-d4-f1-{int(time.time())}@grantpilot-test.org"
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {mint_token(session, email)}"

    r = session.post(
        f"{BASE_URL}/api/reports",
        json={
            "reporting_period_start": "2025-04-01",
            "reporting_period_end": "2026-03-31",
            "funder_report_template_id": FCDO_TEMPLATE_ID,
        },
        timeout=60,
    )
    r.raise_for_status()
    report_id = r.json()["id"]
    print(f"CREATE report_id={report_id}", flush=True)

    doc_ids: dict[str, str] = {}
    for name in UPLOAD_FILES:
        path = DOC_DIR / name
        mime = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if name.endswith(".xlsx")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        with path.open("rb") as fh:
            ur = session.post(
                f"{BASE_URL}/api/reports/{report_id}/documents",
                files={"file": (name, fh, mime)},
                timeout=120,
            )
        ur.raise_for_status()
        doc_ids[name] = ur.json()["id"]
        print(f"UPLOAD {name} -> {doc_ids[name]}", flush=True)

    session.post(f"{BASE_URL}/api/reports/{report_id}/job", timeout=60).raise_for_status()

    gate1_job = poll_job(
        session,
        report_id,
        label="to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_WAIT_GATE1,
    )
    if gate1_job.get("status") == "failed":
        print("STOP: pipeline failed before Gate 1")
        return 1

    db1 = _db_read(report_id)
    xlsx_doc = next(
        (d for d in db1["documents"] if d["original_filename"] == XLSX_NAME),
        None,
    )
    if not xlsx_doc:
        print("STOP: xlsx document not found")
        return 1

    print(f"CLASSIFY xlsx={xlsx_doc['classification']}", flush=True)
    if xlsx_doc["classification"] != "indicator_data":
        print("STOP: xlsx not classified indicator_data")
        return 1

    ej = xlsx_doc.get("extracted_json") or {}
    struct = ej.get("structured") or {}
    trace = ej.get("agent_trace") or {}
    d4_outcome = struct.get("extraction_outcome")
    print(
        f"D4_XLSX outcome={d4_outcome} status={xlsx_doc['extraction_status']} "
        f"degraded_code={trace.get('degraded_code')} attempt_count={trace.get('attempt_count')} "
        f"latency_ms={trace.get('latency_ms')} rows={len(struct.get('indicators') or [])}",
        flush=True,
    )

    if d4_outcome == "degraded":
        print("STOP: D4 still degraded — fetch worker logs and abort synthesis")
        return 2

    extract_trace = (gate1_job.get("agent_trace_json") or {}).get("stages", {}).get(
        "extract", {}
    )
    print(f"EXTRACT_TRACE degraded_docs={extract_trace.get('degraded_documents')}", flush=True)

    kb_r = session.get(f"{BASE_URL}/api/reports/{report_id}/knowledge-bank", timeout=60)
    kb_r.raise_for_status()
    kb = kb_r.json().get("knowledge_bank_json") or kb_r.json()

    g1 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": kb},
        timeout=60,
    )
    g1.raise_for_status()
    print(f"GATE1_CONFIRM at={g1.json().get('gate1_confirmed_at')}", flush=True)

    post_g1 = poll_job(
        session,
        report_id,
        label="post-gate1",
        until_status={"awaiting_human", "failed"},
        max_seconds=MAX_WAIT_POST_GATE1,
    )
    if post_g1.get("stage") != "synthesise":
        print(f"STOP: expected synthesise halt, got {post_g1.get('stage')}")
        return 1

    db2 = _db_read(report_id)
    facts = (db2["report"].get("knowledge_bank_json") or {}).get("facts") or {}
    actual_facts = {
        k: v
        for k, v in facts.items()
        if ".actual" in k.lower() or k.lower().endswith(".actual")
        or (isinstance(v, dict) and "actual" in k.lower())
    }
    print(f"KB facts_total={len(facts)} actual_keys={len(actual_facts)}", flush=True)
    for k, v in list(actual_facts.items())[:8]:
        val = v.get("value") if isinstance(v, dict) else v
        print(f"  ACTUAL {k}={val!r}", flush=True)

    gaps = (db2["report"].get("gap_analysis_json") or {}).get("gaps") or []
    print(f"GAPS count={len(gaps)}", flush=True)

    answered: list[str] = []
    skipped: list[str] = []
    responses: dict = {}
    for g in gaps:
        key = g["item_key"]
        resp = _substantive_gap_answer(g)
        responses[key] = resp
        if resp["disposition"] == "answered":
            answered.append(key)
        else:
            skipped.append(key)

    print(f"GATE2 answered={len(answered)} skipped={len(skipped)}", flush=True)

    g2 = session.post(
        f"{BASE_URL}/api/reports/donor-reports/{report_id}/knowledge-bank/gate2/gap-responses",
        json={"responses": responses},
        timeout=180,
    )
    print(f"GATE2 status={g2.status_code} body={g2.text[:300]}", flush=True)
    if g2.status_code != 200:
        return 1
    if not g2.json().get("gate2_unlocked"):
        print("STOP: gate2 not unlocked")
        return 1

    post_g2 = poll_job(
        session,
        report_id,
        label="post-gate2-synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_WAIT_POST_GATE2,
    )
    print(
        f"FINAL_JOB stage={post_g2.get('stage')} status={post_g2.get('status')} "
        f"error={post_g2.get('error')!r}",
        flush=True,
    )

    final_db = _db_read(report_id)
    content = final_db["report"].get("content_json") or {}
    sections = content.get("sections") or []
    job_trace = final_db["job"].get("agent_trace_json") or {}

    claude_in, claude_out = _collect_claude_tokens(final_db)
    oai_in, oai_out = _openai_synth_tokens(job_trace)
    if oai_in == 0 and oai_out == 0:
        synth = job_trace.get("stages", {}).get("synthesise", {})
        oai_in = int(synth.get("openai_input_tokens") or 0)
        oai_out = int(synth.get("openai_output_tokens") or 0)

    claude_usd = (
        claude_in * CLAUDE_INPUT_USD_PER_1M / 1_000_000
        + claude_out * CLAUDE_OUTPUT_USD_PER_1M / 1_000_000
    )
    oai_usd = (
        oai_in * OPENAI_INPUT_USD_PER_1M / 1_000_000
        + oai_out * OPENAI_OUTPUT_USD_PER_1M / 1_000_000
    )

    artifact = {
        "report_id": report_id,
        "precondition": pre,
        "d4_xlsx": {
            "document_id": str(xlsx_doc["id"]),
            "classification": xlsx_doc["classification"],
            "extraction_outcome": d4_outcome,
            "attempt_count": trace.get("attempt_count"),
            "latency_ms": trace.get("latency_ms"),
            "degraded_code": trace.get("degraded_code"),
            "indicator_rows": len(struct.get("indicators") or []),
            "extracted_json": ej,
        },
        "kb": {
            "facts_total": len(facts),
            "actual_facts_sample": {
                k: (v.get("value") if isinstance(v, dict) else v)
                for k, v in list(actual_facts.items())[:15]
            },
            "all_actual_keys": list(actual_facts.keys()),
        },
        "gate2": {"answered": answered, "skipped": skipped},
        "job": {
            "stage": final_db["job"].get("stage"),
            "status": final_db["job"].get("status"),
            "agent_trace_json": job_trace,
        },
        "cost": {
            "claude_input_tokens": claude_in,
            "claude_output_tokens": claude_out,
            "claude_usd": claude_usd,
            "openai_input_tokens": oai_in,
            "openai_output_tokens": oai_out,
            "openai_usd": oai_usd,
            "total_usd": claude_usd + oai_usd,
        },
        "content_json": content,
    }

    out_path = REPO / f"FCDO_D4_F1_WALK_{report_id[:8]}.json"
    out_path.write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    print(f"ARTIFACT={out_path}", flush=True)

    print("\n=== SECTIONS (verbatim) ===", flush=True)
    for sec in sections:
        print("\n---", flush=True)
        print(f"section_key={sec.get('section_key')}", flush=True)
        print(f"label={sec.get('label')}", flush=True)
        print(f"generation_status={sec.get('generation_status')}", flush=True)
        constraints = sec.get("constraints_applied") or {}
        print(f"word_limit_respected={constraints.get('word_limit_respected')}", flush=True)
        block = sec.get("content") or {}
        print(f"evidence_used={json.dumps(block.get('evidence_used') or [])}", flush=True)
        if sec.get("generation_status") == "FAILED":
            print(f"failure_reason={sec.get('failure_reason')!r}", flush=True)
        else:
            print("FULL_TEXT_BEGIN", flush=True)
            print(block.get("text") or "", flush=True)
            print("FULL_TEXT_END", flush=True)

    print("\n=== COST ===", flush=True)
    print(json.dumps(artifact["cost"], indent=2), flush=True)

    ok = (
        d4_outcome == "complete"
        and len(actual_facts) > 0
        and final_db["job"].get("stage") == "critique"
        and len(sections) == 8
    )
    print(f"STRUCTURAL_OK={ok}", flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
