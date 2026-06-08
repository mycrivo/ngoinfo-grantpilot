from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.reports.schemas.gap_check import GapAnswerPatchInput
from app.reports.schemas.gap_compliance_v1 import GAP_AGENT_NAME
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    KNOWLEDGE_BANK_RECONCILIATION_VERSION,
    RECONCILER_AGENT_NAME,
)
from app.reports.services.gap_check_service import get_gap_check, patch_gap_answers


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
        "readiness_score": 2,
        "ready_for_gate2": False,
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


def test_get_gap_check_returns_unanswered_gaps(monkeypatch):
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    gap_key = "summary:section:overall_progress"
    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        knowledge_bank_json=_gate1_kb(),
        gap_analysis_json=_gap_analysis(gaps=[_surfaced_gap(gap_key)]),
    )
    monkeypatch.setattr(
        "app.reports.services.gap_check_service.get_owned_donor_report",
        lambda *args, **kwargs: report,
    )

    payload = get_gap_check(db, donor_report_id=report_id, user_id=user_id)
    assert payload["readiness_score"] == 2
    assert len(payload["missing_items"]) == 1
    assert payload["missing_items"][0]["item_key"] == gap_key
    assert payload["missing_items"][0]["question"] == "Please provide overall_progress"


def test_patch_gap_answers_marks_gap_resolved(monkeypatch):
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    gap_key = "summary:section:overall_progress"
    report = SimpleNamespace(
        id=report_id,
        user_id=user_id,
        knowledge_bank_json=_gate1_kb(),
        gap_analysis_json=_gap_analysis(gaps=[_surfaced_gap(gap_key)]),
    )
    monkeypatch.setattr(
        "app.reports.services.gap_check_service.get_owned_donor_report",
        lambda *args, **kwargs: report,
    )
    monkeypatch.setattr(
        "app.reports.services.gap_check_service.re_enqueue_gate2_job",
        lambda *args, **kwargs: None,
    )

    payload = patch_gap_answers(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        gap_answers_patch={
            gap_key: GapAnswerPatchInput(
                disposition="answered",
                answer_text="Progress is on track.",
            )
        },
    )
    assert payload["missing_items"] == []
    assert report.knowledge_bank_json["gap_answers"][gap_key]["answer_text"] == "Progress is on track."
