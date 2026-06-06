"""Shared donor-report ownership checks for M&E routes."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.reports.models.donor_report import DonorReport


def get_owned_donor_report(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> DonorReport:
    report = db.get(DonorReport, donor_report_id)
    if report is None or report.user_id != user_id:
        raise NotFoundError(
            error_code="DONOR_REPORT_NOT_FOUND",
            message=f"Donor report {donor_report_id} not found",
            status_code=404,
        )
    return report
