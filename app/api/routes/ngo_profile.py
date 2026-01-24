from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.ngo_profile import (
    NGOProfileCompletenessResponse,
    NGOProfileCreate,
    NGOProfileRead,
    NGOProfileUpdate,
)
from app.services.profile_service import (
    create_profile,
    get_completeness,
    get_profile,
    update_profile,
)

router = APIRouter(prefix="/ngo-profile", tags=["ngo-profile"])


@router.post("", response_model=NGOProfileRead)
def create_ngo_profile(
    payload: NGOProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile = create_profile(db, current_user.id, payload)
    return NGOProfileRead(
        id=str(profile.id),
        user_id=str(profile.user_id),
        organization_name=profile.organization_name,
        country_of_registration=profile.country_of_registration,
        mission_statement=profile.mission_statement,
        focus_sectors=profile.focus_sectors,
        geographic_areas_of_work=profile.geographic_areas_of_work,
        target_groups=profile.target_groups,
        past_projects=profile.past_projects,
        year_of_establishment=profile.year_of_establishment,
        contact_person_name=profile.contact_person_name,
        contact_email=profile.contact_email,
        website=profile.website,
        full_time_staff=profile.full_time_staff,
        annual_budget_amount=profile.annual_budget_amount,
        annual_budget_currency=profile.annual_budget_currency,
        monitoring_and_evaluation_practices=profile.monitoring_and_evaluation_practices,
        funders_worked_with_before=profile.funders_worked_with_before,
        profile_status=profile.profile_status,
        completeness_score=profile.completeness_score,
        missing_fields=profile.missing_fields,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        last_completed_at=profile.last_completed_at.isoformat()
        if profile.last_completed_at
        else None,
    )


@router.get("", response_model=NGOProfileRead)
def read_ngo_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile = get_profile(db, current_user.id)
    return NGOProfileRead(
        id=str(profile.id),
        user_id=str(profile.user_id),
        organization_name=profile.organization_name,
        country_of_registration=profile.country_of_registration,
        mission_statement=profile.mission_statement,
        focus_sectors=profile.focus_sectors,
        geographic_areas_of_work=profile.geographic_areas_of_work,
        target_groups=profile.target_groups,
        past_projects=profile.past_projects,
        year_of_establishment=profile.year_of_establishment,
        contact_person_name=profile.contact_person_name,
        contact_email=profile.contact_email,
        website=profile.website,
        full_time_staff=profile.full_time_staff,
        annual_budget_amount=profile.annual_budget_amount,
        annual_budget_currency=profile.annual_budget_currency,
        monitoring_and_evaluation_practices=profile.monitoring_and_evaluation_practices,
        funders_worked_with_before=profile.funders_worked_with_before,
        profile_status=profile.profile_status,
        completeness_score=profile.completeness_score,
        missing_fields=profile.missing_fields,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        last_completed_at=profile.last_completed_at.isoformat()
        if profile.last_completed_at
        else None,
    )


@router.put("", response_model=NGOProfileRead)
def update_ngo_profile(
    payload: NGOProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile = update_profile(db, current_user.id, payload)
    return NGOProfileRead(
        id=str(profile.id),
        user_id=str(profile.user_id),
        organization_name=profile.organization_name,
        country_of_registration=profile.country_of_registration,
        mission_statement=profile.mission_statement,
        focus_sectors=profile.focus_sectors,
        geographic_areas_of_work=profile.geographic_areas_of_work,
        target_groups=profile.target_groups,
        past_projects=profile.past_projects,
        year_of_establishment=profile.year_of_establishment,
        contact_person_name=profile.contact_person_name,
        contact_email=profile.contact_email,
        website=profile.website,
        full_time_staff=profile.full_time_staff,
        annual_budget_amount=profile.annual_budget_amount,
        annual_budget_currency=profile.annual_budget_currency,
        monitoring_and_evaluation_practices=profile.monitoring_and_evaluation_practices,
        funders_worked_with_before=profile.funders_worked_with_before,
        profile_status=profile.profile_status,
        completeness_score=profile.completeness_score,
        missing_fields=profile.missing_fields,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
        last_completed_at=profile.last_completed_at.isoformat()
        if profile.last_completed_at
        else None,
    )


@router.get("/completeness", response_model=NGOProfileCompletenessResponse)
def read_profile_completeness(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    status, score, missing_fields = get_completeness(db, current_user.id)
    return NGOProfileCompletenessResponse(
        profile_status=status,
        completeness_score=score,
        missing_fields=missing_fields,
    )
