"""P3-2 worker recovery columns on report_jobs.

Revision ID: 0017_report_jobs_worker_recovery
Revises: 0016_updated_at_trigger
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_report_jobs_worker_recovery"
down_revision: Union[str, Sequence[str], None] = "0016_updated_at_trigger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "report_jobs"):
        return

    if not _has_column(inspector, "report_jobs", "last_heartbeat_at"):
        op.add_column(
            "report_jobs",
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column(inspector, "report_jobs", "lease_owner"):
        op.add_column(
            "report_jobs",
            sa.Column("lease_owner", sa.Text(), nullable=True),
        )
    if not _has_column(inspector, "report_jobs", "lease_expires_at"):
        op.add_column(
            "report_jobs",
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not _has_column(inspector, "report_jobs", "requeue_count"):
        op.add_column(
            "report_jobs",
            sa.Column(
                "requeue_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "report_jobs"):
        return

    for column in (
        "requeue_count",
        "lease_expires_at",
        "lease_owner",
        "last_heartbeat_at",
    ):
        if _has_column(inspector, "report_jobs", column):
            op.drop_column("report_jobs", column)
