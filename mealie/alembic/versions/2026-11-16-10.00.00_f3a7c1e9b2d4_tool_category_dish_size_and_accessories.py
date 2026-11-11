"""replace tool icon with category, add dish size, usages and accessory parent

Revision ID: f3a7c1e9b2d4
Revises: e2c6a9d4f7b3
Create Date: 2026-11-16 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "f3a7c1e9b2d4"
down_revision: str | None = "e2c6a9d4f7b3"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

CATEGORIES = ("dishes", "linen", "appliance", "utensils", "tableware", "cutlery")


def upgrade():
    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(), nullable=False, server_default="utensils"))
        batch_op.add_column(sa.Column("dish_shape", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("length", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("width", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("height", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("diameter", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("usages", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("parent_id", mealie.db.migration_types.GUID(), nullable=True))
        batch_op.create_index(batch_op.f("ix_tools_parent_id"), ["parent_id"], unique=False)
        batch_op.create_foreign_key("fk_tools_parent_id", "tools", ["parent_id"], ["id"], ondelete="SET NULL")

    # a preset icon was the kind of tool, so it becomes the category; custom icons fall back to the default
    tools = sa.table("tools", sa.column("icon", sa.String()), sa.column("category", sa.String()))
    op.execute(tools.update().where(tools.c.icon.in_(CATEGORIES)).values(category=tools.c.icon))

    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.drop_column("icon")


def downgrade():
    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.add_column(sa.Column("icon", sa.String(), nullable=True))

    tools = sa.table("tools", sa.column("icon", sa.String()), sa.column("category", sa.String()))
    op.execute(tools.update().values(icon=tools.c.category))

    with op.batch_alter_table("tools", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tools_parent_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_tools_parent_id"))
        batch_op.drop_column("parent_id")
        batch_op.drop_column("usages")
        batch_op.drop_column("diameter")
        batch_op.drop_column("height")
        batch_op.drop_column("width")
        batch_op.drop_column("length")
        batch_op.drop_column("dish_shape")
        batch_op.drop_column("category")
