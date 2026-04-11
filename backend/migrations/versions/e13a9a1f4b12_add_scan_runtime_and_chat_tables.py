"""add scan runtime metadata and chat persistence tables

Revision ID: e13a9a1f4b12
Revises: d92f6b3ac4c1
Create Date: 2026-04-10 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e13a9a1f4b12"
down_revision = "d92f6b3ac4c1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("about_me", sa.Text(), nullable=True))

    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("queue_mode", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("ai_provider_used", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("learn_content_json", sa.Text(), nullable=True))

    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_conversations_scan_id", "chat_conversations", ["scan_id"], unique=False)
    op.create_index("idx_chat_conversations_user_updated", "chat_conversations", ["user_id", "updated_at"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_messages_role"),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_messages_conversation_created", "chat_messages", ["conversation_id", "created_at"], unique=False)


def downgrade():
    op.drop_index("idx_chat_messages_conversation_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("idx_chat_conversations_user_updated", table_name="chat_conversations")
    op.drop_index("idx_chat_conversations_scan_id", table_name="chat_conversations")
    op.drop_table("chat_conversations")

    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.drop_column("learn_content_json")
        batch_op.drop_column("ai_provider_used")
        batch_op.drop_column("queue_mode")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("about_me")
        batch_op.drop_column("age")
        batch_op.drop_column("name")
