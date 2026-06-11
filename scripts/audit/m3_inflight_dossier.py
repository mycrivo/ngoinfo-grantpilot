#!/usr/bin/env python3
"""M3: in-flight strand-risk dossier for FCDO template 55f891ac."""

from __future__ import annotations

import json
import subprocess
from sqlalchemy import create_engine, text

FCDO = "55f891ac-bb8b-4137-bc42-6de8ff935064"
KILL_SECTIONS = frozenset({"detailed_output_scoring", "value_for_money"})
KILL_REFS = frozenset(
    {
        "review_summary_sheet",
        "outcome_assessment",
        "output_scores",
        "impact_weightings",
        "risk_ratings",
        "economy",
        "efficiency",
        "effectiveness",
        "equity",
        "commercial_improvement_where_relevant",
        "FCDO_management_actions",
        "output_score_table",
        "vfm_measures",
    }
)


def main() -> None:
    raw = subprocess.check_output(
        "railway variables --json --service Postgres", shell=True, text=True
    )
    engine = create_engine(json.loads(raw)["DATABASE_PUBLIC_URL"])
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT dr.id AS report_id,
                       dr.status AS report_status,
                       dr.created_at,
                       u.email,
                       rj.id AS job_id,
                       rj.stage,
                       rj.status AS job_status,
                       rj.requeue_count,
                       dr.gap_analysis_json,
                       dr.content_json
                FROM donor_reports dr
                JOIN users u ON u.id = dr.user_id
                JOIN report_jobs rj ON rj.donor_report_id = dr.id
                WHERE dr.funder_report_template_id = CAST(:tid AS uuid)
                  AND rj.status NOT IN ('done', 'failed')
                ORDER BY dr.created_at
                """
            ),
            {"tid": FCDO},
        ).fetchall()

    out = []
    for r in rows:
        m = dict(r._mapping)
        gaps = (m.get("gap_analysis_json") or {}).get("gaps") or []
        gap_refs = {
            str(g.get("required_item_ref") or "")
            for g in gaps
            if isinstance(g, dict)
        }
        gap_sections = {
            str(g.get("section_key") or "")
            for g in gaps
            if isinstance(g, dict)
        }
        content = m.get("content_json") or {}
        content_sections = {
            str(s.get("section_key") or "")
            for s in (content.get("sections") or [])
            if isinstance(s, dict)
        }
        kill_gap_hits = sorted(gap_refs & KILL_REFS)
        kill_section_hits = sorted(gap_sections & KILL_SECTIONS)
        content_kill_sections = sorted(content_sections & KILL_SECTIONS)
        email = str(m["email"])
        out.append(
            {
                "report_id": str(m["report_id"]),
                "created_at": str(m["created_at"]),
                "account": "audit-mint" if email.endswith("@grantpilot-test.org") else "real-user",
                "email": email,
                "report_status": m["report_status"],
                "job_stage": m["stage"],
                "job_status": m["job_status"],
                "requeue_count": m["requeue_count"],
                "open_gaps": len(gaps),
                "gap_refs_kill_list": kill_gap_hits,
                "gap_sections_kill_list": kill_section_hits,
                "content_sections_kill_list": content_kill_sections,
            }
        )
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
