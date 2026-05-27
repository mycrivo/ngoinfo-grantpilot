"""Create M&E module tables (donor reports, templates, uploads, jobs).

Revision ID: 0014_me_module_tables
Revises: 0013_ngo_profiles_knowledge_bank
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_me_module_tables"
down_revision: Union[str, Sequence[str], None] = "0013_ngo_profiles_knowledge_bank"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DONOR_REPORT_STATUS = (
    "status IN ('DRAFT', 'EXTRACTING', 'AWAITING_REVIEW', 'GENERATING', "
    "'DEGRADED', 'COMPLETE')"
)
_REPORTING_FREQUENCY = (
    "reporting_frequency IN ('end_of_grant', 'annual', 'quarterly', 'interim', 'final')"
)
_DOCUMENT_CLASSIFICATION = (
    "classification IS NULL OR classification IN "
    "('proposal', 'grant_letter', 'mou', 'indicator_data', 'photo', 'deck', 'other')"
)
_EXTRACTION_STATUS = (
    "extraction_status IN ('PENDING', 'PROCESSING', 'COMPLETE', 'FAILED')"
)
_REPORT_JOB_STAGE = (
    "stage IN ('classify', 'extract', 'reconcile', 'gap', 'synthesise', "
    "'critique', 'export')"
)
_REPORT_JOB_STATUS = (
    "status IN ('queued', 'running', 'awaiting_human', 'failed', 'done')"
)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


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

    if not _table_exists(inspector, "funder_report_templates"):
        op.create_table(
            "funder_report_templates",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("funder_name", sa.Text(), nullable=False),
            sa.Column("template_name", sa.Text(), nullable=False),
            sa.Column("region", sa.Text(), nullable=False),
            sa.Column("reporting_frequency", sa.Text(), nullable=False),
            sa.Column(
                "report_sections_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "format_rules_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "terminology_map_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("docx_template_ref", sa.Text(), nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
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
            sa.CheckConstraint(
                _REPORTING_FREQUENCY,
                name="ck_funder_report_templates_reporting_frequency",
            ),
            sa.UniqueConstraint(
                "funder_name",
                "template_name",
                name="uq_funder_report_templates_funder_template",
            ),
        )

    if not _has_index(
        inspector, "funder_report_templates", "idx_funder_report_templates_region_active"
    ):
        op.create_index(
            "idx_funder_report_templates_region_active",
            "funder_report_templates",
            ["region", "is_active"],
        )
    if not _has_index(
        inspector, "funder_report_templates", "idx_funder_report_templates_active"
    ):
        op.create_index(
            "idx_funder_report_templates_active",
            "funder_report_templates",
            ["is_active"],
            postgresql_where=sa.text("is_active = true"),
        )

    if not _table_exists(inspector, "donor_reports"):
        op.create_table(
            "donor_reports",
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
                "funder_report_template_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("funder_report_templates.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "linked_proposal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("proposals.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reporting_period_start", sa.Date(), nullable=False),
            sa.Column("reporting_period_end", sa.Date(), nullable=False),
            sa.Column(
                "status",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'DRAFT'"),
            ),
            sa.Column(
                "knowledge_bank_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "indicator_actuals_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "content_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
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
            sa.CheckConstraint(_DONOR_REPORT_STATUS, name="ck_donor_reports_status"),
            sa.CheckConstraint(
                "reporting_period_end >= reporting_period_start",
                name="ck_donor_reports_reporting_period",
            ),
        )

    if not _has_index(inspector, "donor_reports", "idx_donor_reports_user_created"):
        op.create_index(
            "idx_donor_reports_user_created",
            "donor_reports",
            ["user_id", sa.text("created_at DESC")],
        )
    if not _has_index(inspector, "donor_reports", "idx_donor_reports_user_status"):
        op.create_index(
            "idx_donor_reports_user_status",
            "donor_reports",
            ["user_id", "status"],
        )
    if not _has_index(
        inspector, "donor_reports", "idx_donor_reports_funder_template"
    ):
        op.create_index(
            "idx_donor_reports_funder_template",
            "donor_reports",
            ["funder_report_template_id"],
        )
    if not _has_index(
        inspector, "donor_reports", "idx_donor_reports_linked_proposal"
    ):
        op.create_index(
            "idx_donor_reports_linked_proposal",
            "donor_reports",
            ["linked_proposal_id"],
            postgresql_where=sa.text("linked_proposal_id IS NOT NULL"),
        )

    if not _table_exists(inspector, "uploaded_documents"):
        op.create_table(
            "uploaded_documents",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "donor_report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("donor_reports.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("storage_ref", sa.Text(), nullable=False),
            sa.Column("original_filename", sa.Text(), nullable=False),
            sa.Column("mime_type", sa.Text(), nullable=False),
            sa.Column("size_bytes", sa.BigInteger(), nullable=False),
            sa.Column("classification", sa.Text(), nullable=True),
            sa.Column(
                "extracted_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "extraction_status",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'PENDING'"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.CheckConstraint(
                _DOCUMENT_CLASSIFICATION,
                name="ck_uploaded_documents_classification",
            ),
            sa.CheckConstraint(
                _EXTRACTION_STATUS,
                name="ck_uploaded_documents_extraction_status",
            ),
            sa.CheckConstraint(
                "size_bytes > 0",
                name="ck_uploaded_documents_size_bytes",
            ),
        )

    if not _has_index(
        inspector, "uploaded_documents", "idx_uploaded_documents_report_created"
    ):
        op.create_index(
            "idx_uploaded_documents_report_created",
            "uploaded_documents",
            ["donor_report_id", "created_at"],
        )
    if not _has_index(inspector, "uploaded_documents", "idx_uploaded_documents_user"):
        op.create_index(
            "idx_uploaded_documents_user",
            "uploaded_documents",
            ["user_id"],
        )
    if not _has_index(
        inspector, "uploaded_documents", "idx_uploaded_documents_report_classification"
    ):
        op.create_index(
            "idx_uploaded_documents_report_classification",
            "uploaded_documents",
            ["donor_report_id", "classification"],
        )

    if not _table_exists(inspector, "report_jobs"):
        op.create_table(
            "report_jobs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "donor_report_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("donor_reports.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "stage",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'classify'"),
            ),
            sa.Column(
                "status",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'queued'"),
            ),
            sa.Column(
                "agent_trace_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.CheckConstraint(_REPORT_JOB_STAGE, name="ck_report_jobs_stage"),
            sa.CheckConstraint(_REPORT_JOB_STATUS, name="ck_report_jobs_status"),
        )

    if not _has_index(
        inspector, "report_jobs", "idx_report_jobs_donor_report_started"
    ):
        op.create_index(
            "idx_report_jobs_donor_report_started",
            "report_jobs",
            ["donor_report_id", sa.text("started_at DESC")],
        )
    if not _has_index(inspector, "report_jobs", "idx_report_jobs_active_status"):
        op.create_index(
            "idx_report_jobs_active_status",
            "report_jobs",
            ["status"],
            postgresql_where=sa.text(
                "status IN ('queued', 'running', 'awaiting_human')"
            ),
        )
    if not _has_index(inspector, "report_jobs", "idx_report_jobs_donor_report"):
        op.create_index(
            "idx_report_jobs_donor_report",
            "report_jobs",
            ["donor_report_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "report_jobs"):
        op.drop_table("report_jobs")
    if _table_exists(inspector, "uploaded_documents"):
        op.drop_table("uploaded_documents")
    if _table_exists(inspector, "donor_reports"):
        op.drop_table("donor_reports")
    if _table_exists(inspector, "funder_report_templates"):
        op.drop_table("funder_report_templates")
