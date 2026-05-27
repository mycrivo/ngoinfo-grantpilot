"""Gap/compliance agent (E3) — readiness score + funder-aware gap questions."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.reports.gap.template_requirements import (
    TemplateRequirement,
    enumerate_template_requirements,
)
from app.reports.schemas.gap_compliance_v1 import (
    GAP_AGENT_NAME,
    GapComplianceAgentTrace,
    GapComplianceGapItem,
    GapComplianceLLMOutput,
    GapComplianceOutput,
    GapCompliancePersistedEnvelope,
    validate_gap_compliance_output,
)

logger = logging.getLogger("reports.agents.gap_compliance_agent")

AGENT_NAME = GAP_AGENT_NAME
DEFAULT_MODEL = os.getenv("ME_GAP_COMPLIANCE_MODEL", os.getenv("ME_RECONCILER_MODEL", "claude-sonnet-4-6"))
TIMEOUT_SECONDS = int(os.getenv("ME_GAP_COMPLIANCE_TIMEOUT_SECONDS", "180"))
MAX_INPUT_CHARS = 120_000
MAX_OUTPUT_TOKENS = 8192

_MODEL_API_IDS: dict[str, str] = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

_SYSTEM_PROMPT = """You are the GrantPilot M&E gap/compliance agent (E3).

Your ONLY job: compare a Gate-1-confirmed knowledge bank against a funder report
template checklist and identify genuinely MISSING required items.

CARDINAL RULES:
1. DATA-DRIVEN: Use ONLY the template checklist and knowledge bank supplied. Never
   invent funder-specific rules or branch on funder name.
2. DO NOT resolve gaps, invent facts, or suggest values. Only identify missing items
   and ask funder-aware questions.
3. SATISFIED means the knowledge bank already supplies the item from an ALLOWED source:
   - uploaded_documents: a fact with source_document_id and relevant content
   - human_confirmed_gap_answers: gap_answers[item_key].answer_text present
   Do NOT treat unresolved conflicts or bare suggestions as satisfaction.
4. Emit a gap ONLY for checklist items that are genuinely unsatisfied.
5. Questions must use the section label/tone/terminology from the template (read from
   the template JSON — do not use generic wording when the template supplies labels).
6. Use the exact item_key, section_key, required_item_type, and required_item_ref from
   the checklist for every gap. Do not invent alternate keys.

OUTPUT FORMAT:
- Return a single JSON object only — no markdown fences, no prose, no tools.
- JSON schema:
{
  "readiness_score": 0-100 integer (100 only when every checklist item is satisfied),
  "gaps": [
    {
      "item_key": "string (from checklist)",
      "section_key": "string",
      "section_label": "string",
      "required_item_type": "indicator | table | section",
      "required_item_ref": "string",
      "severity": "required",
      "question": "funder-aware question for the human",
      "rationale": "brief why this is missing"
    }
  ]
}
"""

QueryFn = Callable[..., AsyncIterator[Any]]


class GapComplianceAgentError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class GapComplianceAgentResult:
    envelope: GapCompliancePersistedEnvelope
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
        raise GapComplianceAgentError(
            "STOP_PARSE_FAILED",
            f"Gap agent response is not valid JSON: {exc}",
        ) from exc
    if not isinstance(parsed, dict):
        raise GapComplianceAgentError(
            "STOP_PARSE_FAILED",
            "Gap agent response must be a JSON object",
        )
    return parsed


def _requirements_for_prompt(requirements: list[TemplateRequirement]) -> list[dict[str, Any]]:
    return [
        {
            "item_key": req.item_key,
            "section_key": req.section_key,
            "section_label": req.section_label,
            "required_item_type": req.required_item_type,
            "required_item_ref": req.required_item_ref,
            "severity": req.severity,
        }
        for req in requirements
        if req.required_item_type != "section"
    ]


def build_gap_compliance_prompt(
    *,
    knowledge_bank_json: dict[str, Any],
    template_payload: dict[str, Any],
    requirements: list[TemplateRequirement],
    report_context: dict[str, Any],
) -> str:
    checklist = _requirements_for_prompt(requirements)
    payload = {
        "report_context": report_context,
        "template": {
            "funder_name": template_payload.get("funder_name"),
            "template_name": template_payload.get("template_name"),
            "report_sections_json": template_payload.get("report_sections_json"),
            "format_rules_json": template_payload.get("format_rules_json"),
            "terminology_map_json": template_payload.get("terminology_map_json"),
        },
        "checklist": checklist,
        "knowledge_bank": {
            "schema_version": knowledge_bank_json.get("schema_version"),
            "facts": knowledge_bank_json.get("facts"),
            "conflicts": knowledge_bank_json.get("conflicts"),
            "unreadable_sources": knowledge_bank_json.get("unreadable_sources"),
            "gap_answers": knowledge_bank_json.get("gap_answers"),
            "gate1_confirmed_at": knowledge_bank_json.get("gate1_confirmed_at"),
        },
    }
    text = json.dumps(payload, indent=2)
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS]
    return (
        "Score readiness and list gaps for unsatisfied checklist items only.\n\n"
        f"<gap_compliance_input>\n{text}\n</gap_compliance_input>"
    )


def _validate_llm_output(
    raw: dict[str, Any],
    *,
    allowed_item_keys: set[str],
) -> GapComplianceOutput:
    try:
        llm = GapComplianceLLMOutput.model_validate(raw)
    except ValidationError as exc:
        raise GapComplianceAgentError(
            "STOP_VALIDATION_FAILED",
            f"Gap agent LLM output invalid: {exc}",
        ) from exc
    gaps = [GapComplianceGapItem.model_validate(g.model_dump()) for g in llm.gaps]
    ready_for_gate2 = llm.readiness_score == 100 and not gaps
    structured = GapComplianceOutput(
        readiness_score=llm.readiness_score,
        ready_for_gate2=ready_for_gate2,
        gaps=gaps,
    )
    errors = validate_gap_compliance_output(
        structured, allowed_item_keys=allowed_item_keys
    )
    if errors:
        raise GapComplianceAgentError(
            "STOP_VALIDATION_FAILED",
            "; ".join(errors),
        )
    return structured


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
        raise GapComplianceAgentError(
            "STOP_API_ERROR",
            f"Anthropic Messages API call failed: {exc}",
        ) from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text_parts = [
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ]
    if not text_parts:
        raise GapComplianceAgentError(
            "STOP_NO_RESULT",
            "Gap agent returned no text content",
        )
    input_tokens, output_tokens = _extract_token_counts(response.usage)
    return "".join(text_parts), latency_ms, input_tokens, output_tokens


async def _run_gap_query(
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
            raise GapComplianceAgentError(
                "STOP_AGENT_ERROR",
                f"Gap agent returned an error (stop_reason={stop_reason})",
            )
    else:
        text, latency_ms, input_tokens, output_tokens = await _call_anthropic_messages(
            prompt, model=resolved_model
        )
        structured_output = _parse_json_from_text(text)

    if structured_output is None:
        raise GapComplianceAgentError(
            "STOP_NO_RESULT",
            "Gap agent finished without structured output",
        )
    return structured_output, resolved_model, latency_ms, input_tokens, output_tokens


async def run_gap_compliance(
    *,
    knowledge_bank_json: dict[str, Any],
    template_payload: dict[str, Any],
    report_context: dict[str, Any] | None = None,
    query_fn: QueryFn | None = None,
    model: str | None = None,
) -> GapComplianceAgentResult:
    """Run E3 gap/compliance against confirmed KB + funder template."""
    ctx = report_context or {"report_type": "annual"}
    sections = template_payload.get("report_sections_json") or []
    requirements = enumerate_template_requirements(sections, report_context=ctx)
    allowed_item_keys = {req.item_key for req in requirements}
    prompt = build_gap_compliance_prompt(
        knowledge_bank_json=knowledge_bank_json,
        template_payload=template_payload,
        requirements=requirements,
        report_context=ctx,
    )

    logger.info(
        "gap_compliance_agent start checklist=%d model=%s",
        len([r for r in requirements if r.required_item_type != "section"]),
        model or DEFAULT_MODEL,
    )

    structured_output, resolved_model, latency_ms, input_tokens, output_tokens = (
        await asyncio.wait_for(
            _run_gap_query(prompt, query_fn=query_fn, model=model),
            timeout=TIMEOUT_SECONDS,
        )
    )

    structured = _validate_llm_output(
        structured_output, allowed_item_keys=allowed_item_keys
    )
    now = datetime.now(timezone.utc)
    trace = GapComplianceAgentTrace(
        model_used=resolved_model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempt_count=1,
    )
    envelope = GapCompliancePersistedEnvelope(
        gap_agent=AGENT_NAME,
        analyzed_at=now,
        report_context=ctx,
        structured=structured,
        agent_trace=trace,
    )
    return GapComplianceAgentResult(
        envelope=envelope,
        model_used=resolved_model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def load_template_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
