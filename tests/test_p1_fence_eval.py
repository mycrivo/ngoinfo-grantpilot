"""P1-3 fence eval — degrade leak prevention and recovery semantics."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.reports.gap.satisfaction import is_requirement_satisfied, unsatisfied_requirements
from app.reports.gap.template_requirements import TemplateRequirement
from app.reports.knowledge.confirmed_kb import filter_citable_facts, is_fact_citable
from app.reports.services.gate1_confirmation_service import (
    apply_gate1_fact_promotions,
    confirm_gate1,
)
from app.reports.services.report_inputs_builder import (
    build_knowledge_bank_inputs_for_section,
    subset_facts_for_section,
)

E1_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "reconciler"
    / "e1_reconciler_degraded_230290ce_kb.json"
)


@pytest.fixture
def e1_degraded_kb() -> dict:
    return json.loads(E1_FIXTURE.read_text(encoding="utf-8"))


def test_e1_fixture_all_unverified_non_citable_before_gate1(e1_degraded_kb):
    assert filter_citable_facts(e1_degraded_kb) == {}


def test_e1_fixture_still_non_citable_after_gate_stamp_without_promotion(e1_degraded_kb):
    kb = dict(e1_degraded_kb)
    kb["gate1_confirmed_at"] = "2026-01-01T00:00:00+00:00"
    assert filter_citable_facts(kb) == {}


def test_cluster_batch_promotion_makes_facts_citable(e1_degraded_kb):
    kb = dict(e1_degraded_kb)
    kb["gate1_confirmed_at"] = "2026-01-01T00:00:00+00:00"
    facts = kb["facts"]
    outcome = apply_gate1_fact_promotions(
        facts,
        [
            {
                "fact_key": "degraded_pass_through:doc1:indicators.op1_1.ar1_actual",
                "confirmed_value_snapshot": 684,
            }
        ],
        confirmed_at_iso=kb["gate1_confirmed_at"],
    )
    assert outcome.promoted_fact_keys == [
        "degraded_pass_through:doc1:indicators.op1_1.ar1_actual"
    ]
    kb["facts"] = facts
    citable = filter_citable_facts(kb)
    assert len(citable) == 1
    assert is_fact_citable(
        citable["degraded_pass_through:doc1:indicators.op1_1.ar1_actual"],
        gate1_confirmed_at=kb["gate1_confirmed_at"],
    )


def test_promotion_rejects_snapshot_mismatch(e1_degraded_kb):
    facts = dict(e1_degraded_kb["facts"])
    outcome = apply_gate1_fact_promotions(
        facts,
        [
            {
                "fact_key": "degraded_pass_through:doc1:indicators.op1_1.ar1_actual",
                "confirmed_value_snapshot": 999,
            }
        ],
        confirmed_at_iso="2026-01-01T00:00:00+00:00",
    )
    assert outcome.promoted_fact_keys == []
    assert outcome.rejected_promotions[0]["reason"] == "value snapshot mismatch"


def test_synthesis_subset_excludes_unverified_facts(e1_degraded_kb):
    kb = dict(e1_degraded_kb)
    kb["gate1_confirmed_at"] = "2026-01-01T00:00:00+00:00"
    section = {
        "section_key": "detailed_output_scoring",
        "archetype": "ARCH_OUTPUT_SCORING_TABLE",
        "required_indicators": ["OP1.1"],
    }
    inputs = build_knowledge_bank_inputs_for_section(kb, section)
    assert inputs["facts"] == {}


def test_gap_unsatisfied_without_citable_facts(e1_degraded_kb):
    kb = dict(e1_degraded_kb)
    kb["gate1_confirmed_at"] = "2026-01-01T00:00:00+00:00"
    req = TemplateRequirement(
        item_key="detailed_output_scoring:indicator:op1_1",
        section_key="detailed_output_scoring",
        section_label="Output scoring",
        required_item_type="indicator",
        required_item_ref="OP1.1",
    )
    assert not is_requirement_satisfied(
        req,
        facts=kb["facts"],
        gap_answers={},
        gate1_confirmed_at=kb["gate1_confirmed_at"],
    )
    missing = unsatisfied_requirements([req], kb)
    assert len(missing) == 1


def test_partial_degraded_normally_keyed_facts_still_unverified():
    """reconciliation_outcome=degraded with normal keys — not assumed safe."""
    kb = {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "reconciliation_outcome": "degraded",
        "facts": {
            "indicators.op1_1.ar1_actual": {
                "value": 684,
                "verification_status": "unverified",
                "confirmed_by_user": False,
                "source_document_id": "d1",
                "source_label": "x",
                "semantic_label": "actual",
                "provenance": {"excerpt": "684"},
            }
        },
    }
    assert filter_citable_facts(kb) == {}


def test_confirm_gate1_clean_run_no_bulk_rubber_stamp():
    db = MagicMock()
    report_id = uuid.uuid4()
    user_id = uuid.uuid4()
    doc_id = str(uuid.uuid4())

    class Report:
        def __init__(self) -> None:
            self.id = report_id
            self.user_id = user_id
            self.knowledge_bank_json: dict = {}

    report = Report()
    db.get.return_value = report
    kb = {
        "schema_version": "1.0.0",
        "reconciler_agent": "knowledge_bank_reconciler",
        "reconciliation_outcome": "complete",
        "facts": {
            "budget_total": {
                "value": 100,
                "verification_status": "reconciled",
                "source_document_id": doc_id,
                "source_label": "Grant letter",
                "semantic_label": "Total budget",
                "provenance": {"excerpt": "GBP 100 total"},
                "confirmed_by_user": False,
            }
        },
        "conflicts": [],
    }
    persisted, outcome = confirm_gate1(
        db,
        donor_report_id=report_id,
        user_id=user_id,
        knowledge_bank_json=kb,
    )
    assert persisted.get("gate1_confirmed_at")
    assert persisted["facts"]["budget_total"]["confirmed_by_user"] is False
    assert is_fact_citable(
        persisted["facts"]["budget_total"],
        gate1_confirmed_at=persisted["gate1_confirmed_at"],
    )
    assert outcome.promoted_fact_keys == []
