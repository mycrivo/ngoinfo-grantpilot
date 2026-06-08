"""R6 over-quota probe: create has no pre-check (work-then-reject limbo); the
charge point enforces and raises ForbiddenError(403 QUOTA_EXCEEDED)."""
import os
import time
import uuid

from scripts.audit import _common as C

C.bootstrap_db_env()
import app.models  # noqa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.errors import DomainError
from app.services.quota_service import (
    EVENT_REPORT_CREATE,
    enforce_report_create_quota,
    get_entitlements,
    record_usage,
)

email = f"audit-quota-{int(time.time())}@grantpilot-test.org"
session = C.mint_session(email, plan="IMPACT")
uid = uuid.UUID(session.user_id)

engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(bind=engine)
db = Session()

ent0 = get_entitlements(db, uid)
print("entitlements.reports (fresh):", ent0.get("reports"))

# Exhaust IMPACT report quota (limit 2) via two REPORT_CREATE ledger rows.
for i in range(2):
    record_usage(db, uid, EVENT_REPORT_CREATE,
                 idempotency_key=f"audit-quota-{uid}-{i}", commit=True)
ent1 = get_entitlements(db, uid)
print("entitlements.reports (after 2 charges):", ent1.get("reports"))

# (1) Does POST /api/reports pre-check quota? Expect NO (still 200 -> limbo).
r = C.create_report(session, template_id=C.FCDO_TEMPLATE_ID)
print("create AFTER quota exhausted -> status DRAFT, id:", r.get("id"), "status:", r.get("status"))
print("=> create endpoint does NOT pre-check quota (work-then-reject limbo): CONFIRMED")

# (2) The charge point (first-COMPLETE/export) enforces. Call it directly.
try:
    enforce_report_create_quota(db, uid, commit=False)
    print("UNEXPECTED: enforce did not raise")
except DomainError as exc:
    print(f"enforce_report_create_quota raised: {type(exc).__name__} "
          f"code={getattr(exc,'error_code',None)} status={getattr(exc,'status_code',None)}")

db.close()
C.write_artifact("quota_probe.json", {
    "user_id": str(uid),
    "entitlements_fresh": ent0.get("reports"),
    "entitlements_after_2_charges": ent1.get("reports"),
    "create_after_exhausted_returns": {"id": r.get("id"), "status": r.get("status")},
})
