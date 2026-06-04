"""Render donor_reports.content_json to a funder-structured .docx."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt

_REPO_ROOT = Path(__file__).resolve().parents[3]

_TABLE_ROW_RE = re.compile(r"^\|.+\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s:\-|]+\|$")
_CITATION_MARKER_RE = re.compile(r"\s*\[(?:fact|gap):[^\]]+\]\s*", re.IGNORECASE)
_ARCHETYPE_RE = re.compile(r"\bARCH_[A-Z0-9_]+\b")


def resolve_docx_template_path(docx_template_ref: str | None) -> Path | None:
    """Return a readable base .docx path, or None if ref is missing or not on disk."""
    ref = (docx_template_ref or "").strip()
    if not ref:
        return None
    direct = Path(ref)
    if direct.is_file():
        return direct
    from_repo = _REPO_ROOT / ref
    if from_repo.is_file():
        return from_repo
    return None


def _apply_basic_styles(document: Document) -> None:
    style = document.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)


def _terminology_substitutions(terminology_map: dict[str, Any]) -> list[tuple[re.Pattern[str], str]]:
    mapping = terminology_map.get("canonical_to_funder") or {}
    subs: list[tuple[re.Pattern[str], str]] = []
    for canonical, funder_label in mapping.items():
        if not canonical or not funder_label:
            continue
        pattern = re.compile(rf"\b{re.escape(str(canonical))}\b", re.IGNORECASE)
        subs.append((pattern, str(funder_label)))
    return subs


def _strip_internal_tokens(text: str) -> str:
    """Remove inline citation markers and archetype tokens from prose; preserve narrative words."""
    cleaned = _CITATION_MARKER_RE.sub(" ", text)
    cleaned = _ARCHETYPE_RE.sub("", cleaned)
    cleaned = re.sub(r" +", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    return cleaned.strip()


def _apply_terminology(text: str, subs: list[tuple[re.Pattern[str], str]]) -> str:
    out = text
    for pattern, replacement in subs:
        out = pattern.sub(replacement, out)
    return out


def _parse_markdown_table_block(lines: list[str]) -> tuple[list[str], list[list[str]]] | None:
    if len(lines) < 2:
        return None
    if not all(_TABLE_ROW_RE.match(line.strip()) for line in lines[:2]):
        return None
    if not _TABLE_SEP_RE.match(lines[1].strip()):
        return None
    header = [cell.strip() for cell in lines[0].strip().strip("|").split("|")]
    rows: list[list[str]] = []
    for line in lines[2:]:
        if not _TABLE_ROW_RE.match(line.strip()):
            break
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    if not header:
        return None
    return header, rows


def _add_word_table(document: Document, header: list[str], rows: list[list[str]]) -> None:
    col_count = max(len(header), max((len(r) for r in rows), default=0))
    if col_count == 0:
        return
    table = document.add_table(rows=1 + len(rows), cols=col_count)
    table.style = "Table Grid"
    for col_idx in range(col_count):
        table.rows[0].cells[col_idx].text = header[col_idx] if col_idx < len(header) else ""
    for row_idx, row in enumerate(rows, start=1):
        for col_idx in range(col_count):
            table.rows[row_idx].cells[col_idx].text = row[col_idx] if col_idx < len(row) else ""


def _render_section_body(
    document: Document,
    text: str,
) -> None:
    sanitized = _strip_internal_tokens(text)
    if not sanitized:
        return

    lines = sanitized.splitlines()
    buffer: list[str] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _TABLE_ROW_RE.match(line.strip()):
            table_lines = [line]
            j = idx + 1
            while j < len(lines) and _TABLE_ROW_RE.match(lines[j].strip()):
                table_lines.append(lines[j])
                j += 1
            parsed = _parse_markdown_table_block(table_lines)
            if parsed:
                for para in buffer:
                    if para.strip():
                        document.add_paragraph(para.strip())
                buffer.clear()
                header, rows = parsed
                _add_word_table(document, header, rows)
                idx = j
                continue
        buffer.append(line)
        idx += 1

    for para in buffer:
        stripped = para.strip()
        if stripped:
            document.add_paragraph(stripped)


def render_donor_report_docx(
    *,
    content_json: dict[str, Any],
    template_sections: list[Any],
    format_rules_json: dict[str, Any],
    terminology_map_json: dict[str, Any],
    docx_template_ref: str | None,
    reporting_period_start: str,
    reporting_period_end: str,
    funder_name: str,
    template_name: str,
) -> tuple[bytes, str]:
    """
    Build export bytes and report which template path was used.

    Returns (docx_bytes, render_mode) where render_mode is 'base_template' or 'from_scratch'.
    """
    base_path = resolve_docx_template_path(docx_template_ref)
    if base_path is not None:
        document = Document(str(base_path))
        render_mode = "base_template"
    else:
        document = Document()
        render_mode = "from_scratch"

    _apply_basic_styles(document)

    title = str(format_rules_json.get("document_title") or template_name or "Donor Report")
    document.add_heading(title, level=0)
    document.add_paragraph(f"Funder: {funder_name}")
    document.add_paragraph(
        f"Reporting period: {reporting_period_start} to {reporting_period_end}"
    )
    document.add_page_break()

    sections_by_key: dict[str, dict[str, Any]] = {}
    for item in content_json.get("sections") or []:
        if isinstance(item, dict) and item.get("section_key"):
            sections_by_key[str(item["section_key"])] = item

    subs = _terminology_substitutions(terminology_map_json)

    for template_section in template_sections:
        if not isinstance(template_section, dict):
            continue
        section_key = str(template_section.get("section_key") or "")
        heading = str(template_section.get("label") or section_key)
        document.add_heading(_apply_terminology(heading, subs), level=1)

        for table_def in template_section.get("required_tables") or []:
            if not isinstance(table_def, dict):
                continue
            table_label = str(table_def.get("label") or "")
            if table_label:
                document.add_heading(_apply_terminology(table_label, subs), level=2)

        section = sections_by_key.get(section_key)
        if section is None:
            document.add_paragraph("[Section not generated]")
            continue

        status = section.get("generation_status")
        content = section.get("content") or {}
        text = str(content.get("text") or "")

        if status in ("GENERATED", "AWAITING_REVIEW", "ACCEPTED") and text.strip():
            _render_section_body(document, text)
        elif status == "FAILED":
            reason = section.get("failure_reason") or "Generation failed"
            document.add_paragraph(f"[Not generated: {reason}]")
        else:
            document.add_paragraph("[Section not generated]")

        assumptions = content.get("assumptions") or []
        if assumptions:
            document.add_heading("Assumptions", level=3)
            for assumption in assumptions:
                if assumption:
                    document.add_paragraph(str(assumption), style="List Bullet")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue(), render_mode


def build_export_filename(
    *,
    funder_name: str,
    template_name: str,
    reporting_period_start: str,
    reporting_period_end: str,
) -> str:
    def _slug(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")[:40] or "report"

    return (
        f"{_slug(funder_name)}_{_slug(template_name)}_"
        f"{reporting_period_start}_{reporting_period_end}.docx"
    )
