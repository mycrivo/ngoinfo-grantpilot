"""Read-only: stuck job diagnostics for production."""
from __future__ import annotations

import json
import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

RID = sys.argv[1] if len(sys.argv) > 1 else "0f0452f9-d381-4d19-823c-9035d369496d"


def main() -> None:
    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT id, stage, status, error, started_at, finished_at,
               now() AS db_now,
               now() - started_at AS running_for
        FROM report_jobs
        WHERE donor_report_id = %s
        ORDER BY started_at DESC NULLS LAST
        """,
        (RID,),
    )
    print("=== JOBS FOR REPORT ===")
    for row in cur.fetchall():
        print(json.dumps({k: str(v) if v is not None else None for k, v in row.items()}))

    cur.execute(
        """
        SELECT id, original_filename, classification, extraction_status,
               mime_type, storage_ref, size_bytes, created_at,
               extracted_json::text AS extracted_preview
        FROM uploaded_documents
        WHERE donor_report_id = %s
        ORDER BY created_at
        """,
        (RID,),
    )
    print("=== DOCUMENTS ===")
    for row in cur.fetchall():
        d = dict(row)
        preview = d.pop("extracted_preview", None)
        print(json.dumps({k: str(v) if v is not None else None for k, v in d.items()}))
        if preview and preview not in ("{}", "null"):
            print("  extracted:", preview[:500])

    cur.execute(
        """
        SELECT id, donor_report_id, stage, status, left(error, 400) AS error,
               started_at, finished_at
        FROM report_jobs
        WHERE stage = 'extract' AND status = 'failed'
        ORDER BY finished_at DESC NULLS LAST
        LIMIT 8
        """
    )
    print("=== RECENT FAILED EXTRACT (all reports) ===")
    for row in cur.fetchall():
        print(json.dumps({k: str(v) if v is not None else None for k, v in row.items()}))

    cur.execute(
        """
        SELECT id, donor_report_id, stage, status, started_at,
               now() - started_at AS running_for
        FROM report_jobs
        WHERE status = 'running'
        """
    )
    print("=== ALL RUNNING JOBS ===")
    for row in cur.fetchall():
        print(json.dumps({k: str(v) if v is not None else None for k, v in row.items()}))

    conn.close()


if __name__ == "__main__":
    main()
