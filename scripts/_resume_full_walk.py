#!/usr/bin/env python3
"""Resume a full walk from current job stage through export."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.audit import _common as C
from scripts.audit.gap_answers import answer_gap

MAX_SYNTH = int(os.environ.get("MAX_SYNTH", "2400"))
MAX_CRITIQUE = int(os.environ.get("MAX_CRITIQUE", "1800"))
MAX_EXPORT = int(os.environ.get("MAX_EXPORT", "600"))


def main() -> int:
    report_id = sys.argv[1]
    email = sys.argv[2] if len(sys.argv) > 2 else C.owner_email_for_report(report_id)
    run = sys.argv[3] if len(sys.argv) > 3 else "resume"

    session = C.mint_session(email, plan="IMPACT", full_name=f"Resume {run}")
    job = C.poll_job(
        session,
        report_id,
        label="resume-wait",
        until_status={"awaiting_human", "failed", "done"},
        max_seconds=30,
    )
    stage = job.get("stage")
    status = job.get("status")
    print(f"RESUME at stage={stage} status={status}", flush=True)

    if status == "failed":
        print("STOP: job already failed", job.get("error"))
        return 1

    if stage in {"gap", "classify", "extract", "reconcile"}:
        job = C.poll_job(
            session,
            report_id,
            label="to-gate1",
            until_status={"awaiting_human", "failed"},
            until_stage={"gap"},
            max_seconds=MAX_SYNTH,
        )
        if job.get("status") == "failed":
            return 1
        kb = C.get_kb(session, report_id)
        C.resolve_conflicts_via_patch(session, report_id, kb)
        kb = C.get_kb(session, report_id)
        g1 = C.confirm_gate1(session, report_id, kb)
        if g1["status_code"] != 200:
            print("gate1 failed", g1)
            return 1

    if stage in {"gap", "classify", "extract", "reconcile", "synthesise"}:
        job = C.poll_job(
            session,
            report_id,
            label="to-gate2-or-synth",
            until_status={"awaiting_human", "failed"},
            until_stage={"synthesise", "critique", "export"},
            max_seconds=60,
        )
        stage = job.get("stage")

    if stage == "gap" or (
        job.get("status") == "awaiting_human" and stage == "synthesise"
    ):
        gc = C.gap_check(session, report_id)
        gaps = (
            gc["body"].get("missing_items", [])
            if isinstance(gc.get("body"), dict)
            else []
        )
        if not gaps:
            detail = C.report_detail(session, report_id)
            body = detail.get("body") if isinstance(detail.get("body"), dict) else {}
            gaps = ((body.get("gap_analysis_json") or {}).get("gaps") or [])
        responses = {g["item_key"]: answer_gap(g, snippets={}) for g in gaps}
        g2 = C.submit_gate2(session, report_id, responses)
        if g2["status_code"] != 200:
            print("gate2 failed", g2)
            return 1

    synthjob = C.poll_job(
        session,
        report_id,
        label="synth",
        until_status={"awaiting_human", "failed"},
        until_stage={"critique"},
        max_seconds=MAX_SYNTH,
    )
    if synthjob.get("status") == "failed":
        return 1

    resume = C.resume_critique(session, report_id)
    if resume["status_code"] != 200:
        print("resume_critique failed", resume)
        return 1

    g3park = C.poll_job(
        session,
        report_id,
        label="critique",
        until_status={"awaiting_human", "failed"},
        until_stage={"export"},
        max_seconds=MAX_CRITIQUE,
    )
    if g3park.get("status") == "failed":
        return 1

    accept = C.accept_all_sections(session, report_id)
    if accept["status_code"] != 200:
        print("accept_all failed", accept)
        return 1

    g3 = C.confirm_gate3(session, report_id)
    if g3["status_code"] != 200:
        print("gate3 failed", g3)
        return 1

    expjob = C.poll_job(
        session,
        report_id,
        label="export",
        until_status={"done", "failed"},
        max_seconds=MAX_EXPORT,
    )
    export = C.download_export(session, report_id)
    print("EXPORT", export, flush=True)
    if expjob.get("status") != "done" or export.get("status_code") != 200:
        return 1
    print(f"VERDICT=completed report_id={report_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
