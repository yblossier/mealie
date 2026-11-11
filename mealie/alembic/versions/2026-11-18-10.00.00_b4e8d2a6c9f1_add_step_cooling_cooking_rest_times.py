"""Add cooling, cooking and rest times to recipe steps.

Revision ID: b4e8d2a6c9f1
Revises: 8d2e4b6f1a3c
Create Date: 2026-11-18 10:00:00

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "b4e8d2a6c9f1"
down_revision: str | None = "8d2e4b6f1a3c"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("recipe_instructions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cooling_seconds", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("cooking_seconds", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rest_seconds", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("recipe_instructions", schema=None) as batch_op:
        batch_op.drop_column("rest_seconds")
        batch_op.drop_column("cooking_seconds")
        batch_op.drop_column("cooling_seconds")
