"""add api scan id

Revision ID: a1f3b9f9d001
Revises: cad15f6476cd
Create Date: 2026-04-02 16:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision = "a1f3b9f9d001"
down_revision = "cad15f6476cd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("api_scan_id", sa.String(length=36), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM scans")).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE scans SET api_scan_id = :api_scan_id WHERE id = :id"),
            {"api_scan_id": str(uuid.uuid4()), "id": row.id},
        )

    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.alter_column("api_scan_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index(batch_op.f("ix_scans_api_scan_id"), ["api_scan_id"], unique=True)


def downgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_scans_api_scan_id"))
        batch_op.drop_column("api_scan_id")
