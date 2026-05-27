#!/usr/bin/env python3
"""
Non-mutating live proposal extractor run.

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
    / "01_FCDO_BridgeLight_Winning_Proposal.docx"
)
CACHED_MD = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "proposal_extractor"
    / "fcdo_bridgelight_proposal.md"
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
    parser = argparse.ArgumentParser(description="Live proposal extractor run")
    parser.add_argument(
        "--docx",
        type=Path,
        default=DEFAULT_DOCX,
        help="Path to proposal .docx (Docling extraction)",
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
    from app.reports.agents.proposal_extractor import (
        extract_proposal_from_path,
        extract_proposal_text_sync,
    )

    if args.use_docling:
        if not args.docx.is_file():
            print(f"FATAL: docx not found: {args.docx}", file=sys.stderr)
            return 2
        result = asyncio.run(extract_proposal_from_path(args.docx))
        source = str(args.docx)
    else:
        if not args.cached_md.is_file():
            print(f"FATAL: cached fixture not found: {args.cached_md}", file=sys.stderr)
            return 2
        text = args.cached_md.read_text(encoding="utf-8")
        result = extract_proposal_text_sync(text, filename=args.cached_md.name)
        source = str(args.cached_md)

    structured = result.envelope.structured
    payload = {
        "status": "ok",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "extraction_outcome": structured.extraction_outcome,
        "confidence": result.envelope.confidence,
        "latency_ms": result.latency_ms,
        "model_used": result.model_used,
        "max_turns": result.envelope.agent_trace.max_turns if result.envelope.agent_trace else None,
        "summary": structured.summary.model_dump(),
        "objective_count": len(structured.objectives),
        "activity_count": len(structured.activities),
        "indicator_count": len(structured.indicators),
        "absent_target_indicators": [
            i.indicator_key
            for i in structured.indicators
            if i.target.absent
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
