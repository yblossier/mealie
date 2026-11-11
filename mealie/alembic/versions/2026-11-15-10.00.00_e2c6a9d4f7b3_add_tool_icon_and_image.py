"""add tool icon and image

Revision ID: e2c6a9d4f7b3
Revises: d9b3f7a2e5c1
Create Date: 2026-11-15 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e2c6a9d4f7b3"
down_revision: str | None = "d9b3f7a2e5c1"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.add_column(sa.Column("icon", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("image", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.drop_column("image")
        batch_op.drop_column("icon")
