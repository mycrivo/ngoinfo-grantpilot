from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

get_settings.cache_clear()


def _settings(*, me_enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def test_core_health_always_available():
    app = create_app(_settings(me_enabled=False))
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_reports_health_404_when_module_disabled():
    app = create_app(_settings(me_enabled=False))
    client = TestClient(app)
    response = client.get("/api/reports/health")
    assert response.status_code == 404


def test_reports_health_200_when_module_enabled():
    app = create_app(_settings(me_enabled=True))
    client = TestClient(app)
    response = client.get("/api/reports/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "reports"}


def test_proposals_routes_present_when_module_disabled():
    app = create_app(_settings(me_enabled=False))
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert any(path.startswith("/api/proposals") for path in paths)
