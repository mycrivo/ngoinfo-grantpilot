#!/usr/bin/env python3
"""Executable rollback + scratch-Postgres proof for B1 re-stage.

Usage (CI scratch Postgres):
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grantpilot_test \\
    python scripts/audit/b1_rollback_execute.py --proof
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_pre_phase3_exit_2026-06-11.json"
INTENDED = ROOT / "docs/artefacts/me_module/audits/snapshots/fcdo_55f891ac_intended_post_mutation_2026-06-11.json"
TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
EXPECTED_SNAPSHOT_SHA = "aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_payload(row: dict) -> dict:
    return {
        "report_sections_json": row["report_sections_json"],
        "format_rules_json": row.get("format_rules_json"),
        "terminology_map_json": row.get("terminology_map_json"),
        "version": row.get("version"),
    }


def rollback_from_snapshot(conn, snapshot: dict) -> int:
    result = conn.execute(
        text(
            """
            UPDATE funder_report_templates
            SET report_sections_json = CAST(:sections AS jsonb),
                format_rules_json = CAST(:format_rules AS jsonb),
                terminology_map_json = CAST(:terminology AS jsonb),
                version = :version,
                updated_at = now()
            WHERE id = CAST(:tid AS uuid)
            """
        ),
        {
            "tid": TEMPLATE_ID,
            "sections": json.dumps(snapshot["report_sections_json"]),
            "format_rules": json.dumps(snapshot.get("format_rules_json") or {}),
            "terminology": json.dumps(snapshot.get("terminology_map_json") or {}),
            "version": int(snapshot.get("version") or 1),
        },
    )
    return int(result.rowcount or 0)


def ensure_baseline_row(conn, snapshot: dict) -> None:
    tid = TEMPLATE_ID
    existing = conn.execute(
        text("SELECT id FROM funder_report_templates WHERE id = CAST(:tid AS uuid)"),
        {"tid": tid},
    ).first()
    if existing:
        return
    conn.execute(
        text(
            """
            INSERT INTO funder_report_templates
              (id, funder_name, template_name, region, reporting_frequency,
               docx_template_ref, is_active, version,
               report_sections_json, format_rules_json, terminology_map_json)
            VALUES
              (CAST(:tid AS uuid), :funder_name, :template_name, :region, :reporting_frequency,
               :docx_template_ref, :is_active, :version,
               CAST(:sections AS jsonb), CAST(:format_rules AS jsonb), CAST(:terminology AS jsonb))
            """
        ),
        {
            "tid": tid,
            "funder_name": snapshot.get("funder_name") or "FCDO",
            "template_name": snapshot.get("template_name") or "FCDO Annual Review",
            "region": snapshot.get("region") or "UK",
            "reporting_frequency": snapshot.get("reporting_frequency") or "annual",
            "docx_template_ref": snapshot.get("docx_template_ref")
            or "app/reports/templates/docx/fcdo-annual-review.docx",
            "is_active": bool(snapshot.get("is_active", True)),
            "version": int(snapshot.get("version") or 1),
            "sections": json.dumps(snapshot["report_sections_json"]),
            "format_rules": json.dumps(snapshot.get("format_rules_json") or {}),
            "terminology": json.dumps(snapshot.get("terminology_map_json") or {}),
        },
    )


def apply_post_mutation(conn, intended: dict) -> None:
    conn.execute(
        text(
            """
            UPDATE funder_report_templates
            SET report_sections_json = CAST(:sections AS jsonb),
                format_rules_json = CAST(:format_rules AS jsonb),
                terminology_map_json = CAST(:terminology AS jsonb),
                version = version + 1,
                updated_at = now()
            WHERE id = CAST(:tid AS uuid)
            """
        ),
        {
            "tid": TEMPLATE_ID,
            "sections": json.dumps(intended["report_sections_json"]),
            "format_rules": json.dumps(intended.get("format_rules_json") or {}),
            "terminology": json.dumps(intended.get("terminology_map_json") or {}),
        },
    )


def run_proof(db_url: str) -> int:
    snapshot_bytes = SNAPSHOT.read_bytes()
    snap_sha = _sha256_bytes(snapshot_bytes)
    if snap_sha != EXPECTED_SNAPSHOT_SHA:
        print(json.dumps({"error": "snapshot_sha_mismatch", "expected": EXPECTED_SNAPSHOT_SHA, "got": snap_sha}))
        return 1

    snapshot = json.loads(snapshot_bytes.decode("utf-8"))
    intended = json.loads(INTENDED.read_text(encoding="utf-8"))
    engine = create_engine(db_url)

    with engine.begin() as conn:
        ensure_baseline_row(conn, snapshot)
        apply_post_mutation(conn, intended)
        affected = rollback_from_snapshot(conn, snapshot)
        row = conn.execute(
            text(
                """
                SELECT report_sections_json, format_rules_json, terminology_map_json, version
                FROM funder_report_templates WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": TEMPLATE_ID},
        ).mappings().first()

    restored = _canonical_payload(dict(row))
    expected = _canonical_payload(snapshot)
    byte_equal = json.dumps(restored, sort_keys=True) == json.dumps(expected, sort_keys=True)
    print(
        json.dumps(
            {
                "snapshot_sha256": snap_sha,
                "rollback_affected_rows": affected,
                "rollback_byte_equality": byte_equal,
                "database_url_host": db_url.split("@")[-1] if "@" in db_url else "local",
            },
            indent=2,
        )
    )
    return 0 if byte_equal and affected == 1 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proof", action="store_true", help="Run scratch Postgres rollback proof")
    args = parser.parse_args()
    if not args.proof:
        print("Usage: b1_rollback_execute.py --proof (requires DATABASE_URL)", file=sys.stderr)
        return 2
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    return run_proof(db_url)


if __name__ == "__main__":
    raise SystemExit(main())
