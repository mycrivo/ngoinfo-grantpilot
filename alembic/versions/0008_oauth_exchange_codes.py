"""Add OAuth exchange codes table.

Revision ID: 0008_oauth_exchange_codes
Revises: 0007_schema_alignment
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_oauth_exchange_codes"
down_revision: Union[str, Sequence[str], None] = "0007_schema_alignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_oauth_exchange_codes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.Text, nullable=False, unique=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_auth_oauth_exchange_codes_user_id", "auth_oauth_exchange_codes", ["user_id"]
    )
    op.create_index(
        "ix_auth_oauth_exchange_codes_expires_at",
        "auth_oauth_exchange_codes",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_oauth_exchange_codes_expires_at",
        table_name="auth_oauth_exchange_codes",
    )
    op.drop_index(
        "ix_auth_oauth_exchange_codes_user_id",
        table_name="auth_oauth_exchange_codes",
    )
    op.drop_table("auth_oauth_exchange_codes")
