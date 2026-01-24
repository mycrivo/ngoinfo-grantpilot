import enum
import uuid

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicantType(str, enum.Enum):
    NGO = "NGO"
    INDIVIDUAL = "INDIVIDUAL"
    ACADEMIC_INSTITUTION = "ACADEMIC_INSTITUTION"
    CONSORTIUM = "CONSORTIUM"
    MIXED = "MIXED"


class DeadlineType(str, enum.Enum):
    FIXED = "FIXED"
    ROLLING = "ROLLING"
    VARIES = "VARIES"


class OpportunityStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class FundingOpportunity(Base):
    __tablename__ = "funding_opportunities"
    __table_args__ = (
        CheckConstraint(
            "deadline_type != 'FIXED' OR application_deadline IS NOT NULL",
            name="ck_funding_opportunities_deadline_fixed_requires_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )

    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    application_url: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    donor_organization: Mapped[str] = mapped_column(Text, nullable=False)
    funding_type: Mapped[str] = mapped_column(Text, nullable=False)
    applicant_type: Mapped[ApplicantType] = mapped_column(
        ENUM(
            ApplicantType,
            name="applicant_type",
            create_type=False,
        ),
        nullable=False,
    )
    location_text: Mapped[str] = mapped_column(Text, nullable=False)
    focus_areas: Mapped[str] = mapped_column(Text, nullable=False)
    deadline_type: Mapped[DeadlineType] = mapped_column(
        ENUM(
            DeadlineType,
            name="deadline_type",
            create_type=False,
        ),
        nullable=False,
    )
    application_deadline: Mapped[Date | None] = mapped_column(Date, nullable=True)

    currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_min: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    amount_max: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    total_funding_available: Mapped[float | None] = mapped_column(
        Numeric, nullable=True
    )

    short_summary: Mapped[str] = mapped_column(Text, nullable=False)
    overview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    eligibility_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_process: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[OpportunityStatus] = mapped_column(
        ENUM(
            OpportunityStatus,
            name="opportunity_status",
            create_type=False,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    last_verified: Mapped[Date | None] = mapped_column(Date, nullable=True)

    requirements_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    organization_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsing_confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
