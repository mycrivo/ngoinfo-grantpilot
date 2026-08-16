"""Read-only export: persisted production record → ScoreableBundle.

Faithful transcription only. No engine/model calls, no reconstruction, no key
aliasing or meaning authorship. Mapping authored from discovery artefact
BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08 (owner gate released).
"""

from __future__ import annotations

import copy
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.reports.eval.bundle_schema import (
    STAGE_CONTENT,
    STAGE_EXPORT,
    STAGE_GAPS,
    STAGE_KNOWLEDGE_BANK,
    ScoreableBundle,
)

# Root keys observed on knowledge_bank_json during discovery.
_OBSERVED_KB_ROOT_KEYS = frozenset(
    {
        "agent_trace",
        "conflicts",
        "facts",
        "gap_answers",
        "gate1_confirmed_at",
        "gate2_confirmed_at",
        "gate3_confirmed_at",
        "reconciled_at",
        "reconciler_agent",
        "reconciliation_outcome",
        "reconciliation_version",
        "schema_version",
        "unreadable_sources",
    }
)

# Root keys observed on gap_analysis_json during discovery.
_OBSERVED_GAP_ROOT_KEYS = frozenset(
    {
        "agent_trace",
        "analyzed_at",
        "gap_agent",
        "gaps",
        "open_items_count",
        "readiness_basis",
        "ready_for_gate2",
        "report_context",
        "schema_version",
    }
)

# Root keys observed on content_json during discovery.
_OBSERVED_CONTENT_ROOT_KEYS = frozenset(
    {
        "export",
        "generation_summary",
        "sections",
    }
)


@dataclass
class PersistedReportRecord:
    """Already-loaded production artefacts for one donor report (no I/O)."""

    report_id: str
    status: str | None = None
    version: int | None = None
    reporting_period_start: str | None = None
    reporting_period_end: str | None = None
    knowledge_bank_json: dict[str, Any] | None = None
    gap_analysis_json: dict[str, Any] | None = None
    content_json: dict[str, Any] | None = None
    indicator_actuals_json: dict[str, Any] | None = None
    agent_trace_json: dict[str, Any] | None = None
    # Optional plaintext of the already-persisted export DOCX (owner-supplied).
    export_plaintext: str | None = None


@dataclass
class BundleExportResult:
    bundle: ScoreableBundle
    observations: list[str] = field(default_factory=list)
    source_paths: dict[str, str] = field(default_factory=dict)


def _is_empty_json_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (dict, list, str)) and len(value) == 0:
        return True
    return False


def _deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def _fact_key_prefix_families(facts: dict[str, Any]) -> list[str]:
    """Surface visible key-prefix families without deciding equivalence."""
    families: set[str] = set()
    for key in facts:
        if not isinstance(key, str) or not key:
            continue
        if "." in key:
            families.add(key.split(".", 1)[0])
        else:
            families.add(key)
    return sorted(families)


def _collect_unknown_keys(
    payload: dict[str, Any] | None,
    observed: frozenset[str],
    path: str,
) -> list[str]:
    if not isinstance(payload, dict):
        return []
    unknown = sorted(set(payload.keys()) - observed)
    return [f"{path}: unobserved root key {k!r}" for k in unknown]


def _extract_model_config(
    kb: dict[str, Any] | None,
    gaps: dict[str, Any] | None,
    trace: dict[str, Any] | None,
) -> dict[str, Any]:
    """Transcribe model_used fields as persisted; do not invent config."""
    out: dict[str, Any] = {}
    if isinstance(kb, dict):
        at = kb.get("agent_trace")
        if isinstance(at, dict) and "model_used" in at:
            out["knowledge_bank.agent_trace.model_used"] = at.get("model_used")
    if isinstance(gaps, dict):
        at = gaps.get("agent_trace")
        if isinstance(at, dict) and "model_used" in at:
            out["gap_analysis.agent_trace.model_used"] = at.get("model_used")
    if isinstance(trace, dict):
        stages = trace.get("stages")
        if isinstance(stages, dict):
            for stage_name, stage_payload in stages.items():
                if not isinstance(stage_payload, dict):
                    continue
                if "model_used" in stage_payload:
                    out[f"agent_trace.stages.{stage_name}.model_used"] = stage_payload.get(
                        "model_used"
                    )
    return out


ORIGINATING_BUILD_NOT_RECOVERABLE = (
    "The commit recorded here is the commit of the exporting tool. "
    "The build which generated the report is not recoverable from the persisted record."
)


def persisted_scalar(value: Any) -> Any:
    """Transcribe a persisted scalar. Null stays absent (JSON null), never the text 'None'."""
    if value is None:
        return None
    return value


def resolve_exporting_tool_commit() -> str:
    """Best-effort HEAD SHA of the exporting tool; empty string if unavailable."""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return ""


def resolve_git_commit() -> str:
    """Alias of resolve_exporting_tool_commit (legacy name)."""
    return resolve_exporting_tool_commit()


def export_scoreable_bundle(
    record: PersistedReportRecord,
    *,
    git_commit: str | None = None,
    exported_at: str | None = None,
) -> BundleExportResult:
    """Map a persisted record into a ScoreableBundle by faithful transcription.

    Stages with nothing persisted are omitted from ``stages_present`` (absence),
    not coerced to empty containers that would look like a genuine negative.
    """
    observations: list[str] = []
    source_paths: dict[str, str] = {
        "knowledge_bank": "donor_reports.knowledge_bank_json",
        "gap_analysis": "donor_reports.gap_analysis_json",
        "content_json": "donor_reports.content_json",
        "indicator_actuals": "donor_reports.indicator_actuals_json",
        "job_trace": "report_jobs.agent_trace_json",
        "export_text": "content_json.export → persisted DOCX plaintext (optional)",
        "report_meta": "donor_reports.{status,version,reporting_period_*}",
    }

    kb_raw = record.knowledge_bank_json
    gaps_raw = record.gap_analysis_json
    content_raw = record.content_json
    indicators_raw = record.indicator_actuals_json
    trace_raw = record.agent_trace_json

    observations.extend(
        _collect_unknown_keys(kb_raw if isinstance(kb_raw, dict) else None, _OBSERVED_KB_ROOT_KEYS, "knowledge_bank_json")
    )
    observations.extend(
        _collect_unknown_keys(
            gaps_raw if isinstance(gaps_raw, dict) else None, _OBSERVED_GAP_ROOT_KEYS, "gap_analysis_json"
        )
    )
    observations.extend(
        _collect_unknown_keys(
            content_raw if isinstance(content_raw, dict) else None,
            _OBSERVED_CONTENT_ROOT_KEYS,
            "content_json",
        )
    )

    stages_present: list[str] = []
    knowledge_bank: dict[str, Any] = {}
    gap_analysis: dict[str, Any] = {}
    content_json: dict[str, Any] = {}
    job_trace: dict[str, Any] = {}
    export_text = ""

    # --- knowledge_bank ---
    if kb_raw is None or _is_empty_json_value(kb_raw):
        observations.append(
            "knowledge_bank: persisted payload absent or empty — stage omitted from stages_present"
        )
    elif not isinstance(kb_raw, dict):
        observations.append(
            f"knowledge_bank: unexpected type {type(kb_raw).__name__} — stage omitted; value not coerced"
        )
    else:
        knowledge_bank = _deep_copy(kb_raw)
        stages_present.append(STAGE_KNOWLEDGE_BANK)
        facts = knowledge_bank.get("facts")
        if isinstance(facts, dict):
            families = _fact_key_prefix_families(facts)
            if len(families) > 1:
                observations.append(
                    "knowledge_bank.facts: multiple key-prefix families visible "
                    f"({families!r}); keys transcribed exactly — not normalised, "
                    "aliased, merged, or reconciled"
                )
            observations.append(
                f"knowledge_bank.facts: object with {len(facts)} keyed records (not an array)"
            )
        elif isinstance(facts, list):
            observations.append(
                "knowledge_bank.facts: array shape (unobserved at discovery for reference run) "
                f"— transcribed as list of length {len(facts)}; not coerced to object"
            )
        elif facts is None:
            observations.append("knowledge_bank.facts: key absent")
        else:
            observations.append(
                f"knowledge_bank.facts: unexpected type {type(facts).__name__} — left as persisted"
            )

        conflicts = knowledge_bank.get("conflicts")
        if isinstance(conflicts, list):
            observations.append(
                f"knowledge_bank.conflicts: separate collection, {len(conflicts)} entries"
            )
        elif "conflicts" not in knowledge_bank:
            observations.append("knowledge_bank.conflicts: key absent")

    # --- gaps ---
    if gaps_raw is None or _is_empty_json_value(gaps_raw):
        observations.append(
            "gap_analysis: persisted payload absent or empty — stage omitted from stages_present"
        )
    elif not isinstance(gaps_raw, dict):
        observations.append(
            f"gap_analysis: unexpected type {type(gaps_raw).__name__} — stage omitted; value not coerced"
        )
    else:
        gap_analysis = _deep_copy(gaps_raw)
        stages_present.append(STAGE_GAPS)
        gap_items = gap_analysis.get("gaps")
        if isinstance(gap_items, list):
            observations.append(
                f"gap_analysis.gaps: collection of {len(gap_items)} entries "
                "(question + rationale carried as persisted; key is 'gaps', not aliased)"
            )
        elif gap_items is None and "gaps" not in gap_analysis:
            observations.append("gap_analysis.gaps: key absent")

    # --- content ---
    if content_raw is None or _is_empty_json_value(content_raw):
        observations.append(
            "content_json: persisted payload absent or empty — stage omitted from stages_present"
        )
    elif not isinstance(content_raw, dict):
        observations.append(
            f"content_json: unexpected type {type(content_raw).__name__} — stage omitted; value not coerced"
        )
    else:
        content_json = _deep_copy(content_raw)
        stages_present.append(STAGE_CONTENT)
        sections = content_json.get("sections")
        if isinstance(sections, list):
            observations.append(
                f"content_json.sections: array of {len(sections)} sections; "
                "nested content.text / content.claims (bind_status, source_refs) transcribed intact"
            )
        export_meta = content_json.get("export")
        if isinstance(export_meta, dict) and not _is_empty_json_value(export_meta):
            if STAGE_EXPORT not in stages_present:
                stages_present.append(STAGE_EXPORT)
            observations.append(
                "content_json.export: present — export stage marked present from persisted export metadata"
            )
            if export_meta.get("storage_ref"):
                observations.append(
                    "content_json.export.storage_ref: present (DOCX bytes not fetched by mapping)"
                )
        elif "export" in content_json and _is_empty_json_value(export_meta):
            observations.append(
                "content_json.export: empty object — export stage not added from metadata alone"
            )

    # --- indicator_actuals: empty at discovery → absent (not a ScoreableBundle stage) ---
    if indicators_raw is None or _is_empty_json_value(indicators_raw):
        observations.append(
            "indicator_actuals_json: empty or null — recorded as absent; "
            "not populated, inferred, or reconstructed from any other collection"
        )
    else:
        observations.append(
            "indicator_actuals_json: non-empty (unobserved non-empty at discovery) — "
            "transcribed into bundle meta only; not a ScoreableBundle stage"
        )

    # --- job trace ---
    if trace_raw is None or _is_empty_json_value(trace_raw):
        observations.append("agent_trace_json: absent or empty")
    elif isinstance(trace_raw, dict):
        job_trace = _deep_copy(trace_raw)
    else:
        observations.append(
            f"agent_trace_json: unexpected type {type(trace_raw).__name__} — not coerced"
        )

    # --- export plaintext (optional; owner supplies bytes already read) ---
    if record.export_plaintext:
        export_text = record.export_plaintext
        if STAGE_EXPORT not in stages_present:
            stages_present.append(STAGE_EXPORT)
        observations.append(
            "export_text: filled from owner-supplied plaintext of persisted export DOCX"
        )
    else:
        observations.append(
            "export_text: not supplied — left empty; mapping does not fetch or render DOCX"
        )

    commit = git_commit if git_commit is not None else resolve_exporting_tool_commit()
    ts = exported_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    report_meta = {
        "status": persisted_scalar(record.status),
        "version": persisted_scalar(record.version),
        "reporting_period_start": persisted_scalar(record.reporting_period_start),
        "reporting_period_end": persisted_scalar(record.reporting_period_end),
    }
    observations.append(
        "report_meta: transcribed as persisted on the report record; "
        "null fields recorded as absent (JSON null), never the text 'None'; "
        "any disagreement with fact-collection values is left unresolved (engine scope)"
    )

    model_config = _extract_model_config(
        knowledge_bank or None,
        gap_analysis or None,
        job_trace or None,
    )

    meta: dict[str, Any] = {
        "report_id": record.report_id,
        "exported_at": ts,
        "exporting_tool_commit": commit,
        "originating_build_limitation": ORIGINATING_BUILD_NOT_RECOVERABLE,
        "report_meta": report_meta,
        "observations": list(observations),
        "source_paths": dict(source_paths),
        "export_mapping": "bundle_export.export_scoreable_bundle",
        "discovery_artefact": (
            "docs/artefacts/me_module/audits/BUNDLE_EXPORT_DISCOVERY_dfd17248_2026-08-08.json"
        ),
    }
    if indicators_raw is not None and not _is_empty_json_value(indicators_raw):
        meta["indicator_actuals_json"] = _deep_copy(indicators_raw)

    bundle = ScoreableBundle(
        bundle_id=record.report_id,
        provenance="export",
        stages_present=list(stages_present),
        knowledge_bank=knowledge_bank,
        gap_analysis=gap_analysis,
        content_json=content_json,
        job_trace=job_trace,
        model_config=model_config,
        export_text=export_text,
        meta=meta,
    )
    return BundleExportResult(
        bundle=bundle,
        observations=observations,
        source_paths=source_paths,
    )


def bundle_to_export_dict(result: BundleExportResult) -> dict[str, Any]:
    """Serialize bundle + export provenance for an owner-local file (not for git)."""
    return {
        "bundle": result.bundle.to_dict(),
        "observations": list(result.observations),
        "source_paths": dict(result.source_paths),
    }
