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
from app.reports.gap.gap_answer import HUMAN_GAP_ANSWER_SOURCE, is_gap_answer_resolved
from app.reports.schemas.gap_compliance_v1 import GAP_AGENT_NAME
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses
from app.reports.services.gate_preconditions import (
    require_gap_analysis,
    require_gate1_confirmed,
    require_gate2_confirmed,
)

get_settings.cache_clear()


def _settings(*, me_enabled: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        CORS_ALLOWED_ORIGINS="http://localhost:3000",
        ME_MODULE_ENABLED=me_enabled,
    )


def _gate1_kb() -> dict:
    return {
        "schema_version": KNOWLEDGE_BANK_RECONCILIATION_VERSION,
        "facts": {},
        "conflicts": [],
        "gap_answers": {},
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
        "reconciler_agent": RECONCILER_AGENT_NAME,
    }


def _gap_analysis(*, gaps: list[dict]) -> dict:
    return {
        "schema_version": "1.0.0",
        "gap_agent": GAP_AGENT_NAME,
        "analyzed_at": "2026-05-24T12:00:00+00:00",
        "readiness_score": 50,
        "gaps": gaps,
    }


def _surfaced_gap(item_key: str) -> dict:
    parts = item_key.split(":")
    return {
        "item_key": item_key,
        "section_key": parts[0],
        "section_label": parts[0].replace("_", " ").title(),
        "required_item_type": parts[1],
        "required_item_ref": parts[2],
        "severity": "required",
        "question": f"Please provide {parts[2]}",
        "rationale": "Missing from knowledge bank",
    }


def test_answered_gap_has_human_provenance():
    entry = {
        "disposition": "answered",
        "answer_text": "We held three community workshops.",
        "responded_at": "2026-05-24T12:00:00+00:00",
        "provenance": {
            "source": HUMAN_GAP_ANSWER_SOURCE,
            "excerpt": "We held three community workshops.",
        },
        "source_label": HUMAN_GAP_ANSWER_SOURCE,
        "source_document_id": None,
    }
    assert is_gap_answer_resolved(entry)
    assert entry["provenance"]["source"] == HUMAN_GAP_ANSWER_SOURCE
    assert entry["source_document_id"] is None


def test_bare_answer_text_without_provenance_not_resolved():
    assert not is_gap_answer_resolved({"answer_text": "orphan text"})


def test_skip_is_explicit_not_absence():
    entry = {
        "disposition": "skipped",
        "skip_reason": "not_applicable",
        "responded_at": "2026-05-24T12:00:00+00:00",
    }
    assert is_gap_answer_resolved(entry)
    assert "answer_text" not in entry or not entry.get("answer_text")


def test_gate2_unlock_only_when_all_gaps_addressed():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    gap_a = "community_involvement:indicator:community_participation_examples"
    gap_b = "learning:indicator:what_worked"

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _gate1_kb()
            self.gap_analysis_json = _gap_analysis(
                gaps=[_surfaced_gap(gap_a), _surfaced_gap(gap_b)]
            )

    report = Report()
    db.get.return_value = report

    partial = submit_gate2_gap_responses(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        responses={
            gap_a: Gate2GapResponseInput(
                disposition="answered",
                answer_text="Three workshops with local partners.",
            )
        },
    )
    assert partial["gate2_unlocked"] is False
    assert partial["gate2_confirmed_at"] is None
    assert len(partial["remaining_gaps"]) == 1
    assert partial["remaining_gaps"][0]["item_key"] == gap_b

    full = submit_gate2_gap_responses(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        responses={
            gap_b: Gate2GapResponseInput(
                disposition="skipped",
                skip_reason="cannot_provide",
            )
        },
    )
    assert full["gate2_unlocked"] is True
    assert full["gate2_confirmed_at"]
    assert full["remaining_gaps"] == []
    assert report.knowledge_bank_json["gap_answers"][gap_b]["disposition"] == "skipped"


def test_gate2_refuses_without_gate1():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _gate1_kb()
            self.knowledge_bank_json.pop("gate1_confirmed_at")
            self.gap_analysis_json = _gap_analysis(gaps=[])

    db.get.return_value = Report()
    with pytest.raises(DomainError) as exc_info:
        submit_gate2_gap_responses(
            db,
            donor_report_id=report_id,
            user_id=user_id,
            responses={},
        )
    assert exc_info.value.error_code == "GATE1_NOT_CONFIRMED"


def test_gate2_refuses_without_gap_analysis():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _gate1_kb()
            self.gap_analysis_json = {}

    db.get.return_value = Report()
    with pytest.raises(DomainError) as exc_info:
        submit_gate2_gap_responses(
            db,
            donor_report_id=report_id,
            user_id=user_id,
            responses={},
        )
    assert exc_info.value.error_code == "GAP_ANALYSIS_MISSING"


def test_require_gate2_confirmed_guard():
    kb = _gate1_kb()
    with pytest.raises(DomainError) as exc_info:
        require_gate2_confirmed(kb)
    assert exc_info.value.error_code == "GATE2_NOT_CONFIRMED"
    kb["gate2_confirmed_at"] = "2026-05-24T13:00:00+00:00"
    require_gate2_confirmed(kb)


def test_zero_gaps_unlocks_immediately():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json = _gate1_kb()
            self.gap_analysis_json = _gap_analysis(gaps=[])

    db.get.return_value = Report()
    result = submit_gate2_gap_responses(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        responses={},
    )
    assert result["gate2_unlocked"] is True
    assert result["gate2_confirmed_at"]


def test_gate2_endpoint_requires_auth():
    app = create_app(_settings(me_enabled=True))
    client = TestClient(app)
    report_id = uuid.uuid4()
    response = client.post(
        f"/api/reports/donor-reports/{report_id}/knowledge-bank/gate2/gap-responses",
        json={"responses": {}},
    )
    assert response.status_code == 401


def test_require_gap_analysis_parses_gaps():
    gaps = require_gap_analysis(_gap_analysis(gaps=[_surfaced_gap("a:b:c")]))
    assert len(gaps) == 1
