from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.security import create_access_token
from app.main import create_app
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from app.reports.services.gate1_confirmation_service import confirm_gate1
from app.reports.services.gate_preconditions import require_gate1_confirmed

get_settings.cache_clear()


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def _minimal_reconciled_kb() -> dict:
    doc_id = str(uuid.uuid4())
    return {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "facts": {
            "budget_total": {
                "value": 100,
                "unit": None,
                "semantic_label": "Total budget",
                "coverage": "single_source",
                "source_document_id": doc_id,
                "source_label": "Grant letter",
                "provenance": {"excerpt": "GBP 100 total"},
                "interpretation_note": None,
                "confirmed": False,
                "confirmed_at": None,
                "confirmed_by_user": False,
            }
        },
        "conflicts": [],
        "unreadable_sources": [],
        "reconciliation_outcome": "complete",
        "reconciliation_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "reconciler_agent": RECONCILER_AGENT_NAME,
        "reconciled_at": "2026-01-01T00:00:00+00:00",
    }


def test_confirm_gate1_sets_stamp_and_persists_kb():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json: dict = {}

    report = Report()
    db.get.return_value = report
    kb = _minimal_reconciled_kb()

    persisted = confirm_gate1(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=kb,
    )

    assert persisted.get("gate1_confirmed_at")
    assert persisted["facts"]["budget_total"]["value"] == 100
    assert report.knowledge_bank_json == persisted
    db.commit.assert_called_once()


def test_require_gate1_confirmed_fails_without_stamp():
    with pytest.raises(DomainError) as exc_info:
        require_gate1_confirmed(_minimal_reconciled_kb())
    assert exc_info.value.error_code == "GATE1_NOT_CONFIRMED"
    assert exc_info.value.status_code == 409


def test_require_gate1_confirmed_passes_with_stamp():
    kb = _minimal_reconciled_kb()
    kb["gate1_confirmed_at"] = "2026-05-24T12:00:00+00:00"
    require_gate1_confirmed(kb)


def test_gate1_confirm_endpoint_requires_auth():
    app = create_app(_settings(me_enabled=True))
    client = TestClient(app)
    report_id = uuid.uuid4()
    response = client.post(
        f"/api/reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": _minimal_reconciled_kb()},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


def test_gate1_confirm_endpoint_rejects_invalid_token():
    app = create_app(_settings(me_enabled=True))
    client = TestClient(app)
    report_id = uuid.uuid4()
    response = client.post(
        f"/api/reports/{report_id}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": _minimal_reconciled_kb()},
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_gate1_confirm_endpoint_404_when_module_disabled():
    app = create_app(_settings(me_enabled=False))
    client = TestClient(app)
    token, _ = create_access_token(str(uuid.uuid4()), "u@example.com", "free")
    response = client.post(
        f"/api/reports/{uuid.uuid4()}/knowledge-bank/gate1/confirm",
        json={"knowledge_bank_json": _minimal_reconciled_kb()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
