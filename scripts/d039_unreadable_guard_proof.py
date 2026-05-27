#!/usr/bin/env python3
"""
D-039 live proof — image-only PDF must yield unreadable outcome without LLM call.

Requires Docling installed. First DocumentConverter() init may take ~90–150s.
Does not write recorded fixtures.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "docling_intake"
    / "image_only_no_text_layer.pdf"
)

sys.path.insert(0, str(REPO_ROOT))

from app.reports.extraction.docling_content_guard import (  # noqa: E402
    UNREADABLE_DOCUMENT_LOW_CONTENT,
)
from app.reports.agents.grant_terms_extractor import (  # noqa: E402
    extract_grant_terms_from_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="D-039 unreadable guard live proof")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_PDF,
        help="Image-only PDF fixture path",
    )
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(
            f"FATAL: fixture missing: {args.pdf}\n"
            "Run: python scripts/build_image_only_pdf_fixture.py",
            file=sys.stderr,
        )
        return 2

    print(f"=== D-039 proof: grant_terms_from_path on {args.pdf.name} ===")
    print("(Docling cold start may take 90–150s on first run)")

    result = asyncio.run(extract_grant_terms_from_path(args.pdf))
    structured = result.envelope.structured
    trace = result.envelope.agent_trace

    print(f"extraction_outcome={structured.extraction_outcome}")
    print(f"error={result.envelope.error}")
    print(f"unreadable_code={trace.unreadable_code if trace else None}")
    print(f"input_tokens={result.input_tokens}")
    print(f"output_tokens={result.output_tokens}")

    if structured.extraction_outcome != "unreadable":
        print("FAIL: expected extraction_outcome=unreadable", file=sys.stderr)
        return 1
    if result.envelope.error != UNREADABLE_DOCUMENT_LOW_CONTENT:
        print("FAIL: expected UNREADABLE_DOCUMENT_LOW_CONTENT error", file=sys.stderr)
        return 1
    if trace is None or trace.unreadable_code != UNREADABLE_DOCUMENT_LOW_CONTENT:
        print("FAIL: expected unreadable_code on agent_trace", file=sys.stderr)
        return 1
    if result.input_tokens is not None or result.output_tokens is not None:
        print("FAIL: LLM appears to have run (tokens set)", file=sys.stderr)
        return 1

    print("PASS: unreadable guard fired; no fabricated complete extraction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
