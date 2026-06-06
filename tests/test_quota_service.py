from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.core.errors import ForbiddenError, InvalidActionTypeError
from app.models.usage_ledger import UsageActionType, UsageLedger
from app.models.user import User
from app.models.user_plan import UserPlan
from app.services import quota_service


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(32)"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "TEXT"


def _register_sqlite_functions(dbapi_connection, _connection_record):
    dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    dbapi_connection.create_function("now", 0, lambda: datetime.now(timezone.utc).isoformat())


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", _register_sqlite_functions)
    tables = (User.__table__, UserPlan.__table__, UsageLedger.__table__)
    originals = {}
    for table in tables:
        for column in table.columns:
            originals[(table.name, column.name)] = column.server_default
            column.server_default = None
    for table in tables:
        table.create(engine)
    for table in tables:
        for column in table.columns:
            column.server_default = originals[(table.name, column.name)]
    return sessionmaker(bind=engine)()


def _seed_user_plan(db, *, plan_name: str) -> uuid.UUID:
    now = datetime.now(timezone.utc)
    user = User(
        email=f"{uuid.uuid4()}@example.org",
        auth_provider="email",
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    period_start = now
    period_end = now + timedelta(days=30)
    plan = UserPlan(
        id=uuid.uuid4(),
        user_id=user.id,
        plan_name=plan_name,
        plan_activated_at=period_start,
        billing_period_start=period_start if plan_name != quota_service.PLAN_FREE else None,
        billing_period_end=period_end if plan_name != quota_service.PLAN_FREE else None,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    return user.id


def test_build_quota_payload():
    payload = quota_service._build_quota_payload(
        limit=3, used=1, period="BILLING_CYCLE", reset_at="2026-07-01T00:00:00+00:00"
    )
    assert payload == {
        "limit": 3,
        "used": 1,
        "remaining": 2,
        "period": "BILLING_CYCLE",
        "reset_at": "2026-07-01T00:00:00+00:00",
    }


def test_enforce_quota_exhausted(monkeypatch):
    plan = SimpleNamespace(
        plan_name=quota_service.PLAN_FREE,
        billing_period_start=None,
        billing_period_end=None,
        plan_activated_at=None,
    )

    def fake_plan(_db, _user_id, *, commit=True):
        return plan

    def fake_count(_db, _user_id, _event_type, _start, _end):
        return 1

    monkeypatch.setattr(quota_service, "get_or_create_user_plan", fake_plan)
    monkeypatch.setattr(quota_service, "_usage_count", fake_count)

    with pytest.raises(ForbiddenError) as exc:
        quota_service.enforce_quota(SimpleNamespace(), uuid.uuid4(), quota_service.EVENT_FIT_SCAN)

    assert exc.value.error_code == "QUOTA_EXCEEDED"


def test_plan_quotas_impact_fit_scans_ten():
    impact = quota_service.PLAN_QUOTAS[quota_service.PLAN_IMPACT]
    assert impact.fit_scans == 10
    assert impact.reports == 2
    assert impact.proposals == 5


def test_get_entitlements_impact_reports_default():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    payload = quota_service.get_entitlements(db, user_id)
    reports = payload["entitlements"]["reports"]
    assert reports["limit"] == 2
    assert reports["used"] == 0
    assert reports["remaining"] == 2
    assert reports["period"] == "BILLING_CYCLE"
    assert payload["entitlements"]["fit_scans"]["limit"] == 10


def test_get_entitlements_growth_and_free_reports_zero():
    db = _db_session()
    growth_id = _seed_user_plan(db, plan_name=quota_service.PLAN_GROWTH)
    free_id = _seed_user_plan(db, plan_name=quota_service.PLAN_FREE)
    growth = quota_service.get_entitlements(db, growth_id)
    free = quota_service.get_entitlements(db, free_id)
    assert growth["entitlements"]["reports"]["limit"] == 0
    assert free["entitlements"]["reports"]["limit"] == 0
    assert growth["entitlements"]["fit_scans"]["limit"] == 10
    assert free["entitlements"]["fit_scans"]["limit"] == 1


def test_report_create_increments_reports_used():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    quota_service.record_usage(
        db,
        user_id,
        UsageActionType.REPORT_CREATE.value,
        idempotency_key="report:create:1",
    )
    db.commit()
    reports = quota_service.get_entitlements(db, user_id)["entitlements"]["reports"]
    assert reports["used"] == 1
    assert reports["remaining"] == 1


def test_report_create_excludes_prior_cycle_rows():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    plan = db.query(UserPlan).filter(UserPlan.user_id == user_id).one()
    old_time = plan.billing_period_start - timedelta(days=1)
    db.add(
        UsageLedger(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=UsageActionType.REPORT_CREATE.value,
            occurred_at=old_time,
            idempotency_key="report:create:old",
            metadata_json={},
        )
    )
    db.commit()
    reports = quota_service.get_entitlements(db, user_id)["entitlements"]["reports"]
    assert reports["used"] == 0


def test_usage_action_type_accepts_report_actions():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    quota_service.record_usage(
        db,
        user_id,
        UsageActionType.REPORT_CREATE.value,
        idempotency_key="report:create:accept",
    )
    quota_service.record_usage(
        db,
        user_id,
        UsageActionType.REPORT_EXPORT.value,
        idempotency_key="report:export:accept",
    )
    db.commit()


def test_usage_action_type_rejects_invalid():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    with pytest.raises(InvalidActionTypeError):
        quota_service.record_usage(
            db,
            user_id,
            "NOT_A_REAL_ACTION",
            idempotency_key="bad",
        )


def test_get_entitlements_includes_report_exports_block():
    db = _db_session()
    user_id = _seed_user_plan(db, plan_name=quota_service.PLAN_IMPACT)
    payload = quota_service.get_entitlements(db, user_id)
    exports = payload["entitlements"]["report_exports"]
    assert exports["limit"] == 2
    assert exports["used"] == 0
    assert exports["remaining"] == 2
    assert exports["period"] == "BILLING_CYCLE"
