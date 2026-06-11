#!/usr/bin/env python3
"""Extract P3-7 re-walk gap-stage JSON, exports, ledger traces for evidence bundle."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.audit import _common as C

DR = ROOT / "docs/artefacts/me_module/audits/dynamic_run"
SNAP = ROOT / "docs/artefacts/me_module/audits/snapshots"


def extract_from_walk(walk_path: Path, *, prefix: str) -> dict:
    w = json.loads(walk_path.read_text(encoding="utf-8"))
    rid = w["report_id"]
    gap = w.get("snapshots", {}).get("after_gap") or {}
    gap_report = gap.get("report") or {}
    gap_json = gap_report.get("gap_analysis_json") or {}
    gc = w.get("snapshots", {}).get("gap_check_endpoint") or {}
    out = SNAP / f"{prefix}_gap_stage_{rid[:8]}.json"
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

    export_src = DR / f"export_{rid[:8]}.docx"
    if export_src.exists():
        dst = SNAP / f"{prefix}_export_{rid[:8]}.docx"
        shutil.copy2(export_src, dst)
        print(f"copied {dst.relative_to(ROOT)}")

    return {"report_id": rid, "walk": str(walk_path), "verdict": w.get("verdict"), "cost": w.get("cost")}


def ledger_traces(report_ids: list[str]) -> None:
    C.bootstrap_db_env()
    from sqlalchemy import create_engine, text

    engine = create_engine(C.os.environ["DATABASE_URL"])
    evidence: dict = {}
    for rid in report_ids:
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
                      AND idempotency_key LIKE :pat
                    ORDER BY created_at
                    """
                ),
                {"u": str(rep["user_id"]), "pat": f"%{rid}%"},
            ).mappings().all()
        trace = (dict(job).get("agent_trace_json") if job else None) or {}
        evidence[rid[:8]] = {
            "report_id": rid,
            "report_status": rep["status"] if rep else None,
            "requeue_count": dict(job).get("requeue_count") if job else None,
            "job_stage": dict(job).get("stage") if job else None,
            "job_status": dict(job).get("status") if job else None,
            "stages": trace.get("stages") if trace else {},
            "ledger_rows": [dict(x) for x in ledger],
        }
    out_path = SNAP / "p3_7_ledger_traces.json"
    out_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {out_path.relative_to(ROOT)}")


def main() -> int:
    walks = list(DR.glob("walk_p3_7_rewalk_*.json"))
    if not walks:
        print("no p3_7 walk artefacts found", file=sys.stderr)
        return 1
    meta: list[dict] = []
    ids: list[str] = []
    for walk_path in sorted(walks):
        prefix = "p3_7_fcdo" if "fcdo" in walk_path.name else "p3_7_nlcf"
        meta.append(extract_from_walk(walk_path, prefix=prefix))
        ids.append(json.loads(walk_path.read_text())["report_id"])
    ledger_traces(ids)
    summary_path = SNAP / "p3_7_walk_summary.json"
    summary_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
