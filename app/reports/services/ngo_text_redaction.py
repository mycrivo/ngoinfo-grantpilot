"""Single NGO-facing identifier-redaction chokepoint (Package 1).

Every NGO-facing surface of the donor report (section body prose, the
Assumptions & Caveats appendix, deterministic insufficiency prose, table cell
content, and headings) MUST pass through ``redact_internal_identifiers`` before
it reaches the rendered document. The moat promise is that no internal
identifier of any kind (schema key, requirement ref, ``fact:``/``gap:`` key,
gap ``item_key``, archetype token, enum value, colon-delimited path,
``financials.lines.*`` path) ever surfaces to the NGO.

Design contract (translate-first, never delete the honest clause):

1. Recognized attribution scaffolds are collapsed to a clean honest sentence
   (e.g. "... from gap answer <id>." -> "...."). These are the only shapes the
   chokepoint reconstructs.
2. FAIL-SAFE for every other shape: each identifier token is replaced *in place*
   by its plain-English human label. This is the conservative, boring transform
   - it can never delete a sentence, never soften the caveat, and never leave an
   identifier behind. It deliberately does NOT attempt clever sentence rewrites
   on shapes it does not confidently recognize. Boring-and-clean beats
   smart-and-risky; honest meaning is the invariant.

The export tripwire (``app.reports.eval.docx_export_assertions``) is the backstop
that fails the build if any identifier pattern survives this pass.
"""

from __future__ import annotations

import re

# --- Identifier shapes ------------------------------------------------------
# Colon item_key: section:type:ref (>=2 colons, letter-led, NO internal spaces).
# The no-space requirement is the core false-positive guard: identifiers never
# contain spaces, while legitimate prose always puts a space after a colon
# ("Note: the budget"), and times/ratios/scripture ("10:30", "3:1", "John 3:16")
# are digit-led with a single colon.
_COLON_ID = r"[A-Za-z][A-Za-z0-9_]*(?::[A-Za-z0-9_]+){2,}"

# Dotted schema/fact paths, restricted to known KB namespaces so we never trip
# on URLs, "i.e.", decimals, or domain names in honest prose.
_DOTTED_NAMESPACES = ("financials", "indicators", "indicator", "reporting", "objectives", "outcomes")
_DOTTED_ID = (
    r"\b(?:" + "|".join(_DOTTED_NAMESPACES) + r")(?:\.[A-Za-z0-9_]+){2,}"
)

# Internal enum literals that can leak as snake_case tokens. Closed set only -
# common English words ("answered", "skipped") are deliberately excluded so the
# tripwire and translation never touch honest prose.
_ENUM_PHRASES: dict[str, str] = {
    "cannot_provide": "could not be provided",
    "not_applicable": "not applicable",
}

_BRACKET_RE = re.compile(r"\s*\[(?:fact|gap):[^\]]*\]\s*", re.IGNORECASE)
_ARCHETYPE_RE = re.compile(r"\bARCH_[A-Z0-9_]+\b")
_COLON_ID_RE = re.compile(_COLON_ID)
_DOTTED_ID_RE = re.compile(_DOTTED_ID)
_ENUM_RAW = r"(?:" + "|".join(re.escape(k) for k in _ENUM_PHRASES) + r")"
_ENUM_RE = re.compile(r"\b" + _ENUM_RAW + r"\b")

# --- Recognized attribution scaffolds (clean collapse) ----------------------
# "... (was) available/provided from gap answer(s) <id>" -> drop the tail,
# keeping the honest head clause ("No beneficiary numbers were available.").
_SCAFFOLD_FROM_GAP_RE = re.compile(
    r"\s+from\s+gap\s+answers?\s+" + _COLON_ID,
    re.IGNORECASE,
)
# "because <id> was marked <enum>" -> "because the <human> could not be provided".
_SCAFFOLD_BECAUSE_MARKED_RE = re.compile(
    r"because\s+(" + _COLON_ID + r")\s+was\s+marked\s+(" + _ENUM_RAW + r")",
    re.IGNORECASE,
)

_NAMESPACE_WORDS = frozenset(_DOTTED_NAMESPACES) | {"lines"}
_FALLBACK_LABEL = "the requested information"


def humanize_identifier(token: str) -> str:
    """Plain-English label for an internal identifier token (no identifier left)."""
    raw = token.strip()
    if ":" in raw:
        segment = raw.split(":")[-1]
    elif "." in raw:
        parts = [p for p in raw.split(".") if p and p not in _NAMESPACE_WORDS]
        segment = " ".join(parts) if parts else raw.split(".")[-1]
    else:
        segment = raw
    label = segment.replace("_", " ").strip()
    return label or _FALLBACK_LABEL


def _enum_phrase(token: str) -> str:
    return _ENUM_PHRASES.get(token.lower(), token.replace("_", " "))


def _cleanup_whitespace_and_punct(text: str) -> str:
    # Remove spaces left before punctuation by scaffold collapse.
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    # Collapse doubled punctuation introduced by a dropped tail (e.g. " ..").
    text = re.sub(r"([.,;])\1+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def redact_internal_identifiers(text: str) -> str:
    """Strip/translate every internal identifier while preserving honest meaning.

    Safe to call on any NGO-facing string, on any input. Idempotent.
    """
    if not text:
        return text

    cleaned = _BRACKET_RE.sub(" ", text)
    cleaned = _ARCHETYPE_RE.sub("", cleaned)

    # 1. Recognized scaffolds -> clean collapse (strip tail to honest head clause).
    cleaned = _SCAFFOLD_FROM_GAP_RE.sub("", cleaned)
    cleaned = _SCAFFOLD_BECAUSE_MARKED_RE.sub(
        lambda m: f"because the {humanize_identifier(m.group(1))} {_enum_phrase(m.group(2))}",
        cleaned,
    )

    # 2. Fail-safe: in-place human-label substitution for every remaining
    #    identifier. Never deletes a clause, never leaves an identifier.
    cleaned = _COLON_ID_RE.sub(lambda m: humanize_identifier(m.group(0)), cleaned)
    cleaned = _DOTTED_ID_RE.sub(lambda m: humanize_identifier(m.group(0)), cleaned)
    cleaned = _ENUM_RE.sub(lambda m: _enum_phrase(m.group(0)), cleaned)

    return _cleanup_whitespace_and_punct(cleaned)
