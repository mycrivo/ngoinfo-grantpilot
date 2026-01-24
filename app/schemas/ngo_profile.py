from pydantic import BaseModel, Field


class PastProject(BaseModel):
    title: str | None = None
    donor: str | None = None
    duration: str | None = None
    location: str | None = None
    summary: str | None = None


class NGOProfileBase(BaseModel):
    organization_name: str | None = None
    country_of_registration: str | None = None
    mission_statement: str | None = None

    focus_sectors: list[str] = Field(default_factory=list)
    geographic_areas_of_work: list[str] = Field(default_factory=list)
    target_groups: list[str] = Field(default_factory=list)
    past_projects: list[PastProject] = Field(default_factory=list)

    year_of_establishment: int | None = None
    contact_person_name: str | None = None
    contact_email: str | None = None
    website: str | None = None

    full_time_staff: int | None = None
    annual_budget_amount: float | None = None
    annual_budget_currency: str | None = None

    monitoring_and_evaluation_practices: str | None = None
    funders_worked_with_before: list[str] = Field(default_factory=list)


class NGOProfileCreate(NGOProfileBase):
    organization_name: str
    country_of_registration: str
    mission_statement: str


class NGOProfileUpdate(NGOProfileBase):
    organization_name: str
    country_of_registration: str
    mission_statement: str


class NGOProfileRead(NGOProfileBase):
    id: str
    user_id: str
    profile_status: str
    completeness_score: int
    missing_fields: list[str]
    created_at: str
    updated_at: str
    last_completed_at: str | None


class NGOProfileCompletenessResponse(BaseModel):
    profile_status: str
    completeness_score: int
    missing_fields: list[str]
