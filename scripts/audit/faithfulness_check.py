#!/usr/bin/env python3
"""CLI for offline P1-1 faithfulness fixture checks (no live API walks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.reports.eval.faithfulness_check import (
    check_faithfulness_fixture,
    load_faithfulness_fixture,
)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        default = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "fixtures"
            / "synthesis"
            / "clean_faithfulness_fixture.json"
        )
        path = default
    else:
        path = Path(args[0])

    fixture = load_faithfulness_fixture(path)
    report = check_faithfulness_fixture(fixture)
    summary = report.to_summary_dict()
    print(json.dumps(summary, indent=2))
    if not report.passed:
        print("FAITHFULNESS_FAIL", flush=True)
        if report.unmatched_numbers:
            print("unmatched:", json.dumps(report.unmatched_numbers[:10], indent=2))
        if report.missing_expected_numbers:
            print(
                "missing_expected:",
                json.dumps(report.missing_expected_numbers[:10], indent=2),
            )
        if report.degraded_leaks:
            print("degraded_leaks:", report.degraded_leaks[:10])
        return 1
    print("FAITHFULNESS_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
