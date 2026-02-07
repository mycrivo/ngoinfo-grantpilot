import json
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

from app.api.routes import auth as auth_routes


def test_google_start_scope_is_space_delimited(monkeypatch):
    def fake_settings():
        return SimpleNamespace(
            GOOGLE_OAUTH_CLIENT_ID="client",
            GOOGLE_OAUTH_REDIRECT_URI="https://example.com/callback",
            GOOGLE_OAUTH_SCOPES=None,
            AUTH_RATE_LIMIT_ENABLED=False,
        )

    monkeypatch.setattr(auth_routes, "get_settings", fake_settings)
    monkeypatch.setattr(auth_routes, "_store_oauth_state", lambda _state: None)

    class DummyRequest:
        query_params = {}
        client = None
        headers = {}

    response = auth_routes.google_oauth_start(DummyRequest())
    payload = json.loads(response.body.decode("utf-8"))
    authorization_url = payload["authorization_url"]
    parsed = urlparse(authorization_url)
    qs = parse_qs(parsed.query)
    assert "scope" in qs
    assert qs["scope"][0] in {"openid email profile"}
    assert "%2C" not in authorization_url
    assert "," not in authorization_url
