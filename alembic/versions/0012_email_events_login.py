"""Add email events table and users.first_login_at.

Revision ID: 0012_email_events_login
Revises: 0011_proposals
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012_email_events_login"
down_revision: Union[str, Sequence[str], None] = "0011_proposals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users") and not _column_exists(
        inspector, "users", "first_login_at"
    ):
        op.add_column(
            "users",
            sa.Column("first_login_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists(inspector, "email_events"):
        op.create_table(
            "email_events",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("event_key", sa.Text(), nullable=False, unique=True),
            sa.Column("event_type", sa.Text(), nullable=False),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("to_email", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False),
            sa.Column("provider_message_id", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "email_events") and not _has_index(
        inspector, "email_events", "idx_email_events_created_at"
    ):
        op.create_index(
            "idx_email_events_created_at",
            "email_events",
            ["created_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "email_events"):
        if _has_index(inspector, "email_events", "idx_email_events_created_at"):
            op.drop_index("idx_email_events_created_at", table_name="email_events")
        op.drop_table("email_events")

    inspector = sa.inspect(bind)
    if _table_exists(inspector, "users") and _column_exists(
        inspector, "users", "first_login_at"
    ):
        op.drop_column("users", "first_login_at")

