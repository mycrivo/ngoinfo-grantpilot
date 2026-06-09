"""P1-2 deterministic numeric verifier unit tests."""

from __future__ import annotations

from app.reports.knowledge.confirmed_kb import build_confirmed_kb_view
from app.reports.services.numeric_fact_verifier import (
    HONEST_OMISSION_PHRASE,
    LEGACY_NUMERIC_CERTIFICATION,
    extract_significant_numbers,
    normalize_numeric_token,
    verify_section_numerics,
)


def _reconciled(value: int | float | str) -> dict:
    return {
        "value": value,
        "verification_status": "reconciled",
        "confirmed_by_user": False,
        "source_document_id": "doc-1",
        "source_label": "test",
    }


def _kb(*, facts: dict | None = None, gaps: dict | None = None) -> dict:
    return {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "gate2_confirmed_at": "2026-01-02T00:00:00+00:00",
        "facts": facts or {},
        "gap_answers": gaps or {},
    }


def test_normalize_numeric_token_formatting_matrix():
    assert normalize_numeric_token("174,850") == "174850"
    assert normalize_numeric_token("174850") == "174850"
    assert normalize_numeric_token("GBP 174,850") == "174850"
    assert normalize_numeric_token("£174,850") == "174850"


def test_claims_primary_pass_with_formatting_delta():
    kb_view = build_confirmed_kb_view(
        _kb(facts={"financials.total_spend": _reconciled(174850)})
    )
    flags = verify_section_numerics(
        section_text="Total spend was GBP 174,850 for the period.",
        claims=[
            {
                "text": "Total spend GBP 174,850.",
                "source_refs": ["fact:financials.total_spend"],
                "value_tokens": ["174850"],
                "bind_status": "bound",
            }
        ],
        citation_mode="structured",
        kb_view=kb_view,
    )
    assert flags == []


def test_uncited_prose_number_blocked():
    kb_view = build_confirmed_kb_view(
        _kb(facts={"indicators.op1_1.ar1_actual": _reconciled(684)})
    )
    flags = verify_section_numerics(
        section_text="The programme also reported 99999 additional beneficiaries.",
        claims=[
            {
                "text": "684 girls re-enrolled.",
                "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                "value_tokens": ["684"],
                "bind_status": "bound",
            }
        ],
        citation_mode="structured",
        kb_view=kb_view,
    )
    assert len(flags) == 1
    assert flags[0].claim_text == "99999"
    assert flags[0].verification_path == "deterministic_numeric"


def test_tampered_claim_value_blocked():
    kb_view = build_confirmed_kb_view(
        _kb(
            facts={
                "indicators.op1_1.ar1_actual": _reconciled(684),
                "indicators.op1_1.ar1_milestone_target": _reconciled(650),
            }
        )
    )
    flags = verify_section_numerics(
        section_text="BridgeLight re-enrolled 5000 girls against target 650.",
        claims=[
            {
                "text": "5000 girls re-enrolled.",
                "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                "value_tokens": ["5000"],
                "bind_status": "bound",
            },
            {
                "text": "Target 650.",
                "source_refs": ["fact:indicators.op1_1.ar1_milestone_target"],
                "value_tokens": ["650"],
                "bind_status": "bound",
            },
        ],
        citation_mode="structured",
        kb_view=kb_view,
    )
    assert any(f.claim_text.startswith("5000") or "5000" in f.reason for f in flags)


def test_legacy_fallback_not_structured_certification():
    kb_view = build_confirmed_kb_view(
        _kb(facts={"indicators.op1_1.ar1_actual": _reconciled(684)})
    )
    flags = verify_section_numerics(
        section_text="684 girls re-enrolled.",
        claims=[],
        citation_mode="legacy_fallback",
        kb_view=kb_view,
    )
    assert flags == []
    assert LEGACY_NUMERIC_CERTIFICATION


def test_honest_omission_excluded_from_backstop():
    text = f"Attendance was {HONEST_OMISSION_PHRASE} for this indicator."
    assert extract_significant_numbers(text) == []
