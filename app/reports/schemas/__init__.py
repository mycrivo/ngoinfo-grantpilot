"""M&E module JSON schemas — stable contracts for agent outputs."""

from app.reports.schemas.proposal_extraction_v1 import (
    PROPOSAL_EXTRACTION_SCHEMA_VERSION,
    ExtractedActivity,
    ExtractedIndicator,
    ExtractedObjective,
    ExtractionItemStatus,
    ExtractionOutcome,
    LogframeLevel,
    ProposalAgentTrace,
    ProposalExtractedEnvelope,
    ProposalExtractionOutput,
    ProposalExtractionSummary,
    SourceProvenance,
    TargetValue,
)

__all__ = [
    "PROPOSAL_EXTRACTION_SCHEMA_VERSION",
    "ExtractedActivity",
    "ExtractedIndicator",
    "ExtractedObjective",
    "ExtractionItemStatus",
    "ExtractionOutcome",
    "LogframeLevel",
    "ProposalAgentTrace",
    "ProposalExtractedEnvelope",
    "ProposalExtractionOutput",
    "ProposalExtractionSummary",
    "SourceProvenance",
    "TargetValue",
]
