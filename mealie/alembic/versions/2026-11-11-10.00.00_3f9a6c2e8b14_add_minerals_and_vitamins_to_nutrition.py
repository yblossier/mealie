"""add minerals and vitamins to nutrition

Revision ID: 3f9a6c2e8b14
Revises: 8d4e2b7c1f6a
Create Date: 2026-11-11 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3f9a6c2e8b14"
down_revision: str | None = "8d4e2b7c1f6a"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

TABLES = ("recipe_nutrition", "ingredient_foods_nutrition")


def upgrade():
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("calcium_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("iron_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("magnesium_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("potassium_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("vitamin_a_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("vitamin_c_content", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("vitamin_d_content", sa.String(), nullable=True))


def downgrade():
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("vitamin_d_content")
            batch_op.drop_column("vitamin_c_content")
            batch_op.drop_column("vitamin_a_content")
            batch_op.drop_column("potassium_content")
            batch_op.drop_column("magnesium_content")
            batch_op.drop_column("iron_content")
            batch_op.drop_column("calcium_content")
