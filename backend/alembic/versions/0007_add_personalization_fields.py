"""add personalization fields to user_preferences

Revision ID: 0007_add_personalization_fields
Revises: 0006_add_resume_parsing_fields
Create Date: 2026-09-23 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_add_personalization_fields"
down_revision: Union[str, None] = "0006_add_resume_parsing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user_preferences")

    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.add_column(
            sa.Column("focus_opportunity_matching", sa.Boolean(), server_default="true", nullable=False)
        )
        batch_op.add_column(
            sa.Column("focus_resume_tailoring", sa.Boolean(), server_default="true", nullable=False)
        )
        batch_op.add_column(
            sa.Column("focus_deadline_tracking", sa.Boolean(), server_default="true", nullable=False)
        )
        batch_op.add_column(
            sa.Column("update_frequency", sa.String(length=50), server_default="daily", nullable=False)
        )
        batch_op.add_column(
            sa.Column("additional_notes", sa.String(length=300), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch_op:
        batch_op.drop_column("additional_notes")
        batch_op.drop_column("update_frequency")
        batch_op.drop_column("focus_deadline_tracking")
        batch_op.drop_column("focus_resume_tailoring")
        batch_op.drop_column("focus_opportunity_matching")
