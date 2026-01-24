import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NGOProfile(Base):
    __tablename__ = "ngo_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_ngo_profiles_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    organization_name: Mapped[str] = mapped_column(Text, nullable=False)
    country_of_registration: Mapped[str] = mapped_column(Text, nullable=False)
    mission_statement: Mapped[str] = mapped_column(Text, nullable=False)

    focus_sectors: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    geographic_areas_of_work: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    target_groups: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    past_projects: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    profile_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="DRAFT"
    )
    completeness_score: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    missing_fields: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_completed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    year_of_establishment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contact_person_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)

    full_time_staff: Mapped[int | None] = mapped_column(Integer, nullable=True)
    annual_budget_amount: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    annual_budget_currency: Mapped[str | None] = mapped_column(
        Text, nullable=True, server_default="USD"
    )

    monitoring_and_evaluation_practices: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    funders_worked_with_before: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
