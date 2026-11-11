from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import UUID4, ConfigDict, Field, StringConstraints, field_validator, model_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import MealieOutModel

TABLE_PAGE_SIZE_MIN = 5
TABLE_PAGE_SIZE_MAX = 500
DEFAULT_TABLE_PAGE_SIZE = 15

TablePageSize = Annotated[int, Field(ge=TABLE_PAGE_SIZE_MIN, le=TABLE_PAGE_SIZE_MAX)]


class ToolSupplier(MealieModel):
    """A shop where a missing tool can be searched for."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    """The search URL; `{query}` or `%s` is replaced by the tool name, otherwise the name is appended."""
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.lower().startswith(("http://", "https://")):
            raise ValueError("The supplier URL must start with http:// or https://")
        return v


def default_tool_suppliers() -> list[ToolSupplier]:
    return [ToolSupplier(name="Amazon", url="https://www.amazon.fr/s?k={query}", enabled=True)]


class OpenFoodFactsMode(StrEnum):
    prod = "prod"
    dev = "dev"


OptionalText = Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=200)]


class GroupPreferencesUpdate(MealieModel):
    private_group: bool = True
    show_announcements: bool = True
    default_table_page_size: TablePageSize = DEFAULT_TABLE_PAGE_SIZE
    tool_suppliers: list[ToolSupplier] = Field(default_factory=default_tool_suppliers)
    show_tool_supplier_links: bool = True

    off_mode: OpenFoodFactsMode = OpenFoodFactsMode.prod
    off_app_name: OptionalText = None
    off_app_version: OptionalText = None
    off_app_uuid: OptionalText = None

    usda_api_enabled: bool = True
    usda_api_key: OptionalText = None
    """Write only: None keeps the saved key, an empty string removes it"""

    @field_validator("tool_suppliers", mode="before")
    @classmethod
    def none_to_empty(cls, v):
        return [] if v is None else v

    @field_validator("off_app_name", "off_app_version", "off_app_uuid")
    @classmethod
    def empty_to_none(cls, v: str | None) -> str | None:
        return v or None


class GroupPreferencesCreate(GroupPreferencesUpdate):
    group_id: UUID


class GroupPreferencesOut(GroupPreferencesCreate, MealieOutModel):
    id: UUID4
    usda_api_key: str | None = Field(default=None, exclude=True)
    """Never sent to the clients"""
    usda_api_key_set: bool = False
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_usda_api_key_set(self) -> Self:
        self.usda_api_key_set = bool(self.usda_api_key)
        return self
