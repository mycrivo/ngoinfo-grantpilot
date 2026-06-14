"""F2 fact-safety critic — persist per-section flags into content_json."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.agents.fact_safety_critic import (
    FactSafetyCriticError,
    run_qualitative_fact_safety_critic,
)
from app.reports.knowledge.confirmed_kb import (
    build_confirmed_kb_view,
    non_citable_evidence_refs,
)
from app.reports.knowledge.qualitative_kb_scope import (
    build_qualitative_kb_view,
    serialize_qualitative_kb_for_critic,
)
from app.reports.models.donor_report import DonorReport
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.schemas.qualitative_critic_v1 import (
    fence_flag_dict,
    qualitative_flag_from_specific,
)
from app.reports.services.gate_preconditions import require_gate2_confirmed
from app.reports.services.numeric_fact_verifier import (
    numeric_flag_to_critic_dict,
    verify_section_numerics,
)
from app.reports.services.section_prose import has_non_empty_prose

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
    empty_content_skipped: int = 0


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


def _aggregate_fact_safety_status(
    *,
    flags: list[dict[str, Any]],
    qualitative_status: str,
    qualitative_failed: bool,
) -> str:
    """UNVERIFIED on qualitative failure is fail-closed — blocks human review gate."""
    if qualitative_failed:
        return "UNVERIFIED"
    block_flags = [
        f
        for f in flags
        if isinstance(f, dict) and f.get("severity") == "BLOCK" and not f.get("accepted")
    ]
    if block_flags:
        return "FLAGGED"
    if qualitative_status == "FLAGGED":
        return "FLAGGED"
    return "VERIFIED"


def _unverified_section_flag(*, reason: str) -> dict[str, Any]:
    return {
        "claim_text": "[section unverified]",
        "severity": "BLOCK",
        "reason": reason,
        "source_required": True,
        "accepted": False,
        "accepted_at": None,
        "source_ref": None,
        "verification_path": "qualitative_llm",
    }


async def critique_and_persist(
    db: Session,
    donor_report_id,
    *,
    query_fn_critic: Any | None = None,
) -> ReportFactSafetyStageResult:
    """Run F2 split critic on all sections and overwrite critic_flags in content_json."""
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
    kb_view = build_confirmed_kb_view(kb)

    # Package A: load template section declarations so the critic's per-section fact
    # view mirrors synthesis's (source routing + declared-needs resolve identically).
    template = db.get(FunderReportTemplate, report.funder_report_template_id)
    template_sections = list((template.report_sections_json or []) if template else [])
    template_by_key = {
        str(s.get("section_key")): s
        for s in template_sections
        if isinstance(s, dict) and s.get("section_key")
    }

    verified = flagged = unverified = skipped = empty_content_skipped = 0

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

        if gen_status != "GENERATED":
            section["critic_flags"] = []
            skipped += 1
            continue

        if not has_non_empty_prose(section):
            section["critic_flags"] = [
                _unverified_section_flag(reason="section_prose_empty")
            ]
            section["generation_status"] = "AWAITING_REVIEW"
            empty_content_skipped += 1
            unverified += 1
            continue

        evidence_used = list(content.get("evidence_used") or [])
        fence_blocked = non_citable_evidence_refs(evidence_used, kb)
        fence_flags = [
            fence_flag_dict(
                ref=ref,
                reason="Reference is not citable under verification_status fence (P1-3)",
            )
            for ref in fence_blocked
        ]
        admissible_evidence = [ref for ref in evidence_used if ref not in fence_blocked]

        if fence_flags and not admissible_evidence:
            _apply_critic_result_to_section(
                section,
                flags=fence_flags,
                fact_safety_status="FLAGGED",
            )
            flagged += 1
            continue

        claims = list(content.get("claims") or [])
        citation_mode = content.get("citation_mode")
        numeric_flags = verify_section_numerics(
            section_text=section_text,
            claims=claims,
            citation_mode=citation_mode,
            kb_view=kb_view,
        )
        numeric_dicts = [numeric_flag_to_critic_dict(f) for f in numeric_flags]

        routing_section = template_by_key.get(section_key, section)
        qual_view = build_qualitative_kb_view(
            kb,
            section=routing_section,
            report_sections=template_sections or None,
        )
        scoped_kb = serialize_qualitative_kb_for_critic(qual_view)

        qualitative_failed = False
        qualitative_status = "VERIFIED"
        qual_flag_dicts: list[dict[str, Any]] = []

        try:
            qual_result = await run_qualitative_fact_safety_critic(
                section_key=section_key,
                section_label=section_label,
                section_text=section_text,
                scoped_citable_kb=scoped_kb,
                query_fn=query_fn_critic,
            )
            qualitative_status = qual_result.output.fact_safety_status
            qual_flag_dicts = [
                qualitative_flag_from_specific(item)
                for item in qual_result.output.specifics
                if item.status == "FLAGGED"
            ]
        except FactSafetyCriticError as exc:
            logger.warning(
                "qualitative_fact_safety_critic fail-closed section=%s code=%s",
                section_key,
                exc.code,
            )
            qualitative_failed = True
            qual_flag_dicts = [_unverified_section_flag(reason=exc.message)]

        flags = fence_flags + numeric_dicts + qual_flag_dicts
        status = _aggregate_fact_safety_status(
            flags=flags,
            qualitative_status=qualitative_status,
            qualitative_failed=qualitative_failed,
        )

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
        empty_content_skipped=empty_content_skipped,
    )
