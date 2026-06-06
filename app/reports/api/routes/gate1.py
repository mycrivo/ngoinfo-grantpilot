"""Gate 1 — human confirmation of reconciled knowledge bank."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.reports.schemas.gate1_confirmation import (
    Gate1ConfirmRequest,
    Gate1ConfirmResponse,
)
from app.reports.services.gate1_confirmation_service import confirm_gate1

router = APIRouter(tags=["reports"])


@router.post(
    "/api/reports/{donor_report_id}/knowledge-bank/gate1/confirm",
    response_model=Gate1ConfirmResponse,
)
def confirm_knowledge_bank_gate1(
    donor_report_id: uuid.UUID,
    body: Gate1ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Gate1ConfirmResponse:
    persisted = confirm_gate1(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
        knowledge_bank_json=body.knowledge_bank_json,
    )
    gate1_at = persisted.get("gate1_confirmed_at")
    if not gate1_at:
        raise RuntimeError("gate1_confirmed_at missing after confirm")
    return Gate1ConfirmResponse(
        donor_report_id=donor_report_id,
        knowledge_bank_json=persisted,
        gate1_confirmed_at=str(gate1_at),
    )
