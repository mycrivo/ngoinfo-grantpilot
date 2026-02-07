import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

import app.core.security as security
from app.api.routes import auth as auth_routes
from app.models.auth_oauth_exchange_code import AuthOAuthExchangeCode
from app.models.user import User
from app.services import auth_service


@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kw):
    return "CHAR(32)"


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    User.__table__.create(engine)
    AuthOAuthExchangeCode.__table__.create(engine)
    return sessionmaker(bind=engine)()


def test_google_callback_redirect_uses_code_only(monkeypatch):
    security.get_settings = lambda: SimpleNamespace(AUTH_JWT_SIGNING_KEY="x" * 64)
    auth_service.get_settings = lambda: SimpleNamespace(
        AUTH_ALLOWED_REDIRECT_URLS="https://grantpilot.ngoinfo.org/auth/callback",
        AUTH_POST_LOGIN_REDIRECT_URL="https://grantpilot.ngoinfo.org/auth/callback",
    )
    auth_routes.get_settings = lambda: SimpleNamespace(
        GOOGLE_OAUTH_CLIENT_ID="client",
        GOOGLE_OAUTH_CLIENT_SECRET="secret",
        GOOGLE_OAUTH_REDIRECT_URI="https://example.com/callback",
    )

    class DummyResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    def fake_post(*_args, **_kwargs):
        return DummyResponse(200, {"access_token": "token"})

    def fake_get(*_args, **_kwargs):
        return DummyResponse(
            200,
            {
                "email": "user@example.org",
                "sub": "sub",
                "name": "User",
                "picture": "https://example.org/avatar.png",
            },
        )

    monkeypatch.setattr(auth_routes.httpx, "post", fake_post)
    monkeypatch.setattr(auth_routes.httpx, "get", fake_get)

    state = "state123"
    auth_routes.oauth_state_store[state] = {
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "redirect_mode": True,
    }

    class DummyRequest:
        query_params = {"code": "code", "state": state, "redirect": "1"}
        headers = {}
        client = None

    db = _db_session()
    response = auth_routes.google_oauth_callback(DummyRequest(), db)
    location = response.headers.get("location")
    assert location is not None
    parsed = urlparse(location)
    qs = parse_qs(parsed.query)
    assert "code" in qs
    assert "access_token" not in qs
    assert "refresh_token" not in qs
    assert "expires_in" not in qs
