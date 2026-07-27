#!/usr/bin/env python3
"""PreToolUse: block writes to protected governance files unless override is present."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from governance_guards import run_pretool_guard  # noqa: E402


def main() -> int:
    return run_pretool_guard(which="protected_file")


if __name__ == "__main__":
    raise SystemExit(main())
