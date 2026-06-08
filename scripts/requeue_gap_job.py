#!/usr/bin/env python3
"""Re-queue a failed gap-stage job (run after deterministic gap fix is deployed)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

REPORT_ID = os.environ.get("REPORT_ID", "230290ce-d28a-4138-ae08-901cf1ad69c0")


def _bootstrap_db_env() -> None:
    if os.environ.get("DATABASE_URL"):
        return
    env_path = REPO / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    _bootstrap_db_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1
    engine = create_engine(url)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                UPDATE report_jobs
                SET status = 'queued', error = NULL, updated_at = NOW()
                WHERE id = (
                    SELECT id FROM report_jobs
                    WHERE donor_report_id = CAST(:rid AS uuid)
                      AND stage = 'gap'
                    ORDER BY started_at DESC NULLS LAST, id DESC
                    LIMIT 1
                )
                RETURNING id, status, stage
                """
            ),
            {"rid": REPORT_ID},
        ).mappings().first()
    if row is None:
        print(f"No gap job updated for report {REPORT_ID}", file=sys.stderr)
        return 1
    print(f"Re-queued job_id={row['id']} stage={row['stage']} status={row['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
