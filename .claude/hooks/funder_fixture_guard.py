#!/usr/bin/env python3
"""Claude Code entrypoint — delegates to shared funder/fixture guard."""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".cursor" / "hooks" / "funder_fixture_guard.py")
)
