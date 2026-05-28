"""Add donor_reports.gap_analysis_json for E3 gap/compliance output.

Revision ID: 0015_donor_reports_gap_analysis_json
Revises: 0014_me_module_tables
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_gap_analysis_json"
down_revision: Union[str, Sequence[str], None] = "0014_me_module_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "donor_reports") and not _column_exists(
        inspector, "donor_reports", "gap_analysis_json"
    ):
        op.add_column(
            "donor_reports",
            sa.Column(
                "gap_analysis_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "donor_reports") and _column_exists(
        inspector, "donor_reports", "gap_analysis_json"
    ):
        op.drop_column("donor_reports", "gap_analysis_json")
