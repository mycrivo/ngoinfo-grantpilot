from datetime import datetime, timezone
from typing import Iterable
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.ngo_profile import NGOProfile
from app.schemas.ngo_profile import NGOProfileCreate, NGOProfileUpdate


def _normalize_list(values: Iterable[str] | None) -> list[str]:
    return [value.strip() for value in values or [] if value.strip()]


def _normalize_projects(projects: Iterable[dict] | None) -> list[dict]:
    normalized = []
    for project in projects or []:
        if isinstance(project, dict):
            normalized.append(project)
    return normalized


def _validate_budget(amount: float | None) -> None:
    if amount is not None and amount < 0:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="Invalid annual_budget_amount",
            status_code=422,
        )


def _validate_year(year: int | None) -> None:
    if year is None:
        return
    current_year = datetime.now(timezone.utc).year
    if year < 1800 or year > current_year:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="Invalid year_of_establishment",
            status_code=422,
        )


def _compute_completeness(profile: NGOProfile) -> tuple[int, list[str], str]:
    missing_fields: list[str] = []

    if not profile.organization_name:
        missing_fields.append("organization_name")
    if not profile.country_of_registration:
        missing_fields.append("country_of_registration")
    if not profile.mission_statement:
        missing_fields.append("mission_statement")
    if not profile.focus_sectors:
        missing_fields.append("focus_sectors")
    if not profile.geographic_areas_of_work:
        missing_fields.append("geographic_areas_of_work")
    if not profile.target_groups:
        missing_fields.append("target_groups")

    valid_project = any(
        isinstance(project, dict) and str(project.get("title", "")).strip()
        for project in profile.past_projects or []
    )
    if not valid_project:
        missing_fields.append("past_projects")

    score = 0
    if profile.organization_name and profile.country_of_registration:
        score += 20
    if profile.mission_statement:
        score += 15
    if profile.focus_sectors:
        score += 15
    if profile.geographic_areas_of_work:
        score += 15
    if profile.target_groups:
        score += 15
    if valid_project:
        score += 20
    score = min(score, 100)

    status = "COMPLETE" if not missing_fields else "DRAFT"
    return score, missing_fields, status


def create_profile(db: Session, user_id: uuid.UUID, payload: NGOProfileCreate) -> NGOProfile:
    existing = db.execute(
        select(NGOProfile).where(NGOProfile.user_id == user_id)
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(
            error_code="PROFILE_ALREADY_EXISTS",
            message="Profile already exists",
            status_code=409,
        )

    _validate_year(payload.year_of_establishment)
    _validate_budget(payload.annual_budget_amount)

    profile = NGOProfile(
        user_id=user_id,
        organization_name=payload.organization_name.strip(),
        country_of_registration=payload.country_of_registration.strip(),
        mission_statement=payload.mission_statement.strip(),
        focus_sectors=_normalize_list(payload.focus_sectors),
        geographic_areas_of_work=_normalize_list(payload.geographic_areas_of_work),
        target_groups=_normalize_list(payload.target_groups),
        past_projects=_normalize_projects([p.model_dump() for p in payload.past_projects]),
        year_of_establishment=payload.year_of_establishment,
        contact_person_name=payload.contact_person_name,
        contact_email=payload.contact_email,
        website=payload.website,
        full_time_staff=payload.full_time_staff,
        annual_budget_amount=payload.annual_budget_amount,
        annual_budget_currency=payload.annual_budget_currency or "USD",
        monitoring_and_evaluation_practices=payload.monitoring_and_evaluation_practices,
        funders_worked_with_before=_normalize_list(payload.funders_worked_with_before),
    )

    score, missing_fields, status = _compute_completeness(profile)
    profile.completeness_score = score
    profile.missing_fields = missing_fields
    profile.profile_status = status
    if status == "COMPLETE" and profile.last_completed_at is None:
        profile.last_completed_at = datetime.now(timezone.utc)
    if status == "DRAFT":
        profile.last_completed_at = None

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(db: Session, user_id: uuid.UUID) -> NGOProfile:
    profile = db.execute(
        select(NGOProfile).where(NGOProfile.user_id == user_id)
    ).scalar_one_or_none()
    if not profile:
        raise NotFoundError(
            error_code="PROFILE_NOT_FOUND",
            message="Profile not found",
            status_code=404,
        )
    return profile


def update_profile(db: Session, user_id: uuid.UUID, payload: NGOProfileUpdate) -> NGOProfile:
    profile = get_profile(db, user_id)

    _validate_year(payload.year_of_establishment)
    _validate_budget(payload.annual_budget_amount)

    profile.organization_name = payload.organization_name.strip()
    profile.country_of_registration = payload.country_of_registration.strip()
    profile.mission_statement = payload.mission_statement.strip()
    profile.focus_sectors = _normalize_list(payload.focus_sectors)
    profile.geographic_areas_of_work = _normalize_list(payload.geographic_areas_of_work)
    profile.target_groups = _normalize_list(payload.target_groups)
    profile.past_projects = _normalize_projects([p.model_dump() for p in payload.past_projects])
    profile.year_of_establishment = payload.year_of_establishment
    profile.contact_person_name = payload.contact_person_name
    profile.contact_email = payload.contact_email
    profile.website = payload.website
    profile.full_time_staff = payload.full_time_staff
    profile.annual_budget_amount = payload.annual_budget_amount
    profile.annual_budget_currency = payload.annual_budget_currency or "USD"
    profile.monitoring_and_evaluation_practices = payload.monitoring_and_evaluation_practices
    profile.funders_worked_with_before = _normalize_list(payload.funders_worked_with_before)

    score, missing_fields, status = _compute_completeness(profile)
    profile.completeness_score = score
    profile.missing_fields = missing_fields
    profile.profile_status = status
    if status == "COMPLETE" and profile.last_completed_at is None:
        profile.last_completed_at = datetime.now(timezone.utc)
    if status == "DRAFT":
        profile.last_completed_at = None

    db.commit()
    db.refresh(profile)
    return profile


def get_completeness(db: Session, user_id: uuid.UUID) -> tuple[str, int, list[str]]:
    profile = get_profile(db, user_id)
    return profile.profile_status, profile.completeness_score, profile.missing_fields
