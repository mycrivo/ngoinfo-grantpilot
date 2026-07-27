#!/usr/bin/env python3
"""Report-only tree-wide funder/fixture audit (never blocking)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".cursor" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from governance_guards import tree_scan  # noqa: E402


def to_markdown(report: dict) -> str:
    engine = report["engine_violations"]
    harness = report["harness_informational"]
    lines = [
        "# G1 tree-wide governance audit (report-only)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This job never blocks. Engine-path hits are the P1 decontamination worklist.",
        "Harness hits are informational only (exempt from the string guard).",
        "",
        f"## Engine-path violations ({len(engine)})",
        "",
    ]
    if not engine:
        lines.append("_None._")
    else:
        by_path: dict[str, list[dict]] = defaultdict(list)
        for hit in engine:
            by_path[hit["path"]].append(hit)
        lines.extend(
            [
                "| Path | Count | Sample detail |",
                "|------|------:|---------------|",
            ]
        )
        for path in sorted(by_path):
            hits = by_path[path]
            sample = hits[0].get("detail", "")
            lines.append(f"| `{path}` | {len(hits)} | {sample} |")
        lines.append("")
        lines.append("### Full engine hit list")
        lines.append("")
        for hit in engine:
            lines.append(
                f"- `{hit['path']}` — {hit.get('detail', '')} — `{hit.get('line', '')}`"
            )

    lines.extend(
        [
            "",
            f"## Harness informational ({len(harness)}) — not violations",
            "",
        ]
    )
    if not harness:
        lines.append("_None._")
    else:
        by_path = defaultdict(list)
        for hit in harness:
            by_path[hit["path"]].append(hit)
        lines.extend(
            [
                "| Path | Count | Sample token |",
                "|------|------:|--------------|",
            ]
        )
        for path in sorted(by_path):
            hits = by_path[path]
            lines.append(f"| `{path}` | {len(hits)} | `{hits[0].get('token', '')}` |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Write JSON report")
    parser.add_argument("--md-out", type=Path, help="Write markdown report")
    args = parser.parse_args()

    report = tree_scan(report_harness=True)
    md = to_markdown(report)
    print(md)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(md, encoding="utf-8")

    # Always exit 0 — report-only.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
