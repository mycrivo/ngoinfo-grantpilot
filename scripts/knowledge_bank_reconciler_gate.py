#!/usr/bin/env python3
"""
E1 live acceptance gate — 1 correctness + 3 sequential stability runs.

Pass criterion: every run passes invariant grading (`grade_knowledge_bank`).
Byte-level `stability_fingerprint` is computed and written for observability only;
fingerprint drift between runs is not a gate failure.

Writes recorded knowledge_bank_json and wall-time artefact only on pass.
Always writes per-run knowledge banks and fingerprints to recorded/_drift_debug/.
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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "reconciler"
MANIFEST = FIXTURES / "inputs" / "fcdo_bridgelight_documents.json"
ANSWER_KEY = FIXTURES / "keys" / "fcdo_bridgelight_reconciliation_answer_key.json"
RECORDED_DIR = FIXTURES / "recorded"
RECORDED_KB = RECORDED_DIR / "fcdo_bridgelight_recorded_knowledge_bank.json"
WALL_TIMES = RECORDED_DIR / "gate_wall_times_ms.json"
DRIFT_DEBUG_DIR = RECORDED_DIR / "_drift_debug"
STABILITY_RUNS = 3
STABILITY_POLICY = (
    "invariant-stable on every run (grade_knowledge_bank); "
    "byte fingerprint is observability only, not pass/fail"
)

sys.path.insert(0, str(REPO_ROOT))

from app.reports.agents.knowledge_bank_reconciler import (  # noqa: E402
    envelope_to_knowledge_bank_json,
    reconcile_from_fixture,
)
from tests.reconciliation_grading import (  # noqa: E402
    grade_knowledge_bank,
    stability_fingerprint,
)


@dataclass
class GateRunSnapshot:
    label: str
    kb: dict[str, Any]
    fingerprint: dict[str, Any]
    grade_errors: list[str] = field(default_factory=list)
    run_record: dict[str, Any] = field(default_factory=dict)


def _require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        print("FATAL: ANTHROPIC_API_KEY is missing.", file=sys.stderr)
        sys.exit(2)


def _require_claude_cli() -> None:
    if shutil.which("claude") is None:
        print("FATAL: Claude Code CLI (`claude`) not found on PATH.", file=sys.stderr)
        sys.exit(2)


def _load_key() -> dict:
    return json.loads(ANSWER_KEY.read_text(encoding="utf-8"))


def _run_record(result: object, wall_ms: int, label: str) -> dict[str, Any]:
    envelope = result.envelope  # type: ignore[attr-defined]
    trace = envelope.agent_trace
    structured = envelope.structured
    return {
        "label": label,
        "reconciliation_outcome": structured.reconciliation_outcome,
        "attempt_count": trace.attempt_count if trace else None,
        "num_turns": trace.num_turns if trace else None,
        "wall_ms": wall_ms,
        "degraded_code": trace.degraded_code if trace else None,
        "conflicts_surfaced_count": trace.conflicts_surfaced_count if trace else None,
        "facts_count": len(structured.facts),
        "unreadable_count": len(structured.unreadable_sources),
    }


def _print_run_table(runs: list[dict[str, Any]]) -> None:
    print("=== Per-run gate record ===")
    for row in runs:
        grade_status = "PASS" if row.get("grade_passed") else "FAIL"
        print(
            f"{row['label']}: outcome={row['reconciliation_outcome']} "
            f"grade={grade_status} "
            f"attempt_count={row['attempt_count']} num_turns={row['num_turns']} "
            f"wall_ms={row['wall_ms']} conflicts={row['conflicts_surfaced_count']} "
            f"facts={row['facts_count']} unreadable={row['unreadable_count']}"
        )
        if row.get("grade_errors"):
            for err in row["grade_errors"]:
                print(f"  GRADE: {err}")


def _persist_observability(
    runs: list[GateRunSnapshot],
    *,
    gate_passed: bool,
    failure_reason: str | None = None,
    failure_label: str | None = None,
) -> None:
    DRIFT_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    correctness_fp = runs[0].fingerprint if runs else None
    run_entries: list[dict[str, Any]] = []
    for snapshot in runs:
        fp_match = (
            snapshot.fingerprint == correctness_fp
            if correctness_fp is not None and snapshot.label != runs[0].label
            else None
        )
        run_entries.append(
            {
                **snapshot.run_record,
                "grade_passed": len(snapshot.grade_errors) == 0,
                "grade_errors": snapshot.grade_errors,
                "fingerprint_matches_correctness": fp_match,
            }
        )
    manifest = {
        "gate_passed": gate_passed,
        "failure_reason": failure_reason,
        "failure_label": failure_label,
        "stability_policy": STABILITY_POLICY,
        "runs": run_entries,
    }
    (DRIFT_DEBUG_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    for snapshot in runs:
        safe = snapshot.label.replace(" ", "_")
        (DRIFT_DEBUG_DIR / f"{safe}_knowledge_bank.json").write_text(
            json.dumps(snapshot.kb, indent=2), encoding="utf-8"
        )
        (DRIFT_DEBUG_DIR / f"{safe}_fingerprint.json").write_text(
            json.dumps(snapshot.fingerprint, indent=2), encoding="utf-8"
        )
    print(f"Observability artefacts written to {DRIFT_DEBUG_DIR}")


def _snapshot_from_result(
    label: str,
    result: object,
    wall_ms: int,
    key: dict,
) -> GateRunSnapshot:
    kb = envelope_to_knowledge_bank_json(result.envelope)  # type: ignore[attr-defined]
    grade_errors = (
        grade_knowledge_bank(kb, key)
        if kb.get("reconciliation_outcome") == "complete"
        else [
            f"reconciliation_outcome is {kb.get('reconciliation_outcome')!r}, "
            "expected 'complete'"
        ]
    )
    return GateRunSnapshot(
        label=label,
        kb=kb,
        fingerprint=stability_fingerprint(kb),
        grade_errors=grade_errors,
        run_record=_run_record(result, wall_ms, label),
    )


async def _run_once(label: str) -> tuple[object, int]:
    started = time.perf_counter()
    result = await reconcile_from_fixture(MANIFEST)
    wall_ms = int((time.perf_counter() - started) * 1000)
    return result, wall_ms


def _fail_gate(
    runs: list[GateRunSnapshot],
    *,
    failure_reason: str,
    failure_label: str,
) -> int:
    snapshot = next((r for r in runs if r.label == failure_label), runs[-1])
    print(f"FAIL: {failure_reason} on {failure_label}", file=sys.stderr)
    for err in snapshot.grade_errors:
        print(f"GRADE FAIL: {err}", file=sys.stderr)
    _persist_observability(
        runs,
        gate_passed=False,
        failure_reason=failure_reason,
        failure_label=failure_label,
    )
    return 1


async def _gate(key: dict, *, write_artifacts: bool) -> int:
    runs: list[GateRunSnapshot] = []

    print("=== E1 knowledge-bank reconciler gate: correctness run ===")
    correctness, wall_correct = await _run_once("correctness")
    snap = _snapshot_from_result("correctness", correctness, wall_correct, key)
    runs.append(snap)
    print(
        f"correctness: outcome={snap.kb.get('reconciliation_outcome')} "
        f"wall_ms={wall_correct} grade={'PASS' if not snap.grade_errors else 'FAIL'}"
    )
    if snap.grade_errors:
        return _fail_gate(
            runs,
            failure_reason="grading_failed",
            failure_label="correctness",
        )

    print(f"=== E1 gate: {STABILITY_RUNS} stability runs (sequential, invariant grading) ===")
    for i in range(1, STABILITY_RUNS + 1):
        label = f"stability_{i}"
        result, wall_ms = await _run_once(label)
        snap = _snapshot_from_result(label, result, wall_ms, key)
        runs.append(snap)
        print(
            f"{label}: outcome={snap.kb.get('reconciliation_outcome')} "
            f"wall_ms={wall_ms} grade={'PASS' if not snap.grade_errors else 'FAIL'}"
        )
        if snap.grade_errors:
            return _fail_gate(
                runs,
                failure_reason="grading_failed",
                failure_label=label,
            )

    correctness_fp = runs[0].fingerprint
    for snap in runs[1:]:
        if snap.fingerprint != correctness_fp:
            print(
                f"NOTE: byte fingerprint differs on {snap.label} "
                "(observability only — not a gate failure)"
            )

    table_rows = [
        {
            **r.run_record,
            "grade_passed": len(r.grade_errors) == 0,
            "grade_errors": r.grade_errors,
        }
        for r in runs
    ]
    _print_run_table(table_rows)
    walls = [r.run_record["wall_ms"] for r in runs]
    spread = {
        "min_ms": min(walls),
        "max_ms": max(walls),
        "median_ms": int(statistics.median(walls)),
    }
    print(f"Wall-time spread: {spread}")

    _persist_observability(runs, gate_passed=True)
    if write_artifacts:
        RECORDED_DIR.mkdir(parents=True, exist_ok=True)
        RECORDED_KB.write_text(json.dumps(runs[0].kb, indent=2), encoding="utf-8")
        WALL_TIMES.write_text(
            json.dumps({"runs": table_rows, "spread": spread}, indent=2),
            encoding="utf-8",
        )
        print(f"Recorded: {RECORDED_KB}")
        print(f"Recorded: {WALL_TIMES}")

    print("PASS: E1 gate complete (all runs passed invariant grading).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="E1 knowledge-bank reconciler live gate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run gate checks but do not write recorded artefacts",
    )
    args = parser.parse_args()

    _require_api_key()
    _require_claude_cli()
    key = _load_key()
    return asyncio.run(_gate(key, write_artifacts=not args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
