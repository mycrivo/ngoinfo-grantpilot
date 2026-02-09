"""Create proposals table.

Revision ID: 0011_proposals
Revises: 0010_email_canon_unique
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_proposals"
down_revision: Union[str, Sequence[str], None] = "0010_email_canon_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "proposals"):
        op.create_table(
            "proposals",
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
            sa.Column(
                "fit_scan_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("fit_scans.id"),
                nullable=True,
            ),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT"),
            sa.Column("plan_at_creation", sa.Text(), nullable=False),
            sa.Column("prompt_version", sa.Text(), nullable=False),
            sa.Column("selected_variant_id", sa.Text(), nullable=True),
            sa.Column("content_json", postgresql.JSONB, nullable=False),
            sa.Column(
                "regeneration_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
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
        )

    if not _has_index(inspector, "proposals", "idx_proposals_user_created"):
        op.execute(
            "CREATE INDEX idx_proposals_user_created "
            "ON proposals (user_id, created_at DESC)"
        )
    if not _has_index(inspector, "proposals", "idx_proposals_opportunity"):
        op.create_index(
            "idx_proposals_opportunity",
            "proposals",
            ["funding_opportunity_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "proposals"):
        if _has_index(inspector, "proposals", "idx_proposals_opportunity"):
            op.drop_index("idx_proposals_opportunity", table_name="proposals")
        if _has_index(inspector, "proposals", "idx_proposals_user_created"):
            op.drop_index("idx_proposals_user_created", table_name="proposals")
        op.drop_table("proposals")
