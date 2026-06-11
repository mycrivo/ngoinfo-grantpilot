#!/usr/bin/env python3
"""B2a report purge + B2a-2 probe account deletion + B2b template replace (prod write).

Usage:
  python scripts/audit/b2_phase_exec.py --purge
  python scripts/audit/b2_phase_exec.py --delete-probes
  python scripts/audit/b2_phase_exec.py --replace
  python scripts/audit/b2_phase_exec.py --rollback   # owner instruction only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.audit.b1_template_analysis import (
    KILL_INDICATORS,
    KILL_SECTIONS,
    KILL_TABLES,
    _collect_refs,
    _tag_stats,
)
from scripts.audit.b1_rollback_execute import (
    EXPECTED_SNAPSHOT_SHA,
    SNAPSHOT,
    TEMPLATE_ID,
    rollback_from_snapshot,
)
from scripts.audit.build_fcdo_post_deletion_template import OUT as POST_DELETION

ARTIFACT_DIR = ROOT / "docs/artefacts/me_module/audits/snapshots"
ALLOWED_REAL_USER = "pranabksingh@gmail.com"
PROBE_ACCOUNTS = frozenset({"probe-upload2@test.org", "probe-upload3@test.org"})
EXPECTED_PURGE_COUNT = 41
KILL_REFS = KILL_INDICATORS | KILL_TABLES


def _bootstrap_db() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    from scripts.audit import _common as C

    C.bootstrap_db_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL unavailable")
    return url


def _allowed_email(email: str) -> bool:
    e = (email or "").strip().lower()
    return (
        e == ALLOWED_REAL_USER
        or e.endswith("@grantpilot-test.org")
        or e in PROBE_ACCOUNTS
    )


def _per_item_tagged(sections: list[dict]) -> tuple[int, int]:
    tagged = 0
    total = 0
    for sec in sections:
        ind_req = sec.get("indicator_requirements") or {}
        for ind in sec.get("required_indicators") or []:
            total += 1
            meta = ind_req.get(str(ind)) or {}
            if meta.get("owner") and meta.get("requirement_type"):
                tagged += 1
        tbl_req = sec.get("table_requirements") or {}
        for tbl in sec.get("required_tables") or []:
            if not isinstance(tbl, dict):
                continue
            tkey = str(tbl.get("table_key") or "")
            if not tkey:
                continue
            total += 1
            meta = tbl_req.get(tkey) or {}
            if meta.get("owner") and meta.get("requirement_type"):
                tagged += 1
    return tagged, total


def _verify_intended_payload(intended: dict) -> dict:
    sections = list(intended["report_sections_json"])
    strict_tagged, strict_total = _per_item_tagged(sections)
    remaining_kill = sorted(_collect_refs(sections) & KILL_REFS)
    remaining_kill_sections = sorted(
        {str(s.get("section_key")) for s in sections} & KILL_SECTIONS
    )
    return {
        "section_count": len(sections),
        "strict_v120_tagged": strict_tagged,
        "strict_v120_total": strict_total,
        "kill_list_refs_remaining": remaining_kill,
        "kill_sections_remaining": remaining_kill_sections,
        "tag_stats": _tag_stats(sections),
    }


def _assert_intended(intended: dict) -> None:
    if not POST_DELETION.is_file():
        raise SystemExit(f"STOP: committed post-deletion file missing: {POST_DELETION}")
    check = _verify_intended_payload(intended)
    if check["section_count"] != 6:
        raise SystemExit(f"STOP: section_count != 6 ({check['section_count']})")
    if check["kill_list_refs_remaining"] or check["kill_sections_remaining"]:
        raise SystemExit(f"STOP: kill-list refs remain: {check}")
    if check["strict_v120_tagged"] != check["strict_v120_total"]:
        raise SystemExit(
            f"STOP: untagged requirements {check['strict_v120_tagged']}/{check['strict_v120_total']}"
        )


def _fetch_purge_scope(conn) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT dr.id AS report_id,
                   dr.status,
                   dr.user_id,
                   dr.created_at,
                   u.email,
                   (SELECT COUNT(*) FROM report_jobs rj WHERE rj.donor_report_id = dr.id) AS job_count,
                   (SELECT COUNT(*) FROM uploaded_documents ud WHERE ud.donor_report_id = dr.id) AS doc_count
            FROM donor_reports dr
            JOIN users u ON u.id = dr.user_id
            WHERE dr.funder_report_template_id = CAST(:tid AS uuid)
            ORDER BY dr.created_at
            """
        ),
        {"tid": TEMPLATE_ID},
    ).mappings().all()
    return [dict(r) for r in rows]


def _dump_rows(conn, report_ids: list[str]) -> dict:
    if not report_ids:
        return {"donor_reports": [], "report_jobs": [], "uploaded_documents": []}
    reports = conn.execute(
        text(
            """
            SELECT dr.*, u.email
            FROM donor_reports dr
            JOIN users u ON u.id = dr.user_id
            WHERE dr.id = ANY(CAST(:ids AS uuid[]))
            """
        ),
        {"ids": report_ids},
    ).mappings().all()
    jobs = conn.execute(
        text(
            """
            SELECT * FROM report_jobs
            WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
            """
        ),
        {"ids": report_ids},
    ).mappings().all()
    docs = conn.execute(
        text(
            """
            SELECT * FROM uploaded_documents
            WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
            """
        ),
        {"ids": report_ids},
    ).mappings().all()
    return {
        "donor_reports": [dict(r) for r in reports],
        "report_jobs": [dict(r) for r in jobs],
        "uploaded_documents": [dict(r) for r in docs],
    }


def _delete_r2_objects(docs: list[dict]) -> list[dict]:
    from app.reports.services.document_storage_service import (
        DocumentStorageError,
        DocumentStorageService,
    )

    store = DocumentStorageService()
    failures: list[dict] = []
    for doc in docs:
        ref = doc.get("storage_ref")
        if not ref:
            continue
        try:
            store.delete_object(str(ref))
        except DocumentStorageError as exc:
            failures.append(
                {
                    "document_id": str(doc.get("id")),
                    "storage_ref": ref,
                    "error": getattr(exc, "message", str(exc)),
                }
            )
        except Exception as exc:  # noqa: BLE001 — audit script lists all storage failures
            failures.append(
                {
                    "document_id": str(doc.get("id")),
                    "storage_ref": ref,
                    "error": str(exc),
                }
            )
    return failures


def run_purge() -> int:
    db_url = _bootstrap_db()
    engine = create_engine(db_url)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_path = ARTIFACT_DIR / f"b2a_purge_dump_{ts}.json"

    with engine.connect() as conn:
        scope = _fetch_purge_scope(conn)
        unknown = [r for r in scope if not _allowed_email(str(r.get("email")))]
        if unknown:
            print(
                json.dumps(
                    {"stop": "unknown_account_in_purge_scope", "rows": unknown},
                    indent=2,
                    default=str,
                )
            )
            return 1

        report_ids = [str(r["report_id"]) for r in scope]
        dump_body = {
            "template_id": TEMPLATE_ID,
            "expected_count": EXPECTED_PURGE_COUNT,
            "scope_count": len(scope),
            "rows": _dump_rows(conn, report_ids),
        }
        dump_path.write_text(
            json.dumps(dump_body, indent=2, default=str) + "\n", encoding="utf-8"
        )

    docs_for_r2: list[dict] = dump_body["rows"]["uploaded_documents"]
    r2_failures = _delete_r2_objects(docs_for_r2)

    deleted_counts = {"uploaded_documents": 0, "report_jobs": 0, "donor_reports": 0}
    with engine.begin() as conn:
        if report_ids:
            doc_del = conn.execute(
                text(
                    """
                    DELETE FROM uploaded_documents
                    WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
                    """
                ),
                {"ids": report_ids},
            )
            deleted_counts["uploaded_documents"] = int(doc_del.rowcount or 0)
            job_del = conn.execute(
                text(
                    """
                    DELETE FROM report_jobs
                    WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
                    """
                ),
                {"ids": report_ids},
            )
            deleted_counts["report_jobs"] = int(job_del.rowcount or 0)
            rep_del = conn.execute(
                text(
                    """
                    DELETE FROM donor_reports
                    WHERE id = ANY(CAST(:ids AS uuid[]))
                    """
                ),
                {"ids": report_ids},
            )
            deleted_counts["donor_reports"] = int(rep_del.rowcount or 0)

        remaining_reports = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM donor_reports
                WHERE funder_report_template_id = CAST(:tid AS uuid)
                """
            ),
            {"tid": TEMPLATE_ID},
        ).scalar()
        remaining_jobs = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM report_jobs rj
                JOIN donor_reports dr ON dr.id = rj.donor_report_id
                WHERE dr.funder_report_template_id = CAST(:tid AS uuid)
                """
            ),
            {"tid": TEMPLATE_ID},
        ).scalar()

    result = {
        "purge_dump": str(dump_path.relative_to(ROOT)),
        "scope_count": len(scope),
        "deleted_counts": deleted_counts,
        "r2_delete_failures": r2_failures,
        "remaining_reports_on_template": int(remaining_reports or 0),
        "remaining_jobs_on_template": int(remaining_jobs or 0),
    }
    print(json.dumps(result, indent=2, default=str))
    if int(remaining_reports or 0) != 0 or int(remaining_jobs or 0) != 0:
        return 1
    return 0


def _fetch_probe_users(conn) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT id, email, created_at
            FROM users
            WHERE lower(email) = ANY(CAST(:emails AS text[]))
            ORDER BY email
            """
        ),
        {"emails": [e.lower() for e in PROBE_ACCOUNTS]},
    ).mappings().all()
    return [dict(r) for r in rows]


def _dump_probe_dependents(conn, user_ids: list[str]) -> dict:
    if not user_ids:
        return {}
    users = conn.execute(
        text("SELECT * FROM users WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    plans = conn.execute(
        text("SELECT * FROM user_plans WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    ledger = conn.execute(
        text("SELECT * FROM usage_ledger WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    reports = conn.execute(
        text("SELECT * FROM donor_reports WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    report_ids = [str(r["id"]) for r in reports]
    jobs: list = []
    docs: list = []
    if report_ids:
        jobs = conn.execute(
            text(
                "SELECT * FROM report_jobs WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": report_ids},
        ).mappings().all()
        docs = conn.execute(
            text(
                """
                SELECT * FROM uploaded_documents
                WHERE donor_report_id = ANY(CAST(:ids AS uuid[]))
                   OR user_id = ANY(CAST(:uids AS uuid[]))
                """
            ),
            {"ids": report_ids, "uids": user_ids},
        ).mappings().all()
    proposals = conn.execute(
        text("SELECT * FROM proposals WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    profiles = conn.execute(
        text("SELECT * FROM ngo_profiles WHERE user_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": user_ids},
    ).mappings().all()
    return {
        "users": [dict(r) for r in users],
        "user_plans": [dict(r) for r in plans],
        "usage_ledger": [dict(r) for r in ledger],
        "donor_reports": [dict(r) for r in reports],
        "report_jobs": [dict(j) for j in jobs],
        "uploaded_documents": [dict(d) for d in docs],
        "proposals": [dict(p) for p in proposals],
        "ngo_profiles": [dict(p) for p in profiles],
    }


def run_delete_probes() -> int:
    db_url = _bootstrap_db()
    engine = create_engine(db_url)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_path = ARTIFACT_DIR / f"b2a2_probe_account_dump_{ts}.json"

    with engine.connect() as conn:
        probe_users = _fetch_probe_users(conn)
        found_emails = {str(u["email"]).lower() for u in probe_users}
        if found_emails != {e.lower() for e in PROBE_ACCOUNTS}:
            print(
                json.dumps(
                    {
                        "stop": "probe_account_set_mismatch",
                        "expected": sorted(PROBE_ACCOUNTS),
                        "found": sorted(found_emails),
                    },
                    indent=2,
                )
            )
            return 1

        user_ids = [str(u["id"]) for u in probe_users]
        dump_body = {
            "scoped_emails": sorted(PROBE_ACCOUNTS),
            "user_ids": user_ids,
            "rows": _dump_probe_dependents(conn, user_ids),
        }
        dump_path.write_text(
            json.dumps(dump_body, indent=2, default=str) + "\n", encoding="utf-8"
        )

    docs_for_r2 = dump_body["rows"]["uploaded_documents"]
    r2_failures = _delete_r2_objects(docs_for_r2)

    deleted_counts: dict[str, int] = {}
    with engine.begin() as conn:
        for table, sql in (
            (
                "users",
                """
                DELETE FROM users
                WHERE id = ANY(CAST(:ids AS uuid[]))
                  AND lower(email) = ANY(CAST(:emails AS text[]))
                """,
            ),
        ):
            result = conn.execute(
                text(sql),
                {
                    "ids": user_ids,
                    "emails": [e.lower() for e in PROBE_ACCOUNTS],
                },
            )
            deleted_counts[table] = int(result.rowcount or 0)

        remaining = conn.execute(
            text(
                """
                SELECT email FROM users
                WHERE lower(email) = ANY(CAST(:emails AS text[]))
                """
            ),
            {"emails": [e.lower() for e in PROBE_ACCOUNTS]},
        ).mappings().all()

    out = {
        "probe_dump": str(dump_path.relative_to(ROOT)),
        "deleted_counts": deleted_counts,
        "r2_delete_failures": r2_failures,
        "remaining_probe_users": [dict(r) for r in remaining],
    }
    print(json.dumps(out, indent=2, default=str))
    if remaining:
        return 1
    return 0


def run_replace() -> int:
    if not POST_DELETION.is_file():
        print(json.dumps({"stop": "no_committed_post_deletion_file", "path": str(POST_DELETION)}))
        return 1
    intended = json.loads(POST_DELETION.read_text(encoding="utf-8"))
    _assert_intended(intended)
    intended_canonical = {
        "report_sections_json": intended["report_sections_json"],
        "format_rules_json": intended.get("format_rules_json"),
        "terminology_map_json": intended.get("terminology_map_json"),
    }

    db_url = _bootstrap_db()
    engine = create_engine(db_url)

    with engine.begin() as conn:
        before = conn.execute(
            text(
                """
                SELECT report_sections_json, format_rules_json, terminology_map_json, version
                FROM funder_report_templates WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": TEMPLATE_ID},
        ).mappings().first()
        if not before:
            raise SystemExit("STOP: template row missing")

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
        affected = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM funder_report_templates
                WHERE id = CAST(:tid AS uuid)
                  AND report_sections_json = CAST(:sections AS jsonb)
                  AND format_rules_json = CAST(:format_rules AS jsonb)
                  AND terminology_map_json = CAST(:terminology AS jsonb)
                """
            ),
            {
                "tid": TEMPLATE_ID,
                "sections": json.dumps(intended["report_sections_json"]),
                "format_rules": json.dumps(intended.get("format_rules_json") or {}),
                "terminology": json.dumps(intended.get("terminology_map_json") or {}),
            },
        ).scalar()

        row = conn.execute(
            text(
                """
                SELECT report_sections_json, format_rules_json, terminology_map_json, version
                FROM funder_report_templates WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": TEMPLATE_ID},
        ).mappings().first()

        read_back = {
            "report_sections_json": row["report_sections_json"],
            "format_rules_json": row.get("format_rules_json"),
            "terminology_map_json": row.get("terminology_map_json"),
        }
        verify = _verify_intended_payload(read_back)
        exact = json.dumps(read_back, sort_keys=True) == json.dumps(
            intended_canonical, sort_keys=True
        )

        if verify["section_count"] != 6 or not exact or int(affected or 0) != 1:
            rollback_from_snapshot(conn, json.loads(SNAPSHOT.read_text(encoding="utf-8")))
            print(
                json.dumps(
                    {
                        "stop": "read_back_mismatch_rollback_inside_transaction",
                        "affected_rows": int(affected or 0),
                        "exact_diff_vs_intended": exact,
                        "verify": verify,
                    },
                    indent=2,
                )
            )
            return 1

    print(
        json.dumps(
            {
                "replace_source": str(POST_DELETION.relative_to(ROOT)),
                "affected_rows": 1,
                "read_back": verify,
                "version_before": before.get("version"),
                "version_after": row.get("version"),
                "rollback_snapshot_sha256": EXPECTED_SNAPSHOT_SHA,
            },
            indent=2,
            default=str,
        )
    )
    return 0


def run_rollback() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    db_url = _bootstrap_db()
    engine = create_engine(db_url)
    with engine.begin() as conn:
        affected = rollback_from_snapshot(conn, snapshot)
    print(json.dumps({"rollback_affected_rows": affected, "snapshot": str(SNAPSHOT)}))
    return 0 if affected == 1 else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--delete-probes", action="store_true")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()
    flags = (args.purge, args.delete_probes, args.replace, args.rollback)
    if sum(bool(x) for x in flags) != 1:
        parser.error("exactly one of --purge, --delete-probes, --replace, --rollback")
    if args.purge:
        return run_purge()
    if args.delete_probes:
        return run_delete_probes()
    if args.replace:
        return run_replace()
    return run_rollback()


if __name__ == "__main__":
    raise SystemExit(main())
