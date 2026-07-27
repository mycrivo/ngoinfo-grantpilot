#!/usr/bin/env python3
"""Claude Code entrypoint — delegates to shared secret-write guard."""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".cursor" / "hooks" / "secret_write_guard.py")
)
