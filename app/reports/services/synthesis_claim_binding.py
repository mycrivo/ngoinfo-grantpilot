"""P1-1 structured claim binding — primary citation authority at generation time.

Deletion trigger: after 2 consecutive CLEAN CI runs with SYNTHESIS_CITATION_FALLBACK=0
and faithfulness.unmatched_numbers == 0, remove synthesis_citation_emission.py and
C1/C2 prose-backfill in synthesis_output_hygiene.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.reports.knowledge.confirmed_kb import (
    is_fact_citable,
    is_gap_answer_citable,
)
from app.reports.services.section_prose import (
    FAILURE_EMPTY_PROSE,
    assemble_prose_from_bound_claims,
    has_non_empty_prose,
)
from app.reports.services.synthesis_output_hygiene import (
    normalize_identifier,
    sanitize_prose,
)

from app.reports.services.numeric_fact_verifier import (  # noqa: E402
    HONEST_OMISSION_PHRASE,
    normalize_numeric_token,
)

FAILURE_MISSING_STRUCTURED_CLAIMS = "MISSING_STRUCTURED_CLAIMS"

__all__ = [
    "FAILURE_EMPTY_PROSE",
    "FAILURE_MISSING_STRUCTURED_CLAIMS",
    "BoundSectionContent",
    "StructuredBindOutcome",
    "bind_structured_claims",
    "resolve_structured_synthesis",
    "section_has_citable_inputs",
]

StructuredBindStatus = Literal["bound", "honest_empty", "insufficient_data", "omitted_numeric", "dropped_refs"]
ClaimBindStatus = Literal["bound", "omitted_numeric", "dropped_refs", "empty"]


@dataclass(frozen=True)
class BoundSectionContent:
    text: str
    claims: list[dict[str, Any]]
    evidence_used: list[str]
    omitted_claims: list[dict[str, Any]]
    warnings: list[str]
    structured_bind_status: Literal["bound", "honest_empty"]


@dataclass
class StructuredBindOutcome:
    ok: bool
    content: BoundSectionContent | None = None
    failure_reason: str | None = None


def section_has_citable_inputs(knowledge_bank: dict[str, Any]) -> bool:
    """True when this section's synthesis inputs include citable facts or gap answers."""
    facts = knowledge_bank.get("facts") or {}
    gaps = knowledge_bank.get("gap_answers") or {}
    return bool(facts) or bool(gaps)


def _normalize_value_forms(value: Any) -> set[str]:
    if value is None:
        return set()
    raw = str(value).strip()
    if not raw:
        return set()
    forms = {raw.lower(), normalize_numeric_token(raw)}
    return {form for form in forms if form}


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


def _format_source_ref(prefix: str, key: str) -> str:
    return f"{prefix}:{key}"


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


def _ref_is_citable(
    prefix: str,
    key: str,
    *,
    facts: dict[str, Any],
    gaps: dict[str, Any],
    gate1_confirmed_at: str | None,
) -> bool:
    if prefix == "fact":
        fact = facts.get(key)
        if not isinstance(fact, dict):
            return False
        return is_fact_citable(fact, gate1_confirmed_at=gate1_confirmed_at)
    entry = gaps.get(key)
    if not isinstance(entry, dict):
        return False
    return is_gap_answer_citable(entry)


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
        forms = _normalize_value_forms(entry.get(field_name))
        if normalized in forms:
            return True
        answer = str(entry.get("answer_text") or "")
        if normalized in normalize_numeric_token(answer):
            return True
    return False


def _token_bound_by_refs(
    token: str,
    bound_refs: list[tuple[str, str]],
    *,
    facts: dict[str, Any],
    gaps: dict[str, Any],
) -> bool:
    if not bound_refs:
        return False
    return any(
        _value_in_source(token, prefix=prefix, key=key, facts=facts, gaps=gaps)
        for prefix, key in bound_refs
    )


def _replace_token_in_text(text: str, token: str, replacement: str) -> str:
    if not token or not text:
        return text
    pattern = re.compile(re.escape(token))
    return pattern.sub(replacement, text, count=1)


def bind_structured_claims(
    *,
    claims: list[dict[str, Any]],
    text: str,
    knowledge_bank: dict[str, Any],
) -> BoundSectionContent:
    """Bind model claims against citable KB; apply honest omission for bad numerics."""
    facts = dict(knowledge_bank.get("facts") or {})
    gaps = dict(knowledge_bank.get("gap_answers") or {})
    gate1_at = knowledge_bank.get("gate1_confirmed_at")

    bound_claims: list[dict[str, Any]] = []
    omitted_claims: list[dict[str, Any]] = []
    evidence_seen: set[str] = set()
    evidence_used: list[str] = []
    warnings: list[str] = []
    working_text = str(text or "")

    for raw_claim in claims or []:
        if not isinstance(raw_claim, dict):
            continue
        claim_text = str(raw_claim.get("text") or "")
        value_tokens = [
            str(t).strip()
            for t in (raw_claim.get("value_tokens") or [])
            if str(t).strip()
        ]
        bound_refs: list[tuple[str, str]] = []
        dropped_refs: list[str] = []

        for ref in raw_claim.get("source_refs") or []:
            parsed = _parse_source_ref(str(ref))
            if parsed is None:
                dropped_refs.append(str(ref))
                continue
            prefix, raw_key = parsed
            if prefix == "fact":
                canonical = _resolve_fact_key(raw_key, facts)
                if canonical is None:
                    dropped_refs.append(str(ref))
                    continue
                if not _ref_is_citable(
                    "fact",
                    canonical,
                    facts=facts,
                    gaps=gaps,
                    gate1_confirmed_at=gate1_at,
                ):
                    dropped_refs.append(str(ref))
                    continue
                bound_refs.append(("fact", canonical))
                formatted = _format_source_ref("fact", canonical)
            else:
                canonical = _resolve_gap_key(raw_key, gaps)
                if canonical is None:
                    dropped_refs.append(str(ref))
                    continue
                if not _ref_is_citable(
                    "gap",
                    canonical,
                    facts=facts,
                    gaps=gaps,
                    gate1_confirmed_at=gate1_at,
                ):
                    dropped_refs.append(str(ref))
                    continue
                bound_refs.append(("gap", canonical))
                formatted = _format_source_ref("gap", canonical)

            if formatted not in evidence_seen:
                evidence_seen.add(formatted)
                evidence_used.append(formatted)

        bind_status: ClaimBindStatus
        if not bound_refs:
            bind_status = "dropped_refs"
        elif value_tokens:
            bind_status = "bound"
            for token in value_tokens:
                if not _token_bound_by_refs(
                    token,
                    bound_refs,
                    facts=facts,
                    gaps=gaps,
                ):
                    bind_status = "omitted_numeric"
                    claim_text = _replace_token_in_text(
                        claim_text, token, HONEST_OMISSION_PHRASE
                    )
                    working_text = _replace_token_in_text(
                        working_text, token, HONEST_OMISSION_PHRASE
                    )
                    omitted_claims.append(
                        {
                            "original_text": str(raw_claim.get("text") or ""),
                            "reason": "value_token_not_bound_to_citable_source",
                            "value_tokens": [token],
                        }
                    )
        else:
            bind_status = "bound" if bound_refs else "empty"

        bound_claims.append(
            {
                "text": claim_text,
                "source_refs": [
                    _format_source_ref(prefix, key) for prefix, key in bound_refs
                ],
                "value_tokens": value_tokens,
                "bind_status": bind_status,
                "dropped_refs": dropped_refs,
            }
        )

    cleaned_text = sanitize_prose(working_text)
    if not cleaned_text.strip():
        cleaned_text = sanitize_prose(assemble_prose_from_bound_claims(bound_claims))
    bound_count = sum(1 for c in bound_claims if c.get("bind_status") == "bound")
    structured_bind_status: Literal["bound", "honest_empty"] = (
        "bound" if bound_count > 0 else "honest_empty"
    )

    return BoundSectionContent(
        text=cleaned_text,
        claims=bound_claims,
        evidence_used=evidence_used,
        omitted_claims=omitted_claims,
        warnings=warnings,
        structured_bind_status=structured_bind_status,
    )


def resolve_structured_synthesis(
    *,
    claims: list[dict[str, Any]],
    text: str,
    knowledge_bank: dict[str, Any],
) -> StructuredBindOutcome:
    """Bind claims or fail closed / honest-empty per P1-1 moat rules."""
    has_citable = section_has_citable_inputs(knowledge_bank)

    if not claims:
        if has_citable:
            return StructuredBindOutcome(
                ok=False,
                failure_reason=FAILURE_MISSING_STRUCTURED_CLAIMS,
            )
        return StructuredBindOutcome(
            ok=True,
            content=BoundSectionContent(
                text=sanitize_prose(str(text or "")),
                claims=[],
                evidence_used=[],
                omitted_claims=[],
                warnings=[],
                structured_bind_status="honest_empty",
            ),
        )

    bound = bind_structured_claims(
        claims=claims,
        text=text,
        knowledge_bank=knowledge_bank,
    )
    bound_count = sum(
        1 for c in bound.claims if c.get("bind_status") in ("bound", "omitted_numeric")
        and c.get("source_refs")
    )
    if has_citable and bound_count == 0:
        return StructuredBindOutcome(
            ok=False,
            failure_reason=FAILURE_MISSING_STRUCTURED_CLAIMS,
        )
    if has_citable and bound_count > 0:
        probe = {"content": {"text": bound.text}}
        if not has_non_empty_prose(probe):
            return StructuredBindOutcome(
                ok=False,
                failure_reason=FAILURE_EMPTY_PROSE,
            )
    return StructuredBindOutcome(ok=True, content=bound)
