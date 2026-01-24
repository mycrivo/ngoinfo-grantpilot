"""Add ngo_profiles table.

Revision ID: 0003_ngo_profiles
Revises: 0002_auth_tables
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_ngo_profiles"
down_revision: Union[str, Sequence[str], None] = "0002_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ngo_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("organization_name", sa.Text, nullable=False),
        sa.Column("country_of_registration", sa.Text, nullable=False),
        sa.Column("mission_statement", sa.Text, nullable=False),
        sa.Column(
            "focus_sectors",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "geographic_areas_of_work",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "target_groups",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "past_projects",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "profile_status",
            sa.Text,
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
        sa.Column(
            "completeness_score",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "missing_fields",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
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
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("year_of_establishment", sa.Integer, nullable=True),
        sa.Column("contact_person_name", sa.Text, nullable=True),
        sa.Column("contact_email", sa.Text, nullable=True),
        sa.Column("website", sa.Text, nullable=True),
        sa.Column("full_time_staff", sa.Integer, nullable=True),
        sa.Column("annual_budget_amount", sa.Numeric, nullable=True),
        sa.Column(
            "annual_budget_currency",
            sa.Text,
            nullable=True,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("monitoring_and_evaluation_practices", sa.Text, nullable=True),
        sa.Column(
            "funders_worked_with_before",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.UniqueConstraint("user_id", name="uq_ngo_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("ngo_profiles")
