"""add resume file size bytes column

Revision ID: 0011_add_resume_file_size_bytes
Revises: 0010_add_application_tracking_state
Create Date: 2026-10-01 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_add_resume_file_size_bytes"
down_revision: Union[str, None] = "0010_add_application_tracking_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resumes",
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("resumes", "file_size_bytes")
