"""Tests for SDK token usage aggregation and estimated markers (P3-3)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage

from app.reports.agents.token_usage import (
    SdkUsageAccumulator,
    TokenUsageResolution,
    extract_token_counts,
    messages_api_usage_resolution,
)


def test_extract_token_counts_accepts_prompt_and_completion_aliases():
    assert extract_token_counts({"prompt_tokens": 10, "completion_tokens": 20}) == (10, 20)
    assert extract_token_counts({"input_tokens": 5, "output_tokens": 7}) == (5, 7)


def test_sub_turn_aggregate_sums_assistant_messages():
    accumulator = SdkUsageAccumulator()
    accumulator.absorb_message(
        AssistantMessage(content=[], model="haiku", usage={"input_tokens": 1000, "output_tokens": 50})
    )
    accumulator.absorb_message(
        AssistantMessage(content=[], model="haiku", usage={"input_tokens": 2000, "output_tokens": 120})
    )
    accumulator.absorb_message(
        ResultMessage(
            subtype="success",
            duration_ms=100,
            duration_api_ms=90,
            is_error=False,
            num_turns=3,
            session_id="sess",
            structured_output={"ok": True},
            usage={"input_tokens": 16, "output_tokens": 12255},
            total_cost_usd=0.42,
        )
    )

    usage = accumulator.resolve()
    assert usage == TokenUsageResolution(
        input_tokens=3000,
        output_tokens=170,
        estimated=False,
        cost_usd=0.42,
        source="sub_turn_aggregate",
    )


def test_result_only_multi_turn_marks_estimated():
    accumulator = SdkUsageAccumulator()
    accumulator.absorb_message(
        ResultMessage(
            subtype="success",
            duration_ms=100,
            duration_api_ms=90,
            is_error=False,
            num_turns=3,
            session_id="sess",
            structured_output={"ok": True},
            usage={"input_tokens": 16, "output_tokens": 12255},
        )
    )

    usage = accumulator.resolve()
    assert usage.input_tokens == 16
    assert usage.output_tokens == 12255
    assert usage.estimated is True
    assert usage.source == "result_usage"


def test_result_only_single_turn_not_estimated():
    accumulator = SdkUsageAccumulator()
    accumulator.absorb_message(
        ResultMessage(
            subtype="success",
            duration_ms=50,
            duration_api_ms=40,
            is_error=False,
            num_turns=1,
            session_id="sess",
            structured_output={"ok": True},
            usage={"input_tokens": 100, "output_tokens": 400},
        )
    )

    usage = accumulator.resolve()
    assert usage.estimated is False


def test_model_usage_preferred_over_result_usage_when_no_sub_turns():
    accumulator = SdkUsageAccumulator()
    accumulator.absorb_message(
        ResultMessage(
            subtype="success",
            duration_ms=50,
            duration_api_ms=40,
            is_error=False,
            num_turns=3,
            session_id="sess",
            structured_output={"ok": True},
            usage={"input_tokens": 16, "output_tokens": 12255},
            model_usage={
                "claude-haiku-4-5": {
                    "input_tokens": 8000,
                    "output_tokens": 12000,
                }
            },
        )
    )

    usage = accumulator.resolve()
    assert usage.input_tokens == 8000
    assert usage.output_tokens == 12000
    assert usage.estimated is False
    assert usage.source == "model_usage"


def test_messages_api_usage_resolution_is_authoritative():
    usage = messages_api_usage_resolution(
        SimpleNamespace(input_tokens=21748, output_tokens=512)
    )
    assert usage.estimated is False
    assert usage.input_tokens == 21748
    assert usage.output_tokens == 512


@pytest.mark.asyncio
async def test_proposal_extractor_marks_estimated_for_result_only_stream():
    from app.reports.agents.proposal_extractor import extract_proposal_text

    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield ResultMessage(
            subtype="success",
            duration_ms=200,
            duration_api_ms=180,
            is_error=False,
            num_turns=3,
            session_id="test-session",
            structured_output={
                "confidence": 0.9,
                "objectives": [],
                "activities": [],
                "indicators": [],
            },
            usage={"input_tokens": 16, "output_tokens": 400},
        )

    result = await extract_proposal_text(
        "Sample proposal text for cost truth test.",
        query_fn=_mock_query,
    )
    trace = result.envelope.agent_trace
    assert trace is not None
    assert trace.input_tokens == 16
    assert trace.output_tokens == 400
    assert trace.estimated is True


@pytest.mark.asyncio
async def test_proposal_extractor_aggregates_sub_turn_usage():
    from app.reports.agents.proposal_extractor import extract_proposal_text

    async def _mock_query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield AssistantMessage(
            content=[],
            model="haiku",
            usage={"input_tokens": 5000, "output_tokens": 200},
        )
        yield AssistantMessage(
            content=[],
            model="haiku",
            usage={"input_tokens": 3000, "output_tokens": 100},
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=200,
            duration_api_ms=180,
            is_error=False,
            num_turns=2,
            session_id="test-session",
            structured_output={
                "confidence": 0.9,
                "objectives": [],
                "activities": [],
                "indicators": [],
            },
            usage={"input_tokens": 16, "output_tokens": 400},
            total_cost_usd=0.15,
        )

    result = await extract_proposal_text(
        "Sample proposal text for sub-turn aggregation.",
        query_fn=_mock_query,
    )
    trace = result.envelope.agent_trace
    assert trace is not None
    assert trace.input_tokens == 8000
    assert trace.output_tokens == 300
    assert trace.estimated is False
    assert trace.cost_usd == 0.15
