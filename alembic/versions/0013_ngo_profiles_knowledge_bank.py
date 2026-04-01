"""Add ngo_profiles.knowledge_bank JSONB column.

Revision ID: 0013_ngo_profiles_knowledge_bank
Revises: 0012_email_events_login
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013_ngo_profiles_knowledge_bank"
down_revision: Union[str, Sequence[str], None] = "0012_email_events_login"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "ngo_profiles") and not _column_exists(
        inspector, "ngo_profiles", "knowledge_bank"
    ):
        op.add_column(
            "ngo_profiles",
            sa.Column(
                "knowledge_bank",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "ngo_profiles") and _column_exists(
        inspector, "ngo_profiles", "knowledge_bank"
    ):
        op.drop_column("ngo_profiles", "knowledge_bank")

