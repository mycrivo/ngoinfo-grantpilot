"""P1-1 faithfulness eval — absence + presence on offline CLEAN fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.eval.faithfulness_check import (
    check_content_json_faithfulness,
    check_faithfulness_fixture,
    extract_significant_numbers,
    load_faithfulness_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "synthesis"
    / "clean_faithfulness_fixture.json"
)


@pytest.fixture
def clean_fixture() -> dict:
    return load_faithfulness_fixture(FIXTURE)


def test_clean_fixture_passes_absence_and_presence(clean_fixture):
    report = check_faithfulness_fixture(clean_fixture)
    summary = report.to_summary_dict()
    assert summary["faithfulness.unmatched_numbers"] == 0
    assert summary["faithfulness.missing_expected_numbers"] == 0
    assert summary["faithfulness.degraded_leaks"] == 0
    assert report.passed


def test_unmatched_number_detected():
    content = {
        "sections": [
            {
                "section_key": "summary_and_overview",
                "generation_status": "GENERATED",
                "content": {
                    "citation_mode": "structured",
                    "text": "Fabricated count of 9999 beneficiaries reported.",
                    "claims": [
                        {
                            "text": "684 girls re-enrolled.",
                            "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                            "value_tokens": ["684"],
                            "bind_status": "bound",
                        }
                    ],
                },
            }
        ]
    }
    report = check_content_json_faithfulness(content)
    assert len(report.unmatched_numbers) == 1
    assert report.unmatched_numbers[0]["number"] == "9999"


def test_missing_expected_number_detected(clean_fixture):
    content = json.loads(json.dumps(clean_fixture["content_json"]))
    section = content["sections"][0]
    section["content"]["text"] = section["content"]["text"].replace("684", "not reported this period")
    report = check_content_json_faithfulness(
        content,
        expected_presence=clean_fixture["expected_presence"],
    )
    assert any(
        item["expected_number"] == "684"
        for item in report.missing_expected_numbers
    )


def test_omission_phrase_not_counted_as_unmatched():
    text = "Attendance was not reported this period for this indicator."
    assert extract_significant_numbers(text) == []


def test_degraded_pass_through_leak_detected():
    content = {
        "sections": [
            {
                "section_key": "x",
                "generation_status": "GENERATED",
                "content": {
                    "citation_mode": "structured",
                    "text": "See fact:degraded_pass_through:doc:indicators.op1_1.ar1_actual",
                    "claims": [],
                },
            }
        ]
    }
    report = check_content_json_faithfulness(content)
    assert report.degraded_leaks


def test_legacy_fallback_sections_skipped_for_faithfulness():
    content = {
        "sections": [
            {
                "section_key": "legacy",
                "generation_status": "GENERATED",
                "content": {
                    "citation_mode": "legacy_fallback",
                    "text": "Uncited number 12345 in legacy mode.",
                    "claims": [],
                },
            }
        ]
    }
    report = check_content_json_faithfulness(content)
    assert report.sections_checked == 0
    assert report.unmatched_numbers == []
