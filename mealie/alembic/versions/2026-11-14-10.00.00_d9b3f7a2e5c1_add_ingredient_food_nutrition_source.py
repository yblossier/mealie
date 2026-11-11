"""add ingredient food nutrition source

Revision ID: d9b3f7a2e5c1
Revises: c4a8e2f6d1b9
Create Date: 2026-11-14 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d9b3f7a2e5c1"
down_revision: str | None = "c4a8e2f6d1b9"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("ingredient_foods", schema=None) as batch_op:
        batch_op.add_column(sa.Column("nutrition_source", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("nutrition_reference_code", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("nutrition_reference_name", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("ingredient_foods", schema=None) as batch_op:
        batch_op.drop_column("nutrition_reference_name")
        batch_op.drop_column("nutrition_reference_code")
        batch_op.drop_column("nutrition_source")
