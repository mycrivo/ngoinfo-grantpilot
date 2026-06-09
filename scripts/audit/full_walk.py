#!/usr/bin/env python3
"""Full engine walk for the dynamic audit.

Drives a report through the live engine over HTTP, capturing DB snapshots at
every stage boundary. The synthesis->export tail uses production API routes
(resume-critique, accept-all, gate3 confirm).

Env config:
  AUDIT_RUN      label for the run (default fcdo_full)
  TEMPLATE       fcdo | nlcf            (default fcdo)
  DOCSET         comma list of filenames under the template dir, or 'default'
  STOP_AT        gate1 | gate2 | critique | export   (default export)
  PLAN           FREE | PRO ...         (default FREE)
"""

from __future__ import annotations

import os
import sys
import time

from scripts.audit import _common as C
from scripts.audit.gap_answers import answer_gap

MAX_TO_GATE1 = int(os.environ.get("MAX_TO_GATE1", "1500"))
MAX_TO_GATE2 = int(os.environ.get("MAX_TO_GATE2", "900"))
MAX_SYNTH = int(os.environ.get("MAX_SYNTH", "2400"))
MAX_CRITIQUE = int(os.environ.get("MAX_CRITIQUE", "1800"))
MAX_EXPORT = int(os.environ.get("MAX_EXPORT", "600"))

DEFAULT_DOCSETS = {
    "fcdo": (C.FCDO_DIR, [
        "01_FCDO_BridgeLight_Winning_Proposal.docx",
        "02_FCDO_BridgeLight_Award_Letter.docx",
        "BridgeLight Logframe and Finance AR1 Export.xlsx",
    ]),
    "nlcf": (C.NLCF_DIR, [
        "01_NLCF_Southbank_Application_Proposal.docx",
        "02_NLCF_Southbank_Award_Letter.docx",
        "03_NLCF_Southbank_Monitoring_and_Spend_Table.docx",
    ]),
}

# Genuine pass verdicts — anything else fails the process (CI must go red).
PASSING_VERDICTS = frozenset({"completed", "stopped_at_gate1"})


def exit_code_for_verdict(verdict: str) -> int:
    if verdict in PASSING_VERDICTS:
        return 0
    print(
        f"WALK_FAIL verdict={verdict} (non-passing — step exit 1 for CI)",
        flush=True,
    )
    return 1


def main() -> int:
    run = os.environ.get("AUDIT_RUN", "fcdo_full")
    template = os.environ.get("TEMPLATE", "fcdo").lower()
    stop_at = os.environ.get("STOP_AT", "export").lower()
    plan = os.environ.get("PLAN", "IMPACT")
    template_id = C.FCDO_TEMPLATE_ID if template == "fcdo" else C.NLCF_TEMPLATE_ID

    doc_dir, names = DEFAULT_DOCSETS[template]
    if os.environ.get("DOCSET") and os.environ["DOCSET"] != "default":
        names = [n.strip() for n in os.environ["DOCSET"].split(",") if n.strip()]

    print(f"=== AUDIT RUN {run} template={template} stop_at={stop_at} ===", flush=True)
    snapshots: dict = {}
    resume_id = os.environ.get("RESUME_REPORT_ID")

    if resume_id:
        email = C.owner_email_for_report(resume_id)
        session = C.mint_session(email, plan=plan, full_name=f"Audit {run}")
        report_id = resume_id
        print(f"RESUME report_id={report_id} owner={email}", flush=True)
        snapshots["after_reconcile"] = C.db_capture(report_id)
    else:
        email = f"audit-{run}-{int(time.time())}@grantpilot-test.org"
        session = C.mint_session(email, plan=plan, full_name=f"Audit {run}")
        report = C.create_report(session, template_id=template_id)
        report_id = report["id"]
        print(f"CREATE report_id={report_id} status={report.get('status')}", flush=True)

        for name in names:
            cand = doc_dir / name
            if cand.exists():
                path = cand
            elif (C.REPO / name).exists():
                path = C.REPO / name
            elif os.path.isabs(name) and os.path.exists(name):
                from pathlib import Path as _P
                path = _P(name)
            else:
                print(f"STOP: missing doc {name}", flush=True)
                return 1
            up = C.upload(session, report_id, path)
            print(f"UPLOAD {name} -> {up['id']} mime={up.get('mime_type')}", flush=True)

        enq = C.enqueue(session, report_id)
        print(f"ENQUEUE {enq}", flush=True)

        g1job = C.poll_job(session, report_id, label="to-gate1",
                           until_status={"awaiting_human", "failed"}, until_stage={"gap"},
                           max_seconds=MAX_TO_GATE1)
        snapshots["after_reconcile"] = C.db_capture(report_id)
        if g1job.get("status") == "failed":
            return exit_code_for_verdict(
                _finish(run, report_id, snapshots, verdict="failed_before_gate1", job=g1job)
            )
        if g1job.get("_timeout"):
            return exit_code_for_verdict(
                _finish(run, report_id, snapshots, verdict="timeout_before_gate1", job=g1job)
            )
        if stop_at == "gate1":
            return exit_code_for_verdict(
                _finish(run, report_id, snapshots, verdict="stopped_at_gate1", job=g1job)
            )

    kb = C.get_kb(session, report_id)
    n_resolved = C.resolve_conflicts(kb)
    print(f"GATE1 conflicts_resolved={n_resolved}", flush=True)
    g1 = C.confirm_gate1(session, report_id, kb)
    print(f"GATE1_CONFIRM {g1['status_code']}", flush=True)
    if g1["status_code"] != 200:
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="gate1_confirm_failed", extra={"gate1": g1})
        )

    g2park = C.poll_job(session, report_id, label="to-gate2",
                        until_status={"awaiting_human", "failed"}, until_stage={"synthesise"},
                        max_seconds=MAX_TO_GATE2)
    snapshots["after_gap"] = C.db_capture(report_id)
    gc = C.gap_check(session, report_id)
    print(f"GAP_CHECK status={gc['status_code']} "
          f"items={len(gc['body'].get('missing_items', [])) if isinstance(gc['body'], dict) else 'n/a'}",
          flush=True)
    snapshots["gap_check_endpoint"] = gc
    if g2park.get("status") == "failed":
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="failed_at_gap", job=g2park)
        )

    after_gap = snapshots.get("after_gap") or {}
    if isinstance(after_gap.get("report"), dict):
        gaps = ((after_gap["report"].get("gap_analysis_json") or {}).get("gaps") or [])
    else:
        detail = C.report_detail(session, report_id)
        body = detail.get("body") if isinstance(detail.get("body"), dict) else {}
        gaps = ((body.get("gap_analysis_json") or {}).get("gaps") or [])
        snapshots["after_gap_report_api"] = detail
    responses = {}
    answered = skipped = 0
    for g in gaps:
        resp = answer_gap(g, snippets=None if template == "fcdo" else {})
        responses[g["item_key"]] = resp
        if resp["disposition"] == "answered":
            answered += 1
        else:
            skipped += 1
    print(f"GATE2 gaps={len(gaps)} answered={answered} skipped={skipped}", flush=True)

    if stop_at == "gate2":
        return exit_code_for_verdict(
            _finish(
                run,
                report_id,
                snapshots,
                verdict="stopped_at_gate2",
                extra={
                    "gaps": len(gaps),
                    "answered": answered,
                    "skipped": skipped,
                    "gap_list": gaps,
                },
            )
        )

    g2 = C.submit_gate2(session, report_id, responses)
    print(f"GATE2_SUBMIT status={g2['status_code']} "
          f"unlocked={g2['body'].get('gate2_unlocked') if isinstance(g2['body'], dict) else 'n/a'}",
          flush=True)
    if g2["status_code"] != 200 or not (isinstance(g2["body"], dict) and g2["body"].get("gate2_unlocked")):
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="gate2_not_unlocked", extra={"gate2": g2})
        )

    synthjob = C.poll_job(session, report_id, label="synth",
                          until_status={"awaiting_human", "failed"}, until_stage={"critique"},
                          max_seconds=MAX_SYNTH)
    snapshots["after_synthesis"] = C.db_capture(report_id)
    if synthjob.get("status") == "failed":
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="failed_at_synthesis", job=synthjob)
        )
    if stop_at == "critique" or synthjob.get("_timeout"):
        return exit_code_for_verdict(
            _finish(
                run,
                report_id,
                snapshots,
                verdict="stopped_at_critique_boundary"
                if not synthjob.get("_timeout")
                else "timeout_synth",
                job=synthjob,
            )
        )

    resume = C.resume_critique(session, report_id)
    print(f"RESUME_CRITIQUE {resume['status_code']}", flush=True)
    if resume["status_code"] != 200:
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="resume_critique_failed", extra={"resume": resume})
        )

    g3park = C.poll_job(session, report_id, label="critique",
                        until_status={"awaiting_human", "failed"}, until_stage={"export"},
                        max_seconds=MAX_CRITIQUE)
    snapshots["after_critique"] = C.db_capture(report_id)
    if g3park.get("status") == "failed":
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="failed_at_critique", job=g3park)
        )

    accept = C.accept_all_sections(session, report_id)
    print(f"ACCEPT_ALL {accept['status_code']}", flush=True)
    if accept["status_code"] != 200:
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="accept_all_failed", extra={"accept": accept})
        )
    snapshots["accept_all"] = accept

    g3 = C.confirm_gate3(session, report_id)
    print(f"GATE3_CONFIRM {g3['status_code']}", flush=True)
    if g3["status_code"] != 200:
        return exit_code_for_verdict(
            _finish(run, report_id, snapshots, verdict="gate3_confirm_failed", extra={"gate3": g3})
        )

    expjob = C.poll_job(session, report_id, label="export",
                        until_status={"done", "failed"}, max_seconds=MAX_EXPORT)
    snapshots["after_export"] = C.db_capture(report_id)
    dl = C.download_export(session, report_id)
    print(f"EXPORT_DOWNLOAD {dl}", flush=True)
    detail = C.report_detail(session, report_id)

    return exit_code_for_verdict(
        _finish(
            run,
            report_id,
            snapshots,
            verdict="completed" if expjob.get("status") == "done" else "export_incomplete",
            job=expjob,
            extra={"download": dl, "report_detail": detail.get("body")},
        )
    )


def _finish(run: str, report_id: str, snapshots: dict, *, verdict: str,
            job: dict | None = None, extra: dict | None = None) -> str:
    final = snapshots.get("after_export") or C.db_capture(report_id)
    artifact = {
        "run": run,
        "report_id": report_id,
        "verdict": verdict,
        "final_job": job,
        "cost": C.cost_summary(final),
        "snapshots": snapshots,
    }
    if extra:
        artifact["extra"] = extra
    C.write_artifact(f"walk_{run}_{report_id[:8]}.json", artifact)
    print(f"VERDICT={verdict} report_id={report_id}", flush=True)
    print(f"COST={artifact['cost']}", flush=True)
    return verdict


if __name__ == "__main__":
    sys.exit(main())
