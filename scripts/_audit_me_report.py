"""One-off read-only audit: M&E report state for a user email."""
from __future__ import annotations

import json
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

EMAIL = sys.argv[1] if len(sys.argv) > 1 else "pranabksingh@gmail.com"


def main() -> None:
    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: no DATABASE URL", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT u.id AS user_id, u.email, dr.id AS report_id,
               dr.status AS report_status,
               dr.created_at, dr.updated_at,
               dr.knowledge_bank_json->>'current_gate' AS current_gate,
               ft.funder_name, ft.template_name
        FROM users u
        JOIN donor_reports dr ON dr.user_id = u.id
        LEFT JOIN funder_report_templates ft ON ft.id = dr.funder_report_template_id
        WHERE u.email = %s
        ORDER BY dr.created_at DESC
        LIMIT 5
        """,
        (EMAIL,),
    )
    reports = cur.fetchall()
    print("=== DONOR REPORTS ===")
    if not reports:
        cur.execute("SELECT count(*) AS n FROM users WHERE email = %s", (EMAIL,))
        print("USER_EXISTS", dict(cur.fetchone()))
        conn.close()
        return

    for r in reports:
        print(json.dumps({k: str(v) if v is not None else None for k, v in r.items()}))

    rid = reports[0]["report_id"]
    cur.execute(
        """
        SELECT id, stage, status, error, started_at, finished_at,
               agent_trace_json
        FROM report_jobs
        WHERE donor_report_id = %s
        ORDER BY started_at DESC NULLS LAST, id DESC
        LIMIT 10
        """,
        (str(rid),),
    )
    print("=== REPORT JOBS (latest report) ===")
    for j in cur.fetchall():
        trace = j.pop("agent_trace_json", {}) or {}
        row = {k: str(v) if v is not None else None for k, v in j.items()}
        print(json.dumps(row))
        if trace:
            print("  agent_trace:", json.dumps(trace, default=str)[:4000])

    cur.execute(
        """
        SELECT id, original_filename, classification, extraction_status,
               size_bytes, created_at
        FROM uploaded_documents
        WHERE donor_report_id = %s
        ORDER BY created_at
        """,
        (str(rid),),
    )
    print("=== UPLOADED DOCUMENTS ===")
    for d in cur.fetchall():
        print(json.dumps({k: str(v) if v is not None else None for k, v in d.items()}))

    cur.execute(
        """
        SELECT stage, status, count(*) AS n
        FROM report_jobs
        GROUP BY stage, status
        ORDER BY stage, status
        """
    )
    print("=== ALL REPORT_JOBS BY STAGE/STATUS ===")
    for row in cur.fetchall():
        print(json.dumps(dict(row)))

    conn.close()


if __name__ == "__main__":
    main()
