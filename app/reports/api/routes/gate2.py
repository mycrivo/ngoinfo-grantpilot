"""Gate 2 — human gap-answer intake (answer-or-skip)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.schemas.gate2_gap_answers import (
    Gate2GapAnswersRequest,
    Gate2GapAnswersResponse,
    Gate2RemainingGap,
)
from app.reports.services.gate2_gap_answer_service import submit_gate2_gap_responses

router = APIRouter(tags=["reports"])


@router.post(
    "/api/reports/{donor_report_id}/knowledge-bank/gate2/gap-responses",
    response_model=Gate2GapAnswersResponse,
)
def submit_gap_responses_gate2(
    donor_report_id: uuid.UUID,
    body: Gate2GapAnswersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Gate2GapAnswersResponse:
    result = submit_gate2_gap_responses(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
        responses=body.responses,
    )
    remaining = [
        Gate2RemainingGap(
            item_key=str(g["item_key"]),
            section_key=str(g["section_key"]),
            section_label=str(g.get("section_label") or g["section_key"]),
            required_item_type=str(g["required_item_type"]),
            required_item_ref=str(g["required_item_ref"]),
            question=str(g.get("question") or ""),
        )
        for g in result["remaining_gaps"]
    ]
    gate2_at = result.get("gate2_confirmed_at")
    return Gate2GapAnswersResponse(
        donor_report_id=donor_report_id,
        gate2_confirmed_at=str(gate2_at) if gate2_at else None,
        gate2_unlocked=bool(result["gate2_unlocked"]),
        gap_answers=result["gap_answers"],
        remaining_gaps=remaining,
    )
