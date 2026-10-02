"""add email verification fields to users

Revision ID: 0004_email_verification
Revises: 0003_auth_provider_and_password_hash
Create Date: 2026-09-22 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_email_verification"
down_revision: Union[str, None] = "0003_auth_provider_and_password_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False)
        )
        batch_op.add_column(
            sa.Column("email_verification_token_hash", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("email_verification_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            "ix_users_email_verification_token_hash",
            ["email_verification_token_hash"],
            unique=False,
        )

    # For existing users (especially google users), set email_verified = true
    op.execute("UPDATE users SET email_verified = true WHERE auth_provider = 'google'")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email_verification_token_hash")
        batch_op.drop_column("email_verification_expires_at")
        batch_op.drop_column("email_verification_token_hash")
        batch_op.drop_column("email_verified")
