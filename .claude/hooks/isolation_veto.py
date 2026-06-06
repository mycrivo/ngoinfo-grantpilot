#!/usr/bin/env python3
"""Claude Code entrypoint — delegates to shared isolation veto."""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[1] / ".cursor" / "hooks" / "isolation_veto.py"))
