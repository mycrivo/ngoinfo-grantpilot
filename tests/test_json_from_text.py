"""Tests for JSON extraction from LLM prose responses."""

from __future__ import annotations

from app.reports.parsing.json_from_text import (
    extract_json_object_from_text,
    parse_json_object_from_text,
)


def test_extract_json_from_markdown_fence():
    text = 'Here is the result:\n```json\n{"readiness_score": 42, "gaps": []}\n```'
    parsed = extract_json_object_from_text(text)
    assert parsed == {"readiness_score": 42, "gaps": []}


def test_extract_json_from_prose_preamble():
    prose = (
        "I need to evaluate each checklist item. SATISFIED requires source_document_id.\n"
        '{"readiness_score": 10, "gaps": [{"item_key": "a:b:c", "section_key": "a", '
        '"section_label": "A", "required_item_type": "indicator", '
        '"required_item_ref": "c", "severity": "required", '
        '"question": "Q?", "rationale": "R."}]}'
    )
    parsed = parse_json_object_from_text(prose)
    assert parsed["readiness_score"] == 10
    assert len(parsed["gaps"]) == 1


def test_extract_json_returns_none_for_plain_prose():
    assert extract_json_object_from_text("No JSON here at all.") is None
