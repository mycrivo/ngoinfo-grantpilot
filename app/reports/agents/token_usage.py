"""Token and cost resolution for Claude Agent SDK streams and Messages API usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenUsageResolution:
    input_tokens: int | None
    output_tokens: int | None
    estimated: bool
    cost_usd: float | None = None
    source: str = "none"


def extract_token_counts(usage: Any) -> tuple[int | None, int | None]:
    """Normalize Anthropic / SDK usage dicts and objects to input/output counts."""
    if usage is None:
        return None, None
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
    else:
        input_tokens = getattr(usage, "input_tokens", None) or getattr(
            usage, "prompt_tokens", None
        )
        output_tokens = getattr(usage, "output_tokens", None) or getattr(
            usage, "completion_tokens", None
        )
    return (
        int(input_tokens) if input_tokens is not None else None,
        int(output_tokens) if output_tokens is not None else None,
    )


def _sum_model_usage(model_usage: dict[str, Any]) -> tuple[int | None, int | None]:
    total_input = 0
    total_output = 0
    saw_input = False
    saw_output = False
    for entry in model_usage.values():
        if not isinstance(entry, dict):
            continue
        input_tokens, output_tokens = extract_token_counts(entry)
        if input_tokens is not None:
            total_input += input_tokens
            saw_input = True
        if output_tokens is not None:
            total_output += output_tokens
            saw_output = True
    return (
        total_input if saw_input else None,
        total_output if saw_output else None,
    )


class SdkUsageAccumulator:
    """Aggregate per-turn SDK usage; prefer sub-turn totals over ResultMessage.usage."""

    def __init__(self) -> None:
        self.sub_turn_count = 0
        self._sub_turn_input = 0
        self._sub_turn_output = 0
        self._result_message: Any | None = None

    def absorb_message(self, message: Any) -> None:
        assistant_cls = _assistant_message_type()
        result_cls = _result_message_type()
        if assistant_cls is not None and isinstance(message, assistant_cls):
            input_tokens, output_tokens = extract_token_counts(getattr(message, "usage", None))
            if input_tokens is None and output_tokens is None:
                return
            if input_tokens is not None:
                self._sub_turn_input += input_tokens
            if output_tokens is not None:
                self._sub_turn_output += output_tokens
            self.sub_turn_count += 1
            return
        if result_cls is not None and isinstance(message, result_cls):
            self._result_message = message

    def resolve(self) -> TokenUsageResolution:
        result = self._result_message
        cost_usd = _result_cost_usd(result)

        if self.sub_turn_count > 0:
            return TokenUsageResolution(
                input_tokens=self._sub_turn_input,
                output_tokens=self._sub_turn_output,
                estimated=False,
                cost_usd=cost_usd,
                source="sub_turn_aggregate",
            )

        if result is not None:
            model_usage = getattr(result, "model_usage", None)
            if isinstance(model_usage, dict) and model_usage:
                input_tokens, output_tokens = _sum_model_usage(model_usage)
                if input_tokens is not None or output_tokens is not None:
                    return TokenUsageResolution(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        estimated=False,
                        cost_usd=cost_usd,
                        source="model_usage",
                    )

            input_tokens, output_tokens = extract_token_counts(getattr(result, "usage", None))
            if input_tokens is not None or output_tokens is not None:
                num_turns = int(getattr(result, "num_turns", 1) or 1)
                return TokenUsageResolution(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated=num_turns > 1,
                    cost_usd=cost_usd,
                    source="result_usage",
                )

        return TokenUsageResolution(
            input_tokens=None,
            output_tokens=None,
            estimated=True,
            cost_usd=cost_usd,
            source="none",
        )


def messages_api_usage_resolution(usage: Any) -> TokenUsageResolution:
    """Messages API response.usage is authoritative for a single call."""
    input_tokens, output_tokens = extract_token_counts(usage)
    return TokenUsageResolution(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated=False,
        source="messages_api",
    )


def _result_cost_usd(result: Any | None) -> float | None:
    if result is None:
        return None
    total_cost = getattr(result, "total_cost_usd", None)
    if total_cost is None:
        return None
    try:
        return float(total_cost)
    except (TypeError, ValueError):
        return None


def _assistant_message_type() -> type | None:
    try:
        from claude_agent_sdk import AssistantMessage

        return AssistantMessage
    except ImportError:
        return None


def _result_message_type() -> type | None:
    try:
        from claude_agent_sdk import ResultMessage

        return ResultMessage
    except ImportError:
        return None
