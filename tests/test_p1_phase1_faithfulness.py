"""P1 Phase 1 unified faithfulness gate — P1-1 numeric + P1-2 qualitative/DYN-02."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.eval.faithfulness_check import check_faithfulness_fixture, load_faithfulness_fixture
from tests.critic_eval_helpers import kb_backed_qualitative_query_fn, run_offline_split_critic

CLEAN_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "synthesis"
    / "clean_faithfulness_fixture.json"
)
DYN02_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "critic"
    / "dyn02_false_positive_slice.json"
)


@pytest.fixture
def dyn02_fixture() -> dict:
    return json.loads(DYN02_FIXTURE.read_text(encoding="utf-8"))


def test_p1_1_clean_fixture_still_passes():
    fixture = load_faithfulness_fixture(CLEAN_FIXTURE)
    report = check_faithfulness_fixture(fixture)
    summary = report.to_summary_dict()
    assert summary["faithfulness.unmatched_numbers"] == 0
    assert summary["faithfulness.missing_expected_numbers"] == 0
    assert summary["faithfulness.degraded_leaks"] == 0


def test_dyn02_fixture_zero_false_positives(dyn02_fixture):
    kb = dyn02_fixture["knowledge_bank_json"]
    query_fn = kb_backed_qualitative_query_fn()
    total_blocks = 0
    for section in dyn02_fixture["sections"]:
        flags = run_offline_split_critic(
            knowledge_bank_json=kb,
            section=section,
            qualitative_query_fn=query_fn,
        )
        blocks = [
            f
            for f in flags
            if f.get("severity") == "BLOCK" and not f.get("accepted")
        ]
        total_blocks += len(blocks)
    assert total_blocks == 0


def test_phase1_faithfulness_metrics_shape(dyn02_fixture):
    clean = load_faithfulness_fixture(CLEAN_FIXTURE)
    clean_report = check_faithfulness_fixture(clean)

    dyn02_blocks = 0
    query_fn = kb_backed_qualitative_query_fn()
    for section in dyn02_fixture["sections"]:
        flags = run_offline_split_critic(
            knowledge_bank_json=dyn02_fixture["knowledge_bank_json"],
            section=section,
            qualitative_query_fn=query_fn,
        )
        dyn02_blocks += sum(
            1
            for f in flags
            if f.get("severity") == "BLOCK" and not f.get("accepted")
        )

    metrics = {
        "faithfulness.unmatched_numbers": len(clean_report.unmatched_numbers),
        "faithfulness.missing_expected_numbers": len(
            clean_report.missing_expected_numbers
        ),
        "faithfulness.degraded_leaks": len(clean_report.degraded_leaks),
        "faithfulness.dyn02_false_positives": dyn02_blocks,
    }
    assert metrics["faithfulness.unmatched_numbers"] == 0
    assert metrics["faithfulness.missing_expected_numbers"] == 0
    assert metrics["faithfulness.degraded_leaks"] == 0
    assert metrics["faithfulness.dyn02_false_positives"] == 0
