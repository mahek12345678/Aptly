"""add resume parsing fields to resumes

Revision ID: 0006_add_resume_parsing_fields
Revises: 0005_remove_email_auth_fields
Create Date: 2026-09-23 14:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_add_resume_parsing_fields"
down_revision: Union[str, None] = "0005_remove_email_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_resumes")

    with op.batch_alter_table("resumes") as batch_op:
        batch_op.add_column(sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("parse_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("parsed_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("resumes") as batch_op:
        batch_op.drop_column("parsed_data")
        batch_op.drop_column("parse_error")
        batch_op.drop_column("parsed_at")
