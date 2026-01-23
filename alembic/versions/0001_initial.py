"""Initial contracted schema.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    applicant_type_enum = sa.Enum(
        "NGO",
        "INDIVIDUAL",
        "ACADEMIC_INSTITUTION",
        "CONSORTIUM",
        "MIXED",
        name="applicant_type",
    )
    deadline_type_enum = sa.Enum("FIXED", "ROLLING", "VARIES", name="deadline_type")
    status_enum = sa.Enum(
        "DRAFT", "READY", "PUBLISHED", "ARCHIVED", name="opportunity_status"
    )

    bind = op.get_bind()
    applicant_type_enum.create(bind, checkfirst=True)
    deadline_type_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "funding_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("application_url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("donor_organization", sa.Text, nullable=False),
        sa.Column("funding_type", sa.Text, nullable=False),
        sa.Column("applicant_type", applicant_type_enum, nullable=False),
        sa.Column("location_text", sa.Text, nullable=False),
        sa.Column("focus_areas", sa.Text, nullable=False),
        sa.Column("deadline_type", deadline_type_enum, nullable=False),
        sa.Column("application_deadline", sa.Date, nullable=True),
        sa.Column("currency", sa.Text, nullable=True),
        sa.Column("amount_min", sa.Numeric, nullable=True),
        sa.Column("amount_max", sa.Numeric, nullable=True),
        sa.Column("total_funding_available", sa.Numeric, nullable=True),
        sa.Column("short_summary", sa.Text, nullable=False),
        sa.Column("overview_text", sa.Text, nullable=True),
        sa.Column("eligibility_criteria", sa.Text, nullable=True),
        sa.Column("application_process", sa.Text, nullable=True),
        sa.Column("status", status_enum, nullable=False),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("last_verified", sa.Date, nullable=True),
        sa.Column("requirements_json", postgresql.JSONB, nullable=False),
        sa.Column("organization_types", sa.Text, nullable=True),
        sa.Column("geographic_focus", sa.Text, nullable=True),
        sa.Column("contact_information", sa.Text, nullable=True),
        sa.Column("processing_status", sa.Text, nullable=True),
        sa.Column("parsing_confidence", sa.Numeric, nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.CheckConstraint(
            "deadline_type != 'FIXED' OR application_deadline IS NOT NULL",
            name="ck_funding_opportunities_deadline_fixed_requires_date",
        ),
    )


def downgrade() -> None:
    op.drop_table("funding_opportunities")

    bind = op.get_bind()
    sa.Enum(name="opportunity_status").drop(bind, checkfirst=True)
    sa.Enum(name="deadline_type").drop(bind, checkfirst=True)
    sa.Enum(name="applicant_type").drop(bind, checkfirst=True)
