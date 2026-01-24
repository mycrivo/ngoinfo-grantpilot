"""Add defaults for funding_opportunities system fields.

Revision ID: 0004_funding_defaults
Revises: 0003_ngo_profiles
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_funding_defaults"
down_revision: Union[str, Sequence[str], None] = "0003_ngo_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.alter_column(
        "funding_opportunities",
        "id",
        server_default=sa.text("gen_random_uuid()"),
    )
    op.alter_column(
        "funding_opportunities",
        "created_at",
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "funding_opportunities",
        "updated_at",
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column("funding_opportunities", "updated_at", server_default=None)
    op.alter_column("funding_opportunities", "created_at", server_default=None)
    op.alter_column("funding_opportunities", "id", server_default=None)
