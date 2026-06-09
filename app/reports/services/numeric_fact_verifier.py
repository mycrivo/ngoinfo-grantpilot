"""P1-2 deterministic numeric/date/money verification — zero LLM.

Structured sections: claims[] primary; prose scan is uncited-number backstop only.
Legacy fallback sections use prose-vs-KB matching temporarily — NOT certified to the
structured numeric bar (see LEGACY_NUMERIC_CERTIFICATION).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from app.reports.knowledge.confirmed_kb import ConfirmedKBView
from app.reports.services.synthesis_output_hygiene import normalize_identifier

HONEST_OMISSION_PHRASE = "not reported this period"

_CURRENCY_RE = re.compile(
    r"(?:GBP|£)\s*([\d,]+(?:\.\d+)?)|(?:\b)([\d,]+(?:\.\d+)?)\s*(?:GBP|£)",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\b")
_DATE_VALUE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}-[a-z]{3}-\d{2,4}$",
    re.IGNORECASE,
)
_MIN_SIGNIFICANT_DIGITS = 2

LEGACY_NUMERIC_CERTIFICATION = (
    "legacy_fallback prose-vs-KB numeric path is temporary and NOT equivalent to "
    "structured claims-primary certification; dies with regex layer deletion."
)


@dataclass(frozen=True)
class NumericVerifyFlag:
    claim_text: str
    severity: Literal["BLOCK"]
    reason: str
    source_ref: str | None
    verification_path: Literal["deterministic_numeric"] = "deterministic_numeric"


def normalize_numeric_token(token: str) -> str:
    """Collapse commas/currency for exact-match binding."""
    raw = str(token or "").strip()
    if not raw:
        return ""
    match = _CURRENCY_RE.search(raw)
    if match:
        raw = match.group(1) or match.group(2) or raw
    numeric = re.sub(r"[^0-9.]", "", raw.replace(",", ""))
    if not numeric:
        return ""
    try:
        as_float = float(numeric)
        if as_float == int(as_float):
            return str(int(as_float))
        return f"{as_float:g}"
    except ValueError:
        return numeric


def normalize_date_token(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    return raw


def _normalize_value_forms(value: Any) -> set[str]:
    if value is None:
        return set()
    raw = str(value).strip()
    if not raw:
        return set()
    forms = {raw.lower(), normalize_numeric_token(raw), normalize_date_token(raw)}
    return {form for form in forms if form}


def _is_significant_number(token: str) -> bool:
    normalized = normalize_numeric_token(token)
    if not normalized:
        return False
    digits = re.sub(r"[^0-9]", "", normalized)
    return len(digits) >= _MIN_SIGNIFICANT_DIGITS


def extract_significant_numbers(text: str) -> list[str]:
    if not text:
        return []
    scrubbed = text.replace(HONEST_OMISSION_PHRASE, " ")
    found: list[str] = []
    seen: set[str] = set()
    for match in _NUMBER_RE.finditer(scrubbed):
        raw = match.group(1)
        normalized = normalize_numeric_token(raw)
        if not _is_significant_number(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        found.append(normalized)
    return found


def _parse_source_ref(ref: str) -> tuple[str, str] | None:
    if not isinstance(ref, str):
        return None
    stripped = ref.strip()
    if stripped.startswith("fact:"):
        key = stripped.removeprefix("fact:").strip()
        return ("fact", normalize_identifier(key)) if key else None
    if stripped.startswith("gap:"):
        key = stripped.removeprefix("gap:").strip()
        return ("gap", key.strip()) if key else None
    return None


def _resolve_fact_key(raw_key: str, facts: dict[str, Any]) -> str | None:
    if raw_key in facts:
        return raw_key
    norm = normalize_identifier(raw_key)
    for key in facts:
        if normalize_identifier(key) == norm:
            return key
    return None


def _resolve_gap_key(raw_key: str, gaps: dict[str, Any]) -> str | None:
    if raw_key in gaps:
        return raw_key
    norm = normalize_identifier(raw_key)
    for key in gaps:
        if normalize_identifier(key) == norm:
            return key
    return None


def _value_in_source(
    token: str,
    *,
    prefix: str,
    key: str,
    facts: dict[str, Any],
    gaps: dict[str, Any],
) -> bool:
    normalized = normalize_numeric_token(token)
    if not normalized:
        return True
    if prefix == "fact":
        fact = facts.get(key)
        if not isinstance(fact, dict):
            return False
        return normalized in _normalize_value_forms(fact.get("value"))
    entry = gaps.get(key)
    if not isinstance(entry, dict):
        return False
    for field_name in ("answer_text", "value"):
        if normalized in _normalize_value_forms(entry.get(field_name)):
            return True
        answer = str(entry.get("answer_text") or "")
        if normalized in normalize_numeric_token(answer):
            return True
    return False


def _all_citable_numeric_forms(kb_view: ConfirmedKBView) -> set[str]:
    forms: set[str] = set()
    for fact in kb_view.facts.values():
        if isinstance(fact, dict):
            forms.update(_normalize_value_forms(fact.get("value")))
    for entry in kb_view.gap_answers.values():
        if isinstance(entry, dict):
            forms.update(_normalize_value_forms(entry.get("answer_text")))
            forms.update(_normalize_value_forms(entry.get("value")))
    return {f for f in forms if f and _is_significant_number(f)}


def _verify_claims_primary(
    *,
    claims: list[dict[str, Any]],
    kb_view: ConfirmedKBView,
) -> tuple[list[NumericVerifyFlag], set[str]]:
    flags: list[NumericVerifyFlag] = []
    covered: set[str] = set()
    facts = kb_view.facts
    gaps = kb_view.gap_answers

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        bind_status = claim.get("bind_status")
        if bind_status not in ("bound", "omitted_numeric"):
            continue
        refs = claim.get("source_refs") or []
        if not refs:
            continue
        value_tokens = [
            normalize_numeric_token(str(t))
            for t in (claim.get("value_tokens") or [])
            if normalize_numeric_token(str(t))
        ]
        resolved: list[tuple[str, str]] = []
        for ref in refs:
            parsed = _parse_source_ref(str(ref))
            if parsed is None:
                continue
            prefix, raw_key = parsed
            if prefix == "fact":
                canonical = _resolve_fact_key(raw_key, facts)
            else:
                canonical = _resolve_gap_key(raw_key, gaps)
            if canonical:
                resolved.append((prefix, canonical))

        claim_text = str(claim.get("text") or "")
        for token in value_tokens:
            covered.add(token)
            if not resolved:
                flags.append(
                    NumericVerifyFlag(
                        claim_text=claim_text or token,
                        severity="BLOCK",
                        reason="Numeric claim has no resolvable citable source_refs",
                        source_ref=None,
                    )
                )
                continue
            if not any(
                _value_in_source(
                    token, prefix=p, key=k, facts=facts, gaps=gaps
                )
                for p, k in resolved
            ):
                flags.append(
                    NumericVerifyFlag(
                        claim_text=claim_text or token,
                        severity="BLOCK",
                        reason="Claim value_token does not match cited citable source",
                        source_ref=refs[0] if refs else None,
                    )
                )

    return flags, covered


def _verify_prose_backstop(
    *,
    section_text: str,
    covered_tokens: set[str],
) -> list[NumericVerifyFlag]:
    flags: list[NumericVerifyFlag] = []
    for number in extract_significant_numbers(section_text):
        if number in covered_tokens:
            continue
        flags.append(
            NumericVerifyFlag(
                claim_text=number,
                severity="BLOCK",
                reason="Uncited numeric in prose not covered by any bound claim value_token",
                source_ref=None,
            )
        )
    return flags


def _verify_legacy_prose_vs_kb(
    *,
    section_text: str,
    kb_view: ConfirmedKBView,
) -> list[NumericVerifyFlag]:
    """Temporary path — not structured-certification equivalent."""
    kb_forms = _all_citable_numeric_forms(kb_view)
    flags: list[NumericVerifyFlag] = []
    for number in extract_significant_numbers(section_text):
        if number not in kb_forms:
            flags.append(
                NumericVerifyFlag(
                    claim_text=number,
                    severity="BLOCK",
                    reason=(
                        "Legacy fallback: numeric in prose not matched to any citable "
                        f"KB value ({LEGACY_NUMERIC_CERTIFICATION})"
                    ),
                    source_ref=None,
                )
            )
    return flags


def verify_section_numerics(
    *,
    section_text: str,
    claims: list[dict[str, Any]],
    citation_mode: str | None,
    kb_view: ConfirmedKBView,
) -> list[NumericVerifyFlag]:
    if citation_mode == "legacy_fallback" or not claims:
        return _verify_legacy_prose_vs_kb(section_text=section_text, kb_view=kb_view)

    primary_flags, covered = _verify_claims_primary(claims=claims, kb_view=kb_view)
    backstop_flags = _verify_prose_backstop(
        section_text=section_text,
        covered_tokens=covered,
    )
    return primary_flags + backstop_flags


def numeric_flag_to_critic_dict(flag: NumericVerifyFlag) -> dict[str, Any]:
    return {
        "claim_text": flag.claim_text,
        "severity": flag.severity,
        "reason": flag.reason,
        "source_required": True,
        "accepted": False,
        "accepted_at": None,
        "source_ref": flag.source_ref,
        "verification_path": flag.verification_path,
    }
