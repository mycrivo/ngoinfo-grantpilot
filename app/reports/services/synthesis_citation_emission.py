"""F1 claim-granular citation emission — bind evidence_used at the specificity of prose claims."""

from __future__ import annotations

import re
from typing import Any

from app.reports.services.synthesis_output_hygiene import (
    _extract_indicator_id,
    _indicator_context_tokens,
    _is_date_value,
    _normalize_value,
    _value_in_clause,
    normalize_identifier,
)

_GENERIC_REPORTING_OBLIGATION = "reporting.obligation.annual_review"

_MONEY_RE = re.compile(
    r"(?:GBP|£)\s*([\d,]+(?:\.\d+)?)|(?:\b)([\d,]+(?:\.\d+)?)\s*(?:GBP|£)",
    re.IGNORECASE,
)

_WRONG_INDEX_RE = re.compile(r"^(reporting\.annual_review_period_)\d+(\..+)$")


def _split_claim_clauses(text: str) -> list[str]:
    """Split prose without breaking OP2.1-style dotted indicator ids."""
    parts = re.split(r"(?<![0-9])[.!?;\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def _strip_citation_prefix(ref: str) -> tuple[str, str] | None:
    """Return (prefix, raw_key) for fact:/gap: refs with whitespace normalized."""
    if not isinstance(ref, str):
        return None
    stripped = ref.strip()
    if not stripped:
        return None
    if stripped.startswith("fact:"):
        raw = stripped.removeprefix("fact:").strip()
        if not raw:
            return None
        return "fact:", raw
    if stripped.startswith("gap:"):
        raw = stripped.removeprefix("gap:").strip()
        if not raw:
            return None
        return "gap:", raw
    return None


def _format_ref(prefix: str, key: str) -> str:
    return f"{prefix}{key}"


def _fix_wrong_index_fact_key(raw_key: str, kb_fact_keys: dict[str, Any]) -> str:
    """Map wrong-index reporting keys (e.g. period_0) to canonical KB siblings."""
    if raw_key in kb_fact_keys:
        return raw_key
    match = _WRONG_INDEX_RE.match(raw_key)
    if not match:
        return raw_key
    prefix, suffix = match.group(1), match.group(2)
    candidates = [
        key
        for key in kb_fact_keys
        if key.startswith(prefix) and key.endswith(suffix) and key != raw_key
    ]
    if len(candidates) == 1:
        return candidates[0]
    return raw_key


def _resolve_fact_key(raw_key: str, kb_fact_keys: dict[str, Any]) -> str | None:
    """Resolve emitted fact key to a canonical KB key (normalize, wrong-index fix)."""
    raw_key = normalize_identifier(raw_key.strip())
    if not raw_key:
        return None
    raw_key = _fix_wrong_index_fact_key(raw_key, kb_fact_keys)
    if raw_key in kb_fact_keys:
        return raw_key
    return None


def _resolve_gap_key(raw_key: str, kb_gap_answer_keys: dict[str, Any]) -> str | None:
    raw_key = raw_key.strip()
    if raw_key in kb_gap_answer_keys:
        return raw_key
    return None


def _normalize_emitted_refs(
    evidence_used: list[Any],
    *,
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any],
) -> list[str]:
    """Fix malformed emission (space-prefixed keys, wrong index) before granularity pass."""
    out: list[str] = []
    seen: set[str] = set()
    for ref in evidence_used:
        parsed = _strip_citation_prefix(ref)
        if parsed is None:
            continue
        prefix, raw_key = parsed
        if prefix == "fact:":
            canonical_key = _resolve_fact_key(raw_key, kb_fact_keys)
            if canonical_key is None:
                passthrough = _format_ref(prefix, normalize_identifier(raw_key.strip()))
                if passthrough not in seen:
                    seen.add(passthrough)
                    out.append(passthrough)
                continue
        else:
            canonical_key = _resolve_gap_key(raw_key, kb_gap_answer_keys)
            if canonical_key is None:
                passthrough = _format_ref(prefix, raw_key.strip())
                if passthrough not in seen:
                    seen.add(passthrough)
                    out.append(passthrough)
                continue
        canonical = _format_ref(prefix, canonical_key)
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def _money_amounts_in_clause(clause: str) -> set[str]:
    amounts: set[str] = set()
    for match in _MONEY_RE.finditer(clause):
        for group in match.groups():
            if group:
                amounts |= _normalize_value(group)
    return amounts


def _clause_has_op_context(clause: str, op_id: str) -> bool:
    collapsed = _collapse_token(clause)
    if _indicator_context_tokens(op_id) & set(re.findall(r"[a-z0-9]+", clause.lower())):
        return True
    dotted = op_id.replace("_", ".")
    if dotted in clause.lower().replace(" ", ""):
        return True
    if _collapse_token(dotted) in collapsed:
        return True
    return False


def _collapse_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _upgrade_spend_citations(
    text: str,
    refs: list[str],
    *,
    kb_fact_keys: dict[str, Any],
) -> list[str]:
    """Replace indicator keys with financials.lines keys when prose states GBP line amounts."""
    refs_set = set(refs)
    to_remove: set[str] = set()
    to_add: set[str] = set()

    for clause in _split_claim_clauses(text):
        amounts = _money_amounts_in_clause(clause)
        if not amounts:
            continue

        for fact_key, fact in kb_fact_keys.items():
            if not fact_key.startswith("financials.lines."):
                continue
            op_id = _extract_indicator_id(fact_key)
            if not op_id or not _clause_has_op_context(clause, op_id):
                continue
            value_forms = _normalize_value(fact.get("value"))
            if not (amounts & value_forms):
                continue
            to_add.add(_format_ref("fact:", fact_key))

        for op_id in {_extract_indicator_id(k) for k in kb_fact_keys if k.startswith("financials.lines.")}:
            if not op_id or not _clause_has_op_context(clause, op_id):
                continue
            if not any(a in clause for a in ("GBP", "£", "gbp")):
                continue
            for ref in list(refs_set):
                if not ref.startswith("fact:indicators."):
                    continue
                if _extract_indicator_id(ref.removeprefix("fact:")) == op_id:
                    if any(f"financials.lines.{op_id}." in r for r in to_add):
                        to_remove.add(ref)

    updated = [r for r in refs if r not in to_remove]
    seen = set(updated)
    for ref in sorted(to_add):
        if ref not in seen:
            updated.append(ref)
            seen.add(ref)
    return updated


def _gap_phrases(answer_text: str) -> list[str]:
    phrases: list[str] = []
    for sentence in re.split(r"[.!?\n;]+", answer_text):
        normalized = " ".join(sentence.split())
        if len(normalized) >= 24:
            phrases.append(normalized.lower())
        words = normalized.split()
        for i in range(len(words) - 4):
            chunk = " ".join(words[i : i + 5]).lower()
            if len(chunk) >= 20:
                phrases.append(chunk)
    return phrases


def _gap_text_used_in_prose(answer_text: str, text: str) -> bool:
    prose = " ".join(text.split()).lower()
    answer_lower = " ".join(answer_text.split()).lower()
    for phrase in _gap_phrases(answer_text):
        if phrase in prose:
            return True
    prose_tokens = set(re.findall(r"[a-z0-9]+", prose))
    answer_tokens = set(re.findall(r"[a-z0-9]+", answer_lower))
    if len(prose_tokens & answer_tokens) >= 4:
        shared_numeric = [
            t
            for t in prose_tokens & answer_tokens
            if t.isdigit() and len(t) <= 4
        ]
        if shared_numeric and len(prose_tokens & answer_tokens) >= 3:
            return True
    return False


def _bind_gap_citations(
    text: str,
    refs: list[str],
    *,
    kb_gap_answer_keys: dict[str, Any],
) -> list[str]:
    """Cite gap: keys when section prose reuses gap answer text."""
    seen = set(refs)
    out = list(refs)
    for gap_key, gap_entry in kb_gap_answer_keys.items():
        if not isinstance(gap_entry, dict):
            continue
        answer = str(gap_entry.get("answer_text") or "")
        if not answer or not _gap_text_used_in_prose(answer, text):
            continue
        ref = _format_ref("gap:", gap_key)
        if ref not in seen:
            out.append(ref)
            seen.add(ref)
    return out


def _date_forms_in_prose(value: Any) -> set[str]:
    forms = _normalize_value(value)
    raw = str(value or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        year, month, day = raw.split("-")
        months = (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        )
        mi = int(month) - 1
        if 0 <= mi < 12:
            forms.add(f"{int(day)} {months[mi]} {year}".lower())
            forms.add(f"{day} {months[mi][:3]} {year[-2:]}".lower())
    return forms


def _bind_specific_reporting_citations(
    text: str,
    refs: list[str],
    *,
    kb_fact_keys: dict[str, Any],
) -> list[str]:
    """Bind specific reporting period/deadline facts when prose states those dates."""
    prose = text.lower()
    seen = set(refs)
    out = list(refs)
    specific_added = False

    for fact_key, fact in kb_fact_keys.items():
        if not fact_key.startswith("reporting."):
            continue
        if fact_key == _GENERIC_REPORTING_OBLIGATION:
            continue
        value = fact.get("value")
        if not _is_date_value(value):
            continue
        forms = _date_forms_in_prose(value) | _normalize_value(value)
        if not any(form and form in prose.replace(",", "") for form in forms):
            if not _value_in_clause(text, forms):
                continue
        ref = _format_ref("fact:", fact_key)
        if ref not in seen:
            out.append(ref)
            seen.add(ref)
            specific_added = True

    if specific_added:
        generic = _format_ref("fact:", _GENERIC_REPORTING_OBLIGATION)
        out = [r for r in out if r != generic]
    return out


def _strip_generic_obligation_when_specific_present(refs: list[str]) -> list[str]:
    generic = _format_ref("fact:", _GENERIC_REPORTING_OBLIGATION)
    has_specific = any(
        r.startswith("fact:reporting.annual_review_period")
        or r == "fact:reporting.annual_review_pack_deadline"
        for r in refs
    )
    if has_specific:
        return [r for r in refs if r != generic]
    return refs


def _bind_paired_indicator_citations(
    text: str,
    refs: list[str],
    *,
    kb_fact_keys: dict[str, Any],
) -> list[str]:
    """When target is cited and actual value appears in prose, bind y1_actual (and vice versa)."""
    seen = set(refs)
    out = list(refs)
    for ref in refs:
        if not ref.startswith("fact:indicators."):
            continue
        key = ref.removeprefix("fact:")
        if key.endswith(".y1_target"):
            partner = key[: -len(".y1_target")] + ".y1_actual"
        elif key.endswith(".y1_actual"):
            partner = key[: -len(".y1_actual")] + ".y1_target"
        else:
            continue
        partner_fact = kb_fact_keys.get(partner)
        if not isinstance(partner_fact, dict):
            continue
        if not _value_in_clause(text, _normalize_value(partner_fact.get("value"))):
            continue
        partner_ref = _format_ref("fact:", partner)
        if partner_ref not in seen:
            out.append(partner_ref)
            seen.add(partner_ref)
    return out


def _bind_value_citations_from_prose(
    text: str,
    refs: list[str],
    *,
    kb_fact_keys: dict[str, Any],
) -> list[str]:
    """Bind fact keys when a unique KB value appears in prose with identifier context."""
    seen = set(refs)
    out = list(refs)

    for clause in _split_claim_clauses(text):
        for fact_key, fact in kb_fact_keys.items():
            if not isinstance(fact, dict):
                continue
            if fact_key == _GENERIC_REPORTING_OBLIGATION:
                continue
            if fact_key.startswith("financials.lines."):
                continue
            value = fact.get("value")
            value_forms = _normalize_value(value)
            if not value_forms or not _value_in_clause(clause, value_forms):
                continue
            indicator = _extract_indicator_id(fact_key)
            if indicator and not _clause_has_op_context(clause, indicator):
                if not fact_key.startswith("reporting."):
                    continue
            ref = _format_ref("fact:", fact_key)
            if ref in seen:
                continue
            global_hits = [
                k
                for k, entry in kb_fact_keys.items()
                if isinstance(entry, dict)
                and _normalize_value(entry.get("value")) & value_forms
            ]
            if len(global_hits) != 1 or global_hits[0] != fact_key:
                continue
            out.append(ref)
            seen.add(ref)
    return out


def emit_claim_granular_evidence(
    *,
    text: str,
    evidence_used: list[Any],
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
    section_key: str | None = None,
) -> list[str]:
    """
    F1 emission pass: align evidence_used[] to claim granularity in prose.

    Runs before hygiene (C1/C2). Only cites keys present in facts{} / gap_answers{}.
    Does not invent values absent from the knowledge bank.
    """
    _ = section_key  # reserved for section-scoped rules; gap bind is prose-driven
    gaps = kb_gap_answer_keys or {}
    refs = _normalize_emitted_refs(
        evidence_used,
        kb_fact_keys=kb_fact_keys,
        kb_gap_answer_keys=gaps,
    )
    refs = _upgrade_spend_citations(text, refs, kb_fact_keys=kb_fact_keys)
    refs = _bind_paired_indicator_citations(text, refs, kb_fact_keys=kb_fact_keys)
    refs = _bind_gap_citations(text, refs, kb_gap_answer_keys=gaps)
    refs = _bind_specific_reporting_citations(text, refs, kb_fact_keys=kb_fact_keys)
    refs = _bind_value_citations_from_prose(text, refs, kb_fact_keys=kb_fact_keys)
    refs = _strip_generic_obligation_when_specific_present(refs)

    deduped: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        parsed = _strip_citation_prefix(ref)
        if parsed is None:
            continue
        prefix, raw_key = parsed
        if prefix == "fact:":
            canonical_key = _resolve_fact_key(raw_key, kb_fact_keys)
            if canonical_key is None:
                passthrough = _format_ref(prefix, normalize_identifier(raw_key.strip()))
                if (
                    passthrough not in seen
                    and " " not in passthrough
                    and not passthrough.startswith("fact: ")
                ):
                    seen.add(passthrough)
                    deduped.append(passthrough)
                continue
        else:
            canonical_key = _resolve_gap_key(raw_key, gaps)
            if canonical_key is None:
                passthrough = _format_ref(prefix, raw_key.strip())
                if passthrough not in seen and " " not in passthrough:
                    seen.add(passthrough)
                    deduped.append(passthrough)
                continue
        canonical = _format_ref(prefix, canonical_key)
        if " " in canonical or canonical.startswith("fact: ") or canonical.startswith("gap: "):
            continue
        if canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(canonical)
    return deduped
