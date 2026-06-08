#!/usr/bin/env python3
"""DB-driven steps for the synthesis->export tail.

FINDING UNDER TEST: the engine exposes NO production API to (a) resume the
critique stage after the critique-boundary park, (b) accept sections, or
(c) accept BLOCK critic flags. The only way to advance a report from synthesis
to export is direct DB manipulation (the `_accept_all_sections_for_gate3`
test pattern). These helpers reproduce that gap explicitly so the audit can
reach export and inspect the rendered document. They simulate the missing UI;
they do NOT modify engine code.
"""

from __future__ import annotations

import os
from typing import Any

from scripts.audit._common import bootstrap_db_env


def _engine():
    bootstrap_db_env()
    import app.models  # noqa: F401
    from sqlalchemy import create_engine

    return create_engine(os.environ["DATABASE_URL"])


def resume_critique_via_worker(report_id: str) -> dict[str, Any]:
    """Set the awaiting-human critique job to queued so the worker runs the critic.

    Faithful: the critic itself still runs in the engine/worker. Only the
    missing 'resume critique' UI action is simulated.
    """
    from sqlalchemy import text

    eng = _engine()
    with eng.begin() as c:
        row = c.execute(text(
            """
            SELECT id, stage, status FROM report_jobs
            WHERE donor_report_id = CAST(:rid AS uuid)
            ORDER BY started_at DESC NULLS LAST, id DESC LIMIT 1
            """), {"rid": report_id}).mappings().first()
        if not row:
            return {"ok": False, "reason": "no_job"}
        if row["stage"] != "critique" or row["status"] != "awaiting_human":
            return {"ok": False, "reason": f"unexpected stage/status {row['stage']}/{row['status']}"}
        c.execute(text(
            "UPDATE report_jobs SET status = 'queued' WHERE id = :jid"),
            {"jid": str(row["id"])})
    return {"ok": True, "job_id": str(row["id"]), "action": "set critique job -> queued"}


def accept_all_sections(report_id: str) -> dict[str, Any]:
    """Simulate the missing human review UI: mark every section ACCEPTED and
    accept every BLOCK critic flag. Records what it touched for the audit.
    """
    import json

    from sqlalchemy import text

    eng = _engine()
    with eng.begin() as c:
        row = c.execute(text(
            "SELECT content_json FROM donor_reports WHERE id = CAST(:rid AS uuid)"),
            {"rid": report_id}).mappings().first()
        content = dict(row["content_json"] or {}) if row else {}
        sections = content.get("sections") or []
        blocks_accepted = warns = total_flags = 0
        prior_status: dict[str, int] = {}
        for section in sections:
            st = section.get("generation_status")
            prior_status[st] = prior_status.get(st, 0) + 1
            section["generation_status"] = "ACCEPTED"
            new_flags = []
            for flag in section.get("critic_flags") or []:
                f = dict(flag)
                total_flags += 1
                if f.get("severity") == "BLOCK":
                    blocks_accepted += 1
                elif f.get("severity") == "WARN":
                    warns += 1
                f["accepted"] = True
                new_flags.append(f)
            section["critic_flags"] = new_flags
        content["sections"] = sections
        c.execute(text(
            "UPDATE donor_reports SET content_json = CAST(:cj AS jsonb) "
            "WHERE id = CAST(:rid AS uuid)"),
            {"cj": json.dumps(content), "rid": report_id})
    return {
        "ok": True,
        "sections": len(sections),
        "prior_generation_status_counts": prior_status,
        "block_flags_accepted": blocks_accepted,
        "warn_flags": warns,
        "total_critic_flags": total_flags,
    }
