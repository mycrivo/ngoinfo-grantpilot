"""D-061 Phase B — one-report orphan repair using product normalizer.

Run ONLY after Phase A fleet scan is GREEN and Package 1 is deployed.
Default is dry-run. Pass --apply to perform compare-and-swap write.

Creates resolvability only — never sets resolved_value.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "audit"))

import _common as C  # noqa: E402
from app.reports.knowledge.conflict_integrity import (  # noqa: E402
    ensure_conflicts_materializable,
)
from sqlalchemy import create_engine, text  # noqa: E402

AUTHORIZED_REPORT_ID = "cb090edb-715b-41cb-b3be-61c006fbdb55"
OUT_DIR = ROOT / "docs" / "artefacts" / "me_module" / "audits"


def _as_dict(value: object) -> dict:
    if value is None:
        return {}
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return copy.deepcopy(value)
    raise TypeError(f"unexpected knowledge_bank_json type: {type(value)!r}")


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def _prepare(preimage: dict) -> dict:
    repaired = ensure_conflicts_materializable(
        copy.deepcopy(preimage),
        donor_report_id=AUTHORIZED_REPORT_ID,
        emit_log=True,
    )
    if "reporting_period.end" not in (repaired.get("facts") or {}):
        raise SystemExit("STOP: normalizer did not create reporting_period.end stub")
    stub = repaired["facts"]["reporting_period.end"]
    if stub.get("value") is not None:
        raise SystemExit("STOP: normalizer invented a value — abort")
    for conflict in repaired.get("conflicts") or []:
        if not isinstance(conflict, dict):
            continue
        if conflict.get("fact_key") == "reporting_period.end" and conflict.get(
            "resolved_value"
        ) is not None:
            raise SystemExit("STOP: resolved_value changed — abort")
    return repaired


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the one-row CAS write (default: dry-run only)",
    )
    args = parser.parse_args()

    C.bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    select_sql = text(
        """
        SELECT
          id::text AS donor_report_id,
          knowledge_bank_json,
          knowledge_bank_json->>'gate1_confirmed_at' AS gate1_confirmed_at
        FROM donor_reports
        WHERE id = CAST(:rid AS uuid)
        """
    )

    with engine.connect() as conn:
        row = conn.execute(select_sql, {"rid": AUTHORIZED_REPORT_ID}).mappings().first()
    if not row:
        raise SystemExit(f"report not found: {AUTHORIZED_REPORT_ID}")
    if row["gate1_confirmed_at"]:
        raise SystemExit("STOP: gate1_confirmed_at already set — abort repair")

    preimage = _as_dict(row["knowledge_bank_json"])
    pre_hash = _sha256(_canonical_json(preimage))
    repaired = _prepare(preimage)
    post_hash = _sha256(_canonical_json(repaired))

    pre_path = OUT_DIR / f"GATE1_ORPHAN_REPAIR_PREIMAGE_{ts}.json"
    pre_path.write_text(json.dumps(preimage, indent=2, default=str) + "\n", encoding="utf-8")

    evidence = {
        "mode": "apply" if args.apply else "dry-run",
        "donor_report_id": AUTHORIZED_REPORT_ID,
        "preimage_sha256": pre_hash,
        "postimage_sha256": post_hash,
        "preimage_path": str(pre_path),
        "agent_trace_repairs": (repaired.get("agent_trace") or {}).get(
            "conflict_integrity_repairs"
        ),
        "postimage_preview_facts_keys": sorted((repaired.get("facts") or {}).keys()),
        "applied": False,
        "rows_updated": 0,
    }

    if not args.apply:
        out = OUT_DIR / f"GATE1_ORPHAN_REPAIR_DRYRUN_{ts}.json"
        out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"out": str(out), **evidence}, indent=2))
        return 0

    # CAS: lock row, re-read, refuse if preimage hash drifted, then write.
    update_sql = text(
        """
        UPDATE donor_reports
        SET knowledge_bank_json = CAST(:kb AS jsonb),
            updated_at = NOW()
        WHERE id = CAST(:rid AS uuid)
        """
    )
    lock_sql = text(
        """
        SELECT knowledge_bank_json
        FROM donor_reports
        WHERE id = CAST(:rid AS uuid)
        FOR UPDATE
        """
    )
    with engine.begin() as conn:
        locked = conn.execute(lock_sql, {"rid": AUTHORIZED_REPORT_ID}).mappings().first()
        if not locked:
            raise SystemExit("STOP: report disappeared under lock")
        current = _as_dict(locked["knowledge_bank_json"])
        if _sha256(_canonical_json(current)) != pre_hash:
            raise SystemExit("STOP: row changed since dry-run snapshot — abort")
        result = conn.execute(
            update_sql,
            {
                "rid": AUTHORIZED_REPORT_ID,
                "kb": json.dumps(repaired, default=str),
            },
        )
        if result.rowcount != 1:
            raise SystemExit(f"STOP: update rowcount={result.rowcount}")
        evidence["applied"] = True
        evidence["rows_updated"] = 1

    out = OUT_DIR / f"GATE1_ORPHAN_REPAIR_APPLIED_{ts}.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), **evidence}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
