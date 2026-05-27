from __future__ import annotations

import os

from app.reports.agents.claude_sdk_env import (
    anthropic_api_key_configured,
    merge_claude_subprocess_env,
)


def test_merge_injects_api_key_when_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    env = merge_claude_subprocess_env({"API_TIMEOUT_MS": "90000"})
    assert env["ANTHROPIC_API_KEY"] == "sk-test-key"
    assert env["API_TIMEOUT_MS"] == "90000"


def test_merge_omits_key_when_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env = merge_claude_subprocess_env({"API_TIMEOUT_MS": "90000"})
    assert "ANTHROPIC_API_KEY" not in env


def test_anthropic_api_key_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert anthropic_api_key_configured()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not anthropic_api_key_configured()


def test_classifier_messages_api_auth_and_compat_options(monkeypatch):
    """D1 uses AsyncAnthropic (env key), not SDK ClaudeAgentOptions.env."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-forwarded")
    from app.reports.agents.classifier import build_agent_options

    assert anthropic_api_key_configured()
    options = build_agent_options()
    assert options.model
    assert options.output_format.get("type") == "json_schema"
    assert not hasattr(options, "env")
