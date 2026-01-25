import enum
import uuid

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageActionType(str, enum.Enum):
    """Python-only action type enum (not a Postgres ENUM) for MVP flexibility."""

    FIT_SCAN = "FIT_SCAN"
    PROPOSAL_CREATE = "PROPOSAL_CREATE"
    PROPOSAL_REGEN = "PROPOSAL_REGEN"
    DOCX_EXPORT = "DOCX_EXPORT"


class UsageLedger(Base):
    __tablename__ = "usage_ledger"

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
    event_type: Mapped[str] = mapped_column(
        "action_type",
        Text,
        nullable=False,
        # Valid action_type values: FIT_SCAN, PROPOSAL_CREATE, PROPOSAL_REGEN, DOCX_EXPORT.
    )
    occurred_at: Mapped[DateTime] = mapped_column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
