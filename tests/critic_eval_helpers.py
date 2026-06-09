"""Offline split-critic eval helpers for P1-2 unit/fixture tests (no live LLM)."""

from __future__ import annotations

import json
import re
from typing import Any

from claude_agent_sdk import ResultMessage

from app.reports.knowledge.confirmed_kb import build_confirmed_kb_view
from app.reports.knowledge.qualitative_kb_scope import (
    build_qualitative_kb_view,
    serialize_qualitative_kb_for_critic,
)
from app.reports.services.numeric_fact_verifier import (
    numeric_flag_to_critic_dict,
    verify_section_numerics,
)

_PROMPT_JSON_RE = re.compile(
    r"<qualitative_fact_safety_critic_input>\s*(\{.*?\})\s*</qualitative_fact_safety_critic_input>",
    re.DOTALL,
)


def _parse_qualitative_prompt(prompt: str) -> dict[str, Any]:
    match = _PROMPT_JSON_RE.search(prompt)
    if not match:
        return {}
    return json.loads(match.group(1))


def _kb_corpus_lower(scoped_kb: dict[str, Any]) -> str:
    parts: list[str] = []
    for fact in (scoped_kb.get("facts") or {}).values():
        if isinstance(fact, dict):
            parts.append(str(fact.get("value") or ""))
            parts.append(str(fact.get("excerpt") or ""))
            parts.append(str(fact.get("semantic_label") or ""))
    for gap in (scoped_kb.get("gap_answers") or {}).values():
        if isinstance(gap, dict):
            parts.append(str(gap.get("answer_text") or ""))
    return " ".join(parts).lower()


_SENTENCE_START_SKIP = frozenset({"Activities", "The", "During", "Overall", "Summary"})


def _qualitative_terms_to_check(text: str) -> list[str]:
    terms: list[str] = []
    words = re.findall(r"\b[A-Za-z]+\b", text)
    for index, word in enumerate(words):
        if not word[0].isupper():
            continue
        if index == 0 and word in _SENTENCE_START_SKIP:
            continue
        terms.append(word)
    terms.extend(
        match
        for match in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text)
        if match not in terms
    )
    return terms


def _phrase_in_corpus(phrase: str, corpus: str) -> bool:
    phrase_lower = phrase.lower()
    if phrase_lower in corpus:
        return True
    words = re.findall(r"[a-z0-9]+", phrase_lower)
    return bool(words) and all(word in corpus for word in words)


def kb_backed_qualitative_query_fn(*, fabrications: dict[str, list[str]] | None = None):
    """Mock LLM: VERIFIED when prose terms appear in scoped KB; optional planted flags."""

    fabrications = fabrications or {}

    async def _query(*, prompt: str, options=None):
        _ = options
        payload = _parse_qualitative_prompt(prompt)
        section_key = str(payload.get("section_key") or "")
        section_text = str(payload.get("section_text") or "")
        scoped_kb = payload.get("scoped_citable_knowledge_bank") or {}
        corpus = _kb_corpus_lower(scoped_kb)

        planted = fabrications.get(section_key) or []
        specifics: list[dict[str, Any]] = []
        for phrase in planted:
            if phrase in section_text:
                specifics.append(
                    {
                        "text": phrase,
                        "status": "FLAGGED",
                        "source_ref": None,
                        "severity": "BLOCK",
                        "reason": "Not supported by scoped citable KB",
                    }
                )

        for term in _qualitative_terms_to_check(section_text):
            if term in {"BridgeLight"}:
                continue
            if _phrase_in_corpus(term, corpus):
                continue
            if len(term) < 4:
                continue
            if any(term in p for p in planted):
                continue
            specifics.append(
                {
                    "text": term,
                    "status": "FLAGGED",
                    "source_ref": None,
                    "severity": "BLOCK",
                    "reason": f"{term} not found in scoped KB",
                }
            )

        status = "FLAGGED" if specifics else "VERIFIED"
        yield ResultMessage(
            subtype="success",
            duration_ms=5,
            duration_api_ms=4,
            is_error=False,
            num_turns=1,
            session_id="kb-backed-qual-mock",
            structured_output={
                "specifics": specifics,
                "fact_safety_status": status,
            },
            usage={"input_tokens": 10, "output_tokens": 10},
        )

    return _query


def run_offline_split_critic(
    *,
    knowledge_bank_json: dict[str, Any],
    section: dict[str, Any],
    qualitative_query_fn=None,
) -> list[dict[str, Any]]:
    """Deterministic numeric pass + mocked qualitative pass; returns merged critic flags."""
    kb_view = build_confirmed_kb_view(knowledge_bank_json)
    content = section.get("content") or {}
    section_text = str(content.get("text") or "")

    numeric_flags = verify_section_numerics(
        section_text=section_text,
        claims=list(content.get("claims") or []),
        citation_mode=content.get("citation_mode"),
        kb_view=kb_view,
    )
    flags = [numeric_flag_to_critic_dict(f) for f in numeric_flags]

    if qualitative_query_fn is None:
        return flags

    qual_view = build_qualitative_kb_view(knowledge_bank_json, section=section)
    scoped_kb = serialize_qualitative_kb_for_critic(qual_view)

    import asyncio

    from app.reports.agents.fact_safety_critic import run_qualitative_fact_safety_critic
    from app.reports.schemas.qualitative_critic_v1 import qualitative_flag_from_specific

    result = asyncio.run(
        run_qualitative_fact_safety_critic(
            section_key=str(section.get("section_key") or ""),
            section_label=str(section.get("label") or ""),
            section_text=section_text,
            scoped_citable_kb=scoped_kb,
            query_fn=qualitative_query_fn,
        )
    )
    flags.extend(
        qualitative_flag_from_specific(item)
        for item in result.output.specifics
        if item.status == "FLAGGED"
    )
    return flags
