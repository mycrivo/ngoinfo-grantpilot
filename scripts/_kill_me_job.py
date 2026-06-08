"""One-off: mark an orphaned M&E report job as failed."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import Json, RealDictCursor

JOB_ID = "cd861d32-00d3-4106-83fb-eb050835196b"
REPORT_ID = "0f0452f9-d381-4d19-823c-9035d369496d"
ERROR = (
    "aborted: worker lost job mid-extract; monitoring upload was .docx "
    "(indicator_data requires xlsx or csv)"
)


def main() -> None:
    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: no DATABASE URL", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id, donor_report_id, stage, status, error FROM report_jobs WHERE id = %s",
        (JOB_ID,),
    )
    before = cur.fetchone()
    if before is None:
        print("ERROR: job not found", JOB_ID, file=sys.stderr)
        sys.exit(1)

    print("BEFORE", json.dumps(dict(before)))

    if before["status"] == "failed":
        print("ALREADY_FAILED")
        conn.close()
        return

    if before["status"] not in ("running", "queued"):
        print("ERROR: unexpected status", before["status"], file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    cur.execute(
        """
        UPDATE report_jobs
        SET status = 'failed',
            error = %s,
            finished_at = %s,
            agent_trace_json = COALESCE(agent_trace_json, '{}'::jsonb) || %s::jsonb
        WHERE id = %s AND status IN ('running', 'queued')
        RETURNING id, donor_report_id, stage, status, error, finished_at
        """,
        (
            ERROR,
            now,
            Json(
                {
                    "failure": {
                        "event": "manual_abort",
                        "message": ERROR,
                        "at": now.isoformat(),
                    }
                }
            ),
            JOB_ID,
        ),
    )
    row = cur.fetchone()
    if row is None:
        conn.rollback()
        print("ERROR: update matched no rows", file=sys.stderr)
        sys.exit(1)

    conn.commit()
    print("AFTER", json.dumps({k: str(v) if v is not None else None for k, v in row.items()}))

    cur.execute(
        """
        SELECT id, stage, status, error
        FROM report_jobs
        WHERE donor_report_id = %s
        ORDER BY started_at DESC NULLS LAST
        LIMIT 3
        """,
        (REPORT_ID,),
    )
    print("REPORT_JOBS")
    for r in cur.fetchall():
        print(json.dumps(dict(r)))

    conn.close()


if __name__ == "__main__":
    main()
