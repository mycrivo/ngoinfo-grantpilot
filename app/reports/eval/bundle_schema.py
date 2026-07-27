"""Scoreable run-bundle contract. Harness scores bundles; it does not run pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Stages the starvation logic inspects.
STAGE_KNOWLEDGE_BANK = "knowledge_bank"
STAGE_GAPS = "gaps"
STAGE_CONTENT = "content"
STAGE_EXPORT = "export"

ALL_STAGES = (
    STAGE_KNOWLEDGE_BANK,
    STAGE_GAPS,
    STAGE_CONTENT,
    STAGE_EXPORT,
)


@dataclass
class ScoreableBundle:
    """Persisted run artefacts required to score against the golden pack.

    Production path: owner-triggered export. Tests may construct synthetic bundles.
    """

    bundle_id: str
    provenance: str  # "live" | "export" | "synthetic"
    stages_present: list[str] = field(default_factory=list)
    knowledge_bank: dict[str, Any] = field(default_factory=dict)
    gap_analysis: dict[str, Any] = field(default_factory=dict)
    content_json: dict[str, Any] = field(default_factory=dict)
    job_trace: dict[str, Any] = field(default_factory=dict)
    model_config: dict[str, Any] = field(default_factory=dict)
    export_text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def has_stage(self, stage: str) -> bool:
        return stage in self.stages_present

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ScoreableBundle":
        return cls(
            bundle_id=str(raw.get("bundle_id") or raw.get("report_id") or "unknown"),
            provenance=str(raw.get("provenance") or "export"),
            stages_present=list(raw.get("stages_present") or []),
            knowledge_bank=dict(raw.get("knowledge_bank") or {}),
            gap_analysis=dict(raw.get("gap_analysis") or {}),
            content_json=dict(raw.get("content_json") or {}),
            job_trace=dict(raw.get("job_trace") or {}),
            model_config=dict(raw.get("model_config") or {}),
            export_text=str(raw.get("export_text") or ""),
            meta=dict(raw.get("meta") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "provenance": self.provenance,
            "stages_present": list(self.stages_present),
            "knowledge_bank": self.knowledge_bank,
            "gap_analysis": self.gap_analysis,
            "content_json": self.content_json,
            "job_trace": self.job_trace,
            "model_config": self.model_config,
            "export_text": self.export_text,
            "meta": self.meta,
        }
