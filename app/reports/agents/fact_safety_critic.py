"""F2 fact-safety critic — verify section specifics against cited KB sources."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.reports.schemas.fact_safety_critic_v1 import (
    CRITIC_AGENT_NAME,
    FactSafetyCriticLLMOutput,
    FactSafetySpecificResult,
)
from app.reports.schemas.qualitative_critic_v1 import QualitativeCriticLLMOutput

logger = logging.getLogger("reports.agents.fact_safety_critic")

AGENT_NAME = CRITIC_AGENT_NAME
DEFAULT_MODEL = os.getenv(
    "ME_FACT_SAFETY_CRITIC_MODEL",
    os.getenv("ME_RECONCILER_MODEL", "claude-sonnet-4-6"),
)
TIMEOUT_SECONDS = int(os.getenv("ME_FACT_SAFETY_CRITIC_TIMEOUT_SECONDS", "120"))
MAX_INPUT_CHARS = 80_000
MAX_OUTPUT_TOKENS = 4096

_MODEL_API_IDS: dict[str, str] = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

_QUALITATIVE_SYSTEM_PROMPT = """You are the GrantPilot M&E qualitative fact-safety critic (F2 pass 2).

Your ONLY job: verify checkable QUALITATIVE specifics in rendered section prose against
the scoped citable knowledge bank supplied — names, places, organizations, programme
titles, and narrative outcome statements.

CARDINAL RULES:
1. VERIFY ONLY qualitative content — do NOT evaluate numbers, dates, currency amounts,
   or percentages. Those are adjudicated by a deterministic pass you must defer to.
2. Use ONLY the scoped citable_knowledge_bank (facts, gap_answers, conflicts_resolved).
   Do NOT restrict yourself to evidence_used[] — that list is lossy.
3. A specific PASSES when it appears in (or is faithfully paraphrased from) ANY value,
   excerpt, or answer_text in the scoped citable KB for THIS section context.
4. A specific is FLAGGED (severity BLOCK) when it is checkable and NOT supported by
   the scoped KB — including claims that are true elsewhere but NOT supported HERE.
5. General narrative without a checkable proper noun or concrete claim is not flagged.
6. Return JSON only — no markdown fences, no prose.

OUTPUT FORMAT:
{
  "specifics": [
    {
      "text": "exact substring from section prose",
      "status": "VERIFIED | FLAGGED",
      "source_ref": "fact:key or gap:key when VERIFIED, else null",
      "severity": "BLOCK | WARN (required when FLAGGED)",
      "reason": "brief reason when FLAGGED"
    }
  ],
  "fact_safety_status": "VERIFIED | FLAGGED"
}
"""

_LEGACY_SYSTEM_PROMPT = """You are the GrantPilot M&E fact-safety critic (legacy evidence_used path).

Your ONLY job: verify that named specifics in a synthesised report section trace to
admissible knowledge-bank sources cited in evidence_used[].

CARDINAL RULES:
1. VERIFY ONLY — do NOT re-judge M&E scores, variance, or funder opinions.
2. A specific (number, name, date, money amount, percentage, score) PASSES when it
   faithfully matches a value from the cited source_refs supplied.
3. Use ONLY evidence_used[] as the candidate source set — do not invent other sources.
4. Admissible sources are fact: and gap: keys with their resolved values provided.
5. If a specific appears in the prose but is NOT supported by any cited source value,
   mark it FLAGGED with severity BLOCK.
6. Contradictions between prose and a cited source value are FLAGGED.
7. General narrative without a checkable specific is not flagged.
8. Return JSON only — no markdown fences, no prose.

OUTPUT FORMAT:
{
  "specifics": [
    {
      "text": "exact substring from section prose",
      "status": "VERIFIED | FLAGGED",
      "source_ref": "fact:key or gap:key when VERIFIED, else null",
      "severity": "BLOCK | WARN (required when FLAGGED)",
      "reason": "brief reason when FLAGGED"
    }
  ],
  "fact_safety_status": "VERIFIED | FLAGGED"
}
"""

_NUMERIC_SPECIFIC_RE = re.compile(
    r"^\s*(?:[\d,]+(?:\.\d+)?|\d{4}-\d{2}-\d{2}|(?:gbp|£|\$)\s*[\d,]+)\s*$",
    re.IGNORECASE,
)

QueryFn = Callable[..., AsyncIterator[Any]]


class FactSafetyCriticError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class FactSafetyCriticResult:
    output: FactSafetyCriticLLMOutput
    model_used: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


def _api_model_id(model: str) -> str:
    return _MODEL_API_IDS.get(model, model)


def _extract_token_counts(usage: Any) -> tuple[int | None, int | None]:
    if usage is None:
        return None, None
    input_tokens = getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None) or getattr(usage, "completion_tokens", None)
    return (
        int(input_tokens) if input_tokens is not None else None,
        int(output_tokens) if output_tokens is not None else None,
    )


def _parse_json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.match(
            r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", stripped, re.DOTALL | re.IGNORECASE
        )
        if match:
            stripped = match.group(1).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise FactSafetyCriticError(
            "STOP_PARSE_FAILED",
            f"Critic response is not valid JSON: {exc}",
        ) from exc
    if not isinstance(parsed, dict):
        raise FactSafetyCriticError(
            "STOP_PARSE_FAILED",
            "Critic response must be a JSON object",
        )
    return parsed


def resolve_cited_sources(
    *,
    evidence_used: list[str],
    facts: dict[str, Any],
    gap_answers: dict[str, Any],
) -> dict[str, Any]:
    """Map fact:/gap: refs to admissible KB values for critic verification."""
    resolved: dict[str, Any] = {}
    for ref in evidence_used:
        if not isinstance(ref, str):
            continue
        if ref.startswith("fact:"):
            key = ref.removeprefix("fact:")
            fact = facts.get(key)
            if isinstance(fact, dict):
                resolved[ref] = fact.get("value")
        elif ref.startswith("gap:"):
            key = ref.removeprefix("gap:")
            entry = gap_answers.get(key)
            if isinstance(entry, dict):
                resolved[ref] = entry.get("answer_text")
    return resolved


def strip_numeric_flags_from_llm_output(
    specifics: list[FactSafetySpecificResult],
) -> list[FactSafetySpecificResult]:
    """Drop numeric/date/currency specifics — deterministic pass owns them."""
    kept: list[FactSafetySpecificResult] = []
    for item in specifics:
        text = str(item.text or "").strip()
        if _NUMERIC_SPECIFIC_RE.match(text):
            continue
        if re.search(r"\b\d[\d,]*(?:\.\d+)?\b", text) and len(text) < 24:
            continue
        kept.append(item)
    return kept


def build_qualitative_critic_prompt(
    *,
    section_key: str,
    section_label: str,
    section_text: str,
    scoped_citable_kb: dict[str, Any],
) -> str:
    payload = {
        "section_key": section_key,
        "section_label": section_label,
        "section_text": section_text,
        "scoped_citable_knowledge_bank": scoped_citable_kb,
        "numeric_adjudication": {
            "covered_by_deterministic_pass": True,
            "instruction": "Do NOT evaluate numbers, dates, currency, or percentages.",
        },
    }
    text = json.dumps(payload, indent=2)
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
    return (
        "Verify qualitative specifics in section_text against scoped_citable_knowledge_bank.\n\n"
        f"<qualitative_fact_safety_critic_input>\n{text}\n</qualitative_fact_safety_critic_input>"
    )


def build_fact_safety_critic_prompt(
    *,
    section_key: str,
    section_label: str,
    section_text: str,
    evidence_used: list[str],
    cited_sources: dict[str, Any],
) -> str:
    payload = {
        "section_key": section_key,
        "section_label": section_label,
        "section_text": section_text,
        "evidence_used": evidence_used,
        "cited_sources": cited_sources,
    }
    text = json.dumps(payload, indent=2)
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
    return (
        "Verify every named specific in section_text against cited_sources only.\n\n"
        f"<fact_safety_critic_input>\n{text}\n</fact_safety_critic_input>"
    )


def _validate_qualitative_output(raw: dict[str, Any]) -> QualitativeCriticLLMOutput:
    try:
        llm = QualitativeCriticLLMOutput.model_validate(raw)
    except ValidationError as exc:
        raise FactSafetyCriticError(
            "STOP_VALIDATION_FAILED",
            f"Qualitative critic LLM output invalid: {exc}",
        ) from exc

    filtered = strip_numeric_flags_from_llm_output(list(llm.specifics))
    flagged = [s for s in filtered if s.status == "FLAGGED"]
    status = "FLAGGED" if flagged else "VERIFIED"

    normalized: list[FactSafetySpecificResult] = []
    for item in filtered:
        if item.status == "FLAGGED" and not item.severity:
            normalized.append(
                FactSafetySpecificResult(
                    text=item.text,
                    status=item.status,
                    source_ref=item.source_ref,
                    severity="BLOCK",
                    reason=item.reason or "Not supported by scoped citable KB",
                )
            )
        else:
            normalized.append(item)
    return QualitativeCriticLLMOutput(
        specifics=normalized,
        fact_safety_status=status,
    )


def _validate_llm_output(raw: dict[str, Any]) -> FactSafetyCriticLLMOutput:
    try:
        llm = FactSafetyCriticLLMOutput.model_validate(raw)
    except ValidationError as exc:
        raise FactSafetyCriticError(
            "STOP_VALIDATION_FAILED",
            f"Critic LLM output invalid: {exc}",
        ) from exc

    flagged = [s for s in llm.specifics if s.status == "FLAGGED"]
    if flagged and llm.fact_safety_status == "VERIFIED":
        llm = FactSafetyCriticLLMOutput(
            specifics=llm.specifics,
            fact_safety_status="FLAGGED",
        )
    elif not flagged:
        llm = FactSafetyCriticLLMOutput(specifics=llm.specifics, fact_safety_status="VERIFIED")

    normalized: list[FactSafetySpecificResult] = []
    for item in llm.specifics:
        if item.status == "FLAGGED" and not item.severity:
            normalized.append(
                FactSafetySpecificResult(
                    text=item.text,
                    status=item.status,
                    source_ref=item.source_ref,
                    severity="BLOCK",
                    reason=item.reason or "Not supported by cited sources",
                )
            )
        else:
            normalized.append(item)
    return FactSafetyCriticLLMOutput(
        specifics=normalized,
        fact_safety_status=llm.fact_safety_status,
    )


async def _call_anthropic_messages(
    prompt: str,
    *,
    model: str,
    system_prompt: str,
) -> tuple[str, int, int | None, int | None]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(timeout=float(TIMEOUT_SECONDS))
    api_model = _api_model_id(model)
    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=api_model,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        raise FactSafetyCriticError(
            "STOP_API_ERROR",
            f"Anthropic Messages API call failed: {exc}",
        ) from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text_parts = [
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ]
    if not text_parts:
        raise FactSafetyCriticError(
            "STOP_NO_RESULT",
            "Critic returned no text content",
        )
    input_tokens, output_tokens = _extract_token_counts(response.usage)
    return "".join(text_parts), latency_ms, input_tokens, output_tokens


async def _run_critic_query(
    prompt: str,
    *,
    query_fn: QueryFn | None,
    model: str | None = None,
    system_prompt: str = _QUALITATIVE_SYSTEM_PROMPT,
) -> tuple[dict[str, Any], str, int | None, int | None, int | None]:
    resolved_model = model or DEFAULT_MODEL
    structured_output: dict[str, Any] | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None

    if query_fn is not None:
        is_error = False
        stop_reason: str | None = None
        async for message in query_fn(prompt=prompt, options=None):
            is_error = bool(getattr(message, "is_error", False))
            stop_reason = getattr(message, "stop_reason", stop_reason)
            latency_ms = getattr(message, "duration_ms", latency_ms)
            input_tokens, output_tokens = _extract_token_counts(
                getattr(message, "usage", None)
            )
            so = getattr(message, "structured_output", None)
            if so is not None:
                structured_output = so
                break
        if is_error:
            raise FactSafetyCriticError(
                "STOP_AGENT_ERROR",
                f"Critic returned an error (stop_reason={stop_reason})",
            )
    else:
        text, latency_ms, input_tokens, output_tokens = await _call_anthropic_messages(
            prompt, model=resolved_model, system_prompt=system_prompt
        )
        structured_output = _parse_json_from_text(text)

    if structured_output is None:
        raise FactSafetyCriticError(
            "STOP_NO_RESULT",
            "Critic finished without structured output",
        )
    return structured_output, resolved_model, latency_ms, input_tokens, output_tokens


async def run_qualitative_fact_safety_critic(
    *,
    section_key: str,
    section_label: str,
    section_text: str,
    scoped_citable_kb: dict[str, Any],
    query_fn: QueryFn | None = None,
    model: str | None = None,
) -> FactSafetyCriticResult:
    """P1-2 qualitative LLM pass — rendered prose vs scoped citable KB."""
    prompt = build_qualitative_critic_prompt(
        section_key=section_key,
        section_label=section_label,
        section_text=section_text,
        scoped_citable_kb=scoped_citable_kb,
    )

    logger.info(
        "qualitative_fact_safety_critic start section=%s model=%s",
        section_key,
        model or DEFAULT_MODEL,
    )

    try:
        structured_output, resolved_model, latency_ms, input_tokens, output_tokens = (
            await asyncio.wait_for(
                _run_critic_query(
                    prompt,
                    query_fn=query_fn,
                    model=model,
                    system_prompt=_QUALITATIVE_SYSTEM_PROMPT,
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )
    except asyncio.TimeoutError as exc:
        raise FactSafetyCriticError(
            "STOP_TIMEOUT",
            f"Qualitative fact-safety critic exceeded {TIMEOUT_SECONDS}s timeout",
        ) from exc

    qual = _validate_qualitative_output(structured_output)
    legacy = FactSafetyCriticLLMOutput(
        specifics=qual.specifics,
        fact_safety_status=qual.fact_safety_status,
    )
    return FactSafetyCriticResult(
        output=legacy,
        model_used=resolved_model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


async def run_fact_safety_critic(
    *,
    section_key: str,
    section_label: str,
    section_text: str,
    evidence_used: list[str],
    cited_sources: dict[str, Any],
    query_fn: QueryFn | None = None,
    model: str | None = None,
) -> FactSafetyCriticResult:
    """Run F2 critic for one generated section."""
    prompt = build_fact_safety_critic_prompt(
        section_key=section_key,
        section_label=section_label,
        section_text=section_text,
        evidence_used=evidence_used,
        cited_sources=cited_sources,
    )

    logger.info(
        "fact_safety_critic start section=%s model=%s",
        section_key,
        model or DEFAULT_MODEL,
    )

    try:
        structured_output, resolved_model, latency_ms, input_tokens, output_tokens = (
            await asyncio.wait_for(
                _run_critic_query(
                    prompt,
                    query_fn=query_fn,
                    model=model,
                    system_prompt=_LEGACY_SYSTEM_PROMPT,
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )
    except asyncio.TimeoutError as exc:
        raise FactSafetyCriticError(
            "STOP_TIMEOUT",
            f"Fact-safety critic exceeded {TIMEOUT_SECONDS}s timeout",
        ) from exc

    output = _validate_llm_output(structured_output)
    return FactSafetyCriticResult(
        output=output,
        model_used=resolved_model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
