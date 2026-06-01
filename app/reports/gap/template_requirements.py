"""Derive gap-check requirements from funder template JSON (data-driven, no per-funder code)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RequiredItemType = Literal["indicator", "table", "section"]


@dataclass(frozen=True)
class TemplateRequirement:
    item_key: str
    section_key: str
    section_label: str
    required_item_type: RequiredItemType
    required_item_ref: str
    severity: str = "required"

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.section_key, self.required_item_type, self.required_item_ref)


def _item_key(section_key: str, item_type: str, item_ref: str) -> str:
    return f"{section_key}:{item_type}:{item_ref}"


def _section_visible(section: dict[str, Any], report_context: dict[str, Any]) -> bool:
    if not section.get("required", True):
        return False
    conditional = section.get("conditional_display") or {}
    if not conditional.get("enabled"):
        return True
    condition = conditional.get("condition")
    if not condition:
        return True
    report_type = str(report_context.get("report_type", "annual"))
    if condition.strip() == "report_type == 'final'":
        return report_type == "final"
    return True


def enumerate_template_requirements(
    report_sections_json: list[dict[str, Any]],
    *,
    report_context: dict[str, Any] | None = None,
) -> list[TemplateRequirement]:
    """Build the checklist E3 must evaluate (required sections, indicators, tables)."""
    ctx = report_context or {"report_type": "annual"}
    requirements: list[TemplateRequirement] = []
    for section in report_sections_json:
        if not _section_visible(section, ctx):
            continue
        section_key = section.get("section_key")
        section_label = section.get("label") or section_key
        if not section_key:
            continue
        requirements.append(
            TemplateRequirement(
                item_key=_item_key(section_key, "section", section_key),
                section_key=section_key,
                section_label=section_label,
                required_item_type="section",
                required_item_ref=section_key,
            )
        )
        for indicator_key in section.get("required_indicators") or []:
            requirements.append(
                TemplateRequirement(
                    item_key=_item_key(section_key, "indicator", indicator_key),
                    section_key=section_key,
                    section_label=section_label,
                    required_item_type="indicator",
                    required_item_ref=indicator_key,
                )
            )
        for table in section.get("required_tables") or []:
            table_key = table.get("table_key")
            if not table_key:
                continue
            min_rows = table.get("min_rows") or 0
            if min_rows < 1:
                continue
            requirements.append(
                TemplateRequirement(
                    item_key=_item_key(section_key, "table", table_key),
                    section_key=section_key,
                    section_label=section_label,
                    required_item_type="table",
                    required_item_ref=table_key,
                )
            )
    return requirements


def merge_template_requirements(
    base: list[TemplateRequirement],
    extra: list[TemplateRequirement],
) -> list[TemplateRequirement]:
    """Append derived requirements (e.g. logframe rows) without duplicating item_key."""
    seen = {req.item_key for req in base}
    merged = list(base)
    for req in extra:
        if req.item_key in seen:
            continue
        merged.append(req)
        seen.add(req.item_key)
    return merged
