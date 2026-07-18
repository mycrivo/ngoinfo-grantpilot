"""Gap/compliance agent (E3) output schema — persisted to donor_reports.gap_analysis_json."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GAP_COMPLIANCE_VERSION = "1.0.0"
GAP_AGENT_NAME = "gap_compliance_agent"

GapSeverity = Literal["required", "recommended"]
RequirementOwner = Literal["ngo", "funder"]
RequirementType = Literal["data", "narrative", "funder_supplied"]
SuggestedAction = Literal["confirm_existing", "provide", "skip"]
ReadinessBasis = Literal["ngo_data", "post_draft"]


class GapComplianceGapItem(BaseModel):
    item_key: str = Field(min_length=1)
    section_key: str = Field(min_length=1)
    section_label: str = Field(min_length=1)
    required_item_type: Literal["indicator", "table", "section"]
    required_item_ref: str = Field(min_length=1)
    severity: GapSeverity = "required"
    question: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    owner: RequirementOwner | None = "ngo"
    requirement_type: RequirementType | None = "data"
    suggested_action: SuggestedAction | None = None


class GapComplianceAgentTrace(BaseModel):
    model_used: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated: bool | None = None
    cost_usd: float | None = None
    attempt_count: int | None = None


class GapComplianceOutput(BaseModel):
    schema_version: str = GAP_COMPLIANCE_VERSION
    open_items_count: int = Field(ge=0, default=0)
    ready_for_gate2: bool = False
    gaps: list[GapComplianceGapItem] = Field(default_factory=list)
    readiness_basis: ReadinessBasis = "ngo_data"


class GapCompliancePersistedEnvelope(BaseModel):
    """Shape stored on donor_reports.gap_analysis_json."""

    schema_version: str = GAP_COMPLIANCE_VERSION
    gap_agent: str = GAP_AGENT_NAME
    analyzed_at: datetime | None = None
    report_context: dict[str, Any] = Field(default_factory=lambda: {"report_type": "annual"})
    structured: GapComplianceOutput
    agent_trace: GapComplianceAgentTrace | None = None
    error: str | None = None


class GapComplianceLLMGap(BaseModel):
    item_key: str
    section_key: str
    section_label: str
    required_item_type: Literal["indicator", "table", "section"]
    required_item_ref: str
    severity: GapSeverity = "required"
    question: str
    rationale: str


class GapComplianceLLMOutput(BaseModel):
    readiness_score: int = Field(ge=0, le=100)
    gaps: list[GapComplianceLLMGap] = Field(default_factory=list)


def envelope_to_gap_analysis_json(envelope: GapCompliancePersistedEnvelope) -> dict[str, Any]:
    data = envelope.structured.model_dump(mode="json")
    data["schema_version"] = envelope.schema_version
    data["gap_agent"] = envelope.gap_agent
    data["analyzed_at"] = (
        envelope.analyzed_at.isoformat() if envelope.analyzed_at else None
    )
    data["report_context"] = envelope.report_context
    if envelope.agent_trace:
        data["agent_trace"] = envelope.agent_trace.model_dump(mode="json")
    if envelope.error:
        data["error"] = envelope.error
    return data


def validate_gap_compliance_output(
    output: GapComplianceOutput,
    *,
    allowed_item_keys: set[str],
) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for gap in output.gaps:
        if gap.item_key not in allowed_item_keys:
            errors.append(f"gap item_key {gap.item_key!r} not in template checklist")
        identity = (gap.section_key, gap.required_item_type, gap.required_item_ref)
        if identity in seen:
            errors.append(f"duplicate gap identity {identity!r}")
        seen.add(identity)
        if not gap.question.strip():
            errors.append(f"gap {gap.item_key!r} missing question")
    # open_items_count counts every emitted gap (data + D-053 elevated narrative).
    if output.open_items_count != len(output.gaps):
        errors.append(
            f"open_items_count {output.open_items_count} != gap count {len(output.gaps)}"
        )
    if output.open_items_count == 0 and output.gaps:
        errors.append("open_items_count 0 incompatible with non-empty gaps")
    return errors
