from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, orm
from sqlalchemy.orm import Mapped, mapped_column

from mealie.db.models._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase

from .._model_utils.auto_init import AutoInitOptions, auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..group.group import Group
    from .ingredient import IngredientFoodModel


class Allergen(SqlAlchemyBase, BaseMixins):
    """A food allergen of the group, recognized in recipe ingredients through its keywords."""

    __tablename__ = "allergens"
    __table_args__ = (UniqueConstraint("name", "group_id", name="allergens_name_group_id_key"),)

    id: FilterableColumn[GUID] = mapped_column(GUID, default=GUID.generate, primary_key=True)
    code: FilterableColumn[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: FilterableColumn[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="")
    exclusions: Mapped[str] = mapped_column(Text, nullable=False, default="")

    group_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped[Group] = orm.relationship("Group", back_populates="allergens")
    foods: Mapped[list[IngredientFoodModel]] = orm.relationship(
        "IngredientFoodModel", secondary="ingredient_foods_to_allergens", back_populates="allergens"
    )

    model_config = AutoInitOptions(exclude={"foods"})

    @auto_init()
    def __init__(self, **_) -> None:
        pass
