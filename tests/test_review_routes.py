"""P0-2 review API unit tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import DomainError
from app.reports.services.critique_resume_service import resume_critique_for_report
from app.reports.services.report_section_review_service import accept_all_sections_for_gate3


def _report_with_sections() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        knowledge_bank_json={"gate2_confirmed_at": datetime.now(timezone.utc).isoformat()},
        content_json={
            "sections": [
                {
                    "section_key": "summary",
                    "generation_status": "AWAITING_REVIEW",
                    "content": {
                        "text": "Summary prose with enough substance for acceptance gate checks.",
                    },
                    "critic_flags": [
                        {
                            "claim_text": "42 beneficiaries",
                            "severity": "BLOCK",
                            "accepted": False,
                        }
                    ],
                }
            ],
            "generation_summary": {"warnings": []},
        },
        funder_report_template=SimpleNamespace(funder_name="FCDO", template_name="Annual"),
    )


def test_accept_all_sections_marks_accepted():
    db = MagicMock()
    report = _report_with_sections()
    report_id = report.id
    user_id = report.user_id

    job = SimpleNamespace(
        stage="export",
        status="awaiting_human",
        agent_trace_json={"stages": {"critique": {"action": "critique_completed"}}},
    )

    with patch(
        "app.reports.services.report_section_review_service.get_owned_donor_report",
        return_value=report,
    ), patch(
        "app.reports.services.report_section_review_service._latest_job",
        return_value=job,
    ), patch(
        "app.reports.services.report_section_review_service._critique_completed",
        return_value=True,
    ):
        result = accept_all_sections_for_gate3(
            db,
            donor_report_id=report_id,
            user_id=user_id,
        )

    section = result.content_json["sections"][0]
    assert section["generation_status"] == "ACCEPTED"
    assert section["critic_flags"][0]["accepted"] is True


def test_resume_critique_rejects_when_not_parked():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    report = SimpleNamespace(
        knowledge_bank_json={"gate2_confirmed_at": "2026-01-01T00:00:00+00:00"},
        content_json={"sections": [{"section_key": "summary"}]},
    )

    with patch(
        "app.reports.services.critique_resume_service.get_owned_donor_report",
        return_value=report,
    ), patch(
        "app.reports.services.critique_resume_service._latest_critique_trace",
        return_value={},
    ), patch(
        "app.reports.services.critique_resume_service.re_enqueue_critique_job",
        return_value=None,
    ):
        with pytest.raises(DomainError) as exc:
            resume_critique_for_report(
                db,
                donor_report_id=report_id,
                user_id=user_id,
            )
    assert exc.value.error_code == "CRITIQUE_NOT_PARKED"
