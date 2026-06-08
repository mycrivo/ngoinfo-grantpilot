"""Single source of truth for systemic vs per-document extraction failures (P2)."""

from __future__ import annotations

import re

# Table B — always hard-fail regardless of message shape.
_HARD_FAIL_STOP_CODES = frozenset(
    {
        "STOP_WRONG_CLASSIFICATION",
        "STOP_DOCUMENT_NOT_FOUND",
    }
)

# Table A — per-document degrade when not systemic.
_PER_DOCUMENT_DEGRADE_STOP_CODES = frozenset(
    {
        "STOP_EMPTY_INPUT",
        "STOP_STRUCTURED_OUTPUT_FAILED",
        "STOP_NO_RESULT",
    }
)

# Shared by Table B (STOP_AGENT_ERROR + infra) and Table C (infra branch).
_INFRA_SIGNATURE_RE = re.compile(
    r"(?:\b401\b|\b403\b|\b429\b|\b5\d{2}\b|authentication|api[_ -]?key|"
    r"overloaded|connection(?:\s+(?:refused|error|reset))?|"
    r"credentials?|rate[\s-]?limit|service unavailable|endpoint|anthropic|"
    r"unauthorized|forbidden|too many requests|internal server error|"
    r"bad gateway|gateway timeout|temporarily unavailable|"
    r"document storage is not configured|missing:\s*me_documents_s3)",
    re.IGNORECASE,
)


def is_systemic_extraction_failure(
    *,
    code: str | None = None,
    message: str | None = None,
) -> bool:
    """True when failure indicates broken run/infra, not a single bad document."""
    if code in _HARD_FAIL_STOP_CODES:
        return True
    text = " ".join(part for part in (code, message) if part)
    if not text:
        return False
    return bool(_INFRA_SIGNATURE_RE.search(text))


def is_per_document_degrade_stop_code(code: str) -> bool:
    return code in _PER_DOCUMENT_DEGRADE_STOP_CODES or code == "STOP_AGENT_ERROR"
