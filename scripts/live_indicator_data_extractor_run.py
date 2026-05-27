#!/usr/bin/env python3
"""Non-mutating live indicator-data extractor run."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "indicator_extractor"
    / "fcdo_bridgelight_indicator_data.xlsx"
)


def _require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        print("FATAL: ANTHROPIC_API_KEY is missing.", file=sys.stderr)
        sys.exit(2)


def _require_claude_cli() -> None:
    if shutil.which("claude") is None:
        print("FATAL: Claude Code CLI (`claude`) not found on PATH.", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live indicator-data extractor run")
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    args = parser.parse_args()

    _require_api_key()
    _require_claude_cli()
    sys.path.insert(0, str(REPO_ROOT))

    async def _run() -> int:
        from app.reports.agents.indicator_data_extractor import (
            extract_indicator_data_from_path,
        )

        result = await extract_indicator_data_from_path(args.xlsx)
        out = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "extractor_agent": result.envelope.extractor_agent,
            "extraction_outcome": result.envelope.structured.extraction_outcome,
            "row_count": len(result.envelope.structured.indicators),
            "confidence": result.envelope.confidence,
            "latency_ms": result.latency_ms,
            "model_used": result.model_used,
        }
        print(json.dumps(out, indent=2))
        return 0

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
