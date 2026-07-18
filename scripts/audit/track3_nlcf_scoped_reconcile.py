#!/usr/bin/env python3
"""Track 3 STOP-A release: full-row drift diff + scoped community_involvement reconcile.

Uses existing snapshot (64e6ebc6…) as rollback source — never overwrites it.
Railway CLI via cmd.exe only.
"""
from __future__ import annotations

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
DRIFT_OUT = (
    REPO
    / "docs/artefacts/me_module/audits/TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json"
)
EVIDENCE_OUT = (
    REPO
    / "docs/artefacts/me_module/audits/TRACK3_PHASE_A_SCOPED_RECONCILE_EVIDENCE_2026-07-18.json"
)
EXPECTED_SNAP_SHA = "64e6ebc60be775d20e451a51cd796f23e3829726c08617d8f580e8e808661afa"
SECTION_KEY = "community_involvement"
RECONCILE_KEYS = ("fact_namespaces", "source_section_labels", "indicator_requirements")


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Not JSON serializable: {type(obj)!r}")


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=_json_default)


def _railway_pg_url() -> str:
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


def _fcdo_fingerprint(conn) -> dict:
    return dict(
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


def build_drift(snapshot: dict, committed: dict) -> dict:
    """Field-level diff of entire live snapshot row vs committed instance."""
    diffs: list[dict] = []
    scalar_keys = [
        "funder_name",
        "template_name",
        "region",
        "reporting_frequency",
        "docx_template_ref",
        "is_active",
        "version",
    ]
    for k in scalar_keys:
        lv, cv = snapshot.get(k), committed.get(k)
        if _canon(lv) != _canon(cv):
            diffs.append({"path": k, "live": lv, "committed": cv})

    for blob in ("format_rules_json", "terminology_map_json"):
        if _canon(snapshot.get(blob)) != _canon(committed.get(blob)):
            # nested key-level
            live_b = snapshot.get(blob) or {}
            comm_b = committed.get(blob) or {}
            if not isinstance(live_b, dict) or not isinstance(comm_b, dict):
                diffs.append({"path": blob, "live": live_b, "committed": comm_b})
            else:
                keys = set(live_b) | set(comm_b)
                for sk in sorted(keys):
                    if _canon(live_b.get(sk, "<MISSING>")) != _canon(
                        comm_b.get(sk, "<MISSING>")
                    ):
                        diffs.append(
                            {
                                "path": f"{blob}.{sk}",
                                "live": live_b.get(sk, "<MISSING>"),
                                "committed": comm_b.get(sk, "<MISSING>"),
                            }
                        )

    live_secs = {
        s["section_key"]: s
        for s in (snapshot.get("report_sections_json") or [])
        if isinstance(s, dict) and "section_key" in s
    }
    comm_secs = {
        s["section_key"]: s
        for s in (committed.get("report_sections_json") or [])
        if isinstance(s, dict) and "section_key" in s
    }
    for sk in sorted(set(live_secs) | set(comm_secs)):
        if sk not in live_secs:
            diffs.append(
                {
                    "path": f"report_sections_json[{sk}]",
                    "live": "<MISSING>",
                    "committed": comm_secs[sk],
                }
            )
            continue
        if sk not in comm_secs:
            diffs.append(
                {
                    "path": f"report_sections_json[{sk}]",
                    "live": live_secs[sk],
                    "committed": "<MISSING>",
                }
            )
            continue
        lv, cv = live_secs[sk], comm_secs[sk]
        field_keys = set(lv) | set(cv)
        for fk in sorted(field_keys):
            if _canon(lv.get(fk, "<MISSING>")) != _canon(cv.get(fk, "<MISSING>")):
                diffs.append(
                    {
                        "path": f"report_sections_json[{sk}].{fk}",
                        "live": lv.get(fk, "<MISSING>"),
                        "committed": cv.get(fk, "<MISSING>"),
                    }
                )

    return {
        "snapshot_sha256": hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest(),
        "live_version": snapshot.get("version"),
        "committed_version": committed.get("version"),
        "divergence_count": len(diffs),
        "divergences": diffs,
    }


def cmd_drift() -> int:
    if not SNAPSHOT_PATH.is_file():
        print("STOP: snapshot missing", file=sys.stderr)
        return 2
    snap_sha = hashlib.sha256(SNAPSHOT_PATH.read_bytes()).hexdigest()
    if snap_sha != EXPECTED_SNAP_SHA:
        print(
            f"STOP: snapshot SHA mismatch expected={EXPECTED_SNAP_SHA} got={snap_sha}",
            file=sys.stderr,
        )
        return 2
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    drift = build_drift(snapshot, committed)
    DRIFT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DRIFT_OUT.write_text(
        json.dumps(drift, indent=2, default=_json_default) + "\n", encoding="utf-8"
    )
    print(f"DRIFT_OUT={DRIFT_OUT}")
    print(f"divergence_count={drift['divergence_count']}")
    for d in drift["divergences"]:
        print(f"  DIFF {d['path']}")
    return 0


def cmd_apply() -> int:
    if not SNAPSHOT_PATH.is_file():
        print("STOP: snapshot missing", file=sys.stderr)
        return 2
    snap_bytes = SNAPSHOT_PATH.read_bytes()
    snap_sha = hashlib.sha256(snap_bytes).hexdigest()
    if snap_sha != EXPECTED_SNAP_SHA:
        print(
            f"STOP: snapshot SHA mismatch expected={EXPECTED_SNAP_SHA} got={snap_sha}",
            file=sys.stderr,
        )
        return 2
    snapshot = json.loads(snap_bytes.decode("utf-8"))
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    committed_ci = _section(committed["report_sections_json"], SECTION_KEY)
    if not committed_ci:
        print("STOP: committed community_involvement missing", file=sys.stderr)
        return 2

    engine = create_engine(_railway_pg_url())
    with engine.begin() as conn:
        live = _fetch_row(conn, NLCF_ID)
        if _canon(live["report_sections_json"]) != _canon(snapshot["report_sections_json"]):
            print(
                "STOP: live report_sections_json diverged from snapshot — refuse mutation",
                file=sys.stderr,
            )
            return 2
        if int(live["version"]) != int(snapshot["version"]):
            print(
                f"STOP: live version {live['version']} != snapshot {snapshot['version']}",
                file=sys.stderr,
            )
            return 2

        fcdo_before = _fcdo_fingerprint(conn)
        live_sections = deepcopy(live["report_sections_json"])
        live_ci = _section(live_sections, SECTION_KEY)
        if live_ci is None:
            print("STOP: live community_involvement missing", file=sys.stderr)
            return 2

        before_fields = {k: deepcopy(live_ci.get(k, "<MISSING>")) for k in RECONCILE_KEYS}
        for k in RECONCILE_KEYS:
            live_ci[k] = deepcopy(committed_ci[k])
        after_fields = {k: deepcopy(live_ci[k]) for k in RECONCILE_KEYS}
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
        rb_ci = _section(readback["report_sections_json"], SECTION_KEY) or {}
        field_ok = all(
            _canon(rb_ci.get(k)) == _canon(committed_ci[k]) for k in RECONCILE_KEYS
        )

        section_failures: list[str] = []
        snap_by = {
            s["section_key"]: s
            for s in snapshot["report_sections_json"]
            if isinstance(s, dict)
        }
        rb_by = {
            s["section_key"]: s
            for s in readback["report_sections_json"]
            if isinstance(s, dict)
        }
        if set(snap_by) != set(rb_by):
            section_failures.append("section_key set mismatch")
        for key in sorted(snap_by):
            if key == SECTION_KEY:
                snap_s = deepcopy(snap_by[key])
                rb_s = deepcopy(rb_by[key])
                for k in RECONCILE_KEYS:
                    snap_s.pop(k, None)
                    rb_s.pop(k, None)
                if _canon(snap_s) != _canon(rb_s):
                    section_failures.append(
                        f"{key}: fields outside reconcile set changed"
                    )
                continue
            if _canon(snap_by[key]) != _canon(rb_by[key]):
                section_failures.append(f"{key}: changed vs snapshot")

        # Non-section columns (except version/updated_at) byte-identical to snapshot
        column_failures: list[str] = []
        for col in (
            "funder_name",
            "template_name",
            "region",
            "reporting_frequency",
            "format_rules_json",
            "terminology_map_json",
            "docx_template_ref",
            "is_active",
        ):
            if _canon(readback[col]) != _canon(snapshot[col]):
                column_failures.append(col)

        fcdo_after = _fcdo_fingerprint(conn)
        fcdo_untouched = (
            str(fcdo_before["id"]) == str(fcdo_after["id"])
            and fcdo_before["version"] == fcdo_after["version"]
            and fcdo_before["sections_md5"] == fcdo_after["sections_md5"]
            and fcdo_before["row_md5"] == fcdo_after["row_md5"]
        )

        ok = (
            field_ok
            and int(readback["version"]) == new_version
            and not section_failures
            and not column_failures
            and fcdo_untouched
        )

        evidence = {
            "snapshot_sha256": snap_sha,
            "snapshot_path": str(SNAPSHOT_PATH),
            "applied_diff": {
                "community_involvement": {
                    "from": before_fields,
                    "to": after_fields,
                },
                "version": {"from": snapshot["version"], "to": new_version},
            },
            "readback": {
                "three_fields_match_committed": field_ok,
                "reconciled_fields": {
                    k: rb_ci.get(k) for k in RECONCILE_KEYS
                },
                "version": readback["version"],
                "other_sections_byte_identical": not section_failures,
                "section_failures": section_failures,
                "other_columns_byte_identical": not column_failures,
                "column_failures": column_failures,
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
        EVIDENCE_OUT.write_text(
            json.dumps(evidence, indent=2, default=_json_default) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(evidence, indent=2, default=_json_default))

        if not ok:
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
            print("ROLLBACK_OK")
            return 4

    print("SCOPED_RECONCILE_OK")
    return 0


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("drift", "apply"):
        print("Usage: track3_nlcf_scoped_reconcile.py drift|apply", file=sys.stderr)
        return 2
    if sys.argv[1] == "drift":
        return cmd_drift()
    return cmd_apply()


if __name__ == "__main__":
    raise SystemExit(main())
