#!/usr/bin/env python3
"""
D4 live acceptance gate — 1 correctness + 3 sequential stability runs.

Writes recorded fixture and wall-time artefact only on pass. No retry-until-green.
On fingerprint drift failure, persists compared payloads under recorded/_drift_debug/
(diagnosis only — does not overwrite the recorded fixture).
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
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "indicator_extractor"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_indicator_data_answer_key.json"
XLSX = FIXTURES / "fcdo_bridgelight_indicator_data.xlsx"
RECORDED_DIR = FIXTURES / "recorded"
RECORDED_EXTRACTION = RECORDED_DIR / "fcdo_bridgelight_recorded_extraction.json"
WALL_TIMES = RECORDED_DIR / "gate_wall_times_ms.json"
DRIFT_DEBUG_DIR = RECORDED_DIR / "_drift_debug"
STABILITY_RUNS = 3

sys.path.insert(0, str(REPO_ROOT))

from app.reports.agents.indicator_data_extractor import (  # noqa: E402
    extract_indicator_data_from_path,
)
from app.reports.schemas.indicator_data_extraction_v1 import (  # noqa: E402
    IndicatorDataExtractionOutput,
)
from tests.indicator_data_grading import (  # noqa: E402
    grade_extraction_output,
    stability_fingerprint,
)


def _require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        print("FATAL: ANTHROPIC_API_KEY is missing.", file=sys.stderr)
        sys.exit(2)


def _require_claude_cli() -> None:
    if shutil.which("claude") is None:
        print("FATAL: Claude Code CLI (`claude`) not found on PATH.", file=sys.stderr)
        sys.exit(2)


def _load_answer_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _run_record(result: object, wall_ms: int, label: str) -> dict[str, Any]:
    envelope = result.envelope  # type: ignore[attr-defined]
    trace = envelope.agent_trace
    return {
        "label": label,
        "extraction_outcome": envelope.structured.extraction_outcome,
        "attempt_count": trace.attempt_count if trace else None,
        "num_turns": trace.num_turns if trace else None,
        "wall_ms": wall_ms,
        "degraded_code": trace.degraded_code if trace else None,
        "rows": len(envelope.structured.indicators),
    }


def _print_run_table(runs: list[dict[str, Any]]) -> None:
    print("=== Per-run gate record ===")
    for row in runs:
        print(
            f"{row['label']}: outcome={row['extraction_outcome']} "
            f"attempt_count={row['attempt_count']} num_turns={row['num_turns']} "
            f"wall_ms={row['wall_ms']} degraded_code={row['degraded_code']}"
        )


async def _run_once(label: str) -> tuple[object, int]:
    started = time.perf_counter()
    result = await extract_indicator_data_from_path(XLSX)
    wall_ms = int((time.perf_counter() - started) * 1000)
    return result, wall_ms


def _persist_drift_debug(
    *,
    reason: str,
    correctness_result: object,
    stability_results: list[tuple[str, object]],
    run_records: list[dict[str, Any]],
    canonical_fingerprint: str | None = None,
    failing_fingerprint: str | None = None,
    committed_fingerprint: str | None = None,
) -> None:
    """Save compared structured outputs on fingerprint drift — not the recorded fixture."""
    DRIFT_DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    correctness_envelope = correctness_result.envelope  # type: ignore[attr-defined]
    (DRIFT_DEBUG_DIR / "correctness_envelope.json").write_text(
        json.dumps(correctness_envelope.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    (DRIFT_DEBUG_DIR / "correctness_structured.json").write_text(
        json.dumps(correctness_envelope.structured.model_dump(mode="json"), indent=2)
        + "\n",
        encoding="utf-8",
    )
    (DRIFT_DEBUG_DIR / "correctness_fingerprint.json").write_text(
        json.dumps(json.loads(canonical_fingerprint or "{}"), indent=2) + "\n"
        if canonical_fingerprint
        else "{}\n",
        encoding="utf-8",
    )

    for label, result in stability_results:
        envelope = result.envelope  # type: ignore[attr-defined]
        (DRIFT_DEBUG_DIR / f"{label}_envelope.json").write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        (DRIFT_DEBUG_DIR / f"{label}_structured.json").write_text(
            json.dumps(envelope.structured.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )

    if RECORDED_EXTRACTION.is_file():
        committed = json.loads(RECORDED_EXTRACTION.read_text(encoding="utf-8"))
        (DRIFT_DEBUG_DIR / "committed_recorded_envelope.json").write_text(
            json.dumps(committed, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest: dict[str, Any] = {
        "reason": reason,
        "canonical_fingerprint": json.loads(canonical_fingerprint)
        if canonical_fingerprint
        else None,
        "failing_fingerprint": json.loads(failing_fingerprint)
        if failing_fingerprint
        else None,
        "committed_fingerprint": json.loads(committed_fingerprint)
        if committed_fingerprint
        else None,
        "run_records": run_records,
        "artefacts": {
            "correctness_envelope": "correctness_envelope.json",
            "correctness_structured": "correctness_structured.json",
            "stability_runs": [label for label, _ in stability_results],
        },
    }
    (DRIFT_DEBUG_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote drift debug artefacts to {DRIFT_DEBUG_DIR} (reason={reason})")


async def _gate(key: dict, *, write_artifacts: bool) -> int:
    prior_content_fp: str | None = None
    if RECORDED_EXTRACTION.is_file():
        prior_payload = json.loads(RECORDED_EXTRACTION.read_text(encoding="utf-8"))
        prior_structured = IndicatorDataExtractionOutput.model_validate(
            prior_payload["structured"]
        )
        prior_content_fp = stability_fingerprint(prior_structured)

    run_records: list[dict[str, Any]] = []
    stability_results: list[tuple[str, object]] = []

    print("=== D4 indicator-data gate: correctness run ===")
    correctness, correctness_ms = await _run_once("correctness")
    run_records.append(_run_record(correctness, correctness_ms, "correctness"))
    try:
        grade_extraction_output(correctness.envelope.structured, key)
    except AssertionError as exc:
        print(f"FAIL correctness grading: {exc!r}", file=sys.stderr)
        _print_run_table(run_records)
        return 1

    canonical = stability_fingerprint(correctness.envelope.structured)
    new_content_fp = canonical
    content_fp_drift = (
        prior_content_fp is not None and prior_content_fp != new_content_fp
    )
    if content_fp_drift:
        print(
            "FAIL recorded fixture content fingerprint drift vs committed fixture",
            file=sys.stderr,
        )

    print(
        f"=== D4 indicator-data gate: {STABILITY_RUNS} stability runs "
        "(sequential; Claude CLI cannot safely parallelize sessions) ==="
    )
    for idx in range(STABILITY_RUNS):
        label = f"stability_{idx + 1}"
        try:
            result, wall_ms = await _run_once(label)
        except Exception as exc:
            print(f"FAIL {label} raised: {exc}", file=sys.stderr)
            _print_run_table(run_records)
            return 1
        run_records.append(_run_record(result, wall_ms, label))
        stability_results.append((label, result))
        outcome = result.envelope.structured.extraction_outcome
        if outcome != "complete":
            print(f"FAIL {label} outcome={outcome}", file=sys.stderr)
            _print_run_table(run_records)
            return 1
        fp = stability_fingerprint(result.envelope.structured)
        if fp != canonical:
            print(f"FAIL {label} content drift vs correctness", file=sys.stderr)
            _persist_drift_debug(
                reason=f"{label}_content_drift_vs_correctness",
                correctness_result=correctness,
                stability_results=stability_results,
                run_records=run_records,
                canonical_fingerprint=canonical,
                failing_fingerprint=fp,
                committed_fingerprint=prior_content_fp,
            )
            _print_run_table(run_records)
            return 1

    all_ms = [r["wall_ms"] for r in run_records]
    wall_times = {
        "runs": run_records,
        "correctness_ms": correctness_ms,
        "stability_ms": [r["wall_ms"] for r in run_records if r["label"].startswith("stability")],
        "spread": {
            "min_ms": min(all_ms),
            "max_ms": max(all_ms),
            "median_ms": int(statistics.median(all_ms)),
            "runs": len(all_ms),
        },
    }
    print(f"PASS wall_time_spread={wall_times['spread']}")
    _print_run_table(run_records)

    if write_artifacts:
        RECORDED_DIR.mkdir(parents=True, exist_ok=True)
        WALL_TIMES.write_text(json.dumps(wall_times, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {WALL_TIMES}")
        if content_fp_drift:
            print(
                "SKIP recorded extraction write — content fingerprint drift",
                file=sys.stderr,
            )
            _persist_drift_debug(
                reason="correctness_content_drift_vs_committed_recorded_fixture",
                correctness_result=correctness,
                stability_results=stability_results,
                run_records=run_records,
                canonical_fingerprint=canonical,
                failing_fingerprint=new_content_fp,
                committed_fingerprint=prior_content_fp,
            )
            _print_run_table(run_records)
            return 1
        payload = correctness.envelope.model_dump(mode="json")
        RECORDED_EXTRACTION.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {RECORDED_EXTRACTION}")

    if content_fp_drift:
        _persist_drift_debug(
            reason="correctness_content_drift_vs_committed_recorded_fixture",
            correctness_result=correctness,
            stability_results=stability_results,
            run_records=run_records,
            canonical_fingerprint=canonical,
            failing_fingerprint=new_content_fp,
            committed_fingerprint=prior_content_fp,
        )
        _print_run_table(run_records)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="D4 indicator-data live gate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    _require_api_key()
    _require_claude_cli()
    if not XLSX.is_file():
        print(f"FATAL: missing fixture {XLSX}", file=sys.stderr)
        return 2

    key = _load_answer_key()
    return asyncio.run(_gate(key, write_artifacts=not args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
