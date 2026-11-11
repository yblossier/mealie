"""add ingredient food nutrition

Revision ID: 8d4e2b7c1f6a
Revises: f3a1ae61d772
Create Date: 2026-11-10 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "8d4e2b7c1f6a"
down_revision: str | None = "f3a1ae61d772"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "ingredient_foods_nutrition",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("food_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("calories", sa.String(), nullable=True),
        sa.Column("carbohydrate_content", sa.String(), nullable=True),
        sa.Column("cholesterol_content", sa.String(), nullable=True),
        sa.Column("fat_content", sa.String(), nullable=True),
        sa.Column("fiber_content", sa.String(), nullable=True),
        sa.Column("protein_content", sa.String(), nullable=True),
        sa.Column("saturated_fat_content", sa.String(), nullable=True),
        sa.Column("sodium_content", sa.String(), nullable=True),
        sa.Column("sugar_content", sa.String(), nullable=True),
        sa.Column("trans_fat_content", sa.String(), nullable=True),
        sa.Column("unsaturated_fat_content", sa.String(), nullable=True),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["food_id"],
            ["ingredient_foods.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ingredient_foods_nutrition", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ingredient_foods_nutrition_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_ingredient_foods_nutrition_food_id"), ["food_id"], unique=True)


def downgrade():
    with op.batch_alter_table("ingredient_foods_nutrition", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ingredient_foods_nutrition_food_id"))
        batch_op.drop_index(batch_op.f("ix_ingredient_foods_nutrition_created_at"))

    op.drop_table("ingredient_foods_nutrition")
