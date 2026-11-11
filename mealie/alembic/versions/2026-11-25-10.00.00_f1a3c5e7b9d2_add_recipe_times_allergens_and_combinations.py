"""Add the recipe cooling and rest times, the food allergens and the combination substitutions.

Revision ID: f1a3c5e7b9d2
Revises: e9b2c6d4f1a7
Create Date: 2026-11-25 10:00:00

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "f1a3c5e7b9d2"
down_revision: str | None = "e9b2c6d4f1a7"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def _create_association(table: str, left: str, left_target: str, right: str, right_target: str, key: str):
    op.create_table(
        table,
        sa.Column(left, mealie.db.migration_types.GUID(), nullable=True),
        sa.Column(right, mealie.db.migration_types.GUID(), nullable=True),
        sa.ForeignKeyConstraint([left], [left_target], ondelete="CASCADE"),
        sa.ForeignKeyConstraint([right], [right_target], ondelete="CASCADE"),
        sa.UniqueConstraint(left, right, name=key),
    )
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.create_index(batch_op.f(f"ix_{table}_{left}"), [left], unique=False)
        batch_op.create_index(batch_op.f(f"ix_{table}_{right}"), [right], unique=False)


def _drop_association(table: str, left: str, right: str):
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.drop_index(batch_op.f(f"ix_{table}_{right}"))
        batch_op.drop_index(batch_op.f(f"ix_{table}_{left}"))

    op.drop_table(table)


def upgrade():
    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cooling_time", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("rest_time", sa.String(), nullable=True))

    with op.batch_alter_table("recipe_settings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("show_allergens", sa.Boolean(), nullable=True))
    op.execute("UPDATE recipe_settings SET show_allergens = TRUE")

    _create_association(
        "ingredient_foods_to_allergens",
        "food_id",
        "ingredient_foods.id",
        "allergen_id",
        "allergens.id",
        "ingredient_foods_to_allergens_key",
    )
    _create_association(
        "ingredient_foods_substitutions_additional_foods",
        "substitution_id",
        "ingredient_foods_substitutions.id",
        "food_id",
        "ingredient_foods.id",
        "ingredient_foods_substitutions_additional_foods_key",
    )
    _create_association(
        "recipes_ingredients_substitutions_additional_foods",
        "substitution_id",
        "recipes_ingredients_substitutions.id",
        "food_id",
        "ingredient_foods.id",
        "recipes_ingredients_substitutions_additional_foods_key",
    )


def downgrade():
    _drop_association("recipes_ingredients_substitutions_additional_foods", "substitution_id", "food_id")
    _drop_association("ingredient_foods_substitutions_additional_foods", "substitution_id", "food_id")
    _drop_association("ingredient_foods_to_allergens", "food_id", "allergen_id")

    with op.batch_alter_table("recipe_settings", schema=None) as batch_op:
        batch_op.drop_column("show_allergens")

    with op.batch_alter_table("recipes", schema=None) as batch_op:
        batch_op.drop_column("rest_time")
        batch_op.drop_column("cooling_time")
