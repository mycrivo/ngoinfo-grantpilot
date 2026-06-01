"""F1 synthesis output hygiene — evidence_used binding and prose sanitization."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

_AGGREGATE_FINANCIAL_MARKERS = (
    "total",
    "programme_budget",
    "aggregate",
    "grand_total",
    "lines_total",
    "output_line",
    "forecast",
)

_PAIR_FACETS: dict[str, str] = {
    "actual": "target",
    "target": "actual",
    "budget": "spend",
    "spend": "budget",
}

_DATE_VALUE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}-[a-z]{3}-\d{2,4}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SanitizedSectionContent:
    text: str
    evidence_used: list[str]
    dropped_citations: list[str]
    remapped_citations: list[dict[str, str]]
    auto_citations: list[str]


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


def _collapse_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _extract_indicator_id(key: str) -> str | None:
    normalized = normalize_identifier(key).lower()
    match = re.search(r"op(\d+)_(\d+)", normalized)
    if match:
        return f"op{match.group(1)}_{match.group(2)}"
    match = re.search(r"op(\d+)\.(\d+)", normalized)
    if match:
        return f"op{match.group(1)}_{match.group(2)}"
    return None


def _map_facet_token(token: str) -> str:
    collapsed = _collapse_token(token)
    if not collapsed:
        return "other"
    if collapsed in {"actual", "ar1actual"}:
        return "actual"
    if collapsed in {"target", "ar1target", "milestonetarget", "milestone"}:
        return "target"
    if collapsed in {"budget", "ar1budget"}:
        return "budget"
    if collapsed in {"spend", "actualspend", "ar1actualspend"}:
        return "spend"
    if "budget" in collapsed and "actual" not in collapsed:
        return "budget"
    if "spend" in collapsed:
        return "spend"
    return "other"


def _extract_facet(key: str) -> str:
    parts = normalize_identifier(key).split(".")
    for part in reversed(parts):
        facet = _map_facet_token(part)
        if facet != "other":
            return facet
    return "other"


def _is_aggregate_financial_key(key: str) -> bool:
    lower = key.lower()
    return any(marker in lower for marker in _AGGREGATE_FINANCIAL_MARKERS)


def fact_key_signature(key: str) -> str:
    """Deterministic near-miss signature for a fact or gap key path."""
    indicator = _extract_indicator_id(key)
    facet = _extract_facet(key)
    lower = key.lower()

    if lower.startswith("financials"):
        if _is_aggregate_financial_key(key):
            agg_part = _collapse_token(".".join(key.split(".")[1:]))
            return f"fin|agg|{agg_part}|{facet}"
        if indicator:
            return f"fin|line|{indicator}|{facet}"
        sem_part = _collapse_token(".".join(key.split(".")[1:]))
        return f"fin|sem|{sem_part}|{facet}"

    if indicator and lower.startswith("indicators"):
        return f"ind|{indicator}|{facet}"
    if indicator:
        return f"ind|{indicator}|{facet}"

    return f"unique|{_collapse_token(key)}"


def _signature_lookup(keys: dict[str, Any]) -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = {}
    for canonical in keys:
        sig = fact_key_signature(canonical)
        lookup.setdefault(sig, []).append(canonical)
    return lookup


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
    signature_lookup: dict[str, list[str]],
    remapped: list[dict[str, str]],
    original_ref: str,
) -> str | None:
    if raw_key in lookup:
        canonical = lookup[raw_key]
        return f"{prefix}{canonical}"

    normalized = normalize_identifier(raw_key)
    canonical = lookup.get(normalized)
    if canonical is not None:
        if canonical != raw_key:
            remapped.append({"from": original_ref, "to": f"{prefix}{canonical}"})
        return f"{prefix}{canonical}"

    sig = fact_key_signature(raw_key)
    candidates = signature_lookup.get(sig) or []
    if len(candidates) == 1:
        canonical = candidates[0]
        remapped.append({"from": original_ref, "to": f"{prefix}{canonical}"})
        return f"{prefix}{canonical}"

    return None


def sanitize_evidence_used(
    evidence_used: list[Any],
    *,
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
) -> tuple[list[str], list[str], list[dict[str, str]]]:
    """Bind fact:/gap: citations to KB allowlists; return (kept, dropped, remapped)."""
    fact_lookup = _canonical_lookup(kb_fact_keys)
    gap_lookup = _canonical_lookup(kb_gap_answer_keys or {})
    fact_sig = _signature_lookup(kb_fact_keys)
    gap_sig = _signature_lookup(kb_gap_answer_keys or {})

    kept: list[str] = []
    dropped: list[str] = []
    remapped: list[dict[str, str]] = []
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
                signature_lookup=fact_sig,
                remapped=remapped,
                original_ref=ref,
            )
        elif ref.startswith("gap:"):
            resolved = _resolve_citation(
                prefix="gap:",
                raw_key=ref.removeprefix("gap:"),
                lookup=gap_lookup,
                signature_lookup=gap_sig,
                remapped=remapped,
                original_ref=ref,
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

    return kept, dropped, remapped


def _normalize_value(value: Any) -> set[str]:
    if value is None:
        return set()
    raw = str(value).strip()
    if not raw:
        return set()

    forms: set[str] = {raw.lower(), _collapse_token(raw)}
    numeric = re.sub(r"[^0-9.]", "", raw.replace(",", ""))
    if numeric:
        forms.add(numeric)
        try:
            as_float = float(numeric)
            if as_float == int(as_float):
                forms.add(str(int(as_float)))
            forms.add(f"{as_float:g}")
        except ValueError:
            pass
    return {form for form in forms if form}


def _is_date_value(value: Any) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    if _DATE_VALUE_RE.match(raw):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", raw):
        return True
    if re.search(r"\b\d{1,2}-[A-Za-z]{3}-\d{2,4}\b", raw):
        return True
    return False


def _split_clauses(text: str) -> list[str]:
    parts = re.split(r"[.!?\n;]+", text)
    return [part.strip() for part in parts if part.strip()]


def _clause_tokens(clause: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", clause.lower()))


def _indicator_context_tokens(indicator_id: str) -> set[str]:
    match = re.match(r"op(\d+)_(\d+)", indicator_id)
    if not match:
        return {_collapse_token(indicator_id)}
    first, second = match.group(1), match.group(2)
    return {
        f"op{first}_{second}",
        f"op{first}{second}",
        f"op{first}.{second}",
        _collapse_token(f"op{first}_{second}"),
    }


def _context_has_identifier(
    clause: str,
    fact_key: str,
    fact: dict[str, Any],
    *,
    conservative: bool = False,
) -> bool:
    tokens = _clause_tokens(clause)
    collapsed_clause = _collapse_token(clause)

    indicator = _extract_indicator_id(fact_key)
    if indicator:
        if _indicator_context_tokens(indicator) & tokens:
            return True
        dotted = indicator.replace("_", ".")
        if dotted in clause.lower().replace(" ", ""):
            return True
        if _collapse_token(dotted) in collapsed_clause:
            return True

    if conservative:
        return False

    label = str(fact.get("semantic_label") or "")
    for word in re.findall(r"[a-zA-Z0-9]+", label):
        if len(word) < 4:
            continue
        token = _collapse_token(word)
        if token and token in collapsed_clause:
            return True

    gap_item = str(fact.get("item_key") or fact_key)
    for segment in gap_item.split(":"):
        token = _collapse_token(segment)
        if len(token) >= 4 and token in collapsed_clause:
            return True

    return False


def _value_in_clause(clause: str, value_forms: set[str]) -> bool:
    clause_plain = clause.replace(",", "")
    clause_lower = clause.lower()
    collapsed = _collapse_token(clause)

    for form in value_forms:
        if not form:
            continue
        if form in clause_lower or form in collapsed:
            return True
        if form.replace(".", "").isdigit() and re.search(
            r"\b" + re.escape(form.replace(".", "")) + r"\b",
            clause_plain,
        ):
            return True
    return False


def _global_value_matches(
    value_forms: set[str],
    entries: dict[str, dict[str, Any]],
    *,
    value_field: str,
) -> list[str]:
    matches: list[str] = []
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        entry_forms = _normalize_value(entry.get(value_field))
        if value_forms & entry_forms:
            matches.append(key)
    return matches


def _is_conservative_entry(fact_key: str, value: Any) -> bool:
    return _is_date_value(value) or _is_aggregate_financial_key(fact_key)


def _paired_fact_keys(fact_key: str, kb_facts: dict[str, Any]) -> list[str]:
    facet = _extract_facet(fact_key)
    partner_facet = _PAIR_FACETS.get(facet)
    if partner_facet is None:
        return []

    indicator = _extract_indicator_id(fact_key)
    if indicator:
        return [
            key
            for key in kb_facts
            if _extract_indicator_id(key) == indicator and _extract_facet(key) == partner_facet
        ]

    if fact_key.startswith("financials"):
        prefix = ".".join(fact_key.split(".")[:-1])
        return [
            key
            for key in kb_facts
            if key.startswith(prefix + ".") and _extract_facet(key) == partner_facet
        ]

    return []


def _try_backfill_ref(
    *,
    key: str,
    prefix: str,
    value: Any,
    clause: str,
    kb_entries: dict[str, Any],
    value_field: str,
    backfill_seen: set[str],
    auto_citations: list[str],
) -> bool:
    if not isinstance(kb_entries.get(key), dict):
        return False

    value_forms = _normalize_value(value)
    if not value_forms or not _value_in_clause(clause, value_forms):
        return False

    global_matches = _global_value_matches(value_forms, kb_entries, value_field=value_field)
    if len(global_matches) != 1 or global_matches[0] != key:
        return False

    entry = kb_entries[key]
    conservative = _is_conservative_entry(key, value)
    if not _context_has_identifier(clause, key, entry, conservative=conservative):
        return False

    ref = f"{prefix}{key}"
    if ref in backfill_seen:
        return True
    backfill_seen.add(ref)
    auto_citations.append(ref)
    return True


def enrich_evidence_from_kb(
    *,
    text: str,
    evidence_used: list[str],
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """Deterministic prose→KB citation backfill with fail-closed ambiguity guards."""
    gap_keys = kb_gap_answer_keys or {}
    backfill_seen: set[str] = set()
    auto_citations: list[str] = []

    for clause in _split_clauses(text):
        for fact_key, fact in kb_fact_keys.items():
            if not isinstance(fact, dict):
                continue
            if _try_backfill_ref(
                key=fact_key,
                prefix="fact:",
                value=fact.get("value"),
                clause=clause,
                kb_entries=kb_fact_keys,
                value_field="value",
                backfill_seen=backfill_seen,
                auto_citations=auto_citations,
            ):
                for partner_key in _paired_fact_keys(fact_key, kb_fact_keys):
                    partner = kb_fact_keys.get(partner_key)
                    if isinstance(partner, dict):
                        _try_backfill_ref(
                            key=partner_key,
                            prefix="fact:",
                            value=partner.get("value"),
                            clause=clause,
                            kb_entries=kb_fact_keys,
                            value_field="value",
                            backfill_seen=backfill_seen,
                            auto_citations=auto_citations,
                        )

        for gap_key, gap_entry in gap_keys.items():
            if not isinstance(gap_entry, dict):
                continue
            wrapped = {**gap_entry, "item_key": gap_key}
            _try_backfill_ref(
                key=gap_key,
                prefix="gap:",
                value=gap_entry.get("answer_text"),
                clause=clause,
                kb_entries={gap_key: wrapped},
                value_field="answer_text",
                backfill_seen=backfill_seen,
                auto_citations=auto_citations,
            )

    auto_sorted = sorted(auto_citations)
    merged = list(evidence_used)
    merged_seen = set(evidence_used)
    for ref in auto_sorted:
        if ref not in merged_seen:
            merged.append(ref)
            merged_seen.add(ref)
    return merged, auto_sorted


def sanitize_generated_content(
    *,
    text: str,
    evidence_used: list[Any],
    kb_fact_keys: dict[str, Any],
    kb_gap_answer_keys: dict[str, Any] | None = None,
) -> SanitizedSectionContent:
    """Sanitize F1 model output before persisting to content_json."""
    cleaned_text = sanitize_prose(text)
    cleaned_evidence, dropped, remapped = sanitize_evidence_used(
        evidence_used,
        kb_fact_keys=kb_fact_keys,
        kb_gap_answer_keys=kb_gap_answer_keys,
    )
    enriched_evidence, auto_citations = enrich_evidence_from_kb(
        text=cleaned_text,
        evidence_used=cleaned_evidence,
        kb_fact_keys=kb_fact_keys,
        kb_gap_answer_keys=kb_gap_answer_keys,
    )
    return SanitizedSectionContent(
        text=cleaned_text,
        evidence_used=enriched_evidence,
        dropped_citations=dropped,
        remapped_citations=remapped,
        auto_citations=auto_citations,
    )
