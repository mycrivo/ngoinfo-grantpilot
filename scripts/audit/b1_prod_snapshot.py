#!/usr/bin/env python3
"""B1 read-only: pull prod FCDO template row, diff vs repo instance, write rollback."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
FCDO_TEMPLATE_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
REPO_INSTANCE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
SNAPSHOT_DIR = ROOT / "docs" / "artefacts" / "me_module" / "audits" / "snapshots"
KILL_SECTIONS = frozenset({"detailed_output_scoring", "value_for_money"})
KILL_INDICATORS = frozenset(
    {
        "output_scores",
        "impact_weightings",
        "risk_ratings",
        "economy",
        "efficiency",
        "effectiveness",
        "equity",
        "commercial_improvement_where_relevant",
        "FCDO_management_actions",
    }
)
KILL_TABLES = frozenset({"output_score_table", "vfm_measures", "review_summary_sheet"})


def _db_url() -> str:
    raw = subprocess.check_output(
        "railway variables --json --service Postgres",
        shell=True,
        text=True,
    )
    return json.loads(raw)["DATABASE_PUBLIC_URL"]


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _section_keys(sections: list[dict]) -> set[str]:
    return {str(s.get("section_key") or "") for s in sections}


def _tagged_refs(section: dict) -> set[str]:
    refs: set[str] = set()
    for ref in section.get("required_indicators") or []:
        reqs = section.get("indicator_requirements") or {}
        meta = reqs.get(ref) if isinstance(reqs, dict) else None
        if isinstance(meta, dict) and meta.get("owner"):
            refs.add(ref)
    for table in section.get("required_tables") or []:
        if not isinstance(table, dict):
            continue
        key = str(table.get("table_key") or "")
        reqs = section.get("table_requirements") or {}
        meta = reqs.get(key) if isinstance(reqs, dict) else None
        if isinstance(meta, dict) and meta.get("owner"):
            refs.add(key)
    return refs


def main() -> int:
    engine = create_engine(_db_url())
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, funder_name, template_name, region, reporting_frequency,
                       docx_template_ref, is_active, version,
                       report_sections_json, format_rules_json, terminology_map_json,
                       created_at, updated_at
                FROM funder_report_templates
                WHERE id = CAST(:tid AS uuid)
                """
            ),
            {"tid": FCDO_TEMPLATE_ID},
        ).mappings().first()
        if not row:
            print("SNAPSHOT_FAIL missing template row", file=sys.stderr)
            return 1
        alembic = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    snapshot = dict(row)
    for key in ("report_sections_json", "format_rules_json", "terminology_map_json"):
        val = snapshot.get(key)
        if isinstance(val, str):
            snapshot[key] = json.loads(val)

    today = date.today().isoformat()
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap_path = SNAPSHOT_DIR / f"fcdo_55f891ac_pre_phase3_exit_{today}.json"
    snap_text = json.dumps(snapshot, indent=2, ensure_ascii=False, default=str) + "\n"
    snap_path.write_text(snap_text, encoding="utf-8")
    checksum = _sha256(snap_text)

    rollback_path = SNAPSHOT_DIR / f"fcdo_55f891ac_rollback_{today}.sql"
    rollback_path.write_text(
        f"""-- Rollback: restore prod FCDO template from B1 snapshot ({today})
-- Checksum SHA256: {checksum}
BEGIN;
UPDATE funder_report_templates
SET
  report_sections_json = :report_sections_json::jsonb,
  format_rules_json = :format_rules_json::jsonb,
  terminology_map_json = :terminology_map_json::jsonb,
  version = {snapshot['version']},
  updated_at = now()
WHERE id = '{FCDO_TEMPLATE_ID}';
-- Verify affected rows = 1 before COMMIT;
COMMIT;
""",
        encoding="utf-8",
    )

    repo = json.loads(REPO_INSTANCE.read_text(encoding="utf-8"))
    prod_sections = list(snapshot["report_sections_json"] or [])
    repo_sections = list(repo.get("report_sections_json") or [])
    prod_keys = _section_keys(prod_sections)
    repo_keys = _section_keys(repo_sections)

    removed_sections = sorted(prod_keys - repo_keys)
    added_sections = sorted(repo_keys - prod_keys)

    prod_funder_sections = [
        s["section_key"]
        for s in prod_sections
        if str(s.get("owner") or "") == "funder"
        or s.get("section_key") in KILL_SECTIONS
    ]
    repo_funder_sections = [
        s["section_key"]
        for s in repo_sections
        if str(s.get("owner") or "") == "funder"
    ]

    staging = {
        "template_id": FCDO_TEMPLATE_ID,
        "snapshot_path": str(snap_path.relative_to(ROOT)),
        "rollback_sql_path": str(rollback_path.relative_to(ROOT)),
        "checksum_sha256": checksum,
        "alembic_version_prod": alembic,
        "prod_version": snapshot.get("version"),
        "repo_source": str(REPO_INSTANCE.relative_to(ROOT)),
        "diff_summary": {
            "sections_removed_in_repo": removed_sections,
            "sections_added_in_repo": added_sections,
            "prod_funder_owned_section_keys": sorted(set(prod_funder_sections)),
            "repo_funder_owned_section_keys": sorted(set(repo_funder_sections)),
            "kill_list_sections": sorted(KILL_SECTIONS),
            "kill_list_indicators": sorted(KILL_INDICATORS),
            "kill_list_tables": sorted(KILL_TABLES),
        },
        "repo_tag_coverage_sample": sorted(
            ref
            for s in repo_sections
            for ref in _tagged_refs(s)
        )[:20],
    }
    staging_path = SNAPSHOT_DIR / f"b1_staging_summary_{today}.json"
    staging_path.write_text(json.dumps(staging, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(staging, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
