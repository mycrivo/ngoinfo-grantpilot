"""Ensure donor_reports.updated_at bumps on every row update (P0-4).

Revision ID: 0016_donor_reports_updated_at_trigger
Revises: 0015_gap_analysis_json
Create Date: 2026-06-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_donor_reports_updated_at_trigger"
down_revision: Union[str, Sequence[str], None] = "0015_gap_analysis_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TRIGGER_NAME = "donor_reports_set_updated_at"


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "donor_reports"):
        return

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_TRIGGER_NAME}()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON donor_reports")
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_NAME}
        BEFORE UPDATE ON donor_reports
        FOR EACH ROW
        EXECUTE FUNCTION {_TRIGGER_NAME}();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "donor_reports"):
        return
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON donor_reports")
    op.execute(f"DROP FUNCTION IF EXISTS {_TRIGGER_NAME}()")
