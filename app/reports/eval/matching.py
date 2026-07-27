"""Value normalisation for golden↔bundle matching (D-040 / D-041 pattern).

Match by normalised value + source document — never by engine fact_key.
"""

from __future__ import annotations

import re
from typing import Any


_WS = re.compile(r"\s+")
_CURRENCY = re.compile(r"[£$€,]")


def normalise_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        # Preserve ints without trailing .0; keep meaningful floats.
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    text = str(value).strip()
    if not text:
        return None
    text = _CURRENCY.sub("", text)
    text = text.replace("%", "").strip()
    text = _WS.sub(" ", text)
    text = text.lower()
    # Collapse unicode dashes to ascii hyphen for comparison.
    text = text.replace("–", "-").replace("—", "-")
    return text


def normalise_source(source: Any) -> str | None:
    if source is None:
        return None
    text = str(source).strip().upper()
    if not text:
        return None
    # Collapse "D1, D3" / "D1 header" → primary codes set membership checks use contains.
    return _WS.sub(" ", text)


def sources_compatible(golden_source: Any, bank_source: Any) -> bool:
    """True if bank source is compatible with golden source_document codes."""
    g = normalise_source(golden_source)
    b = normalise_source(bank_source)
    if g is None and b is None:
        return True
    if g is None or b is None:
        return False
    # Golden may list "D1, D3"; bank may say "D3" or a filename containing D3.
    golden_tokens = {t.strip(" ,;") for t in re.split(r"[,/]", g) if t.strip(" ,;")}
    if not golden_tokens:
        return g in b or b in g
    return any(tok in b for tok in golden_tokens if tok.startswith("D") or tok == "DERIVED")


def values_match(golden_value: Any, bank_value: Any) -> bool:
    return normalise_value(golden_value) == normalise_value(bank_value)
