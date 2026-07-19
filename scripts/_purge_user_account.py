#!/usr/bin/env python3
"""Purge all M&E reports and reset usage ledger for one user (prod admin utility)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.audit import _common as C

EMAIL = sys.argv[1] if len(sys.argv) > 1 else "REDACTED_OWNER@example.invalid"
ARTIFACT_DIR = REPO / "docs" / "artefacts" / "me_module" / "audits" / "snapshots"


def main() -> int:
    C.bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_path = ARTIFACT_DIR / f"user_purge_{EMAIL.split('@')[0]}_{ts}.json"

    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, email FROM users WHERE email = :email"),
            {"email": EMAIL},
        ).mappings().first()
        if not user:
            print(f"ERROR: user not found: {EMAIL}", file=sys.stderr)
            return 1
        user_id = str(user["id"])

        reports = conn.execute(
            text(
                """
                SELECT dr.id, dr.status, dr.created_at, dr.funder_report_template_id
                FROM donor_reports dr
                WHERE dr.user_id = CAST(:uid AS uuid)
                ORDER BY dr.created_at
                """
            ),
            {"uid": user_id},
        ).mappings().all()
        report_ids = [str(r["id"]) for r in reports]

        docs: list[dict] = []
        jobs: list[dict] = []
        if report_ids:
            docs = [
                dict(r)
                for r in conn.execute(
                    text(
                        """
                        SELECT * FROM uploaded_documents
                        WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
                        """
                    ),
                    {"ids": report_ids},
                ).mappings().all()
            ]
            jobs = [
                dict(r)
                for r in conn.execute(
                    text(
                        """
                        SELECT * FROM report_jobs
                        WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
                        """
                    ),
                    {"ids": report_ids},
                ).mappings().all()
            ]

        ledger = [
            dict(r)
            for r in conn.execute(
                text(
                    """
                    SELECT id, action_type, idempotency_key, created_at
                    FROM usage_ledger
                    WHERE user_id = CAST(:uid AS uuid)
                    ORDER BY created_at
                    """
                ),
                {"uid": user_id},
            ).mappings().all()
        ]

    dump_path.parent.mkdir(parents=True, exist_ok=True)
    dump_path.write_text(
        json.dumps(
            {
                "email": EMAIL,
                "user_id": user_id,
                "donor_reports": [dict(r) for r in reports],
                "report_jobs": jobs,
                "uploaded_documents": docs,
                "usage_ledger": ledger,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"dump {dump_path}")

    # Reuse B2 R2 delete helper
    from scripts.audit.b2_phase_exec import _delete_r2_objects

    r2_failures = _delete_r2_objects(docs)

    deleted = {"donor_reports": 0, "report_jobs": 0, "uploaded_documents": 0, "usage_ledger": 0}
    with engine.begin() as conn:
        if report_ids:
            deleted["uploaded_documents"] = int(
                conn.execute(
                    text(
                        "DELETE FROM uploaded_documents WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))"
                    ),
                    {"ids": report_ids},
                ).rowcount
                or 0
            )
            deleted["report_jobs"] = int(
                conn.execute(
                    text(
                        "DELETE FROM report_jobs WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))"
                    ),
                    {"ids": report_ids},
                ).rowcount
                or 0
            )
            deleted["donor_reports"] = int(
                conn.execute(
                    text("DELETE FROM donor_reports WHERE id = ANY(CAST(:ids AS uuid[]))"),
                    {"ids": report_ids},
                ).rowcount
                or 0
            )
        deleted["usage_ledger"] = int(
            conn.execute(
                text("DELETE FROM usage_ledger WHERE user_id = CAST(:uid AS uuid)"),
                {"uid": user_id},
            ).rowcount
            or 0
        )

        remaining_reports = conn.execute(
            text("SELECT COUNT(*) FROM donor_reports WHERE user_id = CAST(:uid AS uuid)"),
            {"uid": user_id},
        ).scalar()
        remaining_ledger = conn.execute(
            text("SELECT COUNT(*) FROM usage_ledger WHERE user_id = CAST(:uid AS uuid)"),
            {"uid": user_id},
        ).scalar()

    result = {
        "email": EMAIL,
        "user_id": user_id,
        "deleted": deleted,
        "r2_delete_failures": r2_failures,
        "remaining_reports": int(remaining_reports or 0),
        "remaining_ledger": int(remaining_ledger or 0),
        "purge_dump": str(dump_path.relative_to(REPO)),
    }
    print(json.dumps(result, indent=2, default=str))
    if remaining_reports or remaining_ledger:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
