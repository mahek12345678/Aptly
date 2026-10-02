"""remove email auth fields from users

Revision ID: 0005_remove_email_auth_fields
Revises: 0004_email_verification
Create Date: 2026-09-23 13:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_remove_email_auth_fields"
down_revision: Union[str, None] = "0004_email_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up any leftover temp table from failed batch alter in SQLite
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_users")
    # Purge any legacy email-only users that don't have a google_id
    op.execute("DELETE FROM users WHERE google_id IS NULL")

    with op.batch_alter_table("users") as batch_op:
        # Drop email verification index and columns
        try:
            batch_op.drop_index("ix_users_email_verification_token_hash")
        except Exception:
            pass
        batch_op.drop_column("email_verification_expires_at")
        batch_op.drop_column("email_verification_token_hash")
        batch_op.drop_column("email_verified")
        # Drop email/password authentication columns
        batch_op.drop_column("auth_provider")
        batch_op.drop_column("password_hash")
        # Ensure google_id is non-nullable for Google-only auth
        batch_op.alter_column(
            "google_id",
            existing_type=sa.String(length=255),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "google_id",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("password_hash", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("auth_provider", sa.String(length=50), server_default="google", nullable=False)
        )
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), server_default="true", nullable=False)
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
