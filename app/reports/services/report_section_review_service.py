"""Gate 3 section review — accept flags, accept sections, edit prose (P0-2)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError, NotFoundError
from app.reports.models.enums import ReportJobStage, ReportJobStatus
from app.reports.models.report_job import ReportJob
from app.reports.schemas.content_json_v1 import compute_generation_summary_from_sections
from app.reports.services.gate_preconditions import require_gate2_confirmed
from app.reports.services.report_access import get_owned_donor_report

from app.reports.services.section_prose import has_non_empty_prose

logger = logging.getLogger("reports.services.report_section_review")


def _latest_job(db: Session, donor_report_id: uuid.UUID) -> ReportJob | None:
    return (
        db.query(ReportJob)
        .filter(ReportJob.donor_report_id == donor_report_id)
        .order_by(ReportJob.started_at.desc().nullslast(), ReportJob.id.desc())
        .first()
    )


def _critique_completed(db: Session, donor_report_id: uuid.UUID) -> bool:
    job = _latest_job(db, donor_report_id)
    if job is None:
        return False
    critique = (job.agent_trace_json or {}).get("stages", {}).get("critique") or {}
    return critique.get("action") == "critique_completed"


def _validate_gate3_review_eligible(
    db: Session,
    *,
    report,
    donor_report_id: uuid.UUID,
) -> None:
    kb = report.knowledge_bank_json or {}
    if kb.get("gate3_confirmed_at"):
        raise DomainError(
            error_code="GATE3_ALREADY_CONFIRMED",
            message="Gate 3 has already been confirmed for this report",
            status_code=409,
        )
    require_gate2_confirmed(kb)

    job = _latest_job(db, donor_report_id)
    if job is None:
        raise DomainError(
            error_code="GATE3_REVIEW_NOT_READY",
            message="No report job exists for Gate 3 review",
            status_code=409,
        )

    if job.stage == ReportJobStage.CRITIQUE.value and job.status == ReportJobStatus.AWAITING_HUMAN.value:
        raise DomainError(
            error_code="CRITIQUE_NOT_COMPLETED",
            message="Run the fact-safety critic before reviewing sections",
            status_code=409,
        )

    if not (job.stage == ReportJobStage.EXPORT.value and job.status == ReportJobStatus.AWAITING_HUMAN.value):
        raise DomainError(
            error_code="GATE3_REVIEW_NOT_READY",
            message="Report is not awaiting Gate 3 review",
            status_code=409,
        )

    if not _critique_completed(db, donor_report_id):
        raise DomainError(
            error_code="CRITIQUE_NOT_COMPLETED",
            message="Fact-safety critic must complete before Gate 3 review",
            status_code=409,
        )


def _find_section(content_json: dict[str, Any], section_key: str) -> dict[str, Any] | None:
    for section in content_json.get("sections") or []:
        if isinstance(section, dict) and section.get("section_key") == section_key:
            return section
    return None


def _section_has_unaccepted_blocks(section: dict[str, Any]) -> bool:
    for flag in section.get("critic_flags") or []:
        if (
            isinstance(flag, dict)
            and flag.get("severity") == "BLOCK"
            and not flag.get("accepted")
        ):
            return True
    return False


def _apply_flag_acceptances(
    section: dict[str, Any],
    claim_texts: list[str],
) -> int:
    accepted_count = 0
    now = datetime.now(timezone.utc).isoformat()
    claims = set(claim_texts)
    flags = section.get("critic_flags") or []
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        if flag.get("claim_text") not in claims:
            continue
        if not flag.get("accepted"):
            flag["accepted"] = True
            flag["accepted_at"] = now
            accepted_count += 1
    return accepted_count


def patch_report_section(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    section_key: str,
    content_text: str | None = None,
    accept_critic_flags: list[str] | None = None,
    accept_section: bool = False,
) -> dict[str, Any]:
    """Patch one section during Gate 3 review."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    _validate_gate3_review_eligible(db, report=report, donor_report_id=donor_report_id)

    content_json = dict(report.content_json or {})
    section = _find_section(content_json, section_key)
    if section is None:
        raise NotFoundError(
            error_code="SECTION_NOT_FOUND",
            message=f"Section {section_key!r} not found",
            status_code=404,
        )

    if accept_critic_flags:
        _apply_flag_acceptances(section, accept_critic_flags)

    if content_text is not None:
        content = dict(section.get("content") or {})
        content["text"] = content_text
        section["content"] = content
        section["human_edited"] = True
        section["last_edited_at"] = datetime.now(timezone.utc).isoformat()

    if accept_section:
        if section.get("generation_status") == "FAILED":
            raise DomainError(
                error_code="GATE3_SECTION_NOT_ACCEPTABLE",
                message="Cannot accept a FAILED section",
                status_code=422,
            )
        if not has_non_empty_prose(section):
            raise DomainError(
                error_code="GATE3_SECTION_EMPTY_PROSE",
                message="Cannot accept a section with empty prose",
                status_code=422,
            )
        if _section_has_unaccepted_blocks(section):
            raise DomainError(
                error_code="GATE3_UNACCEPTED_BLOCKS",
                message="Accept or resolve all BLOCK critic flags before accepting the section",
                status_code=422,
            )
        section["generation_status"] = "ACCEPTED"

    warnings = list((content_json.get("generation_summary") or {}).get("warnings") or [])
    content_json["generation_summary"] = compute_generation_summary_from_sections(
        content_json.get("sections") or [],
        warnings=warnings,
    )
    report.content_json = content_json
    db.add(report)
    db.commit()
    db.refresh(report)
    db.refresh(report, attribute_names=["funder_report_template"])
    logger.info(
        "section_patched donor_report_id=%s section_key=%s accept_section=%s",
        donor_report_id,
        section_key,
        accept_section,
    )
    return report


def accept_all_sections_for_gate3(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Bulk accept all sections and BLOCK flags (Gate 3 shortcut)."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    _validate_gate3_review_eligible(db, report=report, donor_report_id=donor_report_id)

    content_json = dict(report.content_json or {})
    now = datetime.now(timezone.utc).isoformat()
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        status = section.get("generation_status")
        if status == "FAILED":
            raise DomainError(
                error_code="GATE3_SECTION_NOT_ACCEPTABLE",
                message="Cannot accept all while FAILED sections remain",
                status_code=422,
                details={"section_key": section.get("section_key")},
            )
        if not has_non_empty_prose(section):
            raise DomainError(
                error_code="GATE3_SECTION_EMPTY_PROSE",
                message="Cannot accept all while sections have empty prose",
                status_code=422,
                details={"section_key": section.get("section_key")},
            )
        section["generation_status"] = "ACCEPTED"
        for flag in section.get("critic_flags") or []:
            if isinstance(flag, dict):
                flag["accepted"] = True
                flag["accepted_at"] = now

    warnings = list((content_json.get("generation_summary") or {}).get("warnings") or [])
    content_json["generation_summary"] = compute_generation_summary_from_sections(
        content_json.get("sections") or [],
        warnings=warnings,
    )
    report.content_json = content_json
    db.add(report)
    db.commit()
    db.refresh(report)
    db.refresh(report, attribute_names=["funder_report_template"])
    return report
