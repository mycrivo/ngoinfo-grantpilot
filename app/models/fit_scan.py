import uuid

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FitScan(Base):
    __tablename__ = "fit_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    funding_opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("funding_opportunities.id"),
        nullable=False,
    )
    plan_at_time_of_scan: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_rating: Mapped[str] = mapped_column(Text, nullable=False)
    overall_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    subscores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="fit_scans")
    funding_opportunity = relationship(
        "FundingOpportunity", back_populates="fit_scans"
    )

    def __repr__(self) -> str:
        return (
            "FitScan("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"overall_recommendation={self.overall_recommendation}"
            ")"
        )
