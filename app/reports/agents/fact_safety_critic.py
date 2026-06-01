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

_SYSTEM_PROMPT = """You are the GrantPilot M&E fact-safety critic (F2).

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

fact_safety_status is VERIFIED only when every checkable specific is VERIFIED.
Use FLAGGED when any specific is FLAGGED.
"""

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


async def _call_anthropic_messages(prompt: str, *, model: str) -> tuple[str, int, int | None, int | None]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(timeout=float(TIMEOUT_SECONDS))
    api_model = _api_model_id(model)
    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=api_model,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0,
            system=_SYSTEM_PROMPT,
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
            prompt, model=resolved_model
        )
        structured_output = _parse_json_from_text(text)

    if structured_output is None:
        raise FactSafetyCriticError(
            "STOP_NO_RESULT",
            "Critic finished without structured output",
        )
    return structured_output, resolved_model, latency_ms, input_tokens, output_tokens


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
                _run_critic_query(prompt, query_fn=query_fn, model=model),
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
