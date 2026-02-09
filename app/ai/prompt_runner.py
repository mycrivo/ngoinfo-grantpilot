from __future__ import annotations

import json
from typing import Any

import openai

from app.core.config import get_settings
from app.core.errors import DomainError

PROMPT_LIBRARY_VERSION = "1.0.1"
MODEL_NAME = "gpt-5.2"

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
    settings = get_settings()
    openai.api_key = settings.OPENAI_API_KEY
    openai.max_retries = 0
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
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
        )
    except Exception as exc:  # pragma: no cover - OpenAI SDK exceptions vary by version
        raise DomainError(
            error_code="AI_SERVICE_ERROR",
            message="AI service temporarily unavailable",
            status_code=503,
        ) from exc

    content = response.choices[0].message.content if response.choices else None
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

