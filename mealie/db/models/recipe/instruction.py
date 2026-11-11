from sqlalchemy import ForeignKey, Integer, String, orm
from sqlalchemy.orm import Mapped, mapped_column

from .._model_base import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import AutoInitOptions, auto_init
from .._model_utils.guid import GUID


class RecipeIngredientRefLink(SqlAlchemyBase, BaseMixins):
    __tablename__ = "recipe_ingredient_ref_link"
    instruction_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("recipe_instructions.id"), index=True)
    reference_id: Mapped[GUID | None] = mapped_column(GUID, index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class RecipeNoteRefLink(SqlAlchemyBase, BaseMixins):
    __tablename__ = "recipe_note_ref_link"
    instruction_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("recipe_instructions.id"), index=True)
    reference_id: Mapped[GUID | None] = mapped_column(GUID, index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class RecipeToolRefLink(SqlAlchemyBase, BaseMixins):
    __tablename__ = "recipe_tool_ref_link"
    instruction_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("recipe_instructions.id"), index=True)
    reference_id: Mapped[GUID | None] = mapped_column(GUID, index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class RecipeStepRefLink(SqlAlchemyBase, BaseMixins):
    """A step whose result is used as a base by the instruction"""

    __tablename__ = "recipe_step_ref_link"
    instruction_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("recipe_instructions.id"), index=True)
    reference_id: Mapped[GUID | None] = mapped_column(GUID, index=True)

    @auto_init()
    def __init__(self, **_) -> None:
        pass


class RecipeInstruction(SqlAlchemyBase):
    __tablename__ = "recipe_instructions"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    recipe_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("recipes.id"), index=True)
    position: Mapped[int | None] = mapped_column(Integer, index=True)
    type: Mapped[str | None] = mapped_column(String, default="")
    title: Mapped[str | None] = mapped_column(String)  # This is the section title
    text: Mapped[str | None] = mapped_column(String)
    summary: Mapped[str | None] = mapped_column(String)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    cooling_seconds: Mapped[int | None] = mapped_column(Integer)
    cooking_seconds: Mapped[int | None] = mapped_column(Integer)
    rest_seconds: Mapped[int | None] = mapped_column(Integer)

    ingredient_references: Mapped[list[RecipeIngredientRefLink]] = orm.relationship(
        RecipeIngredientRefLink, cascade="all, delete-orphan"
    )
    note_references: Mapped[list[RecipeNoteRefLink]] = orm.relationship(RecipeNoteRefLink, cascade="all, delete-orphan")
    tool_references: Mapped[list[RecipeToolRefLink]] = orm.relationship(RecipeToolRefLink, cascade="all, delete-orphan")
    step_references: Mapped[list[RecipeStepRefLink]] = orm.relationship(RecipeStepRefLink, cascade="all, delete-orphan")
    model_config = AutoInitOptions(
        exclude={
            "id",
            "ingredient_references",
            "note_references",
            "tool_references",
            "step_references",
        }
    )

    @auto_init()
    def __init__(
        self,
        session,
        ingredient_references=None,
        note_references=None,
        tool_references=None,
        step_references=None,
        **_,
    ) -> None:
        self.ingredient_references = [
            RecipeIngredientRefLink(**ref, session=session) for ref in (ingredient_references or [])
        ]
        self.note_references = [RecipeNoteRefLink(**ref, session=session) for ref in (note_references or [])]
        self.tool_references = [RecipeToolRefLink(**ref, session=session) for ref in (tool_references or [])]
        self.step_references = [RecipeStepRefLink(**ref, session=session) for ref in (step_references or [])]
