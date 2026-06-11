#!/usr/bin/env python3
"""Extract B3 gap-stage JSON, exports, ledger traces for P3 exit evidence."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.audit import _common as C

DR = ROOT / "docs/artefacts/me_module/audits/dynamic_run"
SNAP = ROOT / "docs/artefacts/me_module/audits/snapshots"

REPORT_IDS = (
    "7cdcc3a8-e15e-449b-991c-b79d99c918ec",
    "df7450dc-5d63-4461-98fc-9f09dea44a70",
)


def main() -> None:
    for name in ("walk_p3_b3_fcdo_7cdcc3a8.json", "walk_p3_b3_nlcf_df7450dc.json"):
        w = json.loads((DR / name).read_text(encoding="utf-8"))
        rid = w["report_id"]
        gap = w.get("snapshots", {}).get("after_gap") or {}
        gap_report = gap.get("report") or {}
        gap_json = gap_report.get("gap_analysis_json") or {}
        gc = w.get("snapshots", {}).get("gap_check_endpoint") or {}
        out = SNAP / f"p3_b3_gap_stage_{rid[:8]}.json"
        payload = {
            "report_id": rid,
            "owner_email": w.get("snapshots", {}).get("owner_email"),
            "gap_analysis_json": gap_json,
            "gap_check_endpoint": gc,
            "agent_trace_gap_stage": (w.get("final_job") or {})
            .get("agent_trace_json", {})
            .get("stages", {})
            .get("gap"),
        }
        out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)}")

    for src_name, dst_name in (
        ("export_7cdcc3a8.docx", "p3_b3_export_fcdo_7cdcc3a8.docx"),
        ("export_df7450dc.docx", "p3_b3_export_nlcf_df7450dc.docx"),
    ):
        src = DR / src_name
        if src.exists():
            dst = SNAP / dst_name
            shutil.copy2(src, dst)
            print(f"copied {dst.relative_to(ROOT)}")

    C.bootstrap_db_env()
    engine = create_engine(C.os.environ["DATABASE_URL"])
    evidence: dict = {}
    for rid in REPORT_IDS:
        with engine.connect() as c:
            job = c.execute(
                text(
                    """
                    SELECT requeue_count, agent_trace_json, stage, status
                    FROM report_jobs
                    WHERE donor_report_id = CAST(:r AS uuid)
                    ORDER BY started_at DESC LIMIT 1
                    """
                ),
                {"r": rid},
            ).mappings().first()
            rep = c.execute(
                text("SELECT user_id, status FROM donor_reports WHERE id = CAST(:r AS uuid)"),
                {"r": rid},
            ).mappings().first()
            ledger = c.execute(
                text(
                    """
                    SELECT action_type, idempotency_key, created_at
                    FROM usage_ledger
                    WHERE user_id = CAST(:u AS uuid)
                      AND action_type = 'REPORT_CREATE'
                    ORDER BY created_at
                    """
                ),
                {"u": str(rep["user_id"])},
            ).mappings().all()
        trace = (dict(job).get("agent_trace_json") if job else None) or {}
        degraded = 0
        for st in (trace.get("stages") or {}).values():
            if isinstance(st, dict) and st.get("degraded_pass_through"):
                degraded += int(st["degraded_pass_through"])
        evidence[rid[:8]] = {
            "report_id": rid,
            "requeue_count": dict(job).get("requeue_count") if job else None,
            "degraded_pass_through_sum": degraded,
            "report_create_ledger": [dict(x) for x in ledger],
            "report_status": dict(rep).get("status") if rep else None,
        }

    out_path = SNAP / "p3_b3_ledger_traces.json"
    out_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, default=str))


if __name__ == "__main__":
    main()
