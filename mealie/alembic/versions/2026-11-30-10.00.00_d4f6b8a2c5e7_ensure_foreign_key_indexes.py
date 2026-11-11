"""Ensure the foreign key indexes of f3a1ae61d772 exist.

Revision ID: d4f6b8a2c5e7
Revises: c3e5a7b9d1f2
Create Date: 2026-11-30 10:00:00

The nutrition migrations were first applied on top of 5c1e7d2a9b3f. A database that ran them before
they were rebased on f3a1ae61d772 skipped that revision, so this one creates the missing indexes.

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4f6b8a2c5e7"
down_revision: str | None = "c3e5a7b9d1f2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

INDEXES = [
    ("ix_recipes_ingredients_recipe_id", "recipes_ingredients", "recipe_id"),
    ("ix_ingredient_foods_aliases_food_id", "ingredient_foods_aliases", "food_id"),
    ("ix_ingredient_units_aliases_unit_id", "ingredient_units_aliases", "unit_id"),
    (
        "ix_shopping_list_item_recipe_reference_shopping_list_item_id",
        "shopping_list_item_recipe_reference",
        "shopping_list_item_id",
    ),
    ("ix_shopping_list_recipe_reference_shopping_list_id", "shopping_list_recipe_reference", "shopping_list_id"),
]


def upgrade():
    inspector = sa.inspect(op.get_bind())
    for name, table, column in INDEXES:
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, [column], unique=False)


def downgrade():
    # The indexes belong to f3a1ae61d772, which drops them on its own downgrade.
    pass
