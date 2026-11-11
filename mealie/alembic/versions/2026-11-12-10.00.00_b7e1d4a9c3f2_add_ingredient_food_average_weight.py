"""add ingredient food average weight

Revision ID: b7e1d4a9c3f2
Revises: 3f9a6c2e8b14
Create Date: 2026-11-12 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7e1d4a9c3f2"
down_revision: str | None = "3f9a6c2e8b14"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("ingredient_foods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("average_weight", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("ingredient_foods", schema=None) as batch_op:
        batch_op.drop_column("average_weight")
