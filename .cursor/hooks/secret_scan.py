#!/usr/bin/env python3
"""Secret scan before git commit and on risky writes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from me_module_hooks import (  # noqa: E402
    EDIT_TOOLS,
    emit_allow,
    emit_deny,
    normalize_path,
    projected_content,
    read_hook_input,
    read_text,
    scan_staged_files_for_secrets,
    scan_text_for_secrets,
    REPO_ROOT,
)


def main() -> int:
    payload = read_hook_input()
    hook_event = payload.get("hook_event_name") or ""

    # Cursor beforeShellExecution
    command = payload.get("command") or ""
    if command and "git" in command and "commit" in command:
        hits = scan_staged_files_for_secrets()
        if hits:
            message = "Secret scan blocked git commit:\n- " + "\n- ".join(hits)
            emit_deny(message, message)
            return 2
        emit_allow()
        return 0

    # Claude Code PreToolUse Bash
    tool_name = payload.get("tool_name") or payload.get("tool") or ""
    tool_input = payload.get("tool_input") or payload.get("arguments") or {}
    if tool_name in {"Bash", "Shell"}:
        bash_cmd = tool_input.get("command") or tool_input.get("cmd") or ""
        if "git" in bash_cmd and "commit" in bash_cmd:
            hits = scan_staged_files_for_secrets()
            if hits:
                message = "Secret scan blocked git commit:\n- " + "\n- ".join(hits)
                emit_deny(message, message)
                return 2
        emit_allow()
        return 0

    # Scan .env and credential-like files on edit
    if tool_name in EDIT_TOOLS:
        rel_path = normalize_path(tool_input.get("path") or tool_input.get("file_path") or "")
        if rel_path and any(
            part in rel_path.lower()
            for part in (".env", "credentials", "secrets", "id_rsa", "id_ed25519")
        ):
            full_path = REPO_ROOT / rel_path
            content = projected_content(full_path, tool_name, tool_input) or read_text(full_path)
            hits = scan_text_for_secrets(content, rel_path)
            if hits:
                message = "Secret scan blocked edit:\n- " + "\n- ".join(hits)
                emit_deny(message, message)
                return 2

    emit_allow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
