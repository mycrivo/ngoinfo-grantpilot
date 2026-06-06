#!/usr/bin/env python3
"""Gap retry loop for post-F1 walk report 39059799 (throwaway)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORT_ID = "39059799-e109-47f6-a218-979d8513f687"
JOB_ID = "f94a2cfd-b1c2-483e-8217-4448eb3196b5"
MAX_ATTEMPTS = 20
LOG = REPO / "FCDO_PLANTED_CONFLICT_POST_F1_WALK_39059799_gap_loop.log"


def main() -> int:
    env = {**os.environ, "REPORT_ID": REPORT_ID, "JOB_ID": JOB_ID}
    resume = REPO / "scripts" / "fcdo_planted_conflict_post_f1_resume.py"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        header = f"\n=== GAP ATTEMPT {attempt} ===\n"
        print(header, end="", flush=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(header)
        p = subprocess.run(
            [sys.executable, str(resume)],
            env=env,
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(p.stdout)
            if p.stderr:
                fh.write(p.stderr)
        print(p.stdout, end="", flush=True)
        if p.stderr:
            print(p.stderr, end="", file=sys.stderr)
        if p.returncode == 0:
            print("WALK COMPLETE", flush=True)
            return 0
        if p.returncode != 2:
            print(f"STOP non-gap failure exit={p.returncode}", flush=True)
            return p.returncode
    print(f"STOP: gap failed {MAX_ATTEMPTS} times", flush=True)
    return 2


if __name__ == "__main__":
    sys.exit(main())
