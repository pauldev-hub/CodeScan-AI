"""add scan summary json columns

Revision ID: b6a3d3f4c8e2
Revises: a1f3b9f9d001
Create Date: 2026-04-08 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b6a3d3f4c8e2"
down_revision = "a1f3b9f9d001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pros_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("cons_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("refactor_suggestions_json", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("scans", schema=None) as batch_op:
        batch_op.drop_column("refactor_suggestions_json")
        batch_op.drop_column("cons_json")
        batch_op.drop_column("pros_json")
