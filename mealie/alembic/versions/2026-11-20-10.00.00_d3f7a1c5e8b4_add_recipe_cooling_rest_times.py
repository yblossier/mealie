"""Add cooling and rest times to recipes.

Revision ID: d3f7a1c5e8b4
Revises: c7d1e5f9a3b2
Create Date: 2026-11-20 10:00:00

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "d3f7a1c5e8b4"
down_revision: str | None = "c7d1e5f9a3b2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cooling_time_seconds", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rest_time_seconds", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.drop_column("rest_time_seconds")
        batch_op.drop_column("cooling_time_seconds")
