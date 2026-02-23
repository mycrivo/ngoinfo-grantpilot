from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.funding_opportunity import FundingOpportunity
from app.schemas.funding_opportunities import (
    FundingOpportunityResponse,
    FundingOpportunityResponseItem,
    StandardErrorResponse,
)

router = APIRouter(prefix="/api", tags=["funding-opportunities"])


@router.get(
    "/funding-opportunities/{opportunity_id}",
    response_model=FundingOpportunityResponse,
    responses={
        401: {"model": StandardErrorResponse},
        403: {"model": StandardErrorResponse},
        404: {"model": StandardErrorResponse},
        500: {"model": StandardErrorResponse},
    },
)
def get_funding_opportunity(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _ = current_user
    opportunity = db.get(FundingOpportunity, opportunity_id)
    if not opportunity:
        raise NotFoundError(
            error_code="OPPORTUNITY_NOT_FOUND",
            message="Funding opportunity not found",
            status_code=404,
        )

    focus_areas = [
        area.strip()
        for area in (opportunity.focus_areas or "").split(",")
        if area.strip()
    ]
    status_value = (
        opportunity.status.value
        if hasattr(opportunity.status, "value")
        else str(opportunity.status)
    )
    deadline_type_value = (
        opportunity.deadline_type.value
        if hasattr(opportunity.deadline_type, "value")
        else str(opportunity.deadline_type)
    )
    applicant_type_value = (
        opportunity.applicant_type.value
        if hasattr(opportunity.applicant_type, "value")
        else str(opportunity.applicant_type)
    )

    return FundingOpportunityResponse(
        funding_opportunity=FundingOpportunityResponseItem(
            id=opportunity.id,
            title=opportunity.title,
            donor_organization=opportunity.donor_organization,
            funding_type=opportunity.funding_type,
            applicant_type=applicant_type_value,
            location_text=opportunity.location_text,
            focus_areas=focus_areas,
            deadline_type=deadline_type_value,
            application_deadline=opportunity.application_deadline,
            short_summary=opportunity.short_summary,
            source_url=opportunity.source_url,
            application_url=opportunity.application_url,
            status=status_value,
            is_active=opportunity.is_active,
            last_verified=opportunity.last_verified,
        )
    )
