#!/usr/bin/env python3
"""Phase A: snapshot + surgical Track 3 elevate flags on live NLCF template row.

Owner-triggered only. Railway CLI must be authenticated. Invokes railway via cmd.exe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[2]
NLCF_ID = "2d5d75b7-12f5-46b5-adaa-d5939a5249a8"
FCDO_ID = "55f891ac-bb8b-4137-bc42-6de8ff935064"
SNAPSHOT_PATH = (
    REPO
    / "docs/artefacts/me_module/audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json"
)
COMMITTED = REPO / "docs/artefacts/me_module/TEMPLATE_INSTANCE_NLCF.json"
SECTION_KEY = "community_involvement"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, memoryview):
        return bytes(obj).hex()
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Not JSON serializable: {type(obj)!r}")


def _railway_pg_url() -> str:
    # Command Prompt only — never PowerShell for Railway CLI.
    raw = subprocess.check_output(
        ["cmd", "/c", "railway variables --json --service Postgres"],
        cwd=str(REPO),
        text=True,
    )
    vars_ = json.loads(raw)
    url = vars_.get("DATABASE_PUBLIC_URL") or vars_.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Postgres DATABASE_PUBLIC_URL / DATABASE_URL missing")
    return url


def _fetch_row(conn, template_id: str) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT id, funder_name, template_name, region, reporting_frequency,
                   report_sections_json, format_rules_json, terminology_map_json,
                   docx_template_ref, is_active, version, created_at, updated_at
            FROM funder_report_templates
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": template_id},
    ).mappings().one()
    return dict(row)


def _section(sections: list, key: str) -> dict | None:
    for s in sections or []:
        if isinstance(s, dict) and s.get("section_key") == key:
            return s
    return None


def _diff_other_fields(live: dict, committed: dict) -> list[str]:
    """Diff community_involvement excluding indicator_requirements."""
    keys = set(live) | set(committed)
    keys.discard("indicator_requirements")
    diffs: list[str] = []
    for k in sorted(keys):
        lv = live.get(k, "<MISSING>")
        cv = committed.get(k, "<MISSING>")
        if json.dumps(lv, sort_keys=True, default=_json_default) != json.dumps(
            cv, sort_keys=True, default=_json_default
        ):
            diffs.append(
                f"{k}: live={json.dumps(lv, default=_json_default)[:400]!r} "
                f"committed={json.dumps(cv, default=_json_default)[:400]!r}"
            )
    return diffs


def cmd_snapshot() -> int:
    engine = create_engine(_railway_pg_url())
    with engine.connect() as conn:
        row = _fetch_row(conn, NLCF_ID)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, indent=2, sort_keys=True, default=_json_default) + "\n"
    SNAPSHOT_PATH.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest()
    print(f"SNAPSHOT_PATH={SNAPSHOT_PATH}")
    print(f"SHA256={digest}")
    print(f"version={row['version']}")
    return 0


def cmd_apply() -> int:
    if not SNAPSHOT_PATH.is_file():
        print("STOP: snapshot missing — refuse mutation", file=sys.stderr)
        return 2

    snap_bytes = SNAPSHOT_PATH.read_bytes()
    snap_sha = hashlib.sha256(snap_bytes).hexdigest()
    snapshot = json.loads(snap_bytes.decode("utf-8"))
    committed_doc = json.loads(COMMITTED.read_text(encoding="utf-8"))
    # TEMPLATE_INSTANCE may be {sections: [...]} or bare list / wrapped
    if isinstance(committed_doc, list):
        committed_sections = committed_doc
    elif "report_sections_json" in committed_doc:
        committed_sections = committed_doc["report_sections_json"]
    elif "sections" in committed_doc:
        committed_sections = committed_doc["sections"]
    else:
        # instance file top-level often has report_sections under a key
        committed_sections = committed_doc.get("report_sections") or committed_doc.get(
            "template", {}
        ).get("report_sections_json")
        if committed_sections is None:
            # Try common wrapper used in this repo
            for k, v in committed_doc.items():
                if isinstance(v, list) and v and isinstance(v[0], dict) and "section_key" in v[0]:
                    committed_sections = v
                    break
    if not committed_sections:
        print("STOP: could not locate sections in TEMPLATE_INSTANCE_NLCF.json", file=sys.stderr)
        return 2

    committed_ci = _section(committed_sections, SECTION_KEY)
    if not committed_ci or "indicator_requirements" not in committed_ci:
        print("STOP: committed community_involvement.indicator_requirements missing", file=sys.stderr)
        return 2

    engine = create_engine(_railway_pg_url())
    with engine.begin() as conn:
        live = _fetch_row(conn, NLCF_ID)
        # Sanity: live must match snapshot pre-mutation
        if json.dumps(live["report_sections_json"], sort_keys=True, default=_json_default) != json.dumps(
            snapshot["report_sections_json"], sort_keys=True, default=_json_default
        ):
            print("STOP: live row diverged from snapshot since capture — refuse mutation", file=sys.stderr)
            return 2

        fcdo_before = dict(
            conn.execute(
                text(
                    """
                    SELECT id, version,
                           md5(report_sections_json::text) AS sections_md5,
                           md5(row_to_json(t)::text) AS row_md5
                    FROM funder_report_templates t
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": FCDO_ID},
            ).mappings().one()
        )

        live_sections = deepcopy(live["report_sections_json"])
        live_ci = _section(live_sections, SECTION_KEY)
        if live_ci is None:
            print("STOP: live community_involvement section missing", file=sys.stderr)
            return 2

        diffs = _diff_other_fields(live_ci, committed_ci)
        if diffs:
            print("STOP: community_involvement diverges outside indicator_requirements:")
            for d in diffs:
                print(f"  DIFF {d}")
            return 3

        before_ir = deepcopy(live_ci.get("indicator_requirements"))
        after_ir = deepcopy(committed_ci["indicator_requirements"])
        live_ci["indicator_requirements"] = after_ir
        new_version = int(live["version"]) + 1

        conn.execute(
            text(
                """
                UPDATE funder_report_templates
                SET report_sections_json = CAST(:sections AS jsonb),
                    version = :version,
                    updated_at = now()
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {
                "sections": json.dumps(live_sections, default=_json_default),
                "version": new_version,
                "id": NLCF_ID,
            },
        )

        readback = _fetch_row(conn, NLCF_ID)
        rb_ci = _section(readback["report_sections_json"], SECTION_KEY)
        ir = (rb_ci or {}).get("indicator_requirements") or {}
        flag_a = ir.get("community_participation_examples", {}).get(
            "elevate_on_proposal_failure"
        )
        flag_b = ir.get("partner_or_local_collaboration_examples", {}).get(
            "elevate_on_proposal_failure"
        )

        # Every other section byte-identical to snapshot
        snap_sections = snapshot["report_sections_json"]
        rb_sections = readback["report_sections_json"]
        section_failures: list[str] = []
        snap_by_key = {
            s["section_key"]: s for s in snap_sections if isinstance(s, dict)
        }
        rb_by_key = {s["section_key"]: s for s in rb_sections if isinstance(s, dict)}
        if set(snap_by_key) != set(rb_by_key):
            section_failures.append(
                f"section_key set mismatch snap={sorted(snap_by_key)} rb={sorted(rb_by_key)}"
            )
        for key in sorted(snap_by_key):
            if key == SECTION_KEY:
                # Only indicator_requirements may change
                snap_s = deepcopy(snap_by_key[key])
                rb_s = deepcopy(rb_by_key[key])
                snap_s.pop("indicator_requirements", None)
                rb_s.pop("indicator_requirements", None)
                if json.dumps(snap_s, sort_keys=True, default=_json_default) != json.dumps(
                    rb_s, sort_keys=True, default=_json_default
                ):
                    section_failures.append(
                        f"{key}: non-indicator_requirements fields changed"
                    )
                continue
            if json.dumps(snap_by_key[key], sort_keys=True, default=_json_default) != json.dumps(
                rb_by_key[key], sort_keys=True, default=_json_default
            ):
                section_failures.append(f"{key}: changed vs snapshot")

        fcdo_after = dict(
            conn.execute(
                text(
                    """
                    SELECT id, version,
                           md5(report_sections_json::text) AS sections_md5,
                           md5(row_to_json(t)::text) AS row_md5
                    FROM funder_report_templates t
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": FCDO_ID},
            ).mappings().one()
        )
        fcdo_untouched = (
            str(fcdo_before["id"]) == str(fcdo_after["id"])
            and fcdo_before["version"] == fcdo_after["version"]
            and fcdo_before["sections_md5"] == fcdo_after["sections_md5"]
            and fcdo_before["row_md5"] == fcdo_after["row_md5"]
        )

        ok_flags = flag_a is True and flag_b is True
        ok_version = int(readback["version"]) == new_version
        ok_sections = not section_failures

        evidence = {
            "snapshot_sha256": snap_sha,
            "snapshot_path": str(SNAPSHOT_PATH),
            "before_indicator_requirements": before_ir,
            "after_indicator_requirements": after_ir,
            "applied_diff": {
                "community_involvement.indicator_requirements": {
                    "from": before_ir,
                    "to": after_ir,
                },
                "version": {"from": snapshot["version"], "to": new_version},
            },
            "readback": {
                "elevate_community_participation_examples": flag_a,
                "elevate_partner_or_local_collaboration_examples": flag_b,
                "version": readback["version"],
                "other_sections_byte_identical": ok_sections,
                "section_failures": section_failures,
                "fcdo_untouched": fcdo_untouched,
            },
            "fcdo_before": {
                "id": str(fcdo_before["id"]),
                "version": fcdo_before["version"],
                "sections_md5": fcdo_before["sections_md5"],
                "row_md5": fcdo_before["row_md5"],
            },
            "fcdo_after": {
                "id": str(fcdo_after["id"]),
                "version": fcdo_after["version"],
                "sections_md5": fcdo_after["sections_md5"],
                "row_md5": fcdo_after["row_md5"],
            },
        }
        print(json.dumps(evidence, indent=2, default=_json_default))

        if not (ok_flags and ok_version and ok_sections and fcdo_untouched):
            print("VERIFICATION_FAILED — rolling back from snapshot", file=sys.stderr)
            conn.execute(
                text(
                    """
                    UPDATE funder_report_templates
                    SET report_sections_json = CAST(:sections AS jsonb),
                        format_rules_json = CAST(:format_rules AS jsonb),
                        terminology_map_json = CAST(:terminology AS jsonb),
                        funder_name = :funder_name,
                        template_name = :template_name,
                        region = :region,
                        reporting_frequency = :reporting_frequency,
                        docx_template_ref = :docx_template_ref,
                        is_active = :is_active,
                        version = :version,
                        updated_at = now()
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {
                    "sections": json.dumps(
                        snapshot["report_sections_json"], default=_json_default
                    ),
                    "format_rules": json.dumps(
                        snapshot["format_rules_json"], default=_json_default
                    ),
                    "terminology": json.dumps(
                        snapshot["terminology_map_json"], default=_json_default
                    ),
                    "funder_name": snapshot["funder_name"],
                    "template_name": snapshot["template_name"],
                    "region": snapshot["region"],
                    "reporting_frequency": snapshot["reporting_frequency"],
                    "docx_template_ref": snapshot["docx_template_ref"],
                    "is_active": snapshot["is_active"],
                    "version": snapshot["version"],
                    "id": NLCF_ID,
                },
            )
            restored = _fetch_row(conn, NLCF_ID)
            print(
                json.dumps(
                    {
                        "rollback": "restored",
                        "restored_version": restored["version"],
                        "restored_sha_of_sections": hashlib.sha256(
                            json.dumps(
                                restored["report_sections_json"],
                                sort_keys=True,
                                default=_json_default,
                            ).encode()
                        ).hexdigest(),
                    },
                    indent=2,
                )
            )
            return 4

    print("PHASE_A_OK")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("snapshot", "apply"))
    args = p.parse_args()
    if args.action == "snapshot":
        return cmd_snapshot()
    return cmd_apply()


if __name__ == "__main__":
    raise SystemExit(main())
