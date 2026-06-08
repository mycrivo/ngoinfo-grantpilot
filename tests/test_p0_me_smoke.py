"""P0 eval harness skeleton — moat smoke assertions (unit level)."""

from __future__ import annotations

from app.reports.extraction.docling_adapter import DoclingIntakeError
from app.reports.orchestration.extract_isolation import classify_intake_exception
from app.reports.schemas.content_json_v1 import compute_generation_summary_from_sections


def test_docling_intake_error_classified_as_degrade():
    assert classify_intake_exception(DoclingIntakeError("libxcb")) == "degrade"


def test_generation_summary_counts_unaccepted_blocks():
    sections = [
        {
            "generation_status": "AWAITING_REVIEW",
            "critic_flags": [
                {"severity": "BLOCK", "accepted": False},
                {"severity": "WARN", "accepted": False},
            ],
        }
    ]
    summary = compute_generation_summary_from_sections(sections, warnings=[])
    assert summary["critic_blocks"] == 1
    assert summary["awaiting_review"] == 1


def test_generation_summary_after_accept_all():
    sections = [
        {
            "generation_status": "ACCEPTED",
            "critic_flags": [{"severity": "BLOCK", "accepted": True}],
        }
    ]
    summary = compute_generation_summary_from_sections(sections, warnings=[])
    assert summary["critic_blocks"] == 0
    assert summary["accepted"] == 1
