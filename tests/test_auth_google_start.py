import json
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

from app.api.routes import auth as auth_routes


def test_google_start_scope_is_space_delimited(monkeypatch):
    captured: dict[str, str] = {}

    def fake_settings():
        return SimpleNamespace(
            GOOGLE_OAUTH_CLIENT_ID="client",
            GOOGLE_OAUTH_CLIENT_SECRET="secret",
            GOOGLE_OAUTH_REDIRECT_URI="https://example.com/callback",
            GOOGLE_OAUTH_SCOPES=None,
            AUTH_RATE_LIMIT_ENABLED=False,
        )

    class DummyOAuthClient:
        def __init__(self, client_id, client_secret, scope, redirect_uri):
            self.scope = scope
            self.redirect_uri = redirect_uri

        def create_authorization_url(self, _auth_url, **_kwargs):
            query = f"scope={self.scope}&redirect_uri={self.redirect_uri}"
            return f"https://accounts.google.com/o/oauth2/v2/auth?{query}", "state123"

    monkeypatch.setattr(auth_routes, "get_settings", fake_settings)
    monkeypatch.setattr(
        auth_routes,
        "_store_oauth_state",
        lambda _state, code_verifier: captured.setdefault("code_verifier", code_verifier),
    )
    monkeypatch.setattr(auth_routes, "OAuth2Client", DummyOAuthClient)

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
    assert captured.get("code_verifier")


def test_google_start_stores_state_and_verifier(monkeypatch):
    captured: dict[str, str] = {}

    def fake_settings():
        return SimpleNamespace(
            GOOGLE_OAUTH_CLIENT_ID="client",
            GOOGLE_OAUTH_CLIENT_SECRET="secret",
            GOOGLE_OAUTH_REDIRECT_URI="https://example.com/callback",
            GOOGLE_OAUTH_SCOPES=None,
            AUTH_RATE_LIMIT_ENABLED=False,
        )

    class DummyOAuthClient:
        def __init__(self, client_id, client_secret, scope, redirect_uri):
            self.scope = scope
            self.redirect_uri = redirect_uri

        def create_authorization_url(self, _auth_url, **_kwargs):
            return "https://accounts.google.com/o/oauth2/v2/auth?scope=openid", "state456"

    monkeypatch.setattr(auth_routes, "get_settings", fake_settings)
    monkeypatch.setattr(
        auth_routes,
        "_store_oauth_state",
        lambda _state, code_verifier: captured.setdefault("code_verifier", code_verifier),
    )
    monkeypatch.setattr(auth_routes, "OAuth2Client", DummyOAuthClient)

    class DummyRequest:
        query_params = {"redirect": "1"}
        client = None
        headers = {}

    response = auth_routes.google_oauth_start(DummyRequest())
    payload = json.loads(response.body.decode("utf-8"))
    authorization_url = payload["authorization_url"]
    assert payload["state"] == "state456"
    assert captured.get("code_verifier")
