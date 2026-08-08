#!/usr/bin/env python3
"""Owner-triggered: emit a human-readable scorecard from a local bundle file.

Does not read production. Does not judge or compare to expected figures.
The real-report scorecard run is the owner's — builder does not produce it.

Usage:
  python scripts/audit/scorecard_emit.py --bundle /tmp/bundle.json --out /tmp/scorecard.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Local bundle JSON from bundle_export_run")
    parser.add_argument("--out", type=Path, default=None, help="Write markdown here (default: stdout)")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional structured JSON companion")
    args = parser.parse_args()

    sys.path.insert(0, str(REPO))
    from app.reports.eval.bundle_schema import ScoreableBundle
    from app.reports.eval.scorecard import emit_scorecard, scorecard_to_dict

    raw = json.loads(args.bundle.read_text(encoding="utf-8"))
    bundle_raw = raw.get("bundle") if isinstance(raw, dict) and "bundle" in raw else raw
    bundle = ScoreableBundle.from_dict(bundle_raw)
    md = emit_scorecard(bundle)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(md)
    if args.json_out:
        payload = scorecard_to_dict(bundle)
        args.json_out.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {args.json_out}")


if __name__ == "__main__":
    main()
