from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class OpenAIClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.openai.com/v1"):
        settings = get_settings()
        self._api_key = api_key or settings.OPENAI_API_KEY
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any],
        temperature: float,
        top_p: float,
        frequency_penalty: float,
        presence_penalty: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "response_format": response_format,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "max_tokens": max_tokens,
        }
        resp = self._client.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"OpenAI request failed: {resp.status_code} {resp.text}")
        return resp.json()
