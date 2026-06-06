#!/usr/bin/env python3
"""Flag migration ↔ model column-name drift for M&E tables."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from me_module_hooks import (  # noqa: E402
    EDIT_TOOLS,
    check_migration_parity,
    emit_additional_context,
    emit_allow,
    normalize_path,
    read_hook_input,
)


def main() -> int:
    payload = read_hook_input()
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}

    if tool_name not in EDIT_TOOLS:
        emit_allow()
        return 0

    rel_path = normalize_path(tool_input.get("path") or tool_input.get("file_path") or "")
    if not rel_path:
        emit_allow()
        return 0

    triggers = (
        rel_path.startswith("app/reports/models/"),
        rel_path.startswith("alembic/versions/0014_me_module"),
    )
    if not any(triggers):
        emit_allow()
        return 0

    warnings = check_migration_parity()
    if warnings:
        emit_additional_context("M&E migration parity warnings:\n- " + "\n- ".join(warnings))
    else:
        emit_allow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
