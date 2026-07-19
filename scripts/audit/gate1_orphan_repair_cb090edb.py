"""D-061 Phase B — one-report orphan repair using product normalizer.

Run ONLY after Phase A fleet scan is GREEN and Package 1 is deployed.
Default is dry-run. Pass --apply with --approved-preimage-sha256 to write.

Creates resolvability only — never sets resolved_value.

Apply guarantee: apply starts only when the live row's canonical preimage SHA-256
exactly matches the dry-run preimage the owner authorized. No silent
re-normalization of a drifted row.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "audit"))

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


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_text(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def field_level_kb_diff(preimage: dict[str, Any], postimage: dict[str, Any]) -> dict[str, Any]:
    """Field-level diff for owner inspection before apply (R1)."""
    pre_facts = dict(preimage.get("facts") or {})
    post_facts = dict(postimage.get("facts") or {})
    facts_added: dict[str, Any] = {}
    facts_changed: dict[str, Any] = {}
    facts_removed = sorted(k for k in pre_facts if k not in post_facts)

    for key, post_fact in post_facts.items():
        if key not in pre_facts:
            facts_added[key] = post_fact
            continue
        pre_fact = pre_facts[key]
        if not isinstance(pre_fact, dict) or not isinstance(post_fact, dict):
            if pre_fact != post_fact:
                facts_changed[key] = {"from": pre_fact, "to": post_fact}
            continue
        field_changes: dict[str, Any] = {}
        for field, new_val in post_fact.items():
            if pre_fact.get(field) != new_val:
                field_changes[field] = {"from": pre_fact.get(field), "to": new_val}
        for field, old_val in pre_fact.items():
            if field not in post_fact:
                field_changes[field] = {"from": old_val, "to": None}
        if field_changes:
            facts_changed[key] = field_changes

    pre_trace = (preimage.get("agent_trace") or {}) if isinstance(
        preimage.get("agent_trace"), dict
    ) else {}
    post_trace = (postimage.get("agent_trace") or {}) if isinstance(
        postimage.get("agent_trace"), dict
    ) else {}
    pre_repairs = list(pre_trace.get("conflict_integrity_repairs") or [])
    post_repairs = list(post_trace.get("conflict_integrity_repairs") or [])

    top_added = {
        k: postimage[k]
        for k in postimage
        if k not in preimage and k not in {"facts", "conflicts", "agent_trace"}
    }
    top_changed = {
        k: {"from": preimage.get(k), "to": postimage.get(k)}
        for k in preimage
        if k in postimage
        and k not in {"facts", "conflicts", "agent_trace"}
        and preimage.get(k) != postimage.get(k)
    }

    return {
        "facts_added": facts_added,
        "facts_changed": facts_changed,
        "facts_removed": facts_removed,
        "conflict_integrity_repairs_added": post_repairs[len(pre_repairs) :],
        "top_level_added": top_added,
        "top_level_changed": top_changed,
        "canonical_stub": facts_added.get("reporting_period.end"),
        "provenance_only_markers": {
            key: (post_facts[key] or {}).get("provenance_only_for")
            for key in sorted(post_facts)
            if isinstance(post_facts.get(key), dict)
            and (post_facts[key] or {}).get("provenance_only_for")
            and (
                key not in pre_facts
                or (pre_facts.get(key) or {}).get("provenance_only_for")
                != (post_facts[key] or {}).get("provenance_only_for")
            )
        },
    }


def prepare_repair(preimage: dict) -> dict:
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
    import _common as C  # local import — keeps pure helpers importable in tests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the one-row write (requires --approved-preimage-sha256)",
    )
    parser.add_argument(
        "--approved-preimage-sha256",
        default=None,
        help=(
            "Canonical SHA-256 of the dry-run preimage the owner authorized. "
            "Required with --apply. Apply STOPs unless the live row matches exactly."
        ),
    )
    args = parser.parse_args()

    if args.apply and not args.approved_preimage_sha256:
        raise SystemExit(
            "STOP: --apply requires --approved-preimage-sha256=<dry-run preimage_sha256>. "
            "Guarantee: apply starts only from the exact knowledge_bank_json preimage "
            "the owner inspected in dry-run; refusing to run without that anchor."
        )

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
    pre_hash = sha256_text(canonical_json(preimage))

    if args.apply:
        approved = str(args.approved_preimage_sha256).strip().lower()
        if pre_hash != approved:
            raise SystemExit(
                "STOP: live knowledge_bank_json does not match --approved-preimage-sha256. "
                "Guarantee refused: apply will not start from a drifted row and will not "
                "silently re-normalize a different preimage. Re-run dry-run, inspect the "
                f"new evidence, and re-authorize. live_preimage_sha256={pre_hash} "
                f"approved_preimage_sha256={approved}"
            )

    repaired = prepare_repair(preimage)
    post_hash = sha256_text(canonical_json(repaired))
    diff = field_level_kb_diff(preimage, repaired)

    pre_path = OUT_DIR / f"GATE1_ORPHAN_REPAIR_PREIMAGE_{ts}.json"
    post_path = OUT_DIR / f"GATE1_ORPHAN_REPAIR_POSTIMAGE_{ts}.json"
    pre_path.write_text(json.dumps(preimage, indent=2, default=str) + "\n", encoding="utf-8")
    post_path.write_text(json.dumps(repaired, indent=2, default=str) + "\n", encoding="utf-8")

    evidence = {
        "mode": "apply" if args.apply else "dry-run",
        "donor_report_id": AUTHORIZED_REPORT_ID,
        "preimage_sha256": pre_hash,
        "postimage_sha256": post_hash,
        "preimage_path": str(pre_path),
        "postimage_path": str(post_path),
        "preimage": preimage,
        "postimage": repaired,
        "field_level_diff": diff,
        "agent_trace_repairs": (repaired.get("agent_trace") or {}).get(
            "conflict_integrity_repairs"
        ),
        "approved_preimage_sha256": args.approved_preimage_sha256,
        "apply_guarantee": (
            "Apply starts only when live canonical preimage SHA-256 equals the "
            "owner-authorized dry-run preimage SHA-256; then the product normalizer "
            "runs on that matched preimage under FOR UPDATE."
        ),
        "applied": False,
        "rows_updated": 0,
    }

    if not args.apply:
        out = OUT_DIR / f"GATE1_ORPHAN_REPAIR_DRYRUN_{ts}.json"
        out.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "out": str(out),
                    "preimage_sha256": pre_hash,
                    "postimage_sha256": post_hash,
                    "preimage_path": str(pre_path),
                    "postimage_path": str(post_path),
                    "field_level_diff": diff,
                    "apply_hint": (
                        f"python scripts/audit/gate1_orphan_repair_cb090edb.py "
                        f"--apply --approved-preimage-sha256={pre_hash}"
                    ),
                },
                indent=2,
                default=str,
            )
        )
        return 0

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
        locked_hash = sha256_text(canonical_json(current))
        approved = str(args.approved_preimage_sha256).strip().lower()
        if locked_hash != approved:
            raise SystemExit(
                "STOP: row changed under lock vs --approved-preimage-sha256. "
                "Guarantee refused: apply will not start from a drifted preimage. "
                f"locked_preimage_sha256={locked_hash} approved_preimage_sha256={approved}"
            )
        # Recompute postimage from the locked matched preimage (same bytes as authorized).
        locked_repaired = prepare_repair(current)
        result = conn.execute(
            update_sql,
            {
                "rid": AUTHORIZED_REPORT_ID,
                "kb": json.dumps(locked_repaired, default=str),
            },
        )
        if result.rowcount != 1:
            raise SystemExit(f"STOP: update rowcount={result.rowcount}")
        evidence["applied"] = True
        evidence["rows_updated"] = 1
        evidence["postimage"] = locked_repaired
        evidence["postimage_sha256"] = sha256_text(canonical_json(locked_repaired))
        evidence["field_level_diff"] = field_level_kb_diff(current, locked_repaired)

    out = OUT_DIR / f"GATE1_ORPHAN_REPAIR_APPLIED_{ts}.json"
    out.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "applied": True, "preimage_sha256": pre_hash}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
