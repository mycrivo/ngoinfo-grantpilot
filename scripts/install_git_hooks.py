#!/usr/bin/env python3
"""Install repo git hooks via core.hooksPath=.githooks (Command Prompt safe).

Usage (Command Prompt or PowerShell):
  py -3 scripts\\install_git_hooks.py
  python scripts\\install_git_hooks.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_PATH = ".githooks"


def main() -> int:
    hooks_dir = REPO_ROOT / HOOKS_PATH
    pre_commit = hooks_dir / "pre-commit"
    if not pre_commit.is_file():
        print(f"ERROR: missing {pre_commit}", file=sys.stderr)
        return 1

    try:
        subprocess.run(
            ["git", "config", "core.hooksPath", HOOKS_PATH],
            cwd=REPO_ROOT,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: failed to set core.hooksPath: {exc}", file=sys.stderr)
        print("Run from the repo root with git available.", file=sys.stderr)
        return 1

    # Best-effort executable bit for Unix checkouts; no-op failure on Windows.
    try:
        pre_commit.chmod(pre_commit.stat().st_mode | 0o111)
    except OSError:
        pass

    print(f"Installed git hooks: core.hooksPath={HOOKS_PATH}")
    print("Verify: git config --get core.hooksPath")
    print("Blocked commits print a governance denial; bypass locally with:")
    print("  git commit --no-verify")
    print("(CI governance-guards job remains non-bypassable.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
