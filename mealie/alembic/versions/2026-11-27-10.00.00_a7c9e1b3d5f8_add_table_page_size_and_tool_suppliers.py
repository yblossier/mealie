"""Add the configuration table page size, the tool suppliers and the nutrition APIs preferences,
and let several food substitution combinations share their first food.

Revision ID: a7c9e1b3d5f8
Revises: f1a3c5e7b9d2
Create Date: 2026-11-27 10:00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c9e1b3d5f8"
down_revision: str | None = "f1a3c5e7b9d2"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

# Existing groups keep the Amazon search link they had before suppliers became configurable.
DEFAULT_TOOL_SUPPLIERS = [{"name": "Amazon", "url": "https://www.amazon.fr/s?k={query}", "enabled": True}]


def upgrade():
    with op.batch_alter_table("group_preferences", schema=None) as batch_op:
        batch_op.add_column(sa.Column("default_table_page_size", sa.Integer(), nullable=False, server_default="15"))
        batch_op.add_column(sa.Column("tool_suppliers", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("show_tool_supplier_links", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("off_mode", sa.String(), nullable=False, server_default="prod"))
        batch_op.add_column(sa.Column("off_app_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("off_app_version", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("off_app_uuid", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("usda_api_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("usda_api_key", sa.String(), nullable=True))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("table_page_size", sa.Integer(), nullable=True))

    group_preferences = sa.table("group_preferences", sa.column("tool_suppliers", sa.JSON()))
    op.execute(group_preferences.update().values(tool_suppliers=DEFAULT_TOOL_SUPPLIERS))

    # Combinations sharing their first food ("butter + flour", "butter + oil") are distinct substitutions
    with op.batch_alter_table("ingredient_foods_substitutions", schema=None) as batch_op:
        batch_op.drop_constraint("ingredient_foods_substitutions_food_ids_key", type_="unique")


def downgrade():
    # Only one substitution per (food, first substitute food) survives the restored constraint
    op.execute(
        """
        DELETE FROM ingredient_foods_substitutions_additional_foods
        WHERE substitution_id IN (
            SELECT s.id FROM ingredient_foods_substitutions s
            WHERE s.substitute_food_id IS NOT NULL AND EXISTS (
                SELECT 1 FROM ingredient_foods_substitutions o
                WHERE o.food_id = s.food_id AND o.substitute_food_id = s.substitute_food_id AND o.id < s.id
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM ingredient_foods_substitutions
        WHERE substitute_food_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM ingredient_foods_substitutions o
            WHERE o.food_id = ingredient_foods_substitutions.food_id
            AND o.substitute_food_id = ingredient_foods_substitutions.substitute_food_id
            AND o.id < ingredient_foods_substitutions.id
        )
        """
    )
    with op.batch_alter_table("ingredient_foods_substitutions", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "ingredient_foods_substitutions_food_ids_key", ["food_id", "substitute_food_id"]
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("table_page_size")

    with op.batch_alter_table("group_preferences", schema=None) as batch_op:
        batch_op.drop_column("usda_api_key")
        batch_op.drop_column("usda_api_enabled")
        batch_op.drop_column("off_app_uuid")
        batch_op.drop_column("off_app_version")
        batch_op.drop_column("off_app_name")
        batch_op.drop_column("off_mode")
        batch_op.drop_column("show_tool_supplier_links")
        batch_op.drop_column("tool_suppliers")
        batch_op.drop_column("default_table_page_size")
