"""add ingredient food nutrition logs

Revision ID: c4a8e2f6d1b9
Revises: b7e1d4a9c3f2
Create Date: 2026-11-13 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "c4a8e2f6d1b9"
down_revision: str | None = "b7e1d4a9c3f2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "ingredient_foods_nutrition_logs",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("food_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("ai_model", sa.String(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("corrections", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["food_id"], ["ingredient_foods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ingredient_foods_nutrition_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingredient_foods_nutrition_logs_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_ingredient_foods_nutrition_logs_food_id"), ["food_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ingredient_foods_nutrition_logs_group_id"), ["group_id"], unique=False)


def downgrade():
    with op.batch_alter_table("ingredient_foods_nutrition_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingredient_foods_nutrition_logs_group_id"))
        batch_op.drop_index(batch_op.f("ix_ingredient_foods_nutrition_logs_food_id"))
        batch_op.drop_index(batch_op.f("ix_ingredient_foods_nutrition_logs_created_at"))

    op.drop_table("ingredient_foods_nutrition_logs")
