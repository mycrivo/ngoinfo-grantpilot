"""Add commercial spine tables.

Revision ID: 0005_commercial_spine
Revises: 0004_funding_defaults
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_commercial_spine"
down_revision: Union[str, Sequence[str], None] = "0004_funding_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "user_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("plan_name", sa.Text(), nullable=False),
        sa.Column(
            "plan_activated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "plan_name IN ('FREE', 'GROWTH', 'IMPACT')",
            name="ck_user_plans_plan_name",
        ),
    )
    op.create_table(
        "usage_ledger",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('FIT_SCAN', 'PROPOSAL')",
            name="ck_usage_ledger_event_type",
        ),
        sa.UniqueConstraint(
            "user_id",
            "event_type",
            "idempotency_key",
            name="uq_usage_ledger_idempotency",
        ),
    )
    op.create_index("ix_usage_ledger_user_id", "usage_ledger", ["user_id"])
    op.create_index("ix_usage_ledger_event_type", "usage_ledger", ["event_type"])
    op.create_index("ix_usage_ledger_occurred_at", "usage_ledger", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_usage_ledger_occurred_at", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_event_type", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_user_id", table_name="usage_ledger")
    op.drop_table("usage_ledger")
    op.drop_table("user_plans")
