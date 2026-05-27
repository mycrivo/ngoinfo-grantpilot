#!/usr/bin/env python3
"""
Non-mutating live grant-terms extractor run.

Requires ANTHROPIC_API_KEY and Claude Code CLI (`claude`) on PATH.
Never mocks or skips when the key is missing.
"""

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
DEFAULT_DOCX = (
    REPO_ROOT
    / "M_E_Module"
    / "Sample_docs"
    / "FCDO_Test_Set"
    / "02_FCDO_BridgeLight_Award_Letter.docx"
)
CACHED_MD = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "grant_terms_extractor"
    / "fcdo_bridgelight_award_letter.md"
)


def _require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
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
            "FATAL: Claude Code CLI (`claude`) not found on PATH.",
            file=sys.stderr,
        )
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live grant-terms extractor run")
    parser.add_argument(
        "--docx",
        type=Path,
        default=DEFAULT_DOCX,
        help="Path to award letter .docx (Docling extraction)",
    )
    parser.add_argument(
        "--cached-md",
        type=Path,
        default=CACHED_MD,
        help="Use cached markdown instead of Docling",
    )
    parser.add_argument(
        "--use-docling",
        action="store_true",
        help="Run Docling on --docx instead of cached markdown",
    )
    args = parser.parse_args()

    _require_api_key()
    _require_claude_cli()

    sys.path.insert(0, str(REPO_ROOT))

    async def _run() -> int:
        from app.reports.agents.grant_terms_extractor import (
            extract_grant_terms_from_path,
            extract_grant_terms_text,
        )

        if args.use_docling:
            result = await extract_grant_terms_from_path(args.docx)
        else:
            text = args.cached_md.read_text(encoding="utf-8")
            result = await extract_grant_terms_text(
                text, filename=args.cached_md.name
            )

        out = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "extractor_agent": result.envelope.extractor_agent,
            "extraction_outcome": result.envelope.structured.extraction_outcome,
            "confidence": result.envelope.confidence,
            "latency_ms": result.latency_ms,
            "model_used": result.model_used,
            "structured": result.envelope.structured.model_dump(mode="json"),
        }
        print(json.dumps(out, indent=2))
        return 0

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
