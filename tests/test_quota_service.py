from types import SimpleNamespace

import pytest

from app.core.errors import ForbiddenError
from app.services import quota_service


def test_build_quota_payload():
    payload = quota_service._build_quota_payload(allowed=3, used=1)
    assert payload == {"allowed": 3, "used": 1, "remaining": 2}


def test_enforce_quota_exhausted(monkeypatch):
    plan = SimpleNamespace(
        plan_name=quota_service.PLAN_FREE,
        current_period_start=None,
        current_period_end=None,
        plan_activated_at=None,
    )

    def fake_plan(_db, _user_id):
        return plan

    def fake_count(_db, _user_id, _event_type, _start, _end):
        return 1

    monkeypatch.setattr(quota_service, "get_or_create_user_plan", fake_plan)
    monkeypatch.setattr(quota_service, "_usage_count", fake_count)

    with pytest.raises(ForbiddenError) as exc:
        quota_service.enforce_quota(SimpleNamespace(), "user", quota_service.EVENT_FIT_SCAN)

    assert exc.value.error_code == "QUOTA_EXCEEDED"
