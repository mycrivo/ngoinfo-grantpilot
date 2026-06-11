"""P3-4 output quality — proposal context, humaniser, faithfulness hard-red gates."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.reports.ai.prompts.synthesis import build_synthesis_user_prompt
from app.reports.eval.faithfulness_check import load_faithfulness_fixture
from app.reports.eval.gates import gate_faithfulness
from app.reports.services.synthesis_output_hygiene import detect_humaniser_violations

ROOT = Path(__file__).resolve().parents[1]
CLEAN_FIXTURE = ROOT / "tests" / "fixtures" / "synthesis" / "clean_faithfulness_fixture.json"
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"


@pytest.fixture
def clean_fixture() -> dict:
    return load_faithfulness_fixture(CLEAN_FIXTURE)


@pytest.mark.hard_red
def test_p34_faithfulness_unmatched_numbers_hard_red(clean_fixture):
    """P3-4 hard red: any unmatched_numbers regression blocks ship."""
    result = gate_faithfulness(
        clean_fixture["content_json"],
        expected_presence=clean_fixture.get("expected_presence"),
    )
    assert result.passed, result.summary
    assert result.summary["faithfulness.unmatched_numbers"] == 0


@pytest.mark.hard_red
def test_p34_faithfulness_detects_injected_hallucination(clean_fixture):
    content = dict(clean_fixture["content_json"])
    sections = list(content.get("sections") or [])
    if not sections:
        pytest.skip("fixture has no sections")
    first = dict(sections[0])
    body = dict(first.get("content") or {})
    body["text"] = (body.get("text") or "") + " We reached 9999 beneficiaries."
    first["content"] = body
    sections[0] = first
    content["sections"] = sections
    result = gate_faithfulness(content)
    assert not result.passed
    assert result.summary["faithfulness.unmatched_numbers"] >= 1


def test_humaniser_detects_banned_words_and_proposal_voice():
    violations = detect_humaniser_violations(
        "This project will leverage a comprehensive robust synergy."
    )
    assert "banned_word:leverage" in violations
    assert "banned_word:comprehensive" in violations
    assert "proposal_voice_detected" in violations


def test_synthesis_prompt_includes_proposal_context_and_tone():
    import json

    fcdo = json.loads(FCDO_TEMPLATE.read_text(encoding="utf-8"))
    section = fcdo["report_sections_json"][0]
    report_inputs = {
        "template": {
            "funder_name": fcdo["funder_name"],
            "template_name": fcdo["template_name"],
            "format_rules_json": fcdo.get("format_rules_json", {}),
            "terminology_map_json": fcdo.get("terminology_map_json", {}),
        },
        "derived": {
            "linked_proposal_summary": "Approach: We delivered teacher training across three districts.",
            "narrative_constraints": {"voice": "third_person_formal", "strict_word_limits": True},
            "terminology_resolved": {"project": "programme / project"},
        },
        "knowledge_bank": {"facts": {}, "gap_answers": {}},
    }
    prompt = build_synthesis_user_prompt(report_inputs=report_inputs, section=section)

    assert "teacher training across three districts" in prompt
    assert "LINKED PROPOSAL CONTEXT" in prompt
    assert "Section tone:" in prompt
    assert "formal, evidence-led, concise" in prompt
    assert "third_person_formal" in prompt
