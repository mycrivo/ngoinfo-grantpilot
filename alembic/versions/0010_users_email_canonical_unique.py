"""Add canonical email uniqueness index.

Revision ID: 0010_users_email_canonical_unique
Revises: 0009_stripe_events
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_users_email_canonical_unique"
down_revision: Union[str, Sequence[str], None] = "0009_stripe_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_users_email_canonical",
        "users",
        [sa.text("lower(trim(email))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_users_email_canonical", table_name="users")
