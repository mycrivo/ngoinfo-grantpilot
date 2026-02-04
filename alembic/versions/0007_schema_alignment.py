"""Align users and user_plans schema.

Revision ID: 0007_schema_alignment
Revises: 0006_fit_scans
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_schema_alignment"
down_revision: Union[str, Sequence[str], None] = "0006_fit_scans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_unique(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "users"):
        existing_columns = _column_names(inspector, "users")
        if "stripe_customer_id" not in existing_columns:
            op.add_column(
                "users", sa.Column("stripe_customer_id", sa.Text(), nullable=True)
            )
        if not _has_unique(inspector, "users", "uq_users_stripe_customer_id"):
            op.create_unique_constraint(
                "uq_users_stripe_customer_id", "users", ["stripe_customer_id"]
            )

    if _table_exists(inspector, "user_plans"):
        existing_columns = _column_names(inspector, "user_plans")
        if "plan_activated_at" not in existing_columns:
            op.add_column(
                "user_plans",
                sa.Column("plan_activated_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "user_plans"):
        existing_columns = _column_names(inspector, "user_plans")
        if "plan_activated_at" in existing_columns:
            op.drop_column("user_plans", "plan_activated_at")

    if _table_exists(inspector, "users"):
        if _has_unique(inspector, "users", "uq_users_stripe_customer_id"):
            op.drop_constraint(
                "uq_users_stripe_customer_id", "users", type_="unique"
            )
        existing_columns = _column_names(inspector, "users")
        if "stripe_customer_id" in existing_columns:
            op.drop_column("users", "stripe_customer_id")
