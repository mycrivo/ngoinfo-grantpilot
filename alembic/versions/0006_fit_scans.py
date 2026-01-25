"""Create fit_scans table.

Revision ID: 0006_fit_scans
Revises: 0005_commercial_spine
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_fit_scans"
down_revision: Union[str, Sequence[str], None] = "0005_commercial_spine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "fit_scans"):
        op.create_table(
            "fit_scans",
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
            sa.Column(
                "funding_opportunity_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("funding_opportunities.id"),
                nullable=False,
            ),
            sa.Column("plan_at_time_of_scan", sa.Text(), nullable=False),
            sa.Column("prompt_version", sa.Text(), nullable=False),
            sa.Column("model_rating", sa.Text(), nullable=False),
            sa.Column("overall_recommendation", sa.Text(), nullable=False),
            sa.Column("subscores", postgresql.JSONB, nullable=False),
            sa.Column("result_json", postgresql.JSONB, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )

    if not _has_index(inspector, "fit_scans", "idx_fit_scans_user_created"):
        op.execute(
            "CREATE INDEX idx_fit_scans_user_created "
            "ON fit_scans (user_id, created_at DESC)"
        )
    if not _has_index(inspector, "fit_scans", "idx_fit_scans_opportunity"):
        op.create_index(
            "idx_fit_scans_opportunity", "fit_scans", ["funding_opportunity_id"]
        )
    if not _has_index(inspector, "fit_scans", "idx_fit_scans_user_opportunity"):
        op.create_index(
            "idx_fit_scans_user_opportunity",
            "fit_scans",
            ["user_id", "funding_opportunity_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "fit_scans"):
        if _has_index(inspector, "fit_scans", "idx_fit_scans_user_opportunity"):
            op.drop_index("idx_fit_scans_user_opportunity", table_name="fit_scans")
        if _has_index(inspector, "fit_scans", "idx_fit_scans_opportunity"):
            op.drop_index("idx_fit_scans_opportunity", table_name="fit_scans")
        if _has_index(inspector, "fit_scans", "idx_fit_scans_user_created"):
            op.drop_index("idx_fit_scans_user_created", table_name="fit_scans")
        op.drop_table("fit_scans")
