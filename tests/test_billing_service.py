from datetime import datetime, timezone
import uuid
from types import SimpleNamespace

from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.stripe_event import StripeEvent
from app.models.user import User
from app.models.user_plan import UserPlan
from app.services import billing_service


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
    tables = (User.__table__, UserPlan.__table__, StripeEvent.__table__)
    originals = {}
    for table in tables:
        for column in table.columns:
            originals[(table.name, column.name)] = column.server_default
            column.server_default = None
    User.__table__.create(engine)
    UserPlan.__table__.create(engine)
    StripeEvent.__table__.create(engine)
    for table in tables:
        for column in table.columns:
            column.server_default = originals[(table.name, column.name)]
    return sessionmaker(bind=engine)()


def test_persist_stripe_event_idempotent():
    db = _db_session()
    created = billing_service.persist_stripe_event(
        db,
        stripe_event_id="evt_1",
        event_type="checkout.session.completed",
        payload={"id": "evt_1", "type": "checkout.session.completed"},
    )
    db.commit()

    created_again = billing_service.persist_stripe_event(
        db,
        stripe_event_id="evt_1",
        event_type="checkout.session.completed",
        payload={"id": "evt_1", "type": "checkout.session.completed"},
    )
    assert created is True
    assert created_again is False


def test_subscription_deleted_downgrades_to_free():
    db = _db_session()
    now = datetime.now(timezone.utc)
    user = User(
        email="billing@example.org",
        auth_provider="email",
        stripe_customer_id="cus_123",
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()

    plan = UserPlan(
        id=uuid.uuid4(),
        user_id=user.id,
        plan_name="GROWTH",
        stripe_subscription_id="sub_123",
        billing_period_start=datetime.now(timezone.utc),
        billing_period_end=datetime.now(timezone.utc),
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()

    event = {
        "id": "evt_2",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_123", "customer": "cus_123"}},
    }
    settings = SimpleNamespace(
        STRIPE_PRICE_ID_GROWTH="price_growth",
        STRIPE_PRICE_ID_IMPACT="price_impact",
    )
    result, error_message, should_retry = billing_service.handle_stripe_event(
        db, event, settings=settings
    )
    db.commit()

    updated_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).one()
    assert result == billing_service.PROCESSING_SUCCESS
    assert error_message is None
    assert should_retry is False
    assert updated_plan.plan_name == "FREE"
    assert updated_plan.stripe_subscription_id is None
    assert updated_plan.billing_period_start is None
    assert updated_plan.billing_period_end is None
