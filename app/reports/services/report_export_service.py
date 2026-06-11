"""Stage H — render content_json to .docx, persist to R2, update report status."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.errors import DomainError, ForbiddenError
from app.models.ngo_profile import NGOProfile
from app.services.quota_service import charge_report_on_first_complete
from app.reports.export.docx_renderer import build_export_filename, render_donor_report_docx
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DonorReportStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.services.document_storage_service import (
    DocumentStorageError,
    DocumentStorageService,
)
from app.reports.services.gate_preconditions import require_gate3_confirmed

logger = logging.getLogger("reports.services.report_export")

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class ReportExportServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class StorageProtocol(Protocol):
    def upload_bytes(self, key: str, data: bytes, content_type: str) -> None: ...
    def fetch_bytes(self, key: str) -> bytes: ...

    @staticmethod
    def build_storage_ref(user_id, report_id, filename: str) -> str: ...


@dataclass(frozen=True)
class ReportExportResult:
    storage_ref: str
    filename: str
    render_mode: str
    template_version: int
    bytes_written: int


def export_and_persist(
    db: Session,
    donor_report_id,
    *,
    storage: StorageProtocol | None = None,
) -> ReportExportResult:
    """Render docx, upload to object storage, persist content_json.export, set COMPLETE."""
    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise ReportExportServiceError(
            "STOP_REPORT_NOT_FOUND",
            f"Donor report {donor_report_id} not found",
        )

    try:
        require_gate3_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise ReportExportServiceError("STOP_GATE3", exc.message) from exc

    content_json = dict(report.content_json or {})
    sections = content_json.get("sections") or []
    if not sections:
        raise ReportExportServiceError(
            "STOP_NO_CONTENT",
            "content_json has no sections to export",
        )

    template = db.get(FunderReportTemplate, report.funder_report_template_id)
    if template is None:
        raise ReportExportServiceError(
            "STOP_TEMPLATE_NOT_FOUND",
            "Funder template not found",
        )

    report.status = DonorReportStatus.GENERATING.value
    db.add(report)
    db.commit()
    db.refresh(report)

    store = storage or DocumentStorageService()

    try:
        profile = (
            db.query(NGOProfile).filter(NGOProfile.user_id == report.user_id).one_or_none()
        )
        ngo_name = profile.organization_name if profile else "Organisation"
        generated_at = datetime.now(timezone.utc)
        docx_bytes, render_mode = render_donor_report_docx(
            content_json=content_json,
            template_sections=template.report_sections_json or [],
            format_rules_json=template.format_rules_json or {},
            terminology_map_json=template.terminology_map_json or {},
            docx_template_ref=template.docx_template_ref,
            reporting_period_start=report.reporting_period_start.isoformat(),
            reporting_period_end=report.reporting_period_end.isoformat(),
            funder_name=template.funder_name,
            template_name=template.template_name,
            ngo_name=ngo_name,
            generated_at=generated_at,
            knowledge_bank_json=report.knowledge_bank_json or {},
            gap_analysis_json=report.gap_analysis_json or {},
        )
        filename = build_export_filename(
            funder_name=template.funder_name,
            template_name=template.template_name,
            reporting_period_start=report.reporting_period_start.isoformat(),
            reporting_period_end=report.reporting_period_end.isoformat(),
        )
        storage_ref = DocumentStorageService.build_storage_ref(
            report.user_id,
            report.id,
            filename,
        )
        old_export_ref = str(
            ((report.content_json or {}).get("export") or {}).get("storage_ref") or ""
        )
        store.upload_bytes(storage_ref, docx_bytes, DOCX_CONTENT_TYPE)
        if old_export_ref and old_export_ref != storage_ref:
            try:
                store.delete_object(old_export_ref)
            except DocumentStorageError as exc:
                raise ReportExportServiceError(
                    "STOP_EXPORT_STORAGE_CLEANUP",
                    exc.message,
                ) from exc

        generated_at = generated_at.isoformat()
        content_json["export"] = {
            "storage_ref": storage_ref,
            "filename": filename,
            "content_type": DOCX_CONTENT_TYPE,
            "generated_at": generated_at,
            "template_version": int(template.version or 1),
            "render_mode": render_mode,
        }
        report.content_json = content_json
        charge_report_on_first_complete(
            db, report.user_id, report.id, commit=False
        )
        report.status = DonorReportStatus.COMPLETE.value
        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(
            "report_export complete donor_report_id=%s storage_ref=%s mode=%s bytes=%d",
            donor_report_id,
            storage_ref,
            render_mode,
            len(docx_bytes),
        )
        return ReportExportResult(
            storage_ref=storage_ref,
            filename=filename,
            render_mode=render_mode,
            template_version=int(template.version or 1),
            bytes_written=len(docx_bytes),
        )
    except ForbiddenError:
        db.rollback()
        report = db.get(DonorReport, donor_report_id)
        if report is not None:
            report.status = DonorReportStatus.GENERATING.value
            db.add(report)
            db.commit()
        raise
    except Exception as exc:
        report.status = DonorReportStatus.DEGRADED.value
        db.add(report)
        db.commit()
        if isinstance(exc, ReportExportServiceError):
            raise
        raise ReportExportServiceError(
            "STOP_EXPORT_FAILED",
            str(exc),
        ) from exc


def fetch_export_bytes(
    report: DonorReport,
    *,
    storage: StorageProtocol | None = None,
) -> tuple[bytes, dict[str, Any]]:
    export_meta = (report.content_json or {}).get("export") or {}
    storage_ref = export_meta.get("storage_ref")
    if not storage_ref:
        raise DomainError(
            error_code="EXPORT_NOT_FOUND",
            message="No exported document is available for this report",
            status_code=404,
        )
    store = storage or DocumentStorageService()
    return store.fetch_bytes(str(storage_ref)), export_meta
