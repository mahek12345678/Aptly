"""add job application fields

Revision ID: 0008_add_job_application_fields
Revises: 0007_add_personalization_fields
Create Date: 2026-09-23 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_add_job_application_fields"
down_revision: Union[str, None] = "0007_add_personalization_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("job_applications") as batch_op:
        batch_op.add_column(
            sa.Column("application_url", sa.String(length=1024), nullable=True)
        )
        batch_op.add_column(
            sa.Column("notes", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("source", sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("job_applications") as batch_op:
        batch_op.drop_column("source")
        batch_op.drop_column("notes")
        batch_op.drop_column("application_url")
