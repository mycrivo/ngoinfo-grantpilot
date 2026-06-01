"""F2 fact-safety critic — persist per-section flags into content_json."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.agents.fact_safety_critic import (
    FactSafetyCriticError,
    resolve_cited_sources,
    run_fact_safety_critic,
)
from app.reports.gap.gap_answer import GAP_ANSWER_DISPOSITION_ANSWERED
from app.reports.models.donor_report import DonorReport
from app.reports.schemas.fact_safety_critic_v1 import (
    critic_flag_from_specific,
    unverified_section_flag,
)
from app.reports.services.gate_preconditions import require_gate2_confirmed

logger = logging.getLogger("reports.services.report_fact_safety")


class ReportFactSafetyServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ReportFactSafetyStageResult:
    section_count: int
    verified: int
    flagged: int
    unverified: int
    skipped: int
    critic_blocks: int


def _answered_gap_answers(gap_answers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, entry in (gap_answers or {}).items():
        if isinstance(entry, dict) and entry.get("disposition") == GAP_ANSWER_DISPOSITION_ANSWERED:
            out[key] = entry
    return out


def _apply_critic_result_to_section(
    section: dict[str, Any],
    *,
    flags: list[dict[str, Any]],
    fact_safety_status: str,
) -> None:
    section["critic_flags"] = flags
    if section.get("generation_status") != "GENERATED":
        return
    if fact_safety_status in ("FLAGGED", "UNVERIFIED"):
        section["generation_status"] = "AWAITING_REVIEW"
    elif fact_safety_status == "VERIFIED":
        section["generation_status"] = "GENERATED"


def _update_generation_summary(content_json: dict[str, Any]) -> None:
    sections = content_json.get("sections") or []
    summary = dict(content_json.get("generation_summary") or {})
    critic_blocks = 0
    awaiting_review = 0
    for section in sections:
        if not isinstance(section, dict):
            continue
        for flag in section.get("critic_flags") or []:
            if isinstance(flag, dict) and flag.get("severity") == "BLOCK" and not flag.get("accepted"):
                critic_blocks += 1
        if section.get("generation_status") == "AWAITING_REVIEW":
            awaiting_review += 1
    summary["critic_blocks"] = critic_blocks
    summary["awaiting_review"] = awaiting_review
    content_json["generation_summary"] = summary


async def critique_and_persist(
    db: Session,
    donor_report_id,
    *,
    query_fn_critic: Any | None = None,
) -> ReportFactSafetyStageResult:
    """Run F2 critic on all sections and overwrite critic_flags in content_json."""
    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise ReportFactSafetyServiceError(
            "STOP_REPORT_NOT_FOUND",
            f"Donor report {donor_report_id} not found",
        )

    try:
        require_gate2_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise ReportFactSafetyServiceError("STOP_GATE2", exc.message) from exc

    content_json = dict(report.content_json or {})
    sections = list(content_json.get("sections") or [])
    if not sections:
        raise ReportFactSafetyServiceError(
            "STOP_NO_CONTENT",
            "content_json has no sections to critique",
        )

    kb = report.knowledge_bank_json or {}
    facts = dict(kb.get("facts") or {})
    gap_answers = _answered_gap_answers(kb.get("gap_answers") or {})

    verified = flagged = unverified = skipped = 0

    for section in sections:
        if not isinstance(section, dict):
            continue
        gen_status = section.get("generation_status")
        section_key = str(section.get("section_key") or "")
        section_label = str(section.get("label") or section_key)
        content = section.get("content") or {}
        section_text = str(content.get("text") or "")

        if gen_status == "FAILED":
            section["critic_flags"] = []
            skipped += 1
            continue

        if gen_status != "GENERATED" or not section_text.strip():
            section["critic_flags"] = []
            skipped += 1
            continue

        evidence_used = list(content.get("evidence_used") or [])
        cited_sources = resolve_cited_sources(
            evidence_used=evidence_used,
            facts=facts,
            gap_answers=gap_answers,
        )

        try:
            result = await run_fact_safety_critic(
                section_key=section_key,
                section_label=section_label,
                section_text=section_text,
                evidence_used=evidence_used,
                cited_sources=cited_sources,
                query_fn=query_fn_critic,
            )
        except FactSafetyCriticError as exc:
            logger.warning(
                "fact_safety_critic fail-closed section=%s code=%s",
                section_key,
                exc.code,
            )
            _apply_critic_result_to_section(
                section,
                flags=[unverified_section_flag(reason=exc.message)],
                fact_safety_status="UNVERIFIED",
            )
            unverified += 1
            continue

        output = result.output
        flags = [
            critic_flag_from_specific(item)
            for item in output.specifics
            if item.status == "FLAGGED"
        ]
        status = output.fact_safety_status
        if flags and status == "VERIFIED":
            status = "FLAGGED"

        _apply_critic_result_to_section(
            section,
            flags=flags,
            fact_safety_status=status,
        )
        if status == "VERIFIED":
            verified += 1
        elif status == "FLAGGED":
            flagged += 1
        else:
            unverified += 1

    content_json["sections"] = sections
    _update_generation_summary(content_json)
    report.content_json = content_json
    db.add(report)
    db.commit()
    db.refresh(report)

    summary = content_json.get("generation_summary") or {}
    critic_blocks = int(summary.get("critic_blocks") or 0)

    logger.info(
        "report_fact_safety complete donor_report_id=%s verified=%d flagged=%d "
        "unverified=%d skipped=%d critic_blocks=%d",
        donor_report_id,
        verified,
        flagged,
        unverified,
        skipped,
        critic_blocks,
    )

    return ReportFactSafetyStageResult(
        section_count=len(sections),
        verified=verified,
        flagged=flagged,
        unverified=unverified,
        skipped=skipped,
        critic_blocks=critic_blocks,
    )
