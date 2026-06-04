"""Download exported donor report .docx."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.user import User
from app.reports.services.report_access import get_owned_donor_report
from app.reports.services.report_export_service import DOCX_CONTENT_TYPE, fetch_export_bytes

router = APIRouter(tags=["reports"])


@router.get("/api/reports/{donor_report_id}/export")
def download_report_export(
    donor_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    report = get_owned_donor_report(
        db,
        donor_report_id=donor_report_id,
        user_id=current_user.id,
    )
    try:
        data, export_meta = fetch_export_bytes(report)
    except DomainError as exc:
        if exc.status_code == 404:
            raise exc
        raise

    filename = str(export_meta.get("filename") or "donor-report.docx")
    content_type = str(export_meta.get("content_type") or DOCX_CONTENT_TYPE)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
