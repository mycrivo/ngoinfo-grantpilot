from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("openai")

_MAX_RETRIES = 1
_RETRY_BASE_DELAY_SECONDS = 0.6


@dataclass(frozen=True)
class OpenAIServiceError(Exception):
    category: str
    retryable: bool
    status_code: int | None = None
    retry_attempted: int = 0
    openai_error_code: str | None = None
    openai_rejected_param: str | None = None


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
        fallback_model: str | None = None,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any],
        temperature: float,
        top_p: float,
        frequency_penalty: float,
        presence_penalty: float,
        max_tokens: int,
        feature: str = "unknown",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        api_path = "/chat/completions"

        def _extract_openai_error_details(resp: httpx.Response) -> tuple[str | None, str | None]:
            try:
                payload = resp.json()
            except Exception:
                return (None, None)
            if not isinstance(payload, dict):
                return (None, None)
            error_obj = payload.get("error")
            if not isinstance(error_obj, dict):
                return (None, None)
            error_code = error_obj.get("code")
            rejected_param = error_obj.get("param")
            return (
                error_code if isinstance(error_code, str) else None,
                rejected_param if isinstance(rejected_param, str) else None,
            )

        def _is_token_param_unsupported(
            *, status_code: int, error_code: str | None, rejected_param: str | None, token_param: str
        ) -> bool:
            return (
                status_code == 400
                and error_code == "unsupported_parameter"
                and rejected_param == token_param
            )

        def _create_with_model(request_model: str) -> dict[str, Any]:
            token_param = "max_completion_tokens"
            payload = {
                "model": request_model,
                "messages": messages,
                "response_format": response_format,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                token_param: max_tokens,
            }

            max_attempts = _MAX_RETRIES + 1
            last_error: OpenAIServiceError | None = None

            for attempt in range(max_attempts):
                start = time.monotonic()
                try:
                    logger.info(
                        "openai_call_start feature=%s user_id=%s model=%s api_path=%s token_param=%s attempt=%s",
                        feature,
                        user_id or "unknown",
                        request_model,
                        api_path,
                        token_param,
                        attempt + 1,
                    )
                    resp = self._client.post(
                        f"{self._base_url}{api_path}",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                    )
                    openai_error_code, openai_rejected_param = _extract_openai_error_details(resp)
                    # Token-parameter compatibility fallback:
                    # If this model/API surface rejects max_completion_tokens, retry once with max_tokens.
                    if _is_token_param_unsupported(
                        status_code=resp.status_code,
                        error_code=openai_error_code,
                        rejected_param=openai_rejected_param,
                        token_param=token_param,
                    ):
                        logger.warning(
                            "openai_token_param_fallback feature=%s user_id=%s model=%s api_path=%s "
                            "from=%s to=max_tokens status=%s openai_error_code=%s rejected_param=%s",
                            feature,
                            user_id or "unknown",
                            request_model,
                            api_path,
                            token_param,
                            resp.status_code,
                            openai_error_code or "none",
                            openai_rejected_param or "none",
                        )
                        payload.pop(token_param, None)
                        token_param = "max_tokens"
                        payload[token_param] = max_tokens
                        resp = self._client.post(
                            f"{self._base_url}{api_path}",
                            headers={"Authorization": f"Bearer {self._api_key}"},
                            json=payload,
                        )
                        openai_error_code, openai_rejected_param = _extract_openai_error_details(resp)
                    if resp.status_code == 429:
                        raise OpenAIServiceError(
                            category="rate_limit",
                            retryable=True,
                            status_code=resp.status_code,
                            retry_attempted=attempt,
                            openai_error_code=openai_error_code,
                            openai_rejected_param=openai_rejected_param,
                        )
                    if resp.status_code >= 500:
                        raise OpenAIServiceError(
                            category="server_error",
                            retryable=True,
                            status_code=resp.status_code,
                            retry_attempted=attempt,
                            openai_error_code=openai_error_code,
                            openai_rejected_param=openai_rejected_param,
                        )
                    if resp.status_code >= 400:
                        raise OpenAIServiceError(
                            category="request_error",
                            retryable=False,
                            status_code=resp.status_code,
                            retry_attempted=attempt,
                            openai_error_code=openai_error_code,
                            openai_rejected_param=openai_rejected_param,
                        )
                    data = resp.json()
                    latency_ms = int((time.monotonic() - start) * 1000)
                    logger.info(
                        "openai_call_success feature=%s user_id=%s model=%s api_path=%s token_param=%s "
                        "latency_ms=%s attempts=%s",
                        feature,
                        user_id or "unknown",
                        request_model,
                        api_path,
                        token_param,
                        latency_ms,
                        attempt + 1,
                    )
                    return data
                except OpenAIServiceError as exc:
                    last_error = exc
                except httpx.TimeoutException as exc:
                    last_error = OpenAIServiceError(
                        category="timeout",
                        retryable=True,
                        retry_attempted=attempt,
                    )
                except httpx.RequestError as exc:
                    last_error = OpenAIServiceError(
                        category="connection_error",
                        retryable=True,
                        retry_attempted=attempt,
                    )

                latency_ms = int((time.monotonic() - start) * 1000)
                retryable = last_error.retryable if last_error else False
                logger.warning(
                    "openai_call_error feature=%s user_id=%s category=%s retryable=%s "
                    "model=%s api_path=%s token_param=%s status=%s openai_error_code=%s "
                    "rejected_param=%s attempt=%s latency_ms=%s",
                    feature,
                    user_id or "unknown",
                    last_error.category if last_error else "unknown",
                    retryable,
                    request_model,
                    api_path,
                    token_param,
                    str(last_error.status_code) if last_error and last_error.status_code is not None else "none",
                    last_error.openai_error_code if last_error and last_error.openai_error_code else "none",
                    last_error.openai_rejected_param if last_error and last_error.openai_rejected_param else "none",
                    attempt + 1,
                    latency_ms,
                )

                if not last_error or not retryable or attempt >= _MAX_RETRIES:
                    break

                delay = _RETRY_BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 0.2)
                time.sleep(delay)
                logger.info(
                    "openai_call_retry feature=%s user_id=%s model=%s api_path=%s attempt=%s delay_s=%.2f",
                    feature,
                    user_id or "unknown",
                    request_model,
                    api_path,
                    attempt + 2,
                    delay,
                )

            if last_error:
                raise last_error
            raise OpenAIServiceError(category="unknown_error", retryable=False)

        try:
            return _create_with_model(model)
        except OpenAIServiceError as exc:
            if (
                fallback_model
                and fallback_model != model
                and exc.category == "request_error"
                and exc.status_code == 400
            ):
                logger.warning(
                    "openai_model_fallback feature=%s user_id=%s primary_model=%s fallback_model=%s "
                    "status=%s openai_error_code=%s rejected_param=%s",
                    feature,
                    user_id or "unknown",
                    model,
                    fallback_model,
                    str(exc.status_code) if exc.status_code is not None else "none",
                    exc.openai_error_code or "none",
                    exc.openai_rejected_param or "none",
                )
                return _create_with_model(fallback_model)
            raise
