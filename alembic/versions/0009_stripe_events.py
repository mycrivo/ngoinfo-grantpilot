"""Add stripe_events event store.

Revision ID: 0009_stripe_events
Revises: 0008_oauth_exchange_codes
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_stripe_events"
down_revision: Union[str, Sequence[str], None] = "0008_oauth_exchange_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False,
            server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("stripe_event_id", sa.Text, nullable=False, unique=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_result", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_stripe_events_received_at", "stripe_events", ["received_at"])
    op.create_index("ix_stripe_events_event_type", "stripe_events", ["event_type"])
    op.create_index(
        "ix_stripe_events_processing_result",
        "stripe_events",
        ["processing_result"],
    )


def downgrade() -> None:
    op.drop_index("ix_stripe_events_processing_result", table_name="stripe_events")
    op.drop_index("ix_stripe_events_event_type", table_name="stripe_events")
    op.drop_index("ix_stripe_events_received_at", table_name="stripe_events")
    op.drop_table("stripe_events")
