"""P1-2 adversarial split-critic cases A–E (offline, no live LLM)."""

from __future__ import annotations

import asyncio
import json

import pytest

from app.reports.agents.fact_safety_critic import (
    FactSafetyCriticError,
    run_qualitative_fact_safety_critic,
)
from app.reports.knowledge.confirmed_kb import build_confirmed_kb_view
from app.reports.knowledge.qualitative_kb_scope import (
    build_qualitative_kb_view,
    serialize_qualitative_kb_for_critic,
)
from app.reports.services.numeric_fact_verifier import verify_section_numerics
from claude_agent_sdk import ResultMessage
from tests.critic_eval_helpers import kb_backed_qualitative_query_fn


def _reconciled(value: int | float | str, *, excerpt: str | None = None) -> dict:
    return {
        "value": value,
        "verification_status": "reconciled",
        "confirmed_by_user": False,
        "source_document_id": "doc-1",
        "source_label": "test",
        "provenance": {"excerpt": excerpt or str(value)},
    }


def _kb(*, facts: dict | None = None, gaps: dict | None = None) -> dict:
    return {
        "gate1_confirmed_at": "2026-01-01T00:00:00+00:00",
        "gate2_confirmed_at": "2026-01-02T00:00:00+00:00",
        "facts": facts or {},
        "gap_answers": gaps or {},
    }


def _section(**kwargs) -> dict:
    base = {
        "section_key": "summary_and_overview",
        "label": "Summary and Overview",
        "archetype": "ARCH_EXECUTIVE_REVIEW_SUMMARY",
    }
    base.update(kwargs)
    return base


def _fabrication_query_fn(*, flagged_phrase: str):
    async def _query(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield ResultMessage(
            subtype="success",
            duration_ms=5,
            duration_api_ms=4,
            is_error=False,
            num_turns=1,
            session_id="fabrication-mock",
            structured_output={
                "specifics": [
                    {
                        "text": flagged_phrase,
                        "status": "FLAGGED",
                        "source_ref": None,
                        "severity": "BLOCK",
                        "reason": "Qualitative fabrication not in scoped KB",
                    }
                ],
                "fact_safety_status": "FLAGGED",
            },
            usage={"input_tokens": 10, "output_tokens": 10},
        )

    return _query


def test_case_a_uncited_fabricated_numerics_blocked():
    kb = _kb(facts={"indicators.op1_1.ar1_actual": _reconciled(684)})
    kb_view = build_confirmed_kb_view(kb)
    text = (
        "During the reporting period BridgeLight re-enrolled 684 girls. "
        "The programme also constructed 1247 boreholes across Kasungu district."
    )
    flags = verify_section_numerics(
        section_text=text,
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
    assert any(f.claim_text == "1247" for f in flags)


def test_case_b_dyn02_supported_prose_passes_with_scoped_kb():
    kb = _kb(
        facts={
            "grant.intervention_districts": _reconciled(
                "Machinga, Mangochi",
                excerpt="Machinga and Mangochi districts",
            ),
            "indicators.op1_1.ar1_actual": _reconciled(684),
        }
    )
    section = _section(
        content={
            "citation_mode": "structured",
            "text": "BridgeLight delivered across Machinga and Mangochi districts.",
            "evidence_used": ["fact:indicators.op1_1.ar1_actual"],
            "claims": [
                {
                    "text": "684 girls.",
                    "source_refs": ["fact:indicators.op1_1.ar1_actual"],
                    "value_tokens": ["684"],
                    "bind_status": "bound",
                }
            ],
        }
    )
    kb_view = build_confirmed_kb_view(kb)
    numeric_flags = verify_section_numerics(
        section_text=section["content"]["text"],
        claims=section["content"]["claims"],
        citation_mode="structured",
        kb_view=kb_view,
    )
    assert numeric_flags == []

    qual_view = build_qualitative_kb_view(kb, section=section)
    scoped = serialize_qualitative_kb_for_critic(qual_view)
    result = asyncio.run(
        run_qualitative_fact_safety_critic(
            section_key=section["section_key"],
            section_label=section["label"],
            section_text=section["content"]["text"],
            scoped_citable_kb=scoped,
            query_fn=kb_backed_qualitative_query_fn(),
        )
    )
    assert result.output.fact_safety_status == "VERIFIED"


def test_case_c_tampered_value_blocked_deterministic():
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
                "text": "5000 girls.",
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
    assert flags


def test_case_d_thin_evidence_used_still_passes_qualitative():
    kb = _kb(
        facts={
            "grant.intervention_districts": _reconciled(
                "Machinga, Mangochi",
                excerpt="Machinga and Mangochi",
            )
        }
    )
    section = _section(
        content={
            "text": "Activities continued in Machinga and Mangochi.",
            "evidence_used": [],
            "citation_mode": "structured",
            "claims": [],
        }
    )
    qual_view = build_qualitative_kb_view(kb, section=section)
    scoped = serialize_qualitative_kb_for_critic(qual_view)
    result = asyncio.run(
        run_qualitative_fact_safety_critic(
            section_key=section["section_key"],
            section_label=section["label"],
            section_text=section["content"]["text"],
            scoped_citable_kb=scoped,
            query_fn=kb_backed_qualitative_query_fn(),
        )
    )
    assert result.output.fact_safety_status == "VERIFIED"


def test_case_e_qualitative_fabrication_without_numbers_blocked():
    kb = _kb(
        facts={
            "grant.programme_name": _reconciled("BridgeLight Girls Education Programme")
        }
    )
    section = _section(
        content={
            "text": (
                "The programme expanded into Zambezi Province under partner "
                "Save the Children UK."
            ),
            "evidence_used": ["fact:grant.programme_name"],
            "citation_mode": "structured",
            "claims": [],
        }
    )
    qual_view = build_qualitative_kb_view(kb, section=section)
    scoped = serialize_qualitative_kb_for_critic(qual_view)
    planted = "Save the Children UK"
    result = asyncio.run(
        run_qualitative_fact_safety_critic(
            section_key=section["section_key"],
            section_label=section["label"],
            section_text=section["content"]["text"],
            scoped_citable_kb=scoped,
            query_fn=_fabrication_query_fn(flagged_phrase=planted),
        )
    )
    assert result.output.fact_safety_status == "FLAGGED"
    assert result.output.specifics[0].text == planted


def test_qualitative_error_raises_fail_closed():
    async def _fail(*, prompt: str, options=None):
        _ = prompt
        _ = options
        yield ResultMessage(
            subtype="error",
            duration_ms=1,
            duration_api_ms=1,
            is_error=True,
            num_turns=1,
            session_id="fail",
            structured_output=None,
            usage={"input_tokens": 1, "output_tokens": 0},
        )

    with pytest.raises(FactSafetyCriticError):
        asyncio.run(
            run_qualitative_fact_safety_critic(
                section_key="summary_and_overview",
                section_label="Summary",
                section_text="Some prose.",
                scoped_citable_kb={"facts": {}, "gap_answers": {}},
                query_fn=_fail,
            )
        )
