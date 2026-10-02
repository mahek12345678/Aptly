"""create job_listings and daily_matches tables

Revision ID: 0009_create_job_listings_and_daily_matches
Revises: 0008_add_job_application_fields
Create Date: 2026-09-23 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0009_create_job_listings_and_daily_matches"
down_revision: Union[str, None] = "0008_add_job_application_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create job_listings table
    op.create_table(
        "job_listings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), server_default="mock", nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role_title", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("employment_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("application_url", sa.String(length=1024), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("compensation", sa.String(length=100), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_job_listings_external_id"), "job_listings", ["external_id"], unique=False)
    op.create_index(op.f("ix_job_listings_source"), "job_listings", ["source"], unique=False)

    # 2. Create daily_matches table
    op.create_table(
        "daily_matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_listing_id", UUID(as_uuid=True), sa.ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("preference_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("final_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("match_reasons", sa.JSON(), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dismissed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("saved", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(op.f("ix_daily_matches_user_id"), "daily_matches", ["user_id"], unique=False)
    op.create_index(op.f("ix_daily_matches_job_listing_id"), "daily_matches", ["job_listing_id"], unique=False)
    op.create_index(op.f("ix_daily_matches_dismissed"), "daily_matches", ["dismissed"], unique=False)
    op.create_index(op.f("ix_daily_matches_saved"), "daily_matches", ["saved"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_matches_saved"), table_name="daily_matches")
    op.drop_index(op.f("ix_daily_matches_dismissed"), table_name="daily_matches")
    op.drop_index(op.f("ix_daily_matches_job_listing_id"), table_name="daily_matches")
    op.drop_index(op.f("ix_daily_matches_user_id"), table_name="daily_matches")
    op.drop_table("daily_matches")

    op.drop_index(op.f("ix_job_listings_source"), table_name="job_listings")
    op.drop_index(op.f("ix_job_listings_external_id"), table_name="job_listings")
    op.drop_table("job_listings")
