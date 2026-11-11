"""'add recipe_step_ref_link'

Revision ID: c7d1e5f9a3b2
Revises: b4e8d2a6c9f1
Create Date: 2026-11-19 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

import mealie.db.migration_types

# revision identifiers, used by Alembic.
revision = "c7d1e5f9a3b2"
down_revision: str | None = "b4e8d2a6c9f1"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade():
    op.create_table(
        "recipe_step_ref_link",
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
    with op.batch_alter_table("recipe_step_ref_link", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_recipe_step_ref_link_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_step_ref_link_instruction_id"), ["instruction_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_recipe_step_ref_link_reference_id"), ["reference_id"], unique=False)


def downgrade():
    with op.batch_alter_table("recipe_step_ref_link", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_recipe_step_ref_link_reference_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_step_ref_link_instruction_id"))
        batch_op.drop_index(batch_op.f("ix_recipe_step_ref_link_created_at"))

    op.drop_table("recipe_step_ref_link")
