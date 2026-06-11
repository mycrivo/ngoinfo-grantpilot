"""Composite unique index on usage_ledger idempotency (F-6).

Revision ID: 0018_usage_ledger_idempotency_unique
Revises: 0017_report_jobs_worker_recovery
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_usage_ledger_idempotency_unique"
down_revision: Union[str, Sequence[str], None] = "0017_report_jobs_worker_recovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX_NAME = "uq_usage_ledger_user_action_idempotency"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "usage_ledger"):
        return
    if _has_index(inspector, "usage_ledger", _INDEX_NAME):
        return
    op.create_index(
        _INDEX_NAME,
        "usage_ledger",
        ["user_id", "action_type", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "usage_ledger"):
        return
    if _has_index(inspector, "usage_ledger", _INDEX_NAME):
        op.drop_index(_INDEX_NAME, table_name="usage_ledger")
