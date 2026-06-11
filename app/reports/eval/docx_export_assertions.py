"""Machine-check exported docx against content and template contract (P3-7 S4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from docx import Document

from app.reports.export.kb_table_renderer import (
    table_headers_for_definition,
    table_rows_for_definition,
)
from app.reports.gap.section_visibility import visible_sections_for_context
from app.reports.services.section_prose import (
    MIN_SECTION_PROSE_CHARS,
    has_non_empty_prose,
    section_meets_minimum_substance,
)


@dataclass
class DocxExportAssertionReport:
    violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violation_count": len(self.violations),
            "violations": self.violations,
        }


def _docx_table_count(docx_bytes: bytes) -> int:
    document = Document(BytesIO(docx_bytes))
    return len(document.tables)


def _docx_plaintext(docx_bytes: bytes) -> str:
    document = Document(BytesIO(docx_bytes))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


def assert_export_docx(
    *,
    docx_bytes: bytes,
    content_json: dict[str, Any],
    template_sections: list[dict[str, Any]],
    format_rules_json: dict[str, Any] | None = None,
    knowledge_bank_json: dict[str, Any] | None = None,
    gap_analysis_json: dict[str, Any] | None = None,
    report_context: dict[str, Any] | None = None,
) -> DocxExportAssertionReport:
    """Assert non-empty NGO section prose, minimum substance, and KB-backed tables."""
    violations: list[str] = []
    ctx = report_context or {"report_type": "annual"}
    visible = visible_sections_for_context(
        template_sections,
        report_context=ctx,
        include_funder_owned=False,
    )
    visible_keys = {str(s.get("section_key") or "") for s in visible}

    sections_by_key: dict[str, dict[str, Any]] = {}
    for section in content_json.get("sections") or []:
        if isinstance(section, dict) and section.get("section_key"):
            sections_by_key[str(section["section_key"])] = section

    for template_section in visible:
        key = str(template_section.get("section_key") or "")
        section = sections_by_key.get(key)
        if section is None:
            violations.append(f"missing_section:{key}")
            continue
        status = section.get("generation_status")
        if status in ("GENERATED", "AWAITING_REVIEW", "ACCEPTED"):
            if not has_non_empty_prose(section):
                violations.append(f"empty_prose:{key}")
            elif not section_meets_minimum_substance(section):
                violations.append(
                    f"insufficient_prose:{key}:min={MIN_SECTION_PROSE_CHARS}"
                )

    kb_facts = dict((knowledge_bank_json or {}).get("facts") or {})
    expected_tables = 0
    for template_section in template_sections:
        if not isinstance(template_section, dict):
            continue
        key = str(template_section.get("section_key") or "")
        if key not in visible_keys:
            continue
        for table_def in template_section.get("required_tables") or []:
            if not isinstance(table_def, dict):
                continue
            rows = table_rows_for_definition(
                table_def=table_def,
                facts=kb_facts,
                format_rules_json=format_rules_json or {},
                gap_analysis=gap_analysis_json,
            )
            if rows:
                expected_tables += 1
                header = table_headers_for_definition(table_def)
                if not header:
                    violations.append(
                        f"table_header_missing:{key}:{table_def.get('table_key')}"
                    )

    actual_tables = _docx_table_count(docx_bytes)
    if expected_tables > 0 and actual_tables < expected_tables:
        violations.append(
            f"table_count_low:expected>={expected_tables}:actual={actual_tables}"
        )

    if violations:
        return DocxExportAssertionReport(violations=violations)

    plaintext = _docx_plaintext(docx_bytes)
    for template_section in visible:
        key = str(template_section.get("section_key") or "")
        section = sections_by_key.get(key)
        if not section or not has_non_empty_prose(section):
            continue
        snippet = section.get("content", {}).get("text", "")[:60].strip()
        if snippet and snippet not in plaintext:
            violations.append(f"prose_not_in_docx:{key}")

    return DocxExportAssertionReport(violations=violations)
