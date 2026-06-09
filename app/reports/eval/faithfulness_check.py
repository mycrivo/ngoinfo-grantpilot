"""P1-1 faithfulness eval — absence and presence checks on structured claims output."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.reports.services.numeric_fact_verifier import (
    HONEST_OMISSION_PHRASE,
    extract_significant_numbers,
    normalize_numeric_token,
)

_NUMBER_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\b")
_DEGRADED_PASS_THROUGH_RE = re.compile(r"degraded_pass_through", re.IGNORECASE)


@dataclass(frozen=True)
class FaithfulnessReport:
    unmatched_numbers: list[dict[str, Any]] = field(default_factory=list)
    missing_expected_numbers: list[dict[str, Any]] = field(default_factory=list)
    degraded_leaks: list[str] = field(default_factory=list)
    omitted_claims_count: int = 0
    sections_checked: int = 0

    @property
    def passed(self) -> bool:
        return (
            not self.unmatched_numbers
            and not self.missing_expected_numbers
            and not self.degraded_leaks
        )

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "faithfulness.unmatched_numbers": len(self.unmatched_numbers),
            "faithfulness.missing_expected_numbers": len(
                self.missing_expected_numbers
            ),
            "faithfulness.degraded_leaks": len(self.degraded_leaks),
            "faithfulness.omitted_claims": self.omitted_claims_count,
            "faithfulness.passed": self.passed,
        }


def _claim_covers_number(
    number: str,
    claims: list[dict[str, Any]],
) -> bool:
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if claim.get("bind_status") not in ("bound", "omitted_numeric"):
            continue
        if not claim.get("source_refs"):
            continue
        tokens = [
            normalize_numeric_token(str(t))
            for t in (claim.get("value_tokens") or [])
        ]
        if number in tokens:
            return True
    return False


def _scan_degraded_leaks(content_json: dict[str, Any]) -> list[str]:
    serialized = json.dumps(content_json)
    matches = _DEGRADED_PASS_THROUGH_RE.findall(serialized)
    return sorted(set(matches))


def check_content_json_faithfulness(
    content_json: dict[str, Any],
    *,
    expected_presence: dict[str, list[str]] | None = None,
) -> FaithfulnessReport:
    """Absence: every rendered number maps to a bound claim. Presence: expected figures appear."""
    expected_presence = expected_presence or {}
    unmatched: list[dict[str, Any]] = []
    missing_expected: list[dict[str, Any]] = []
    omitted_total = 0
    sections_checked = 0

    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        if section.get("generation_status") != "GENERATED":
            continue
        content = section.get("content") or {}
        if content.get("citation_mode") == "legacy_fallback":
            continue
        section_key = str(section.get("section_key") or "")
        text = str(content.get("text") or "")
        claims = list(content.get("claims") or [])
        sections_checked += 1
        omitted_total += len(content.get("omitted_claims") or [])

        for number in extract_significant_numbers(text):
            if not _claim_covers_number(number, claims):
                unmatched.append(
                    {
                        "section_key": section_key,
                        "number": number,
                        "reason": "no_bound_claim_source_ref",
                    }
                )

        for expected in expected_presence.get(section_key) or []:
            normalized = normalize_numeric_token(str(expected))
            if not normalized:
                continue
            present = normalized in extract_significant_numbers(text)
            if not present:
                missing_expected.append(
                    {
                        "section_key": section_key,
                        "expected_number": normalized,
                        "reason": "expected_figure_absent_from_rendered_output",
                    }
                )

    degraded = _scan_degraded_leaks(content_json)
    return FaithfulnessReport(
        unmatched_numbers=unmatched,
        missing_expected_numbers=missing_expected,
        degraded_leaks=degraded,
        omitted_claims_count=omitted_total,
        sections_checked=sections_checked,
    )


def load_faithfulness_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_faithfulness_fixture(fixture: dict[str, Any]) -> FaithfulnessReport:
    content_json = fixture.get("content_json") or {}
    expected = fixture.get("expected_presence") or {}
    return check_content_json_faithfulness(
        content_json,
        expected_presence=expected,
    )
