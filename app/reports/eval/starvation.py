"""PASS-BY-STARVATION determination from bundle stage presence (D-067)."""

from __future__ import annotations

from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_EXPORT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)

# Which upstream stage must be present for an assertion family to be meaningfully tested.
REQUIRED_STAGE_BY_FAMILY: dict[str, str] = {
    "l1_fact_ledger": STAGE_KNOWLEDGE_BANK,
    "l2_conflicts": STAGE_KNOWLEDGE_BANK,
    "l3_gaps": STAGE_GAPS,
    "l4_report": STAGE_CONTENT,
    "l5_forbidden_content": STAGE_CONTENT,
    "l5_forbidden_gaps": STAGE_GAPS,
    "l5_forbidden_export": STAGE_EXPORT,
}


def stage_present_for_family(bundle: ScoreableBundle, family: str) -> bool:
    stage = REQUIRED_STAGE_BY_FAMILY.get(family)
    if stage is None:
        return True
    return bundle.has_stage(stage)


def is_starved(bundle: ScoreableBundle, family: str) -> bool:
    """True when the invariant would only 'pass' because upstream data never arrived."""
    return not stage_present_for_family(bundle, family)
