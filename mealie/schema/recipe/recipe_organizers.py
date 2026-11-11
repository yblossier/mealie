"""
Categories, tags and tools: the organizers a recipe can carry.

Each organizer has the same shapes:

- `XCreate`: the body for creating or renaming one
- `XSave`: `XCreate` plus the group, as the repository stores it
- `XOut`: a saved organizer, both on its own and inside a recipe
- `XDraft`: an organizer inside a `RecipeDraft`, which may lack its id and slug until the server
  resolves or creates it
"""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, ClassVar

from pydantic import UUID4, ConfigDict, Field, field_validator, model_validator
from slugify import slugify
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from mealie.core.config import get_app_dirs
from mealie.db.models.recipe import Tool
from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import MealieOutModel
from mealie.schema.response.pagination import PaginationBase


def _household_slugs(households: Any) -> Any:
    if not households:
        return []

    try:
        return [household.slug for household in households]
    except AttributeError:
        return households


class OrganizerMerge(MealieModel):
    """Moves every recipe from one organizer to another, then deletes the first one."""

    from_id: UUID4
    to_id: UUID4


class OrganizerOut(MealieOutModel):
    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    recipe_count: int = 0
    """Only set where the query counts recipes, such as the organizer list routes."""

    _searchable_properties: ClassVar[list[str]] = ["name"]
    model_config = ConfigDict(from_attributes=True)


class OrganizerDraft(MealieModel):
    id: UUID4 | None = None
    group_id: UUID4 | None = None
    name: str
    slug: str | None = None
    recipe_count: int = 0

    _searchable_properties: ClassVar[list[str]] = ["name"]
    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name)


# Categories


class CategoryCreate(MealieModel):
    name: str


class CategorySave(CategoryCreate):
    group_id: UUID4


class CategoryOut(OrganizerOut):
    pass


class CategoryDraft(OrganizerDraft):
    pass


class CategoryPagination(PaginationBase):
    items: list[CategoryOut]


# Tags


class TagCreate(MealieModel):
    name: str


class TagSave(TagCreate):
    group_id: UUID4


class TagOut(OrganizerOut):
    pass


class TagDraft(OrganizerDraft):
    pass


class TagPagination(PaginationBase):
    items: list[TagOut]


# Tools


class ToolCategory(StrEnum):
    """The kind of tool, which also sets the icon it is shown with."""

    dishes = "dishes"
    linen = "linen"
    appliance = "appliance"
    utensils = "utensils"
    tableware = "tableware"
    cutlery = "cutlery"


class DishShape(StrEnum):
    rectangular = "rectangular"
    round = "round"


class DishUsage(StrEnum):
    """A heat source a dish can be used on or in."""

    induction = "induction"
    gas = "gas"
    oven = "oven"
    microwave = "microwave"


Centimeters = Annotated[float, Field(gt=0, le=1000)]


class ToolCreate(MealieModel):
    name: str
    households_with_tool: list[str] = []
    category: ToolCategory = ToolCategory.utensils

    dish_shape: DishShape | None = None
    """Only kept for dishes. A round dish is sized by its diameter, any other by length and width."""
    length: Centimeters | None = None
    width: Centimeters | None = None
    height: Centimeters | None = None
    diameter: Centimeters | None = None
    usages: list[DishUsage] = []
    """Only kept for dishes."""

    parent_id: UUID4 | None = None
    """Only kept for appliances: the appliance this accessory can't be used without."""

    @field_validator("usages", mode="after")
    @classmethod
    def dedupe_usages(cls, v: list[DishUsage]) -> list[DishUsage]:
        return [usage for usage in DishUsage if usage in v]

    @model_validator(mode="after")
    def drop_fields_of_other_categories(self) -> ToolCreate:
        if self.category != ToolCategory.dishes:
            self.dish_shape = None
            self.length = self.width = self.height = self.diameter = None
            self.usages = []
        elif self.dish_shape == DishShape.round:
            self.length = self.width = None
        else:
            self.diameter = None

        if self.category != ToolCategory.appliance:
            self.parent_id = None

        return self


class ToolSave(ToolCreate):
    group_id: UUID4


class ToolOut(OrganizerOut):
    households_with_tool: list[str] = []
    """Slugs of the households that own this tool."""
    category: ToolCategory = ToolCategory.utensils
    image: str | None = None
    """Cache key of the tool photo, unset when the tool has no photo."""

    dish_shape: DishShape | None = None
    length: float | None = None
    width: float | None = None
    height: float | None = None
    diameter: float | None = None
    usages: list[DishUsage] = []

    parent_id: UUID4 | None = None
    """The appliance this accessory can't be used without."""

    @field_validator("usages", mode="before")
    def split_usages(cls, v):
        if isinstance(v, str):
            return [usage for usage in v.split(",") if usage in DishUsage.__members__]
        return v or []

    @field_validator("category", mode="before")
    def default_unknown_category(cls, v):
        return v if v in ToolCategory.__members__ else ToolCategory.utensils

    @staticmethod
    def get_directory(tool_id: UUID4 | str) -> Path:
        return get_app_dirs().TOOLS_DIR / str(tool_id)

    @field_validator("households_with_tool", mode="before")
    def convert_households_to_slugs(cls, v):
        return _household_slugs(v)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [selectinload(Tool.households_with_tool)]


class ToolDraft(OrganizerDraft):
    households_with_tool: list[str] = []

    @field_validator("households_with_tool", mode="before")
    def convert_households_to_slugs(cls, v):
        return _household_slugs(v)


class ToolPagination(PaginationBase):
    items: list[ToolOut]
