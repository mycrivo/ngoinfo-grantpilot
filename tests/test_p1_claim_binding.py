"""P1-1 structured claim binding unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.reports.services.synthesis_claim_binding import (
    FAILURE_MISSING_STRUCTURED_CLAIMS,
    HONEST_OMISSION_PHRASE,
    bind_structured_claims,
    resolve_structured_synthesis,
    section_has_citable_inputs,
)

E1_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "reconciler"
    / "e1_reconciler_degraded_230290ce_kb.json"
)


def _reconciled_fact(key: str, value: int | str) -> dict:
    return {
        "value": value,
        "verification_status": "reconciled",
        "confirmed_by_user": False,
        "source_document_id": "doc-1",
        "source_label": "test",
        "semantic_label": key,
        "provenance": {"excerpt": str(value)},
    }


def _kb(*, facts: dict | None = None, gaps: dict | None = None) -> dict:
    return {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "facts": facts or {},
        "gap_answers": gaps or {},
    }


def test_bound_claim_refs_are_citable():
    kb = _kb(
        facts={
            "indicators.op1_1.ar1_actual": _reconciled_fact("actual", 684),
            "indicators.op1_1.ar1_target": _reconciled_fact("target", 650),
        }
    )
    outcome = resolve_structured_synthesis(
        claims=[
            {
                "text": "684 girls re-enrolled against 650 target.",
                "source_refs": [
                    "fact:indicators.op1_1.ar1_actual",
                    "fact:indicators.op1_1.ar1_target",
                ],
                "value_tokens": ["684", "650"],
            }
        ],
        text="684 girls re-enrolled against 650 target.",
        knowledge_bank=kb,
    )
    assert outcome.ok
    assert outcome.content is not None
    assert outcome.content.structured_bind_status == "bound"
    assert "fact:indicators.op1_1.ar1_actual" in outcome.content.evidence_used
    assert outcome.content.claims[0]["bind_status"] == "bound"


def test_non_citable_ref_dropped_and_numeric_omitted():
    e1_kb = json.loads(E1_FIXTURE.read_text(encoding="utf-8"))
    e1_kb["gate1_confirmed_at"] = "2026-01-01T00:00:00+00:00"
    outcome = bind_structured_claims(
        claims=[
            {
                "text": "684 girls re-enrolled.",
                "source_refs": [
                    "fact:degraded_pass_through:doc1:indicators.op1_1.ar1_actual"
                ],
                "value_tokens": ["684"],
            }
        ],
        text="684 girls re-enrolled.",
        knowledge_bank=e1_kb,
    )
    assert outcome.claims[0]["bind_status"] == "dropped_refs"
    assert outcome.evidence_used == []


def test_value_mismatch_yields_honest_omission_section_stays_bindable():
    kb = _kb(facts={"indicators.op1_1.ar1_actual": _reconciled_fact("actual", 684)})
    outcome = resolve_structured_synthesis(
        claims=[
            {
                "text": "999 girls re-enrolled.",
                "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                "value_tokens": ["999"],
            }
        ],
        text="999 girls re-enrolled.",
        knowledge_bank=kb,
    )
    assert outcome.ok
    assert outcome.content is not None
    assert HONEST_OMISSION_PHRASE in outcome.content.text
    assert "999" not in outcome.content.text
    assert len(outcome.content.omitted_claims) == 1
    assert outcome.content.claims[0]["bind_status"] == "omitted_numeric"


def test_derived_evidence_used_is_union_of_claim_refs():
    kb = _kb(
        facts={
            "indicators.op1_1.ar1_actual": _reconciled_fact("actual", 684),
            "indicators.op1_3.ar1_actual": _reconciled_fact("actual2", 438),
        }
    )
    bound = bind_structured_claims(
        claims=[
            {
                "text": "684 re-enrolled.",
                "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                "value_tokens": ["684"],
            },
            {
                "text": "438 completed sessions.",
                "source_refs": ["fact:indicators.op1_3.ar1_actual"],
                "value_tokens": ["438"],
            },
        ],
        text="684 re-enrolled. 438 completed sessions.",
        knowledge_bank=kb,
    )
    assert set(bound.evidence_used) == {
        "fact:indicators.op1_1.ar1_actual",
        "fact:indicators.op1_3.ar1_actual",
    }


def test_missing_structured_claims_when_citable_inputs_exist():
    kb = _kb(facts={"indicators.op1_1.ar1_actual": _reconciled_fact("actual", 684)})
    outcome = resolve_structured_synthesis(
        claims=[],
        text="Prose without bound claims.",
        knowledge_bank=kb,
    )
    assert not outcome.ok
    assert outcome.failure_reason == FAILURE_MISSING_STRUCTURED_CLAIMS


def test_honest_empty_when_no_citable_inputs():
    kb = _kb(facts={}, gaps={})
    assert not section_has_citable_inputs(kb)
    outcome = resolve_structured_synthesis(
        claims=[],
        text="No citable data was available for this section.",
        knowledge_bank=kb,
    )
    assert outcome.ok
    assert outcome.content is not None
    assert outcome.content.structured_bind_status == "honest_empty"
    assert outcome.content.claims == []


def test_missing_structured_claims_when_claims_bind_nothing():
    kb = _kb(facts={"indicators.op1_1.ar1_actual": _reconciled_fact("actual", 684)})
    outcome = resolve_structured_synthesis(
        claims=[
            {
                "text": "Bad ref.",
                "source_refs": ["fact:indicators.does_not_exist"],
                "value_tokens": ["684"],
            }
        ],
        text="684 reported.",
        knowledge_bank=kb,
    )
    assert not outcome.ok
    assert outcome.failure_reason == FAILURE_MISSING_STRUCTURED_CLAIMS


def test_qualitative_claim_without_value_tokens():
    kb = _kb(
        facts={
            "objectives.outcome": {
                **_reconciled_fact("outcome", "Improved retention"),
                "value": "Improved school retention",
            }
        }
    )
    outcome = resolve_structured_synthesis(
        claims=[
            {
                "text": "Progress supported the programme outcome on retention.",
                "source_refs": ["fact:objectives.outcome"],
                "value_tokens": [],
            }
        ],
        text="Progress supported the programme outcome on retention.",
        knowledge_bank=kb,
    )
    assert outcome.ok
    assert outcome.content is not None
    assert outcome.content.claims[0]["bind_status"] == "bound"
