"""D-061 Phase A — read-only fleet scan for orphan conflict keys.

STOP if any orphan exists outside the authorized report id.
Does not mutate production. Run only after Package 1 code is deployed.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "audit"))

import _common as C  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

AUTHORIZED_REPORT_ID = "cb090edb-715b-41cb-b3be-61c006fbdb55"
OUT_DIR = ROOT / "docs" / "artefacts" / "me_module" / "audits"


def _orphan_keys(kb: dict) -> list[str]:
    conflicts = kb.get("conflicts") if isinstance(kb, dict) else None
    facts = kb.get("facts") if isinstance(kb, dict) else None
    if not isinstance(conflicts, list):
        return []
    if not isinstance(facts, dict):
        facts = {}
    orphans: list[str] = []
    for conflict in conflicts:
        if not isinstance(conflict, dict):
            continue
        key = conflict.get("fact_key")
        if not key:
            continue
        key = str(key)
        if not isinstance(facts.get(key), dict):
            orphans.append(key)
    return orphans


def main() -> int:
    C.bootstrap_db_env()
    engine = create_engine(os.environ["DATABASE_URL"])
    sql = text(
        """
        SELECT
          id::text AS donor_report_id,
          status::text AS status,
          knowledge_bank_json->>'gate1_confirmed_at' AS gate1_confirmed_at,
          knowledge_bank_json AS knowledge_bank_json
        FROM donor_reports
        WHERE knowledge_bank_json IS NOT NULL
          AND jsonb_typeof(knowledge_bank_json->'conflicts') = 'array'
          AND jsonb_array_length(knowledge_bank_json->'conflicts') > 0
        """
    )
    orphans: list[dict] = []
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    for row in rows:
        kb = row["knowledge_bank_json"] or {}
        if isinstance(kb, str):
            kb = json.loads(kb)
        keys = _orphan_keys(kb)
        if not keys:
            continue
        orphans.append(
            {
                "donor_report_id": row["donor_report_id"],
                "status": row["status"],
                "gate1_confirmed_at": row["gate1_confirmed_at"],
                "orphan_conflict_keys": keys,
            }
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_path = OUT_DIR / f"GATE1_ORPHAN_FLEET_SCAN_{ts}.json"
    extra = [o for o in orphans if o["donor_report_id"] != AUTHORIZED_REPORT_ID]
    target = [o for o in orphans if o["donor_report_id"] == AUTHORIZED_REPORT_ID]
    verdict = "GREEN"
    stop_reasons: list[str] = []
    if extra:
        verdict = "STOP"
        stop_reasons.append(
            f"{len(extra)} orphan report(s) outside authorized id {AUTHORIZED_REPORT_ID}"
        )
    if not target:
        # Not necessarily STOP — authorized report may already be repaired or gone.
        pass
    elif len(target) == 1 and len(target[0]["orphan_conflict_keys"]) > 1:
        verdict = "STOP"
        stop_reasons.append("authorized report has more than one orphan conflict key")
    elif target and target[0].get("gate1_confirmed_at"):
        verdict = "STOP"
        stop_reasons.append("authorized report already has gate1_confirmed_at")

    payload = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "authorized_report_id": AUTHORIZED_REPORT_ID,
        "reports_with_conflicts_scanned": len(rows),
        "orphan_reports": orphans,
        "extra_orphan_reports": extra,
        "authorized_orphan": target[0] if target else None,
        "verdict": verdict,
        "stop_reasons": stop_reasons,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "verdict": verdict, "orphan_count": len(orphans)}, indent=2))
    if verdict == "STOP":
        print("STOP: do not repair. See evidence JSON.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
