"""Gate 3 — human review of critic flags and section acceptance."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.services.gate_preconditions import require_gate2_confirmed
from app.reports.services.report_access import get_owned_donor_report

from app.reports.services.section_prose import has_non_empty_prose

logger = logging.getLogger("reports.services.gate3_confirmation")


def _sections_not_export_ready(content_json: dict[str, Any]) -> list[str]:
    """Required sections missing non-empty prose or structured bind status."""
    blocked: list[str] = []
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        key = str(section.get("section_key") or "")
        status = section.get("generation_status")
        if status == "FAILED":
            blocked.append(key)
            continue
        if status != "ACCEPTED":
            continue
        if not has_non_empty_prose(section):
            blocked.append(key)
            continue
        content = section.get("content") or {}
        if content.get("citation_mode") == "structured":
            bind_status = content.get("structured_bind_status")
            if bind_status not in ("bound", "honest_empty", "insufficient_data"):
                blocked.append(key)
    return blocked


def re_enqueue_gate3_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    """Re-queue the awaiting Gate 3 job after human confirmation."""
    from app.reports.models.enums import ReportJobStage, ReportJobStatus
    from app.reports.models.report_job import ReportJob

    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.EXPORT.value,
        )
        .order_by(
            ReportJob.started_at.desc().nullslast(),
            ReportJob.id.desc(),
        )
        .all()
    )
    if not candidates:
        return None
    job = candidates[0]
    job.status = ReportJobStatus.QUEUED.value
    db.add(job)
    logger.info(
        "gate3_re_enqueue donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


def _unaccepted_block_flags(content_json: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        for flag in section.get("critic_flags") or []:
            if (
                isinstance(flag, dict)
                and flag.get("severity") == "BLOCK"
                and not flag.get("accepted")
            ):
                blocks.append(flag)
    return blocks


def _sections_pending_review(content_json: dict[str, Any]) -> list[str]:
    pending: list[str] = []
    for section in content_json.get("sections") or []:
        if not isinstance(section, dict):
            continue
        status = section.get("generation_status")
        if status in ("GENERATED", "AWAITING_REVIEW"):
            key = section.get("section_key")
            if key:
                pending.append(str(key))
    return pending


def confirm_gate3(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Stamp gate3_confirmed_at after human review and re-enqueue for export stage."""
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )

    require_gate2_confirmed(report.knowledge_bank_json)

    content_json = report.content_json or {}
    if not content_json.get("sections"):
        raise DomainError(
            error_code="GATE3_NO_CONTENT",
            message="Report content must exist before Gate 3 confirmation",
            status_code=409,
        )

    critique_trace = (
        _latest_job_critique_trace(db, donor_report_id) or {}
    )
    if critique_trace.get("action") != "critique_completed":
        raise DomainError(
            error_code="GATE3_CRITIQUE_INCOMPLETE",
            message="Fact-safety critic must complete before Gate 3 confirmation",
            status_code=409,
        )

    unaccepted = _unaccepted_block_flags(content_json)
    if unaccepted:
        raise DomainError(
            error_code="GATE3_UNACCEPTED_BLOCKS",
            message="All BLOCK critic flags must be accepted before Gate 3 confirmation",
            status_code=422,
            details={"unaccepted_block_count": len(unaccepted)},
        )

    pending = _sections_pending_review(content_json)
    if pending:
        raise DomainError(
            error_code="GATE3_SECTIONS_NOT_ACCEPTED",
            message="All sections must be ACCEPTED before Gate 3 confirmation",
            status_code=422,
            details={"pending_section_keys": pending},
        )

    not_ready = _sections_not_export_ready(content_json)
    if not_ready:
        raise DomainError(
            error_code="GATE3_SECTIONS_NOT_READY",
            message="Every accepted section must have non-empty prose and bind status",
            status_code=422,
            details={"section_keys": not_ready},
        )

    kb = dict(report.knowledge_bank_json or {})
    kb.pop("gate3_confirmed_at", None)
    confirmed_at = datetime.now(timezone.utc)
    kb["gate3_confirmed_at"] = confirmed_at.isoformat()
    report.knowledge_bank_json = kb
    db.add(report)
    re_enqueue_gate3_job(db, donor_report_id=donor_report_id)
    db.commit()
    db.refresh(report)

    logger.info(
        "gate3_confirmed donor_report_id=%s user_id=%s",
        donor_report_id,
        user_id,
    )
    return {
        "donor_report_id": donor_report_id,
        "gate3_confirmed_at": kb.get("gate3_confirmed_at"),
        "knowledge_bank_json": kb,
    }


def _latest_job_critique_trace(db: Session, donor_report_id: uuid.UUID) -> dict[str, Any]:
    from app.reports.models.report_job import ReportJob

    jobs = (
        db.query(ReportJob)
        .filter(ReportJob.donor_report_id == donor_report_id)
        .order_by(ReportJob.started_at.desc().nullslast(), ReportJob.id.desc())
        .all()
    )
    for job in jobs:
        stages = (job.agent_trace_json or {}).get("stages") or {}
        critique = stages.get("critique")
        if isinstance(critique, dict):
            return critique
    return {}
