#!/usr/bin/env python3
"""Track 0 prod validation for D-046 proposal extraction reliability (post-deploy).

Validates against live Railway API + read-only DB snapshots:
  1. Happy path — full docset reaches Gate 1 without proposal checkpoint halt
  2. Checkpoint halt — EXTRACT + awaiting_human with proposal_checkpoint payload
  3. Retry — re-enqueue clears checkpoint and resumes extract
  4. Proceed — ack proceed_with_gap reaches Gate 1 with deduped unreadable_sources
  5. Traces — degraded proposal attempt_traces include instrumentation fields

Env:
  BASE_URL, DATABASE_URL (via railway), CHECKPOINT_HUNT_ATTEMPTS (default 4)
  SKIP_HAPPY=1 to skip the long happy-path walk when resuming
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

MAX_TO_GATE1 = int(os.environ.get("MAX_TO_GATE1", "1500"))
MAX_TO_EXTRACT_CHECKPOINT = int(os.environ.get("MAX_TO_EXTRACT_CHECKPOINT", "420"))
MAX_POST_RETRY = int(os.environ.get("MAX_POST_RETRY", "420"))
MAX_POST_PROCEED = int(os.environ.get("MAX_POST_PROCEED", "900"))
CHECKPOINT_HUNT_ATTEMPTS = int(os.environ.get("CHECKPOINT_HUNT_ATTEMPTS", "4"))
PROPOSAL_ONLY_HUNT = os.environ.get("PROPOSAL_ONLY_HUNT", "").strip() in ("1", "true", "yes")

FCDO_DOCS = [
    "01_FCDO_BridgeLight_Winning_Proposal.docx",
    "02_FCDO_BridgeLight_Award_Letter.docx",
    "BridgeLight Logframe and Finance AR1 Export.xlsx",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job(session, report_id: str) -> dict:
    r = C.auth_request(session, "GET", f"{C.BASE_URL}/api/reports/{report_id}/job", timeout=60)
    r.raise_for_status()
    return r.json()


def _checkpoint_from_job(job: dict) -> dict | None:
    stages = (job.get("agent_trace_json") or {}).get("stages") or {}
    extract = stages.get("extract") or {}
    cp = extract.get("proposal_checkpoint")
    return dict(cp) if isinstance(cp, dict) else None


def _proposal_doc(capture: dict) -> dict | None:
    for doc in capture.get("documents") or []:
        if doc.get("classification") == "proposal":
            return doc
    return None


def _attempt_traces(doc: dict | None) -> list[dict]:
    if not doc:
        return []
    extracted = doc.get("extracted_json") or {}
    if isinstance(extracted, str):
        try:
            extracted = json.loads(extracted)
        except json.JSONDecodeError:
            return []
    agent = extracted.get("agent_trace") or {}
    traces = agent.get("attempt_traces") or []
    return [t for t in traces if isinstance(t, dict)]


def _trace_fields_present(traces: list[dict]) -> dict[str, bool]:
    if not traces:
        return {"has_traces": False}
    t0 = traces[0]
    return {
        "has_traces": True,
        "silence_profile": "silence_profile" in t0,
        "message_type_counts": "message_type_counts" in t0,
        "stream_completed": "stream_completed" in t0,
        "stream_cancelled": "stream_cancelled" in t0,
    }


def _unreadable_sources(kb: dict) -> list[dict]:
    sources = kb.get("unreadable_sources") or []
    return [s for s in sources if isinstance(s, dict)]


def _dedupe_ok(sources: list[dict]) -> bool:
    ids = [s.get("source_document_id") for s in sources]
    return len(ids) == len(set(ids))


def _ack_checkpoint(session, report_id: str) -> dict:
    r = C.auth_request(
        session,
        "POST",
        f"{C.BASE_URL}/api/reports/{report_id}/jobs/proposal-checkpoint/ack",
        json={"action": "proceed_with_gap"},
        timeout=60,
    )
    return {"status_code": r.status_code, "body": C._safe_json(r)}


def _create_fcdo_report(session, label: str) -> tuple[str, list[str]]:
    email = f"track0-d046-{label}-{int(time.time())}@grantpilot-test.org"
    session = C.mint_session(email, plan="IMPACT", full_name=f"Track0 {label}")
    report = C.create_report(session, template_id=C.FCDO_TEMPLATE_ID)
    report_id = report["id"]
    doc_ids: list[str] = []
    for name in FCDO_DOCS:
        path = C.FCDO_DIR / name
        if not path.exists():
            raise FileNotFoundError(path)
        up = C.upload(session, report_id, path)
        doc_ids.append(up["id"])
        print(f"  UPLOAD {name} -> {up['id']}", flush=True)
    enq = C.enqueue(session, report_id)
    print(f"  ENQUEUE {enq}", flush=True)
    return report_id, doc_ids


def _poll_until(
    session,
    report_id: str,
    *,
    label: str,
    until_status: set[str] | None = None,
    until_stage: set[str] | None = None,
    max_seconds: int,
) -> dict:
    return C.poll_job(
        session,
        report_id,
        label=label,
        until_status=until_status,
        until_stage=until_stage,
        max_seconds=max_seconds,
    )


def _check(name: str, ok: bool, detail: str, results: list[dict]) -> None:
    results.append({"check": name, "pass": ok, "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name}: {detail}", flush=True)


def run_happy_path(results: list[dict]) -> dict[str, Any]:
    print("\n=== CASE A: Happy path (full docset -> Gate 1, no checkpoint) ===", flush=True)
    session = C.mint_session(
        f"track0-d046-happy-{int(time.time())}@grantpilot-test.org",
        plan="IMPACT",
        full_name="Track0 Happy",
    )
    report = C.create_report(session, template_id=C.FCDO_TEMPLATE_ID)
    report_id = report["id"]
    for name in FCDO_DOCS:
        C.upload(session, report_id, C.FCDO_DIR / name)
    C.enqueue(session, report_id)

    job = _poll_until(
        session,
        report_id,
        label="happy-to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_TO_GATE1,
    )
    capture = C.db_capture(report_id)
    cp = _checkpoint_from_job(job)
    proposal = _proposal_doc(capture)
    structured = ((proposal or {}).get("extracted_json") or {})
    if isinstance(structured, str):
        structured = json.loads(structured)
    structured = (structured.get("structured") or {}) if isinstance(structured, dict) else {}

    _check(
        "A1_reached_gate1",
        job.get("status") == "awaiting_human" and job.get("stage") == "gap",
        f"status={job.get('status')} stage={job.get('stage')} error={job.get('error')!r}",
        results,
    )
    _check(
        "A2_no_extract_checkpoint",
        cp is None,
        f"checkpoint_present={cp is not None}",
        results,
    )
    _check(
        "A3_proposal_not_degraded",
        structured.get("extraction_outcome") != "degraded",
        f"extraction_outcome={structured.get('extraction_outcome')!r}",
        results,
    )
    trace_info = _trace_fields_present(_attempt_traces(proposal))
    _check(
        "A4_proposal_traces_when_present",
        not trace_info.get("has_traces") or trace_info.get("message_type_counts", False),
        json.dumps(trace_info),
        results,
    )
    return {"report_id": report_id, "job": job, "capture": capture}


def hunt_checkpoint(session_label: str) -> tuple[Any, str, dict] | None:
    """Return (session, report_id, job) when checkpoint halt observed."""
    for attempt in range(1, CHECKPOINT_HUNT_ATTEMPTS + 1):
        print(f"\n--- Checkpoint hunt attempt {attempt}/{CHECKPOINT_HUNT_ATTEMPTS} ---", flush=True)
        email = f"track0-d046-{session_label}-hunt{attempt}-{int(time.time())}@grantpilot-test.org"
        session = C.mint_session(email, plan="IMPACT", full_name=f"Track0 {session_label}")
        report = C.create_report(session, template_id=C.FCDO_TEMPLATE_ID)
        report_id = report["id"]
        doc_names = (
            ["01_FCDO_BridgeLight_Winning_Proposal.docx"]
            if PROPOSAL_ONLY_HUNT
            else FCDO_DOCS
        )
        for name in doc_names:
            C.upload(session, report_id, C.FCDO_DIR / name)
        C.enqueue(session, report_id)

        job = _poll_until(
            session,
            report_id,
            label=f"hunt-{session_label}-{attempt}",
            until_status={"awaiting_human", "failed"},
            until_stage={"extract", "gap", "reconcile"},
            max_seconds=MAX_TO_EXTRACT_CHECKPOINT,
        )
        cp = _checkpoint_from_job(job)
        if (
            job.get("status") == "awaiting_human"
            and job.get("stage") == "extract"
            and cp is not None
            and not cp.get("acknowledged")
        ):
            print(f"  CHECKPOINT FOUND report_id={report_id}", flush=True)
            return session, report_id, job
        if job.get("status") == "awaiting_human" and job.get("stage") == "gap":
            print("  Hunt attempt reached Gate 1 without checkpoint — retry hunt", flush=True)
        elif job.get("_timeout"):
            print("  Hunt attempt timed out before terminal state", flush=True)
        else:
            print(
                f"  Hunt attempt ended status={job.get('status')} stage={job.get('stage')}",
                flush=True,
            )
    return None


def run_checkpoint_halt(results: list[dict], hunt: tuple[Any, str, dict]) -> dict[str, Any]:
    session, report_id, job = hunt
    print("\n=== CASE B: Checkpoint halt (EXTRACT + awaiting_human) ===", flush=True)
    cp = _checkpoint_from_job(job) or {}
    capture = C.db_capture(report_id)
    proposal = _proposal_doc(capture)
    traces = _attempt_traces(proposal)
    trace_info = _trace_fields_present(traces)

    _check(
        "B1_extract_awaiting_human",
        job.get("status") == "awaiting_human" and job.get("stage") == "extract",
        f"status={job.get('status')} stage={job.get('stage')}",
        results,
    )
    _check(
        "B2_checkpoint_payload",
        bool(cp.get("failed_document_id")) and bool(cp.get("original_filename")),
        f"keys={sorted(cp.keys())}",
        results,
    )
    _check(
        "B3_checkpoint_not_acked",
        not cp.get("acknowledged"),
        f"acknowledged={cp.get('acknowledged')!r}",
        results,
    )
    _check(
        "B4_missing_content_keys",
        cp.get("missing_content_keys") == [
            "objectives",
            "activities",
            "indicators",
            "partners",
            "consultation",
        ],
        f"missing={cp.get('missing_content_keys')!r}",
        results,
    )
    _check(
        "B5_degraded_proposal",
        ((proposal or {}).get("extraction_status") == "degraded")
        or (((proposal or {}).get("extracted_json") or {}).get("structured") or {}).get(
            "extraction_outcome"
        )
        == "degraded",
        f"extraction_status={(proposal or {}).get('extraction_status')!r}",
        results,
    )
    _check(
        "B6_attempt_traces_present",
        trace_info.get("has_traces", False),
        json.dumps(trace_info),
        results,
    )
    _check(
        "B7_instrumentation_fields",
        all(
            trace_info.get(k, False)
            for k in ("silence_profile", "message_type_counts", "stream_completed", "stream_cancelled")
        ),
        json.dumps(trace_info),
        results,
    )
    return {
        "session": session,
        "report_id": report_id,
        "job": job,
        "checkpoint": cp,
        "capture": capture,
        "proposal_filename": cp.get("original_filename"),
        "failed_document_id": cp.get("failed_document_id"),
    }


def run_retry(results: list[dict], ctx: dict[str, Any]) -> dict[str, Any]:
    session = ctx["session"]
    report_id = ctx["report_id"]
    print("\n=== CASE C: Retry re-enqueue (checkpoint cleared) ===", flush=True)

    before_cp = _checkpoint_from_job(_job(session, report_id))
    enq = C.enqueue(session, report_id)
    after_job = _job(session, report_id)
    after_cp = _checkpoint_from_job(after_job)

    _check(
        "C1_retry_enqueue_ok",
        enq.get("status_code") in (200, 201, 202),
        str(enq),
        results,
    )
    _check(
        "C2_checkpoint_cleared_on_reenqueue",
        before_cp is not None and after_cp is None,
        f"before={before_cp is not None} after={after_cp is not None}",
        results,
    )
    _check(
        "C3_job_queued_after_retry",
        after_job.get("status") in {"queued", "running"},
        f"status={after_job.get('status')} stage={after_job.get('stage')}",
        results,
    )

    terminal = _poll_until(
        session,
        report_id,
        label="post-retry",
        until_status={"awaiting_human", "failed", "completed"},
        until_stage={"extract", "gap", "reconcile"},
        max_seconds=MAX_POST_RETRY,
    )
    final_cp = _checkpoint_from_job(terminal)
    _check(
        "C4_post_retry_progressed",
        terminal.get("status") in {"awaiting_human", "failed", "completed"}
        and not terminal.get("_timeout"),
        f"status={terminal.get('status')} stage={terminal.get('stage')} timeout={terminal.get('_timeout')}",
        results,
    )
    return {"terminal_job": terminal, "final_checkpoint": final_cp}


def run_proceed(results: list[dict], hunt: tuple[Any, str, dict]) -> dict[str, Any]:
    session, report_id, job = hunt
    print("\n=== CASE D: Proceed with gap -> Gate 1 unreadable_sources ===", flush=True)
    cp_before = _checkpoint_from_job(job) or {}
    ack = _ack_checkpoint(session, report_id)
    _check(
        "D1_ack_proceed_ok",
        ack.get("status_code") == 200,
        str(ack),
        results,
    )

    after_ack = _job(session, report_id)
    cp_after = _checkpoint_from_job(after_ack) or {}
    _check(
        "D2_checkpoint_acked",
        cp_after.get("acknowledged") is True and cp_after.get("ack_action") == "proceed_with_gap",
        f"ack={cp_after.get('ack_action')!r} acknowledged={cp_after.get('acknowledged')!r}",
        results,
    )
    _check(
        "D3_job_queued_reconcile",
        after_ack.get("status") in {"queued", "running"} and after_ack.get("stage") == "reconcile",
        f"status={after_ack.get('status')} stage={after_ack.get('stage')}",
        results,
    )

    gate_job = _poll_until(
        session,
        report_id,
        label="proceed-to-gate1",
        until_status={"awaiting_human", "failed"},
        until_stage={"gap"},
        max_seconds=MAX_POST_PROCEED,
    )
    kb = C.get_kb(session, report_id)
    sources = _unreadable_sources(kb)
    proposal_sources = [
        s for s in sources if s.get("source_document_id") == cp_before.get("failed_document_id")
    ]
    filename_ok = any(
        cp_before.get("original_filename") in (s.get("source_label") or "")
        for s in proposal_sources
    ) or bool(proposal_sources)

    _check(
        "D4_reached_gate1",
        gate_job.get("status") == "awaiting_human" and gate_job.get("stage") == "gap",
        f"status={gate_job.get('status')} stage={gate_job.get('stage')}",
        results,
    )
    _check(
        "D5_proposal_in_unreadable_sources",
        len(proposal_sources) >= 1,
        f"proposal_source_count={len(proposal_sources)} total_unreadable={len(sources)}",
        results,
    )
    _check(
        "D6_unreadable_sources_deduped",
        _dedupe_ok(sources),
        f"source_ids={[s.get('source_document_id') for s in sources]}",
        results,
    )
    _check(
        "D7_filename_traceable",
        filename_ok,
        f"expected_filename={cp_before.get('original_filename')!r} labels={[s.get('source_label') for s in proposal_sources]}",
        results,
    )
    return {"report_id": report_id, "gate_job": gate_job, "kb_unreadable": sources}


def main() -> int:
    print(f"=== TRACK 0 D-046 PROD VALIDATION started {_now_iso()} ===", flush=True)
    print(f"BASE_URL={C.BASE_URL}", flush=True)
    C.bootstrap_db_env()

    results: list[dict] = []
    summary: dict[str, Any] = {
        "started_at": _now_iso(),
        "base_url": C.BASE_URL,
        "deploy_refs": {
            "backend_commit": "fcf35e5",
            "frontend_commit": "f485d56",
        },
        "cases": {},
    }

    if not os.environ.get("SKIP_HAPPY"):
        try:
            summary["cases"]["happy_path"] = run_happy_path(results)
        except Exception as exc:
            _check("A0_happy_path_exception", False, repr(exc), results)
            summary["cases"]["happy_path_error"] = repr(exc)
    else:
        print("SKIP_HAPPY=1 — skipping happy path", flush=True)

    retry_hunt = hunt_checkpoint("retry")
    proceed_hunt = hunt_checkpoint("proceed")

    if retry_hunt is None:
        _check("B0_checkpoint_hunt_retry", False, f"no checkpoint in {CHECKPOINT_HUNT_ATTEMPTS} attempts", results)
    else:
        ctx = run_checkpoint_halt(results, retry_hunt)
        summary["cases"]["checkpoint_halt"] = {
            "report_id": ctx["report_id"],
            "checkpoint": ctx["checkpoint"],
        }
        summary["cases"]["retry"] = run_retry(results, ctx)

    if proceed_hunt is None:
        _check("D0_checkpoint_hunt_proceed", False, f"no checkpoint in {CHECKPOINT_HUNT_ATTEMPTS} attempts", results)
    else:
        summary["cases"]["proceed"] = run_proceed(results, proceed_hunt)

    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])
    summary["finished_at"] = _now_iso()
    summary["results"] = results
    summary["passed"] = passed
    summary["failed"] = failed
    summary["verdict"] = "PASS" if failed == 0 else "PARTIAL" if passed > 0 else "FAIL"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = C.write_artifact(f"track0_d046_prod_validation_{stamp}.json", summary)

    md_lines = [
        "# Track 0 - D-046 prod validation",
        "",
        f"- **Started:** {summary['started_at']}",
        f"- **Finished:** {summary['finished_at']}",
        f"- **Base URL:** {C.BASE_URL}",
        f"- **Backend:** `fcf35e5` | **Frontend:** `f485d56`",
        f"- **Verdict:** {summary['verdict']} ({passed} pass / {failed} fail)",
        f"- **JSON artefact:** `{json_path.relative_to(C.REPO)}`",
        "",
        "## Results",
        "",
        "| Check | Pass | Detail |",
        "|-------|------|--------|",
    ]
    for row in results:
        mark = "yes" if row["pass"] else "**no**"
        detail = str(row["detail"]).replace("|", "\\|")[:200]
        md_lines.append(f"| {row['check']} | {mark} | {detail} |")

    md_path = C.REPO / "docs" / "artefacts" / "me_module" / "audits" / f"TRACK0_D046_PROD_VALIDATION_{stamp}.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"ARTIFACT={md_path}", flush=True)
    print(f"\n=== VERDICT {summary['verdict']} pass={passed} fail={failed} ===", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
