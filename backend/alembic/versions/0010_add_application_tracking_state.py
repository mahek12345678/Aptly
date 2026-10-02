"""add application tracking state fields

Revision ID: 0010_add_application_tracking_state
Revises: 0009_create_job_listings_and_daily_matches
Create Date: 2026-09-23 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_add_application_tracking_state"
down_revision: Union[str, None] = "0009_create_job_listings_and_daily_matches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_applications",
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_job_applications_source_job_id"),
        "job_applications",
        ["source_job_id"],
        unique=False,
    )

    op.add_column(
        "job_applications",
        sa.Column(
            "tracking_state",
            sa.String(length=50),
            server_default="applied",
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_job_applications_tracking_state"),
        "job_applications",
        ["tracking_state"],
        unique=False,
    )

    op.add_column(
        "job_applications",
        sa.Column("application_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "job_applications",
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_applications", "applied_at")
    op.drop_column("job_applications", "application_started_at")
    op.drop_index(op.f("ix_job_applications_tracking_state"), table_name="job_applications")
    op.drop_column("job_applications", "tracking_state")
    op.drop_index(op.f("ix_job_applications_source_job_id"), table_name="job_applications")
    op.drop_column("job_applications", "source_job_id")
