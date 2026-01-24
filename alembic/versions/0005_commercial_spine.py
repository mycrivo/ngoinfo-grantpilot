"""Create commercial spine tables (user_plans, usage_ledger).

Revision ID: 0005_commercial_spine
Revises: 0004_funding_defaults
Create Date: 2026-01-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_commercial_spine"
down_revision: Union[str, Sequence[str], None] = "0004_funding_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = "0004_funding_defaults"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _has_unique(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _has_check(inspector: sa.Inspector, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in inspector.get_check_constraints(table_name)
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "user_plans"):
        op.create_table(
            "user_plans",
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
            sa.Column("plan_name", sa.Text(), nullable=False),
            sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
            sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=True),
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
            sa.CheckConstraint(
                "plan_name IN ('FREE', 'GROWTH', 'IMPACT')",
                name="ck_user_plans_plan_name",
            ),
            sa.UniqueConstraint("user_id", name="uq_user_plans_user_id"),
            sa.UniqueConstraint(
                "stripe_subscription_id", name="uq_user_plans_stripe_subscription_id"
            ),
        )
    else:
        existing_columns = _column_names(inspector, "user_plans")
        if "stripe_subscription_id" not in existing_columns:
            op.add_column("user_plans", sa.Column("stripe_subscription_id", sa.Text()))
        if "billing_period_start" not in existing_columns:
            op.add_column(
                "user_plans",
                sa.Column("billing_period_start", sa.DateTime(timezone=True)),
            )
        if "billing_period_end" not in existing_columns:
            op.add_column(
                "user_plans",
                sa.Column("billing_period_end", sa.DateTime(timezone=True)),
            )
        if "created_at" not in existing_columns:
            op.add_column(
                "user_plans",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                ),
            )
        if "updated_at" not in existing_columns:
            op.add_column(
                "user_plans",
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                ),
            )
        if not _has_check(inspector, "user_plans", "ck_user_plans_plan_name"):
            op.create_check_constraint(
                "ck_user_plans_plan_name",
                "user_plans",
                "plan_name IN ('FREE', 'GROWTH', 'IMPACT')",
            )
        if not _has_unique(inspector, "user_plans", "uq_user_plans_user_id"):
            op.create_unique_constraint("uq_user_plans_user_id", "user_plans", ["user_id"])
        if not _has_unique(inspector, "user_plans", "uq_user_plans_stripe_subscription_id"):
            op.create_unique_constraint(
                "uq_user_plans_stripe_subscription_id",
                "user_plans",
                ["stripe_subscription_id"],
            )

    if not _has_index(inspector, "user_plans", "idx_user_plans_user"):
        op.create_index("idx_user_plans_user", "user_plans", ["user_id"])
    if not _has_index(inspector, "user_plans", "idx_user_plans_stripe_sub"):
        op.create_index(
            "idx_user_plans_stripe_sub",
            "user_plans",
            ["stripe_subscription_id"],
            postgresql_where=sa.text("stripe_subscription_id IS NOT NULL"),
        )

    if not _table_exists(inspector, "usage_ledger"):
        op.create_table(
            "usage_ledger",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("action_type", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.Text(), nullable=False),
            sa.Column(
                "metadata",
                postgresql.JSONB,
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
    else:
        existing_columns = _column_names(inspector, "usage_ledger")
        if "action_type" not in existing_columns:
            op.add_column("usage_ledger", sa.Column("action_type", sa.Text(), nullable=False))
        if "idempotency_key" not in existing_columns:
            op.add_column(
                "usage_ledger", sa.Column("idempotency_key", sa.Text(), nullable=False)
            )
        if "metadata" not in existing_columns:
            op.add_column(
                "usage_ledger",
                sa.Column(
                    "metadata",
                    postgresql.JSONB,
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )
        if "created_at" not in existing_columns:
            op.add_column(
                "usage_ledger",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                ),
            )

    if not _has_index(inspector, "usage_ledger", "idx_usage_ledger_user"):
        op.create_index("idx_usage_ledger_user", "usage_ledger", ["user_id"])
    if not _has_index(inspector, "usage_ledger", "idx_usage_ledger_action"):
        op.create_index("idx_usage_ledger_action", "usage_ledger", ["action_type"])
    if not _has_index(inspector, "usage_ledger", "idx_usage_ledger_user_created"):
        op.execute(
            "CREATE INDEX idx_usage_ledger_user_created "
            "ON usage_ledger (user_id, created_at DESC)"
        )
    if not _has_index(inspector, "usage_ledger", "idx_usage_ledger_idempotency"):
        op.create_index(
            "idx_usage_ledger_idempotency",
            "usage_ledger",
            ["idempotency_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "usage_ledger"):
        if _has_index(inspector, "usage_ledger", "idx_usage_ledger_idempotency"):
            op.drop_index("idx_usage_ledger_idempotency", table_name="usage_ledger")
        if _has_index(inspector, "usage_ledger", "idx_usage_ledger_user_created"):
            op.drop_index("idx_usage_ledger_user_created", table_name="usage_ledger")
        if _has_index(inspector, "usage_ledger", "idx_usage_ledger_action"):
            op.drop_index("idx_usage_ledger_action", table_name="usage_ledger")
        if _has_index(inspector, "usage_ledger", "idx_usage_ledger_user"):
            op.drop_index("idx_usage_ledger_user", table_name="usage_ledger")
        op.drop_table("usage_ledger")

    if _table_exists(inspector, "user_plans"):
        if _has_index(inspector, "user_plans", "idx_user_plans_stripe_sub"):
            op.drop_index("idx_user_plans_stripe_sub", table_name="user_plans")
        if _has_index(inspector, "user_plans", "idx_user_plans_user"):
            op.drop_index("idx_user_plans_user", table_name="user_plans")
        op.drop_table("user_plans")
