"""Gate 2 — persist human gap answers/skips and unlock when all E3 gaps are addressed."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError, ForbiddenError, NotFoundError
from app.reports.gap.gap_answer import (
    GAP_ANSWER_DISPOSITION_ANSWERED,
    GAP_ANSWER_DISPOSITION_SKIPPED,
    HUMAN_GAP_ANSWER_SOURCE,
    is_gap_answer_resolved,
)
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate_preconditions import (
    require_gap_analysis,
    require_gate1_confirmed,
)

logger = logging.getLogger("reports.services.gate2_gap_answers")


def re_enqueue_gate2_job(db: Session, *, donor_report_id: uuid.UUID) -> ReportJob | None:
    """Re-queue the awaiting Gate 2 job after full gap-answer confirmation."""
    from app.reports.models.enums import ReportJobStage, ReportJobStatus
    from app.reports.models.report_job import ReportJob

    candidates = (
        db.query(ReportJob)
        .filter(
            ReportJob.donor_report_id == donor_report_id,
            ReportJob.status == ReportJobStatus.AWAITING_HUMAN.value,
            ReportJob.stage == ReportJobStage.SYNTHESISE.value,
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
        "gate2_re_enqueue donor_report_id=%s job_id=%s",
        donor_report_id,
        job.id,
    )
    return job


def _persisted_answer(
    response: Gate2GapResponseInput,
    *,
    responded_at: datetime,
) -> dict[str, Any]:
    responded_iso = responded_at.isoformat()
    if response.disposition == GAP_ANSWER_DISPOSITION_SKIPPED:
        return {
            "disposition": GAP_ANSWER_DISPOSITION_SKIPPED,
            "skip_reason": response.skip_reason,
            "answer_text": None,
            "responded_at": responded_iso,
            "provenance": None,
            "source_label": HUMAN_GAP_ANSWER_SOURCE,
            "source_document_id": None,
        }
    text = response.answer_text.strip() if response.answer_text else ""
    return {
        "disposition": GAP_ANSWER_DISPOSITION_ANSWERED,
        "answer_text": text,
        "skip_reason": None,
        "responded_at": responded_iso,
        "provenance": {
            "source": HUMAN_GAP_ANSWER_SOURCE,
            "excerpt": text,
        },
        "source_label": HUMAN_GAP_ANSWER_SOURCE,
        "source_document_id": None,
    }


def _remaining_gaps(
    surfaced: list[dict[str, Any]],
    gap_answers: dict[str, Any],
) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for gap in surfaced:
        item_key = gap.get("item_key")
        if not item_key:
            continue
        entry = gap_answers.get(item_key)
        if not is_gap_answer_resolved(entry):
            remaining.append(gap)
    return remaining


def submit_gate2_gap_responses(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    responses: dict[str, Gate2GapResponseInput],
) -> dict[str, Any]:
    """Merge final gap answers/skips; set gate2_confirmed_at when every E3 gap is addressed."""
    from app.reports.models.donor_report import DonorReport

    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise NotFoundError(
            error_code="DONOR_REPORT_NOT_FOUND",
            message=f"Donor report {donor_report_id} not found",
            status_code=404,
        )
    if report.user_id != user_id:
        raise ForbiddenError(
            error_code="FORBIDDEN",
            message="Forbidden",
            status_code=403,
        )

    require_gate1_confirmed(report.knowledge_bank_json)
    surfaced = require_gap_analysis(report.gap_analysis_json)
    surfaced_keys = {
        str(g["item_key"]) for g in surfaced if g.get("item_key")
    }

    unknown = sorted(set(responses) - surfaced_keys)
    if unknown:
        raise DomainError(
            error_code="GATE2_UNKNOWN_GAP_KEYS",
            message="One or more responses reference gaps not surfaced by E3",
            status_code=422,
            details={"unknown_item_keys": unknown},
        )

    kb = dict(report.knowledge_bank_json or {})
    gap_answers = dict(kb.get("gap_answers") or {})
    now = datetime.now(timezone.utc)

    for item_key, response in responses.items():
        gap_answers[item_key] = _persisted_answer(response, responded_at=now)

    kb["gap_answers"] = gap_answers
    kb.pop("gate2_confirmed_at", None)

    remaining = _remaining_gaps(surfaced, gap_answers)
    gate2_unlocked = len(remaining) == 0
    if gate2_unlocked:
        kb["gate2_confirmed_at"] = now.isoformat()

    report.knowledge_bank_json = kb
    db.add(report)
    if gate2_unlocked:
        re_enqueue_gate2_job(db, donor_report_id=donor_report_id)
    db.commit()
    db.refresh(report)

    logger.info(
        "gate2_gap_responses donor_report_id=%s unlocked=%s remaining=%d",
        donor_report_id,
        gate2_unlocked,
        len(remaining),
    )

    return {
        "donor_report_id": donor_report_id,
        "gate2_confirmed_at": kb.get("gate2_confirmed_at"),
        "gate2_unlocked": gate2_unlocked,
        "gap_answers": gap_answers,
        "remaining_gaps": remaining,
    }
