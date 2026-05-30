"""Deterministic agent mocks for orchestrator validation tests."""

from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import ResultMessage


def _result_message(payload: dict[str, Any]) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=100,
        duration_api_ms=80,
        is_error=False,
        num_turns=1,
        session_id="orch-test",
        structured_output=payload,
        usage={"input_tokens": 10, "output_tokens": 10},
    )


def routing_classifier_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = options
        if "proposal.docx" in prompt:
            label = "proposal"
        elif "award_letter" in prompt:
            label = "grant_letter"
        else:
            label = "other"
        yield _result_message(
            {
                "classification": label,
                "confidence": 0.95,
                "justification": f"Test routing to {label}.",
            }
        )

    return _query


def minimal_proposal_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(
            {
                "confidence": 0.91,
                "objectives": [
                    {
                        "objective_key": "impact_test",
                        "label": "Improve education outcomes for girls.",
                        "level": "impact",
                        "status": "extracted",
                        "provenance": {
                            "excerpt": "Improve education outcomes for girls.",
                            "section_label": "Objectives",
                        },
                    }
                ],
                "activities": [],
                "indicators": [],
            }
        )

    return _query


def _grant_field(raw: str, normalized: str) -> dict:
    return {
        "absent": False,
        "raw": raw,
        "normalized": normalized,
        "normalization_ambiguous": False,
        "provenance": {"excerpt": raw[:80], "section_label": "Award"},
        "multi_value": False,
        "stated_values": [],
    }


def minimal_grant_terms_query_fn():
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(
            {
                "confidence": 0.9,
                "funder": _grant_field("Test Funder", "Test Funder"),
                "grant_reference": _grant_field("REF-001", "REF-001"),
                "award_budget": {
                    "amount": _grant_field("GBP 100000", "100000"),
                    "currency": _grant_field("GBP", "GBP"),
                    "tranches": [],
                },
                "grant_period": {
                    "start": _grant_field("2024-01-01", "2024-01-01"),
                    "end": _grant_field("2026-12-31", "2026-12-31"),
                },
                "reporting_period": {
                    "start": _grant_field("2024-01-01", "2024-01-01"),
                    "end": _grant_field("2024-12-31", "2024-12-31"),
                },
                "reporting_obligations": [],
                "reporting_deadlines": [],
            }
        )

    return _query


def slow_query_fn(*, delay_seconds: float = 2.0):
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await asyncio.sleep(delay_seconds)
        yield _result_message({"classification": "proposal", "confidence": 0.9, "justification": "slow"})

    return _query


def reconciler_query_fn(*, source_document_id: str):
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield _result_message(
            {
                "facts": [
                    {
                        "fact_key": "budget_total",
                        "value": "100000",
                        "unit": "GBP",
                        "semantic_label": "Award budget total",
                        "coverage": "single_source",
                        "source_document_id": source_document_id,
                        "source_label": "award_letter.pdf",
                        "provenance": {"excerpt": "GBP 100000"},
                    }
                ],
                "conflicts": [],
            }
        )

    return _query


def slow_grant_terms_query_fn(*, delay_seconds: float = 2.0):
    payload_fn = minimal_grant_terms_query_fn()

    async def _query(*, prompt: str, options=None):
        await __import__("asyncio").sleep(delay_seconds)
        async for message in payload_fn(prompt=prompt, options=options):
            yield message

    return _query


def slow_reconciler_query_fn(*, delay_seconds: float = 2.0):
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        await asyncio.sleep(delay_seconds)
        yield _result_message({"facts": [], "conflicts": []})

    return _query
