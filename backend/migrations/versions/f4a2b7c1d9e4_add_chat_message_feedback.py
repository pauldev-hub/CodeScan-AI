"""add feedback field to chat messages

Revision ID: f4a2b7c1d9e4
Revises: e13a9a1f4b12
Create Date: 2026-04-11 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a2b7c1d9e4"
down_revision = "e13a9a1f4b12"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("feedback", sa.String(length=10), nullable=True))
        batch_op.create_check_constraint(
            "ck_chat_messages_feedback",
            "feedback IN ('like', 'dislike')",
        )


def downgrade():
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.drop_constraint("ck_chat_messages_feedback", type_="check")
        batch_op.drop_column("feedback")
