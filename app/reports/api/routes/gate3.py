"""Gate 3 — human confirmation after critic review."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.schemas.gate3_confirmation import Gate3ConfirmResponse
from app.reports.services.gate3_confirmation_service import confirm_gate3

router = APIRouter(tags=["reports"])


@router.post(
    "/api/reports/{donor_report_id}/knowledge-bank/gate3/confirm",
    response_model=Gate3ConfirmResponse,
)
def confirm_gate3_review(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Gate3ConfirmResponse:
    result = confirm_gate3(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    gate3_at = result.get("gate3_confirmed_at")
    if not gate3_at:
        raise RuntimeError("gate3_confirmed_at missing after confirm")
    return Gate3ConfirmResponse(
        donor_report_id=donor_report_id,
        gate3_confirmed_at=str(gate3_at),
        knowledge_bank_json=result["knowledge_bank_json"],
    )
