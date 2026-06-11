"""Citation precision/recall — content-keyed only (no tokens, costs, or timestamps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CitationPRReport:
    expected_refs: set[str] = field(default_factory=set)
    rendered_refs: set[str] = field(default_factory=set)
    missing_refs: set[str] = field(default_factory=set)
    extra_refs: set[str] = field(default_factory=set)

    @property
    def precision(self) -> float:
        if not self.rendered_refs:
            return 1.0
        return len(self.rendered_refs - self.extra_refs) / len(self.rendered_refs)

    @property
    def recall(self) -> float:
        if not self.expected_refs:
            return 1.0
        return len(self.expected_refs - self.missing_refs) / len(self.expected_refs)

    @property
    def passed(self) -> bool:
        return not self.missing_refs and not self.extra_refs

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "citation.expected_count": len(self.expected_refs),
            "citation.rendered_count": len(self.rendered_refs),
            "citation.missing_count": len(self.missing_refs),
            "citation.extra_count": len(self.extra_refs),
            "citation.precision": round(self.precision, 4),
            "citation.recall": round(self.recall, 4),
            "citation.passed": self.passed,
        }


def _normalize_ref(ref: str) -> str:
    raw = str(ref or "").strip()
    if raw.startswith("fact:"):
        return raw
    if raw.startswith("degraded_pass_through:"):
        return f"fact:{raw}"
    return raw


def _refs_from_claims(claims: list[Any]) -> set[str]:
    refs: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if claim.get("bind_status") not in ("bound", "omitted_numeric"):
            continue
        for ref in claim.get("source_refs") or []:
            normalized = _normalize_ref(str(ref))
            if normalized:
                refs.add(normalized)
    return refs


def evaluate_citation_pr(
    content_json: dict[str, Any],
    *,
    expected_refs: set[str] | None = None,
) -> CitationPRReport:
    """Compare bound claim source_refs against an optional expected ref set."""
    expected = {_normalize_ref(r) for r in (expected_refs or set()) if r}
    rendered: set[str] = set()
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("generation_status") != "GENERATED":
            continue
        content = section.get("content") or {}
        if content.get("citation_mode") == "legacy_fallback":
            continue
        rendered |= _refs_from_claims(list(content.get("claims") or []))

    if not expected:
        expected = set(rendered)

    missing = expected - rendered
    extra = rendered - expected
    return CitationPRReport(
        expected_refs=expected,
        rendered_refs=rendered,
        missing_refs=missing,
        extra_refs=extra,
    )
