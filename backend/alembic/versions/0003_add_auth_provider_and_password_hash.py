"""add auth_provider and password_hash to users and make google_id nullable

Revision ID: 0003_auth_provider_and_password_hash
Revises: 0002_onboarding_fields
Create Date: 2026-09-22 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_auth_provider_and_password_hash"
down_revision: Union[str, None] = "0002_onboarding_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("password_hash", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("auth_provider", sa.String(length=50), server_default="google", nullable=False)
        )
        batch_op.alter_column(
            "google_id",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "google_id",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        batch_op.drop_column("auth_provider")
        batch_op.drop_column("password_hash")
