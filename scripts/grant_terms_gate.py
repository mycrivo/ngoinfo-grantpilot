#!/usr/bin/env python3
"""
D3 live acceptance gate — run once after implementation changes.

1 correctness run (full answer key) + 3 parallel stability runs (content fingerprint).
Writes recorded fixture and wall-time artefact only on pass. No retry-until-green.

Requires ANTHROPIC_API_KEY and Claude Code CLI (`claude`) on PATH.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "grant_terms_extractor"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_award_letter_answer_key.json"
FCDO_TEXT = FIXTURES / "fcdo_bridgelight_award_letter.md"
RECORDED_DIR = FIXTURES / "recorded"
RECORDED_EXTRACTION = RECORDED_DIR / "fcdo_bridgelight_recorded_extraction.json"
WALL_TIMES = RECORDED_DIR / "gate_wall_times_ms.json"
STABILITY_RUNS = 3

sys.path.insert(0, str(REPO_ROOT))

from app.reports.agents.grant_terms_extractor import extract_grant_terms_text  # noqa: E402
from tests.grant_terms_grading import (  # noqa: E402
    grade_extraction_output,
    stability_fingerprint,
)


def _require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        print(
            "FATAL: ANTHROPIC_API_KEY is missing. Set it before running the gate.",
            file=sys.stderr,
        )
        sys.exit(2)


def _require_claude_cli() -> None:
    if shutil.which("claude") is None:
        print("FATAL: Claude Code CLI (`claude`) not found on PATH.", file=sys.stderr)
        sys.exit(2)


def _load_answer_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


async def _run_once(text: str, label: str) -> tuple[object, int]:
    started = time.perf_counter()
    result = await extract_grant_terms_text(
        text,
        filename="fcdo_bridgelight_award_letter.md",
    )
    wall_ms = int((time.perf_counter() - started) * 1000)
    print(f"{label}: outcome={result.envelope.structured.extraction_outcome} wall_ms={wall_ms}")
    return result, wall_ms


async def _gate(text: str, key: dict, *, write_artifacts: bool) -> int:
    print("=== D3 grant-terms gate: correctness run ===")
    correctness, correctness_ms = await _run_once(text, "correctness")
    try:
        grade_extraction_output(correctness.envelope.structured, key)
    except AssertionError as exc:
        print(f"FAIL correctness grading: {exc}", file=sys.stderr)
        return 1

    canonical = stability_fingerprint(correctness.envelope.structured)
    wall_times = {"correctness_ms": correctness_ms, "stability_ms": []}

    print(
        f"=== D3 grant-terms gate: {STABILITY_RUNS} stability runs "
        "(sequential; Claude CLI cannot safely parallelize sessions) ==="
    )

    for idx in range(STABILITY_RUNS):
        try:
            result, wall_ms = await _run_once(text, f"stability_{idx + 1}")
        except Exception as exc:
            print(f"FAIL stability_{idx + 1} raised: {exc}", file=sys.stderr)
            return 1
        wall_times["stability_ms"].append(wall_ms)
        outcome = result.envelope.structured.extraction_outcome
        if outcome != "complete":
            print(f"FAIL stability_{idx + 1} outcome={outcome}", file=sys.stderr)
            return 1
        fp = stability_fingerprint(result.envelope.structured)
        if fp != canonical:
            print(f"FAIL stability_{idx + 1} content drift vs correctness", file=sys.stderr)
            return 1

    all_ms = [correctness_ms, *wall_times["stability_ms"]]
    wall_times["spread"] = {
        "min_ms": min(all_ms),
        "max_ms": max(all_ms),
        "median_ms": int(statistics.median(all_ms)),
        "runs": len(all_ms),
    }
    print(f"PASS wall_time_spread={wall_times['spread']}")

    if write_artifacts:
        RECORDED_DIR.mkdir(parents=True, exist_ok=True)
        payload = correctness.envelope.model_dump(mode="json")
        RECORDED_EXTRACTION.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        WALL_TIMES.write_text(json.dumps(wall_times, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {RECORDED_EXTRACTION}")
        print(f"Wrote {WALL_TIMES}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="D3 grant-terms live gate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run gate checks but do not write recorded fixture or wall times",
    )
    args = parser.parse_args()

    _require_api_key()
    _require_claude_cli()

    if not FCDO_TEXT.is_file():
        print(f"FATAL: missing fixture {FCDO_TEXT}", file=sys.stderr)
        return 2

    text = FCDO_TEXT.read_text(encoding="utf-8")
    key = _load_answer_key()
    return asyncio.run(_gate(text, key, write_artifacts=not args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
