"""P3-8 section insufficiency policy — preflight, prose quality, partial-section edge."""

from __future__ import annotations

import json
from pathlib import Path

from app.reports.services.report_inputs_builder import section_has_synthesizable_inputs
from app.reports.services.report_synthesis_service import _generate_one_section
from app.reports.services.section_prose import (
    MIN_SECTION_PROSE_CHARS,
    STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA,
    build_insufficiency_statement,
    build_insufficient_data_section,
    has_non_empty_prose,
    section_meets_minimum_substance,
)

ROOT = Path(__file__).resolve().parents[1]
NLCF_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_NLCF.json"
FCDO_TEMPLATE = ROOT / "docs" / "artefacts" / "me_module" / "TEMPLATE_INSTANCE_FCDO.json"
P3_8_NLCF_KB = ROOT / "tests" / "fixtures" / "kb" / "p3_8_nlcf_post_gate2_skip_kb.json"
NLCF_REPORT_CONTEXT = {"report_type": "annual"}


def _section_from_template(template_path: Path, section_key: str) -> dict:
    payload = json.loads(template_path.read_text(encoding="utf-8"))
    for section in payload["report_sections_json"]:
        if section.get("section_key") == section_key:
            return section
    raise KeyError(section_key)


def _empty_kb() -> dict:
    return {
        "facts": {},
        "gap_answers": {},
        "gate1_confirmed_at": "2026-05-24T12:00:00+00:00",
    }


def _load_p3_8_nlcf_kb() -> dict:
    return json.loads(P3_8_NLCF_KB.read_text(encoding="utf-8"))


def test_insufficiency_statement_is_professional_and_submittable():
    section = _section_from_template(NLCF_TEMPLATE, "changes_and_next_steps")
    text = build_insufficiency_statement(section=section)
    assert len(text) > MIN_SECTION_PROSE_CHARS + 100
    assert text.endswith(".")
    assert "INSUFFICIENT_INPUT" not in text
    assert "ERROR" not in text
    assert "changes made" in text.lower()
    assert "How you are changing what you do" in text
    assert "left this section blank" in text
    assert "available evidence" in text
    assert any(ch.isdigit() for ch in text) is False


def test_build_insufficient_data_section_metadata():
    section = _section_from_template(NLCF_TEMPLATE, "changes_and_next_steps")
    built = build_insufficient_data_section(section=section)
    assert built["generation_status"] == "GENERATED"
    assert built["content"]["structured_bind_status"] == STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA
    assert built["content"]["citation_mode"] == "structured"
    assert built["content"]["claims"] == []
    assert section_meets_minimum_substance(built)


def test_nlcf_changes_section_zero_satisfied_inputs():
    section = _section_from_template(NLCF_TEMPLATE, "changes_and_next_steps")
    assert not section_has_synthesizable_inputs(_empty_kb(), section)


def test_fcdo_performance_partial_inputs_still_synthesizable():
    from tests.test_gap_compliance_agent import _load_distilled_fcdo_kb

    kb = _load_distilled_fcdo_kb()
    section = _section_from_template(FCDO_TEMPLATE, "performance_and_conclusions")
    assert section_has_synthesizable_inputs(kb, section)


def test_preflight_skips_openai_for_insufficient_section():
    section = _section_from_template(NLCF_TEMPLATE, "changes_and_next_steps")
    called = False

    def _query(*_args, **_kwargs):
        nonlocal called
        called = True
        return {"generation_status": "GENERATED", "generated_content": {"text": "x", "claims": []}}

    result, in_tok, out_tok = _generate_one_section(
        section=section,
        report_inputs={"knowledge_bank": {"facts": {}, "gap_answers": {}}},
        knowledge_bank_json=_empty_kb(),
        report_context={"report_type": "annual"},
        query_fn_synthesis=_query,
        user_id=None,
    )
    assert not called
    assert in_tok == 0 and out_tok == 0
    assert result["content"]["structured_bind_status"] == STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA
    assert has_non_empty_prose(result)


def test_insufficient_input_with_inputs_fails_not_insufficient_data():
    section = _section_from_template(FCDO_TEMPLATE, "performance_and_conclusions")
    from tests.test_gap_compliance_agent import _load_distilled_fcdo_kb

    kb = _load_distilled_fcdo_kb()

    def _query(*_args, **_kwargs):
        return {
            "generation_status": "INSUFFICIENT_INPUT",
            "warnings": ["model declined"],
            "generated_content": {},
        }

    result, _, _ = _generate_one_section(
        section=section,
        report_inputs={"knowledge_bank": kb},
        knowledge_bank_json=kb,
        report_context={"report_type": "annual"},
        query_fn_synthesis=_query,
        user_id=None,
    )
    assert result["generation_status"] == "FAILED"
    assert result.get("content", {}).get("structured_bind_status") != STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA


def test_partial_fcdo_section_synthesis_not_insufficient_data():
    from tests.test_gap_compliance_agent import _load_distilled_fcdo_kb

    kb = _load_distilled_fcdo_kb()
    section = _section_from_template(FCDO_TEMPLATE, "performance_and_conclusions")

    def _query(_section_key, _system, _user):
        return {
            "section_key": "performance_and_conclusions",
            "generation_status": "GENERATED",
            "archetype": section.get("archetype"),
            "generated_content": {
                "claims": [
                    {
                        "text": "Programme delivery continued against confirmed indicator records.",
                        "source_refs": ["fact:indicators.OP1.1.ar1_actual"],
                        "value_tokens": [],
                    }
                ],
                "text": "Programme delivery continued against confirmed indicator records.",
                "assumptions": [],
            },
            "constraints_applied": {"word_limit": 900, "word_limit_respected": True},
            "warnings": [],
        }

    result, _, _ = _generate_one_section(
        section=section,
        report_inputs={"knowledge_bank": kb},
        knowledge_bank_json=kb,
        report_context={"report_type": "annual"},
        query_fn_synthesis=_query,
        user_id=None,
    )
    assert result["generation_status"] == "GENERATED"
    bind_status = result["content"].get("structured_bind_status")
    assert bind_status in ("bound", "honest_empty")
    assert bind_status != STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA


def test_p3_8_nlcf_sparse_section_routing_table():
    kb = _load_p3_8_nlcf_kb()
    # Package A note: this fixture predates the source-section carrier, so its monitoring
    # rows carry no source_section. Under correct (non-bleeding) routing, learning's notes
    # (indicators.9/10, positional) are NOT routable to learning without that signal, and
    # learning no longer falsely inherits financials via the old "work"->"workers" token
    # leak. learning is therefore correctly insufficient on this pre-carrier fixture; the
    # real source-routed proof (learning sees row9/row10) lives in test_section_visibility.
    expect_insufficient = {
        "project_story",
        "community_involvement",
        "changes_and_next_steps",
        "learning",
    }
    expect_synthesis = {"difference_made", "spend_summary"}
    for section_key in expect_insufficient | expect_synthesis:
        section = _section_from_template(NLCF_TEMPLATE, section_key)
        has_inputs = section_has_synthesizable_inputs(
            kb,
            section,
            report_context=NLCF_REPORT_CONTEXT,
        )
        if section_key in expect_insufficient:
            assert has_inputs is False, section_key
        else:
            assert has_inputs is True, section_key


def test_p3_8_nlcf_sparse_sections_preflight_skips_openai():
    kb = _load_p3_8_nlcf_kb()
    for section_key in ("community_involvement", "changes_and_next_steps"):
        section = _section_from_template(NLCF_TEMPLATE, section_key)
        called = False

        def _query(*_args, **_kwargs):
            nonlocal called
            called = True
            return {
                "generation_status": "GENERATED",
                "generated_content": {"text": "should not run", "claims": []},
            }

        result, in_tok, out_tok = _generate_one_section(
            section=section,
            report_inputs={"knowledge_bank": kb},
            knowledge_bank_json=kb,
            report_context=NLCF_REPORT_CONTEXT,
            query_fn_synthesis=_query,
            user_id=None,
        )
        assert not called, section_key
        assert in_tok == 0 and out_tok == 0, section_key
        assert result["generation_status"] == "GENERATED", section_key
        assert (
            result["content"]["structured_bind_status"]
            == STRUCTURED_BIND_STATUS_INSUFFICIENT_DATA
        ), section_key
        assert has_non_empty_prose(result), section_key
