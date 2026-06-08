"""Extract JSON objects from LLM text responses (fences, preamble prose, truncation)."""

from __future__ import annotations

import json
import re
from typing import Any


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    match = re.match(
        r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", stripped, re.DOTALL | re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return stripped


def _extract_balanced_object(text: str, start: int) -> str | None:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json_object_from_text(text: str) -> dict[str, Any] | None:
    """Return the first parseable JSON object found in *text*, or None."""
    stripped = _strip_markdown_fence(text)
    candidates: list[str] = [stripped]
    brace_start = stripped.find("{")
    if brace_start > 0:
        candidates.append(stripped[brace_start:])
    while brace_start != -1:
        fragment = _extract_balanced_object(stripped, brace_start)
        if fragment:
            candidates.append(fragment)
        brace_start = stripped.find("{", brace_start + 1)

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_json_object_from_text(text: str) -> dict[str, Any]:
    """Parse a JSON object from model text; raises ValueError when none found."""
    parsed = extract_json_object_from_text(text)
    if parsed is None:
        raise ValueError("response is not valid JSON")
    return parsed
