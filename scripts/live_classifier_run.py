#!/usr/bin/env python3
"""
Non-mutating live classifier run against the four core text fixtures.

Requires ANTHROPIC_API_KEY and Claude Code CLI (`claude`) on PATH.
Never mocks or skips when the key is missing — exits non-zero immediately.
Does not write to DB, S3, or agent_trace_json. Re-runnable.

Usage:
    python scripts/live_classifier_run.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "classifier"
CORE_FIXTURES = (
    "sample_proposal.txt",
    "sample_grant_letter.txt",
    "sample_indicator_data.txt",
    "sample_mou.txt",
)


def _require_api_key() -> None:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        print(
            "FATAL: ANTHROPIC_API_KEY is missing or empty. "
            "Set it in the environment before running this script. "
            "This script never falls back to mocks.",
            file=sys.stderr,
        )
        sys.exit(2)


def _require_claude_cli() -> None:
    if shutil.which("claude") is None:
        print(
            "FATAL: Claude Code CLI (`claude`) not found on PATH. "
            "Install @anthropic-ai/claude-code and ensure `claude` is available.",
            file=sys.stderr,
        )
        sys.exit(2)


def _run_fixture(path: Path) -> dict:
    sys.path.insert(0, str(REPO_ROOT))
    from app.reports.agents.classifier import classify_document_text_sync

    text = path.read_text(encoding="utf-8")
    started = time.perf_counter()
    result = classify_document_text_sync(text, filename=path.name)
    wall_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "fixture": path.name,
        "classification": result.classification,
        "confidence": result.confidence,
        "latency_ms": result.latency_ms if result.latency_ms is not None else wall_ms,
    }


def main() -> int:
    _require_api_key()
    _require_claude_cli()

    runs: list[dict] = []
    for name in CORE_FIXTURES:
        path = FIXTURES / name
        if not path.is_file():
            print(f"FATAL: fixture not found: {path}", file=sys.stderr)
            return 2
        try:
            runs.append(_run_fixture(path))
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "fixture": name,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                ),
                file=sys.stderr,
            )
            return 1

    payload = {
        "status": "ok",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "fixture_count": len(runs),
        "runs": runs,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
