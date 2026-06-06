#!/usr/bin/env python3
"""Block core files from importing app.reports (isolation veto)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from me_module_hooks import (  # noqa: E402
    EDIT_TOOLS,
    REPO_ROOT,
    check_isolation_violation,
    emit_allow,
    emit_deny,
    normalize_path,
    projected_content,
    read_hook_input,
)


def main() -> int:
    payload = read_hook_input()
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}

    if tool_name not in EDIT_TOOLS:
        emit_allow()
        return 0

    rel_path = tool_input.get("path") or tool_input.get("file_path") or ""
    if not rel_path:
        emit_allow()
        return 0

    full_path = REPO_ROOT / normalize_path(rel_path)
    content = projected_content(full_path, tool_name, tool_input)
    if content is None:
        emit_allow()
        return 0

    violation = check_isolation_violation(normalize_path(rel_path), content)
    if violation:
        emit_deny(violation, violation)
        return 2

    emit_allow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
