#!/usr/bin/env python3
"""Track 3 Phase 2 witnessed walk — fault flag already ON on worker.

Uses normal NLCF docset; flag forces proposal timeout-degrade → checkpoint.
Runs one branch per invocation (BRANCH=answered|skip).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.audit import _common as C
from scripts.audit.gap_answers import answer_gap

REPO = C.REPO
EVIDENCE_DIR = REPO / "docs" / "artefacts" / "me_module" / "audits"
LOG_PATH = EVIDENCE_DIR / "TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log"

ELEVATED_REFS = (
    "community_participation_examples",
    "partner_or_local_collaboration_examples",
)
ELEVATED_KEYS = tuple(f"community_involvement:indicator:{ref}" for ref in ELEVATED_REFS)
ANSWER_TEXT = {
    "community_participation_examples": (
        "TRACK3_P2_ANSWERED_COMMUNITY_PARTICIPATION_MARKER: residents co-designed "
        "three evening workshops in July 2026 and kept attendance registers."
    ),
    "partner_or_local_collaboration_examples": (
        "TRACK3_P2_ANSWERED_PARTNER_COLLAB_MARKER: partnership with Southbank "
        "Community Trust delivered shared volunteer rota and joint outreach."
    ),
}

NLCF_DOCS = [
    C.NLCF_DIR / "01_NLCF_Southbank_Application_Proposal.docx",
    C.NLCF_DIR / "02_NLCF_Southbank_Award_Letter.docx",
    C.NLCF_DIR / "03_NLCF_Southbank_Monitoring_and_Spend_Table.docx",
]

MAX_TO_CHECKPOINT = int(os.environ.get("MAX_TO_CHECKPOINT", "900"))
MAX_TO_GATE1 = int(os.environ.get("MAX_TO_GATE1", "1500"))
MAX_TO_GATE2 = int(os.environ.get("MAX_TO_GATE2", "900"))
MAX_SYNTH = int(os.environ.get("MAX_SYNTH", "2400"))
MAX_CRITIQUE = int(os.environ.get("MAX_CRITIQUE", "1800"))
MAX_EXPORT = int(os.environ.get("MAX_EXPORT", "600"))


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> int:
        for s in self.streams:
            s.write(data)
            s.flush()
        return len(data)

    def flush(self) -> None:
        for s in self.streams:
            s.flush()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_from_job(job: dict) -> dict | None:
    stages = (job.get("agent_trace_json") or {}).get("stages") or {}
    extract = stages.get("extract") or {}
    cp = extract.get("proposal_checkpoint")
    return dict(cp) if isinstance(cp, dict) else None


def _extract_stage(job: dict) -> dict:
    stages = (job.get("agent_trace_json") or {}).get("stages") or {}
    extract = stages.get("extract") or {}
    return dict(extract) if isinstance(extract, dict) else {}


def _ack_proceed(session, report_id: str) -> dict:
    r = C.auth_request(
        session,
        "POST",
        f"{C.BASE_URL}/api/reports/{report_id}/jobs/proposal-checkpoint/ack",
        json={"action": "proceed_with_gap"},
        timeout=60,
    )
    return {"status_code": r.status_code, "body": C._safe_json(r)}


def _gaps_from_capture(capture: dict) -> list[dict]:
    report = capture.get("report") or {}
    gaps = ((report.get("gap_analysis_json") or {}).get("gaps") or [])
    return [g for g in gaps if isinstance(g, dict)]


def _elevated_subset(gaps: list[dict]) -> list[dict]:
    out = []
    for g in gaps:
        ref = g.get("required_item_ref") or ""
        key = g.get("item_key") or ""
        if ref in ELEVATED_REFS or key in ELEVATED_KEYS:
            out.append(g)
    return out


def _assert_elevation(gaps: list[dict]) -> dict:
    elevated = _elevated_subset(gaps)
    refs = sorted({g.get("required_item_ref") for g in elevated})
    questions = [g.get("question") or g.get("gap_question") or "" for g in elevated]
    leaks = []
    for q in questions:
        for token in ELEVATED_REFS + ("item_key", "fact:", "gap:"):
            if token in (q or ""):
                leaks.append({"question": q, "token": token})
    both = set(ELEVATED_REFS).issubset(set(refs)) and len(elevated) == 2
    return {
        "elevated_count": len(elevated),
        "elevated_refs": refs,
        "questions": questions,
        "exact_two": both,
        "internal_identifier_leaks": leaks,
        "raw_elevated": elevated,
    }


def _community_section(content_json: dict | None) -> dict | None:
    if not isinstance(content_json, dict):
        return None
    sections = content_json.get("sections") or content_json.get("report_sections") or []
    if isinstance(sections, dict):
        return sections.get("community_involvement")
    for s in sections:
        if isinstance(s, dict) and s.get("section_key") == "community_involvement":
            return s
    return content_json.get("community_involvement")


def run_branch(branch: str) -> dict:
    t0 = time.time()
    run_label = f"track3-p2-{branch}-{int(time.time())}"
    email = f"audit-{run_label}@grantpilot-test.org"
    session = C.mint_session(
        email, plan=os.environ.get("PLAN", "IMPACT"), full_name=f"Track3P2 {branch}"
    )
    report = C.create_report(session, template_id=C.NLCF_TEMPLATE_ID)
    report_id = report["id"]
    print(f"=== BRANCH {branch} report_id={report_id} ===", flush=True)

    for path in NLCF_DOCS:
        if not path.exists():
            raise FileNotFoundError(path)
        up = C.upload(session, report_id, path)
        print(f"UPLOAD {path.name} -> {up.get('id')}", flush=True)

    enq = C.enqueue(session, report_id)
    print(f"ENQUEUE {enq}", flush=True)

    job = C.poll_job(
        session,
        report_id,
        label=f"{branch}-checkpoint",
        until_status={"awaiting_human", "failed"},
        until_stage={"extract", "gap", "reconcile"},
        max_seconds=MAX_TO_CHECKPOINT,
    )
    cp = _checkpoint_from_job(job)
    extract_stage = _extract_stage(job)
    checkpoint_block = {
        "job_status": job.get("status"),
        "job_stage": job.get("stage"),
        "timeout": bool(job.get("_timeout")),
        "checkpoint": cp,
        "extract_stage_fault_injected": extract_stage.get("proposal_fault_injected"),
        "extract_stage_fault_flag": extract_stage.get("proposal_fault_flag"),
        "extract_stage": extract_stage,
    }
    print(f"CHECKPOINT_STATE {json.dumps(checkpoint_block, default=str)[:4000]}", flush=True)

    if not (
        job.get("status") == "awaiting_human"
        and job.get("stage") == "extract"
        and cp
        and not cp.get("acknowledged")
    ):
        return {
            "branch": branch,
            "report_id": report_id,
            "owner_email": email,
            "verdict": "checkpoint_not_observed",
            "checkpoint": checkpoint_block,
            "duration_seconds": round(time.time() - t0, 1),
            "job": job,
            "induced": True,
        }

    ack = _ack_proceed(session, report_id)
    print(f"ACK_PROCEED {ack}", flush=True)
    checkpoint_block["ack"] = ack

    g1job = C.poll_job(
        session,
        report_id,
        label=f"{branch}-to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_TO_GATE1,
    )
    if g1job.get("status") == "failed" or g1job.get("_timeout"):
        return {
            "branch": branch,
            "report_id": report_id,
            "owner_email": email,
            "verdict": "failed_before_gate1",
            "checkpoint": checkpoint_block,
            "job": g1job,
            "duration_seconds": round(time.time() - t0, 1),
            "induced": True,
        }

    kb = C.get_kb(session, report_id)
    n_resolved = C.resolve_conflicts(kb)
    g1 = C.confirm_gate1(session, report_id, kb)
    print(f"GATE1 conflicts_resolved={n_resolved} confirm={g1['status_code']}", flush=True)

    g2park = C.poll_job(
        session,
        report_id,
        label=f"{branch}-to-gate2",
        until_status={"awaiting_human", "failed"},
        until_stage={"synthesise"},
        max_seconds=MAX_TO_GATE2,
    )
    after_gap = C.db_capture(report_id)
    gc = C.gap_check(session, report_id)
    gaps = _gaps_from_capture(after_gap)
    if not gaps and isinstance(gc.get("body"), dict):
        gaps = gc["body"].get("missing_items") or gc["body"].get("gaps") or gaps

    elevation = _assert_elevation(gaps)
    print(
        "ELEVATION "
        + json.dumps({k: elevation[k] for k in elevation if k != "raw_elevated"}, default=str),
        flush=True,
    )

    responses: dict[str, Any] = {}
    for g in gaps:
        key = g["item_key"]
        ref = g.get("required_item_ref") or ""
        if branch == "answered" and (ref in ELEVATED_REFS or key in ELEVATED_KEYS):
            if ref == ELEVATED_REFS[1] or key.endswith(ELEVATED_REFS[1]):
                text = ANSWER_TEXT[ELEVATED_REFS[1]]
            else:
                text = ANSWER_TEXT[ELEVATED_REFS[0]]
            responses[key] = {"disposition": "answered", "answer_text": text}
        elif branch == "skip" and (ref in ELEVATED_REFS or key in ELEVATED_KEYS):
            responses[key] = {"disposition": "skipped", "skip_reason": "cannot_provide"}
        else:
            responses[key] = answer_gap(g, snippets={})

    g2 = C.submit_gate2(session, report_id, responses)
    print(f"GATE2_SUBMIT {g2['status_code']}", flush=True)

    synthjob = C.poll_job(
        session,
        report_id,
        label=f"{branch}-synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_SYNTH,
    )
    if synthjob.get("status") == "failed":
        return {
            "branch": branch,
            "report_id": report_id,
            "owner_email": email,
            "verdict": "failed_at_synthesis",
            "checkpoint": checkpoint_block,
            "elevation": elevation,
            "gaps": gaps,
            "job": synthjob,
            "duration_seconds": round(time.time() - t0, 1),
            "cost": C.cost_summary(C.db_capture(report_id)),
            "induced": True,
        }

    resume = C.resume_critique(session, report_id)
    g3park = C.poll_job(
        session,
        report_id,
        label=f"{branch}-critique",
        until_status={"awaiting_human", "failed"},
        until_stage={"export"},
        max_seconds=MAX_CRITIQUE,
    )
    accept = C.accept_all_sections(session, report_id)
    g3 = C.confirm_gate3(session, report_id)
    expjob = C.poll_job(
        session,
        report_id,
        label=f"{branch}-export",
        until_status={"done", "failed"},
        max_seconds=MAX_EXPORT,
    )
    dl = C.download_export(session, report_id)
    final = C.db_capture(report_id)
    detail = C.report_detail(session, report_id)
    content = None
    if isinstance(detail.get("body"), dict):
        content = detail["body"].get("content_json")
    if content is None and isinstance(final.get("report"), dict):
        content = final["report"].get("content_json")
    community = _community_section(content if isinstance(content, dict) else None)

    community_checks: dict[str, Any] = {"section_present": community is not None}
    if isinstance(community, dict):
        prose = json.dumps(community, default=str)
        community_checks["status"] = community.get("status") or community.get(
            "bind_status"
        ) or community.get("structured_bind_status")
        if branch == "answered":
            community_checks["contains_participation_marker"] = (
                "TRACK3_P2_ANSWERED_COMMUNITY_PARTICIPATION_MARKER" in prose
            )
            community_checks["contains_partner_marker"] = (
                "TRACK3_P2_ANSWERED_PARTNER_COLLAB_MARKER" in prose
            )
            community_checks["has_gap_provenance"] = "gap:" in prose
        else:
            community_checks["insufficient_data"] = (
                community_checks["status"] == "insufficient_data"
                or community.get("structured_bind_status") == "insufficient_data"
            )
            community_checks["invented_markers_absent"] = (
                "TRACK3_P2_ANSWERED_COMMUNITY_PARTICIPATION_MARKER" not in prose
                and "TRACK3_P2_ANSWERED_PARTNER_COLLAB_MARKER" not in prose
            )

    verdict = "completed" if expjob.get("status") == "done" else "export_incomplete"
    if not elevation.get("exact_two"):
        verdict = "elevation_mismatch_" + verdict

    return {
        "branch": branch,
        "report_id": report_id,
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
    }


def main() -> int:
    branch = os.environ.get("BRANCH", "answered").strip().lower()
    if branch not in ("answered", "skip"):
        print("BRANCH must be answered|skip", file=sys.stderr)
        return 2

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    log_fh = LOG_PATH.open("a", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, log_fh)
    sys.stderr = _Tee(sys.__stderr__, log_fh)

    print(f"\nTRACK3_PHASE2_WALK branch={branch} start {_now()}", flush=True)
    C.bootstrap_db_env()
    result = run_branch(branch)
    out = EVIDENCE_DIR / f"TRACK3_PHASE2_{branch.upper()}_{result['report_id'][:8]}.json"
    out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"BRANCH_EVIDENCE={out}", flush=True)
    print(f"VERDICT={result.get('verdict')} duration={result.get('duration_seconds')}", flush=True)
    return 0 if result.get("verdict", "").startswith("completed") or result.get("verdict") == "completed" else 1


if __name__ == "__main__":
    # completed or elevation_mismatch_completed both non-zero? treat exact completed as 0
    raise SystemExit(main())
