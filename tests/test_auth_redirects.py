from types import SimpleNamespace

from app.services import auth_service


def test_is_redirect_allowed_matches_exact():
    def fake_settings():
        return SimpleNamespace(
            AUTH_ALLOWED_REDIRECT_URLS="https://grantpilot.ngoinfo.org/auth/callback"
        )

    auth_service.get_settings = fake_settings

    assert auth_service.is_redirect_allowed(
        "https://grantpilot.ngoinfo.org/auth/callback"
    )


def test_is_redirect_allowed_rejects_unlisted():
    def fake_settings():
        return SimpleNamespace(
            AUTH_ALLOWED_REDIRECT_URLS="https://grantpilot.ngoinfo.org/auth/callback"
        )

    auth_service.get_settings = fake_settings

    assert not auth_service.is_redirect_allowed(
        "https://grantpilot.ngoinfo.org/auth/callback/extra"
    )
