"""Cause-agnostic parse ladder for F1 synthesis responses (A-JSON resilience).

A malformed synthesis JSON must never freeze the report. This module turns the raw
OpenAI response into either a COMPLETE parsed object or an honest, diagnosable parse
failure — it never salvages a truncated fragment into a "complete-looking" section.

Two moat rules are enforced here:

1. Recovery means *provably complete*, not merely parseable. Step 1 is strict
   ``json.loads`` (which only succeeds on a fully-closed document). Step 2 reuses the
   balanced-object extractor via :func:`extract_complete_json_object`, which accepts
   only the outermost object that closes cleanly — a truncated-mid-string payload has
   no matching close and falls through to failure.

2. Raw payload is trace-only. :class:`SynthesisParseAttempt` carries a bounded
   head/tail snippet + ``finish_reason`` for the internal job trace ONLY. Callers must
   never place these fields on the section object or any NGO-facing surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from app.reports.parsing.json_from_text import extract_complete_json_object
from app.reports.reconciliation.degrade_resilience import bounded_response_snippet

SYNTHESIS_PARSE_FAILURE_REASON = "SYNTHESIS_JSON_PARSE_FAILURE"

_STRATEGY_STRICT = "json.loads"
_STRATEGY_BALANCED = "balanced_object"
_STRATEGY_NONE = "none"


@dataclass(frozen=True)
class SynthesisParseAttempt:
    """Outcome of one parse attempt over one raw synthesis response.

    ``response_head`` / ``response_tail`` / ``finish_reason`` are diagnostic-only and
    must be routed to the internal agent trace, never onto the section or export.
    """

    ok: bool
    payload: dict[str, Any] | None
    parse_strategy: str
    finish_reason: str | None
    response_length: int | None
    response_head: str | None
    response_tail: str | None
    parse_error: str | None

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "parse_strategy": self.parse_strategy,
            "finish_reason": self.finish_reason,
            "response_length": self.response_length,
            "response_head": self.response_head,
            "response_tail": self.response_tail,
            "parse_error": self.parse_error,
        }


def _content_and_finish_reason(response: dict[str, Any]) -> tuple[str | None, str | None]:
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return None, None
    choice0 = choices[0]
    finish_reason = choice0.get("finish_reason")
    message = choice0.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    return (
        content if isinstance(content, str) else None,
        finish_reason if isinstance(finish_reason, str) else None,
    )


def parse_synthesis_response(response: dict[str, Any]) -> SynthesisParseAttempt:
    """Run the parse ladder over one raw OpenAI response.

    Ladder: strict ``json.loads`` (guarantees completeness) -> completeness-preserving
    balanced-object recovery. Anything that cannot be confirmed complete is a failure.
    """
    content, finish_reason = _content_and_finish_reason(response)
    if not content:
        return SynthesisParseAttempt(
            ok=False,
            payload=None,
            parse_strategy=_STRATEGY_NONE,
            finish_reason=finish_reason,
            response_length=0,
            response_head=None,
            response_tail=None,
            parse_error="empty_or_missing_content",
        )

    head, tail, length = bounded_response_snippet(content)

    # Step 1 — strict parse. json.loads only succeeds on a fully-closed document, so a
    # success here is inherently complete.
    parse_error: str | None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
    else:
        if isinstance(parsed, dict):
            return SynthesisParseAttempt(
                ok=True,
                payload=parsed,
                parse_strategy=_STRATEGY_STRICT,
                finish_reason=finish_reason,
                response_length=length,
                response_head=head,
                response_tail=tail,
                parse_error=None,
            )
        parse_error = "top-level JSON is not an object"

    # Step 2 — completeness-preserving recovery (fences / preamble prose only). Returns
    # None for a truncated response, so a silently-truncated section can never bind.
    recovered = extract_complete_json_object(content)
    if recovered is not None and _looks_structurally_complete(recovered):
        return SynthesisParseAttempt(
            ok=True,
            payload=recovered,
            parse_strategy=_STRATEGY_BALANCED,
            finish_reason=finish_reason,
            response_length=length,
            response_head=head,
            response_tail=tail,
            parse_error=None,
        )

    return SynthesisParseAttempt(
        ok=False,
        payload=None,
        parse_strategy=_STRATEGY_NONE,
        finish_reason=finish_reason,
        response_length=length,
        response_head=head,
        response_tail=tail,
        parse_error=parse_error,
    )


def _looks_structurally_complete(payload: dict[str, Any]) -> bool:
    """Defence-in-depth: a recovered object must carry a top-level synthesis key.

    The outer-object-only rule already blocks inner fragments; this additionally rejects
    a balanced object that lacks the synthesis envelope (``generation_status`` /
    ``generated_content``), which a well-formed synthesis response always has.
    """
    return "generation_status" in payload or "generated_content" in payload
