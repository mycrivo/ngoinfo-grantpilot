#!/usr/bin/env python3
"""Resume Phase 2 answered branch as the report owner."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.audit import _common as C
from scripts.audit.gap_answers import answer_gap
from scripts.audit.track3_phase2_witnessed_walk import (
    ANSWER_TEXT,
    ELEVATED_KEYS,
    ELEVATED_REFS,
    LOG_PATH,
    MAX_CRITIQUE,
    MAX_EXPORT,
    MAX_SYNTH,
    MAX_TO_GATE1,
    MAX_TO_GATE2,
    _Tee,
    _ack_proceed,
    _assert_elevation,
    _checkpoint_from_job,
    _community_section,
    _extract_stage,
    _gaps_from_capture,
)

REPORT_ID = "b007f125-cf33-4bba-8acf-6eccde27d063"


def main() -> int:
    log_fh = LOG_PATH.open("a", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, log_fh)
    sys.stderr = _Tee(sys.__stderr__, log_fh)
    print(f"\nRESUME_ANSWERED start {datetime.now(timezone.utc).isoformat()}", flush=True)
    C.bootstrap_db_env()
    t0 = time.time()
    email = C.owner_email_for_report(REPORT_ID)
    print(f"OWNER_EMAIL={email}", flush=True)
    session = C.mint_session(email, plan="IMPACT", full_name="Track3P2 answered resume")

    r = C.auth_request(
        session, "GET", f"{C.BASE_URL}/api/reports/{REPORT_ID}/job", timeout=60
    )
    print(f"JOB_GET status={r.status_code}", flush=True)
    r.raise_for_status()
    job = r.json()
    cp = _checkpoint_from_job(job)
    extract_stage = _extract_stage(job)
    checkpoint_block = {
        "job_status": job.get("status"),
        "job_stage": job.get("stage"),
        "checkpoint": cp,
        "extract_stage_fault_injected": extract_stage.get("proposal_fault_injected"),
        "extract_stage_fault_flag": extract_stage.get("proposal_fault_flag"),
        "extract_stage": extract_stage,
        "resumed": True,
    }
    print(f"CHECKPOINT_STATE {json.dumps(checkpoint_block, default=str)[:5000]}", flush=True)

    if (
        job.get("status") == "awaiting_human"
        and job.get("stage") == "extract"
        and cp
        and not cp.get("acknowledged")
    ):
        ack = _ack_proceed(session, REPORT_ID)
        print(f"ACK_PROCEED {ack}", flush=True)
        checkpoint_block["ack"] = ack
    else:
        print(
            f"SKIP_ACK status={job.get('status')} stage={job.get('stage')} "
            f"acked={None if not cp else cp.get('acknowledged')}",
            flush=True,
        )

    g1job = C.poll_job(
        session,
        REPORT_ID,
        label="to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_TO_GATE1,
    )
    if g1job.get("status") == "failed" or g1job.get("_timeout"):
        print("FAIL gate1", g1job, flush=True)
        return 1

    kb = C.get_kb(session, REPORT_ID)
    n = C.resolve_conflicts(kb)
    g1 = C.confirm_gate1(session, REPORT_ID, kb)
    print(f"GATE1 conflicts_resolved={n} confirm={g1['status_code']}", flush=True)

    g2park = C.poll_job(
        session,
        REPORT_ID,
        label="to-gate2",
        until_status={"awaiting_human", "failed"},
        until_stage={"synthesise"},
        max_seconds=MAX_TO_GATE2,
    )
    after_gap = C.db_capture(REPORT_ID)
    gc = C.gap_check(session, REPORT_ID)
    gaps = _gaps_from_capture(after_gap)
    if not gaps and isinstance(gc.get("body"), dict):
        gaps = gc["body"].get("missing_items") or gc["body"].get("gaps") or gaps
    elevation = _assert_elevation(gaps)
    print(
        "ELEVATION "
        + json.dumps({k: elevation[k] for k in elevation if k != "raw_elevated"}, default=str),
        flush=True,
    )

    responses = {}
    for g in gaps:
        key = g["item_key"]
        ref = g.get("required_item_ref") or ""
        if ref in ELEVATED_REFS or key in ELEVATED_KEYS:
            if ref == ELEVATED_REFS[1] or key.endswith(ELEVATED_REFS[1]):
                text = ANSWER_TEXT[ELEVATED_REFS[1]]
            else:
                text = ANSWER_TEXT[ELEVATED_REFS[0]]
            responses[key] = {"disposition": "answered", "answer_text": text}
        else:
            responses[key] = answer_gap(g, snippets={})

    g2 = C.submit_gate2(session, REPORT_ID, responses)
    print(f"GATE2_SUBMIT {g2['status_code']}", flush=True)

    synthjob = C.poll_job(
        session,
        REPORT_ID,
        label="synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_SYNTH,
    )
    if synthjob.get("status") == "failed":
        result = {
            "branch": "answered",
            "report_id": REPORT_ID,
            "owner_email": email,
            "verdict": "failed_at_synthesis",
            "checkpoint": checkpoint_block,
            "elevation": elevation,
            "induced": True,
            "duration_seconds": round(time.time() - t0, 1),
            "cost": C.cost_summary(C.db_capture(REPORT_ID)),
        }
    else:
        resume = C.resume_critique(session, REPORT_ID)
        g3park = C.poll_job(
            session,
            REPORT_ID,
            label="critique",
            until_status={"awaiting_human", "failed"},
            until_stage={"export"},
            max_seconds=MAX_CRITIQUE,
        )
        accept = C.accept_all_sections(session, REPORT_ID)
        g3 = C.confirm_gate3(session, REPORT_ID)
        expjob = C.poll_job(
            session,
            REPORT_ID,
            label="export",
            until_status={"done", "failed"},
            max_seconds=MAX_EXPORT,
        )
        dl = C.download_export(session, REPORT_ID)
        final = C.db_capture(REPORT_ID)
        detail = C.report_detail(session, REPORT_ID)
        content = None
        if isinstance(detail.get("body"), dict):
            content = detail["body"].get("content_json")
        if content is None and isinstance(final.get("report"), dict):
            content = final["report"].get("content_json")
        community = _community_section(content if isinstance(content, dict) else None)
        community_checks = {"section_present": community is not None}
        if isinstance(community, dict):
            prose = json.dumps(community, default=str)
            community_checks["contains_participation_marker"] = (
                "TRACK3_P2_ANSWERED_COMMUNITY_PARTICIPATION_MARKER" in prose
            )
            community_checks["contains_partner_marker"] = (
                "TRACK3_P2_ANSWERED_PARTNER_COLLAB_MARKER" in prose
            )
            community_checks["has_gap_provenance"] = "gap:" in prose
            community_checks["status"] = community.get("status") or community.get(
                "structured_bind_status"
            )
        verdict = "completed" if expjob.get("status") == "done" else "export_incomplete"
        if not elevation.get("exact_two"):
            verdict = "elevation_mismatch_" + verdict
        result = {
            "branch": "answered",
            "report_id": REPORT_ID,
            "owner_email": email,
            "verdict": verdict,
            "induced": True,
            "checkpoint": checkpoint_block,
            "elevation": elevation,
            "gap_count": len(gaps),
            "gate2_submit": g2,
            "export": dl,
            "export_job_status": expjob.get("status"),
            "community_checks": community_checks,
            "cost": C.cost_summary(final),
            "duration_seconds": round(time.time() - t0, 1),
            "resume_critique": resume,
            "accept_all": accept,
            "gate3": g3,
            "g3park_status": g3park.get("status"),
            "g2park_status": g2park.get("status"),
            "client_note": "resumed as owner after stuck poll; first prod checkpoint already in DB",
        }

    out = Path(
        f"docs/artefacts/me_module/audits/TRACK3_PHASE2_ANSWERED_{REPORT_ID[:8]}.json"
    )
    out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"BRANCH_EVIDENCE={out}", flush=True)
    print(f"VERDICT={result.get('verdict')}", flush=True)
    return 0 if result.get("verdict") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
