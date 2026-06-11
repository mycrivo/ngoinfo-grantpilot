"""Shared template section visibility (synthesis + gap checklist)."""

from __future__ import annotations

from typing import Any


def section_visible(section: dict[str, Any], report_context: dict[str, Any]) -> bool:
    """Whether a section is in scope for the current report context."""
    conditional = section.get("conditional_display") or {}
    if conditional.get("enabled"):
        condition = conditional.get("condition")
        if condition:
            report_type = str(report_context.get("report_type", "annual"))
            if condition.strip() == "report_type == 'final'":
                return report_type == "final"
        return True
    return bool(section.get("required", True))


def visible_sections_for_context(
    report_sections_json: list[dict[str, Any]],
    *,
    report_context: dict[str, Any] | None = None,
    include_funder_owned: bool = True,
) -> list[dict[str, Any]]:
    """Ordered visible sections; optionally exclude funder-owned sections for NGO synthesis."""
    ctx = report_context or {"report_type": "annual"}
    visible: list[dict[str, Any]] = []
    for section in report_sections_json or []:
        if not isinstance(section, dict) or not section.get("section_key"):
            continue
        if not section_visible(section, ctx):
            continue
        if not include_funder_owned and section.get("owner") == "funder":
            continue
        visible.append(section)
    return visible
