"""add scan input language

Revision ID: d92f6b3ac4c1
Revises: b6a3d3f4c8e2
Create Date: 2026-04-10 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d92f6b3ac4c1"
down_revision = "b6a3d3f4c8e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("input_language", sa.String(length=40), nullable=True))


def downgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.drop_column("input_language")
