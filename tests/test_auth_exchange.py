from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.models.auth_oauth_exchange_code import AuthOAuthExchangeCode
from app.models.user import User
from app.models.auth_oauth_exchange_code import AuthOAuthExchangeCode
from app.models.user import User
from app.services.auth_service import consume_oauth_exchange_code, create_oauth_exchange_code


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(32)"


def _mock_security_settings(monkeypatch):
    import app.core.security as security

    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: type("S", (), {"AUTH_JWT_SIGNING_KEY": "x" * 64})(),
    )


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    AuthOAuthExchangeCode.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_oauth_exchange_code_single_use(monkeypatch):
    _mock_security_settings(monkeypatch)
    db = _db_session()
    user = User(email="test@example.org", auth_provider="email")
    db.add(user)
    db.commit()

    code = create_oauth_exchange_code(db, user.id, ttl_seconds=90)
    db.commit()

    record = consume_oauth_exchange_code(db, code)
    assert record is not None
    db.commit()

    record_again = consume_oauth_exchange_code(db, code)
    assert record_again is None


def test_oauth_exchange_code_expired(monkeypatch):
    _mock_security_settings(monkeypatch)
    db = _db_session()
    user = User(email="expired@example.org", auth_provider="email")
    db.add(user)
    db.commit()

    code = create_oauth_exchange_code(db, user.id, ttl_seconds=90)
    db.commit()

    db.query(AuthOAuthExchangeCode).update(
        {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}
    )
    db.commit()

    record = consume_oauth_exchange_code(db, code)
    assert record is None
