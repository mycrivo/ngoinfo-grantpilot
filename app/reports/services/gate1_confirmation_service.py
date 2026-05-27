"""Gate 1 — persist human-confirmed knowledge bank and unlock stamp."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError, ForbiddenError, NotFoundError
from app.reports.schemas.knowledge_bank_reconciliation_v1 import (
    validate_gate1_confirm_payload,
)

logger = logging.getLogger("reports.services.gate1_confirmation")


def confirm_gate1(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    knowledge_bank_json: dict[str, Any],
) -> dict[str, Any]:
    """Overwrite knowledge_bank_json with human final state and set gate1_confirmed_at."""
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

    payload = dict(knowledge_bank_json)
    payload.pop("gate1_confirmed_at", None)

    validation_errors = validate_gate1_confirm_payload(payload)
    if validation_errors:
        raise DomainError(
            error_code="GATE1_VALIDATION_FAILED",
            message="Knowledge bank failed Gate 1 validation",
            status_code=422,
            details={"errors": validation_errors},
        )

    confirmed_at = datetime.now(timezone.utc)
    payload["gate1_confirmed_at"] = confirmed_at.isoformat()
    report.knowledge_bank_json = payload
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        "gate1_confirmed donor_report_id=%s user_id=%s",
        donor_report_id,
        user_id,
    )
    return report.knowledge_bank_json
