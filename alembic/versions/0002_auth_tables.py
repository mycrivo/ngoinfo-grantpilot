"""Add auth tables.

Revision ID: 0002_auth_tables
Revises: 0001_initial
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth_tables"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("full_name", sa.Text, nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("google_sub", sa.Text, nullable=True),
        sa.Column(
            "auth_provider",
            sa.Text,
            nullable=False,
            server_default=sa.text("'email'"),
        ),
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )

    op.create_table(
        "auth_refresh_tokens",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by_token_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_refresh_tokens.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"]
    )
    op.create_index(
        "ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"]
    )

    op.create_table(
        "auth_magic_link_tokens",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("requested_ip", sa.Text, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
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
        "ix_auth_magic_link_tokens_email", "auth_magic_link_tokens", ["email"]
    )
    op.create_index(
        "ix_auth_magic_link_tokens_expires_at",
        "auth_magic_link_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_magic_link_tokens_expires_at", table_name="auth_magic_link_tokens"
    )
    op.drop_index("ix_auth_magic_link_tokens_email", table_name="auth_magic_link_tokens")
    op.drop_table("auth_magic_link_tokens")

    op.drop_index("ix_auth_refresh_tokens_expires_at", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")

    op.drop_table("users")
