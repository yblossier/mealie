"""Add the group allergens.

Revision ID: e9b2c6d4f1a7
Revises: d3f7a1c5e8b4
Create Date: 2026-11-21 10:00:00

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "e9b2c6d4f1a7"
down_revision: str | None = "d3f7a1c5e8b4"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "allergens",
        sa.Column("id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("exclusions", sa.Text(), nullable=False),
        sa.Column("group_id", mealie.db.migration_types.GUID(), nullable=False),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "group_id", name="allergens_name_group_id_key"),
    )
    with op.batch_alter_table("allergens", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_allergens_code"), ["code"], unique=False)
        batch_op.create_index(batch_op.f("ix_allergens_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_allergens_group_id"), ["group_id"], unique=False)


def downgrade():
    with op.batch_alter_table("allergens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_allergens_group_id"))
        batch_op.drop_index(batch_op.f("ix_allergens_created_at"))
        batch_op.drop_index(batch_op.f("ix_allergens_code"))

    op.drop_table("allergens")
