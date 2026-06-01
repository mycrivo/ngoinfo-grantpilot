"""F1 synthesis output hygiene — evidence_used binding and prose sanitization."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SanitizedSectionContent:
    text: str
    evidence_used: list[str]
    dropped_citations: list[str]


def normalize_identifier(key: str) -> str:
    """NFKC plus map Unicode decimal digits to ASCII for identifier matching."""
    normalized = unicodedata.normalize("NFKC", key)
    out: list[str] = []
    for ch in normalized:
        if ch.isdigit():
            try:
                out.append(str(unicodedata.digit(ch)))
            except ValueError:
                out.append(ch)
        else:
            out.append(ch)
    return "".join(out)


def _canonical_lookup(keys: dict[str, Any]) -> dict[str, str]:
    """Map normalized identifier -> canonical key (first canonical wins on collision)."""
    lookup: dict[str, str] = {}
    for canonical in keys:
        lookup[canonical] = canonical
        norm = normalize_identifier(canonical)
        lookup.setdefault(norm, canonical)
    return lookup


def sanitize_prose(text: str) -> str:
    """Remove control and non-printable characters; keep tab and newlines."""
    if not text:
        return text
    return "".join(
        ch
        for ch in text
        if ch in "\n\r\t" or (ord(ch) >= 32 and ord(ch) != 127)
    )


def _resolve_citation(
    *,
    prefix: str,
    raw_key: str,
    lookup: dict[str, str],
) -> str | None:
    if raw_key in lookup:
        return f"{prefix}{lookup[raw_key]}"
    normalized = normalize_identifier(raw_key)
    canonical = lookup.get(normalized)
    if canonical is None:
        return None
    return f"{prefix}{canonical}"


def sanitize_evidence_used(
    evidence_used: list[Any],
    *,
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """Bind fact:/gap: citations to KB allowlists; return (kept, dropped)."""
    fact_lookup = _canonical_lookup(kb_fact_keys)
    gap_lookup = _canonical_lookup(kb_gap_answer_keys or {})

    kept: list[str] = []
    dropped: list[str] = []
    seen: set[str] = set()

    for ref in evidence_used:
        if not isinstance(ref, str) or not ref.strip():
            dropped.append(str(ref))
            continue

        if ref.startswith("fact:"):
            resolved = _resolve_citation(
                prefix="fact:",
                raw_key=ref.removeprefix("fact:"),
                lookup=fact_lookup,
            )
        elif ref.startswith("gap:"):
            resolved = _resolve_citation(
                prefix="gap:",
                raw_key=ref.removeprefix("gap:"),
                lookup=gap_lookup,
            )
        else:
            dropped.append(ref)
            continue

        if resolved is None:
            dropped.append(ref)
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        kept.append(resolved)

    return kept, dropped


def sanitize_generated_content(
    *,
    text: str,
    evidence_used: list[Any],
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
) -> SanitizedSectionContent:
    """Sanitize F1 model output before persisting to content_json."""
    cleaned_text = sanitize_prose(text)
    cleaned_evidence, dropped = sanitize_evidence_used(
        evidence_used,
        kb_fact_keys=kb_fact_keys,
        kb_gap_answer_keys=kb_gap_answer_keys,
    )
    return SanitizedSectionContent(
        text=cleaned_text,
        evidence_used=cleaned_evidence,
        dropped_citations=dropped,
    )
