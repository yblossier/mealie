"""'add recipe_tool_ref_link'

Revision ID: 8d2e4b6f1a3c
Revises: f3a7c1e9b2d4
Create Date: 2026-11-17 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "8d2e4b6f1a3c"
down_revision: str | None = "f3a7c1e9b2d4"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "recipe_tool_ref_link",
        sa.Column("instruction_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("reference_id", mealie.db.migration_types.GUID(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", mealie.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["instruction_id"],
            ["recipe_instructions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("recipe_tool_ref_link", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_recipe_tool_ref_link_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_tool_ref_link_instruction_id"), ["instruction_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_tool_ref_link_reference_id"), ["reference_id"], unique=False)


def downgrade():
    with op.batch_alter_table("recipe_tool_ref_link", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recipe_tool_ref_link_reference_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_tool_ref_link_instruction_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_tool_ref_link_created_at"))

    op.drop_table("recipe_tool_ref_link")
