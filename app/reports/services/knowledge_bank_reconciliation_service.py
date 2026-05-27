"""Persist E1 reconciliation results to donor_reports.knowledge_bank_json."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from sqlalchemy.orm import Session

from app.reports.agents.knowledge_bank_reconciler import (
    AGENT_NAME,
    KnowledgeBankReconcilerError,
    KnowledgeBankReconcilerResult,
    envelope_to_knowledge_bank_json,
    reconcile_documents,
)
from app.reports.models.uploaded_document import UploadedDocument

logger = logging.getLogger("reports.services.knowledge_bank_reconciliation")

QueryFn = Callable[..., AsyncIterator[Any]]


class KnowledgeBankReconciliationServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


async def reconcile_and_persist(
    db: Session,
    donor_report_id: uuid.UUID,
    *,
    query_fn: QueryFn | None = None,
) -> KnowledgeBankReconcilerResult:
    """Run E1 reconciler and persist to donor_reports.knowledge_bank_json.

    Does not set gate1_confirmed_at (E2). Does not write content_json or
    indicator_actuals_json. Does not call extractors.
    """
    from app.reports.models.donor_report import DonorReport

    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise KnowledgeBankReconciliationServiceError(
            "STOP_REPORT_NOT_FOUND",
            f"Donor report {donor_report_id} not found",
        )

    documents = (
        db.query(UploadedDocument)
        .filter(UploadedDocument.donor_report_id == donor_report_id)
        .all()
    )

    try:
        result = await reconcile_documents(documents, query_fn=query_fn)
    except KnowledgeBankReconcilerError as exc:
        report.knowledge_bank_json = {
            "reconciler_agent": AGENT_NAME,
            "error": exc.message,
        }
        db.add(report)
        db.commit()
        raise

    report.knowledge_bank_json = envelope_to_knowledge_bank_json(result.envelope)
    db.add(report)
    db.commit()
    db.refresh(report)
    return result


def reconcile_and_persist_sync(
    db: Session,
    donor_report_id: uuid.UUID,
    *,
    query_fn: QueryFn | None = None,
) -> KnowledgeBankReconcilerResult:
    import asyncio

    return asyncio.run(
        reconcile_and_persist(db, donor_report_id, query_fn=query_fn)
    )
