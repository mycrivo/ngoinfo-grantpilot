"""Tests for OpenAI client retry behaviour."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integrations.openai_client import OpenAIClient, OpenAIServiceError


def _minimal_completion_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true}'}}],
    }
    return resp


def test_synthesis_timeout_retries_once_then_succeeds():
    client = OpenAIClient(api_key="test-key")
    ok = _minimal_completion_response()
    with patch.object(client._client, "post", side_effect=[httpx.TimeoutException("slow"), ok]) as post:
        data = client.create_chat_completion(
            model="gpt-test",
            messages=[{"role": "user", "content": "hi"}],
            response_format={"type": "json_object"},
            temperature=0.0,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            max_tokens=100,
            feature="report_synthesis",
        )
    assert data["choices"]
    assert post.call_count == 2


def test_synthesis_timeout_retries_once_then_raises():
    client = OpenAIClient(api_key="test-key")
    with patch.object(
        client._client,
        "post",
        side_effect=[httpx.TimeoutException("slow"), httpx.TimeoutException("slow")],
    ) as post:
        with pytest.raises(OpenAIServiceError) as exc_info:
            client.create_chat_completion(
                model="gpt-test",
                messages=[{"role": "user", "content": "hi"}],
                response_format={"type": "json_object"},
                temperature=0.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=100,
                feature="report_synthesis",
            )
    assert exc_info.value.category == "timeout"
    assert post.call_count == 2


def test_non_synthesis_timeout_does_not_retry():
    client = OpenAIClient(api_key="test-key")
    with patch.object(client._client, "post", side_effect=httpx.TimeoutException("slow")) as post:
        with pytest.raises(OpenAIServiceError) as exc_info:
            client.create_chat_completion(
                model="gpt-test",
                messages=[{"role": "user", "content": "hi"}],
                response_format={"type": "json_object"},
                temperature=0.0,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                max_tokens=100,
                feature="proposal_extraction",
            )
    assert exc_info.value.category == "timeout"
    assert post.call_count == 1
