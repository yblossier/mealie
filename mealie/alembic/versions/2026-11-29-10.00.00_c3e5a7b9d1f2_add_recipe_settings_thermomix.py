"""Add the Thermomix setting of the recipes.

Revision ID: c3e5a7b9d1f2
Revises: b8d2f4a6c1e3
Create Date: 2026-11-29 10:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e5a7b9d1f2"
down_revision: str | None = "b8d2f4a6c1e3"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("recipe_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("thermomix", sa.Boolean(), nullable=True))
    op.execute("UPDATE recipe_settings SET thermomix = FALSE")


def downgrade():
    with op.batch_alter_table("recipe_settings", schema=None) as batch_op:
        batch_op.drop_column("thermomix")
