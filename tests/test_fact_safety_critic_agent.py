"""Unit tests for F2 fact-safety critic agent."""

from __future__ import annotations

import asyncio

import pytest

from app.reports.agents.fact_safety_critic import (
    FactSafetyCriticError,
    resolve_cited_sources,
    run_fact_safety_critic,
)
from claude_agent_sdk import ResultMessage


def _verified_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = options
        yield ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=8,
            is_error=False,
            num_turns=1,
            session_id="critic-test",
            structured_output={
                "specifics": [],
                "fact_safety_status": "VERIFIED",
            },
            usage={"input_tokens": 5, "output_tokens": 5},
        )

    return _query


def _flagged_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = options
        yield ResultMessage(
            subtype="success",
            duration_ms=10,
            duration_api_ms=8,
            is_error=False,
            num_turns=1,
            session_id="critic-test",
            structured_output={
                "specifics": [
                    {
                        "text": "99999",
                        "status": "FLAGGED",
                        "source_ref": None,
                        "severity": "BLOCK",
                        "reason": "Not in cited sources",
                    }
                ],
                "fact_safety_status": "FLAGGED",
            },
            usage={"input_tokens": 5, "output_tokens": 5},
        )

    return _query


def _error_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield ResultMessage(
            subtype="error",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="critic-test",
            structured_output=None,
            usage={"input_tokens": 1, "output_tokens": 0},
        )

    return _query


def test_resolve_cited_sources_maps_fact_and_gap():
    facts = {"indicators.OP1.1.actual": {"value": 684}}
    gap_answers = {
        "summary:indicator:overall": {
            "disposition": "answered",
            "answer_text": "Overall progress was steady.",
        }
    }
    resolved = resolve_cited_sources(
        evidence_used=[
            "fact:indicators.OP1.1.actual",
            "gap:summary:indicator:overall",
        ],
        facts=facts,
        gap_answers=gap_answers,
    )
    assert resolved["fact:indicators.OP1.1.actual"] == 684
    assert resolved["gap:summary:indicator:overall"] == "Overall progress was steady."


def test_clean_section_returns_verified():
    result = asyncio.run(
        run_fact_safety_critic(
            section_key="summary_and_overview",
            section_label="Summary",
            section_text="The programme reached 684 girls re-enrolled.",
            evidence_used=["fact:indicators.OP1.1.actual"],
            cited_sources={"fact:indicators.OP1.1.actual": 684},
            query_fn=_verified_query_fn(),
        )
    )
    assert result.output.fact_safety_status == "VERIFIED"
    assert result.output.specifics == []


def test_planted_unsupported_specific_is_flagged():
    result = asyncio.run(
        run_fact_safety_critic(
            section_key="summary_and_overview",
            section_label="Summary",
            section_text="The programme reached 99999 girls re-enrolled.",
            evidence_used=["fact:indicators.OP1.1.actual"],
            cited_sources={"fact:indicators.OP1.1.actual": 684},
            query_fn=_flagged_query_fn(),
        )
    )
    assert result.output.fact_safety_status == "FLAGGED"
    assert len(result.output.specifics) == 1
    assert result.output.specifics[0].status == "FLAGGED"
    assert result.output.specifics[0].severity == "BLOCK"


def test_critic_error_raises_fail_closed():
    with pytest.raises(FactSafetyCriticError) as exc:
        asyncio.run(
            run_fact_safety_critic(
                section_key="summary_and_overview",
                section_label="Summary",
                section_text="Some prose.",
                evidence_used=["fact:indicators.OP1.1.actual"],
                cited_sources={"fact:indicators.OP1.1.actual": 684},
                query_fn=_error_query_fn(),
            )
        )
    assert exc.value.code == "STOP_AGENT_ERROR"
