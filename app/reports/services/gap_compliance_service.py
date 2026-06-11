"""Run E3 gap/compliance and persist to donor_reports.gap_analysis_json."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.reports.agents.gap_compliance_agent import (
    GapComplianceAgentError,
    GapComplianceAgentResult,
    run_gap_compliance,
)
from app.reports.schemas.gap_compliance_v1 import envelope_to_gap_analysis_json
from app.reports.services.gate_preconditions import require_gate1_confirmed

logger = logging.getLogger("reports.services.gap_compliance")

QueryFn = Callable[..., AsyncIterator[Any]]


async def run_gap_compliance_and_persist(
    db: Session,
    donor_report_id: uuid.UUID,
    *,
    report_context: dict[str, Any] | None = None,
    query_fn: QueryFn | None = None,
    model: str | None = None,
) -> GapComplianceAgentResult:
    """Enforce Gate 1, run gap agent, overwrite gap_analysis_json (idempotent re-run)."""
    from app.reports.models.donor_report import DonorReport
    from app.reports.models.funder_report_template import FunderReportTemplate

    report = db.get(DonorReport, donor_report_id)
    if report is None:
        from app.core.errors import NotFoundError

        raise NotFoundError(
            error_code="DONOR_REPORT_NOT_FOUND",
            message=f"Donor report {donor_report_id} not found",
            status_code=404,
        )

    require_gate1_confirmed(report.knowledge_bank_json)

    template = db.get(FunderReportTemplate, report.funder_report_template_id)
    if template is None:
        from app.core.errors import NotFoundError

        raise NotFoundError(
            error_code="FUNDER_TEMPLATE_NOT_FOUND",
            message=f"Funder template {report.funder_report_template_id} not found",
            status_code=404,
        )

    template_payload = {
        "funder_name": template.funder_name,
        "template_name": template.template_name,
        "report_sections_json": template.report_sections_json,
        "format_rules_json": template.format_rules_json,
        "terminology_map_json": template.terminology_map_json,
    }

    try:
        result = await run_gap_compliance(
            knowledge_bank_json=report.knowledge_bank_json,
            template_payload=template_payload,
            report_context=report_context,
            query_fn=query_fn,
            model=model,
        )
    except GapComplianceAgentError as exc:
        logger.warning(
            "gap_compliance_failed donor_report_id=%s code=%s",
            donor_report_id,
            exc.code,
        )
        raise

    report.gap_analysis_json = envelope_to_gap_analysis_json(result.envelope)
    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(
        "gap_compliance_persisted donor_report_id=%s open_items=%s gaps=%d",
        donor_report_id,
        result.envelope.structured.open_items_count,
        len(result.envelope.structured.gaps),
    )
    return result


def run_gap_compliance_and_persist_sync(
    db: Session,
    donor_report_id: uuid.UUID,
    *,
    report_context: dict[str, Any] | None = None,
    query_fn: QueryFn | None = None,
    model: str | None = None,
) -> GapComplianceAgentResult:
    import asyncio

    return asyncio.run(
        run_gap_compliance_and_persist(
            db,
            donor_report_id,
            report_context=report_context,
            query_fn=query_fn,
            model=model,
        )
    )
