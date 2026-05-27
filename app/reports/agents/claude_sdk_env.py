"""Headless auth env for Claude Agent SDK subprocess (Claude Code CLI).

The SDK shells out to the ``claude`` CLI. Subprocess env is merged from
``os.environ`` plus ``ClaudeAgentOptions.env``. Gates and Railway workers must
pass ``ANTHROPIC_API_KEY`` explicitly in ``options.env`` so the CLI uses the
env-key door, not an interactive ``claude /login`` session (apiKeySource must
not be ``none`` when the key is configured).
"""

from __future__ import annotations

import os


def merge_claude_subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build ``ClaudeAgentOptions.env`` with explicit API key for headless runs."""
    env = dict(extra or {})
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    return env


def anthropic_api_key_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
