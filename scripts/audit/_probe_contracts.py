import json
import os

from scripts.audit import _common as C

C.bootstrap_db_env()
import app.models  # noqa
from sqlalchemy import create_engine, text

rid = "3347590c-5b4f-4443-8a3d-a5ae455932e2"
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    rep = c.execute(text(
        "SELECT user_id, status, created_at, updated_at FROM donor_reports WHERE id=CAST(:r AS uuid)"),
        {"r": rid}).mappings().first()
    uid = str(rep["user_id"])
    ledger = c.execute(text(
        "SELECT action_type AS event_type, idempotency_key, created_at FROM usage_ledger "
        "WHERE user_id=CAST(:u AS uuid) ORDER BY created_at"),
        {"u": uid}).mappings().all()
    # enum spot-check across all report_jobs stages/statuses seen in audit
    stages = c.execute(text("SELECT DISTINCT stage FROM report_jobs")).scalars().all()
    statuses = c.execute(text("SELECT DISTINCT status FROM report_jobs")).scalars().all()
    classes = c.execute(text("SELECT DISTINCT classification FROM uploaded_documents WHERE classification IS NOT NULL")).scalars().all()

print("report.status =", rep["status"])
print("created_at == updated_at (no onupdate) :", rep["created_at"] == rep["updated_at"],
      "| created=", rep["created_at"], "updated=", rep["updated_at"])
from collections import Counter
evt = Counter(l["event_type"] for l in ledger)
print("usage_ledger event_type counts for FCDO user:", dict(evt))
print("REPORT_CREATE rows:", [l["idempotency_key"] for l in ledger if l["event_type"] == "REPORT_CREATE"])
print("REPORT_EXPORT present:", any(l["event_type"] == "REPORT_EXPORT" for l in ledger))
print("distinct report_jobs.stage:", sorted(stages))
print("distinct report_jobs.status:", sorted(statuses))
print("distinct classifications:", sorted(classes))
C.write_artifact("contracts_probe.json", {
    "report_status": rep["status"],
    "created_at": str(rep["created_at"]),
    "updated_at": str(rep["updated_at"]),
    "updated_equals_created": rep["created_at"] == rep["updated_at"],
    "ledger_event_counts": dict(evt),
    "report_export_written": any(l["event_type"] == "REPORT_EXPORT" for l in ledger),
    "distinct_stages": sorted(stages),
    "distinct_statuses": sorted(statuses),
    "distinct_classifications": sorted(classes),
})
