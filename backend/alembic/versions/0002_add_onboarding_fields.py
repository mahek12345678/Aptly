"""add onboarding fields to user

Revision ID: 0002_onboarding_fields
Revises: 0001_initial
Create Date: 2026-09-22 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_onboarding_fields"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_step")
    op.drop_column("users", "onboarding_completed")
