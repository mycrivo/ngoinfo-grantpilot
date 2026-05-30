"""Shared donor-report ownership checks for M&E routes."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.reports.models.donor_report import DonorReport


def get_owned_donor_report(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DonorReport:
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
    return report
