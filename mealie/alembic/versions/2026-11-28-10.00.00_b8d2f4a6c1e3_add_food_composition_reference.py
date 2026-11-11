"""Add the food composition referential: the foods of the nutrition sources and their import settings.

Revision ID: b8d2f4a6c1e3
Revises: a7c9e1b3d5f8
Create Date: 2026-11-28 10:00:00

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "b8d2f4a6c1e3"
down_revision: str | None = "a7c9e1b3d5f8"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "food_composition_foods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("name_en", sa.String(length=512), nullable=True),
        sa.Column("group_code", sa.String(length=16), nullable=True),
        sa.Column("nutrients", sa.JSON(), nullable=False),
        sa.Column("average_weight", sa.Float(), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "code", name="food_composition_foods_source_code_key"),
    )
    op.create_index(
        op.f("ix_food_composition_foods_created_at"), "food_composition_foods", ["created_at"], unique=False
    )
    op.create_index("ix_food_composition_foods_source_name", "food_composition_foods", ["source", "name"], unique=False)

    op.create_table(
        "food_composition_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("release_time", sa.String(length=64), nullable=True),
        sa.Column("imported_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("food_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source"),
    )
    op.create_index(
        op.f("ix_food_composition_sources_created_at"), "food_composition_sources", ["created_at"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_food_composition_sources_created_at"), table_name="food_composition_sources")
    op.drop_table("food_composition_sources")
    op.drop_index("ix_food_composition_foods_source_name", table_name="food_composition_foods")
    op.drop_index(op.f("ix_food_composition_foods_created_at"), table_name="food_composition_foods")
    op.drop_table("food_composition_foods")
