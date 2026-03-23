from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.core.errors import DomainError
from app.integrations.openai_client import OpenAIClient, OpenAIServiceError

PROMPT_LIBRARY_VERSION = "1.0.1"

PROMPT_CONFIGS: dict[str, dict[str, float | int]] = {
    "GP-P01": {
        "temperature": 0.65,
        "top_p": 1.0,
        "frequency_penalty": 0.4,
        "presence_penalty": 0.0,
        "max_tokens": 2500,
    },
    "GP-P02": {
        "temperature": 0.65,
        "top_p": 1.0,
        "frequency_penalty": 0.4,
        "presence_penalty": 0.0,
        "max_tokens": 2500,
    },
    "GP-U01": {
        "temperature": 0.2,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "max_tokens": 700,
    },
    "GP-F01": {
        "temperature": 0.2,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "max_tokens": 900,
    },
    "GP-F02": {
        "temperature": 0.2,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "max_tokens": 900,
    },
}


def run_prompt(
    *,
    prompt_id: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    top_p: float,
    frequency_penalty: float,
    presence_penalty: float,
    max_tokens: int,
) -> dict[str, Any]:
    expected = PROMPT_CONFIGS.get(prompt_id)
    if not expected:
        raise DomainError(
            error_code="CONFIG_ERROR",
            message="Prompt configuration is missing",
            status_code=500,
        )
    if (
        float(expected["temperature"]) != float(temperature)
        or float(expected["top_p"]) != float(top_p)
        or float(expected["frequency_penalty"]) != float(frequency_penalty)
        or float(expected["presence_penalty"]) != float(presence_penalty)
        or int(expected["max_tokens"]) != int(max_tokens)
    ):
        raise DomainError(
            error_code="CONFIG_ERROR",
            message="Prompt parameters do not match library configuration",
            status_code=500,
        )
    settings = get_settings()
    client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.create_chat_completion(
            model=settings.OPENAI_MODEL_PRIMARY,
            fallback_model=settings.OPENAI_MODEL_FALLBACK,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            max_tokens=max_tokens,
            feature=prompt_id,
        )
    except OpenAIServiceError as exc:
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI service temporarily unavailable",
            status_code=503,
        ) from exc
    except Exception as exc:  # pragma: no cover - runtime safeguard
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI service temporarily unavailable",
            status_code=503,
        ) from exc

    content = None
    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    raw_content = message.get("content")
                    if isinstance(raw_content, str):
                        content = raw_content

    if not content:
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI response was empty",
            status_code=503,
        )
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI response was not valid JSON",
            status_code=503,
        ) from exc

    if not isinstance(parsed, dict):
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI response JSON was not an object",
            status_code=503,
        )
    return parsed

