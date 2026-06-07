"""One-off: refund REPORT_CREATE quota for reports whose pipeline job failed."""
from __future__ import annotations

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
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT id FROM users WHERE email = %s", (EMAIL,))
    user = cur.fetchone()
    if user is None:
        print("ERROR: user not found", EMAIL, file=sys.stderr)
        sys.exit(1)

    user_id = user["id"]
    cur.execute(
        """
        SELECT dr.id AS report_id,
               (
                 SELECT rj.status
                 FROM report_jobs rj
                 WHERE rj.donor_report_id = dr.id
                 ORDER BY
                   CASE WHEN rj.status IN ('queued', 'running', 'awaiting_human') THEN 0 ELSE 1 END,
                   rj.started_at DESC NULLS LAST,
                   rj.id DESC
                 LIMIT 1
               ) AS latest_job_status
        FROM donor_reports dr
        WHERE dr.user_id = %s
        """,
        (str(user_id),),
    )
    reports = cur.fetchall()

    refunded = 0
    skipped = 0
    for row in reports:
        report_id = row["report_id"]
        if row["latest_job_status"] != "failed":
            skipped += 1
            continue

        refund_key = f"report:refund:{report_id}"
        create_key = f"report:create:{report_id}"

        cur.execute(
            """
            SELECT 1 FROM usage_ledger
            WHERE user_id = %s AND action_type = 'REPORT_CREATE_REFUND'
              AND idempotency_key = %s
            """,
            (str(user_id), refund_key),
        )
        if cur.fetchone():
            print("SKIP already refunded", report_id)
            skipped += 1
            continue

        cur.execute(
            """
            SELECT 1 FROM usage_ledger
            WHERE user_id = %s AND action_type = 'REPORT_CREATE'
              AND idempotency_key = %s
            """,
            (str(user_id), create_key),
        )
        if not cur.fetchone():
            print("SKIP no create ledger", report_id)
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO usage_ledger (id, user_id, action_type, idempotency_key, metadata, created_at)
            VALUES (gen_random_uuid(), %s, 'REPORT_CREATE_REFUND', %s, %s::jsonb, now())
            """,
            (
                str(user_id),
                refund_key,
                f'{{"donor_report_id": "{report_id}"}}',
            ),
        )
        refunded += 1
        print("REFUNDED", report_id)

    conn.commit()
    print(f"DONE refunded={refunded} skipped={skipped}")

    cur.execute(
        """
        SELECT
          SUM(CASE WHEN action_type = 'REPORT_CREATE' THEN 1 ELSE 0 END) AS creates,
          SUM(CASE WHEN action_type = 'REPORT_CREATE_REFUND' THEN 1 ELSE 0 END) AS refunds
        FROM usage_ledger
        WHERE user_id = %s
        """,
        (str(user_id),),
    )
    print("LEDGER", dict(cur.fetchone()))
    conn.close()


if __name__ == "__main__":
    main()
