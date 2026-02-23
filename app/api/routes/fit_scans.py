from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.fit_scans import (
    FitScanCreateRequest,
    FitScanListItem,
    FitScanListResponse,
    FitScanResponse,
    FitScanResponseEnvelope,
    StandardErrorResponse,
)
from app.services.fit_scan_service import FitScanService

router = APIRouter(prefix="/api", tags=["fit-scans"])


@router.post("/fit-scans", response_model=FitScanResponseEnvelope)
def create_fit_scan(
    payload: FitScanCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FitScanService(db)
    fit_scan = service.run_fit_scan(
        user=current_user, funding_opportunity_id=payload.funding_opportunity_id
    )
    return FitScanResponseEnvelope(fit_scan=_to_response(fit_scan))


@router.get("/fit-scans/{fit_scan_id}", response_model=FitScanResponseEnvelope)
def get_fit_scan(
    fit_scan_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FitScanService(db)
    fit_scan = service.get_fit_scan(user=current_user, fit_scan_id=fit_scan_id)
    return FitScanResponseEnvelope(fit_scan=_to_response(fit_scan))


@router.get(
    "/fit-scans",
    response_model=FitScanListResponse,
    responses={
        401: {"model": StandardErrorResponse},
        403: {"model": StandardErrorResponse},
        422: {"model": StandardErrorResponse},
        500: {"model": StandardErrorResponse},
    },
)
def list_fit_scans(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = FitScanService(db)
    fit_scans = service.list_fit_scans(user=current_user, limit=limit)
    return FitScanListResponse(
        fit_scans=[
            FitScanListItem(
                id=fit_scan.id,
                funding_opportunity_id=fit_scan.funding_opportunity_id,
                opportunity_title=(
                    fit_scan.funding_opportunity.title
                    if fit_scan.funding_opportunity is not None
                    else None
                ),
                overall_recommendation=fit_scan.overall_recommendation,
                model_rating=fit_scan.model_rating,
                subscores=fit_scan.subscores,
                created_at=fit_scan.created_at,
            )
            for fit_scan in fit_scans
        ]
    )


def _to_response(fit_scan) -> FitScanResponse:
    result_json = fit_scan.result_json or {}
    fit_summary = result_json.get("fit_summary", {})
    risk_flags = result_json.get("risk_flags") or []
    return FitScanResponse(
        id=fit_scan.id,
        funding_opportunity_id=fit_scan.funding_opportunity_id,
        overall_recommendation=fit_scan.overall_recommendation,
        model_rating=fit_scan.model_rating,
        subscores=fit_scan.subscores,
        primary_rationale=fit_summary.get("primary_rationale", ""),
        risk_flags=risk_flags,
        created_at=fit_scan.created_at,
    )
