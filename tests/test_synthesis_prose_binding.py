"""P3-7 regression — recorded raw synthesis response with empty top-level text."""

from __future__ import annotations

import json
from pathlib import Path

from app.reports.services.section_prose import has_non_empty_prose
from app.reports.services.synthesis_claim_binding import resolve_structured_synthesis

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "synthesis"
    / "p3_b3_fcdo_summary_empty_top_level_text_raw.json"
)


def _minimal_kb() -> dict:
    return {
        "gate1_confirmed_at": "2026-06-11T16:00:00+00:00",
        "facts": {
            "objectives.impact_girls_complete_basic_education": {
                "value": "Adolescent girls complete basic education",
                "verification_status": "reconciled",
            },
            "objectives.outcome_improved_retention_attendance_continuity": {
                "value": "Improved retention, attendance and learning continuity",
                "verification_status": "reconciled",
            },
            "indicators.OP1.1.logframe_ar1_actual": {
                "value": 684,
                "verification_status": "reconciled",
            },
            "indicators.OP1.1.logframe_ar1_target": {
                "value": 650,
                "verification_status": "reconciled",
            },
            "indicators.OP1.2.logframe_ar1_actual": {
                "value": 472,
                "verification_status": "reconciled",
            },
            "indicators.OP1.2.logframe_ar1_target": {
                "value": 500,
                "verification_status": "reconciled",
            },
            "indicators.OP1.3.logframe_ar1_actual": {
                "value": 438,
                "verification_status": "reconciled",
            },
            "indicators.OP1.3.logframe_ar1_target": {
                "value": 420,
                "verification_status": "reconciled",
            },
        },
        "gap_answers": {},
    }


def test_recorded_empty_top_level_text_assembles_prose_from_claims():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw = payload["raw_model_response"]
    generated = raw["generated_content"]
    kb = _minimal_kb()

    outcome = resolve_structured_synthesis(
        claims=list(generated.get("claims") or []),
        text=str(generated.get("text") or ""),
        knowledge_bank=kb,
    )

    assert outcome.ok is True
    assert outcome.content is not None
    section = {"content": {"text": outcome.content.text}}
    assert has_non_empty_prose(section)
    assert "684" in outcome.content.text
    assert outcome.content.structured_bind_status == "bound"


def test_recorded_response_with_no_claim_text_fails_closed():
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    raw = payload["raw_model_response"]
    generated = dict(raw["generated_content"])
    generated["claims"] = [
        {
            "text": "",
            "source_refs": ["fact:indicators.OP1.1.logframe_ar1_actual"],
            "value_tokens": [],
        }
    ]
    generated["text"] = ""

    outcome = resolve_structured_synthesis(
        claims=list(generated.get("claims") or []),
        text="",
        knowledge_bank=_minimal_kb(),
    )
    assert outcome.ok is False
    assert outcome.failure_reason in ("EMPTY_SECTION_PROSE", "MISSING_STRUCTURED_CLAIMS")
