from __future__ import annotations

from typing import ClassVar

from pydantic import UUID4, ConfigDict

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import MealieOutModel
from mealie.schema.response.pagination import PaginationBase


class AllergenCreate(MealieModel):
    name: str
    code: str | None = None
    keywords: str = ""
    """Comma-separated words recognizing the allergen in an ingredient"""
    exclusions: str = ""
    """Comma-separated phrases containing a keyword without containing the allergen"""


class AllergenSave(AllergenCreate):
    group_id: UUID4


class AllergenUpdate(AllergenSave):
    id: UUID4


class AllergenOut(AllergenUpdate, MealieOutModel):
    _searchable_properties: ClassVar[list[str]] = ["name", "keywords"]
    model_config = ConfigDict(from_attributes=True)


class AllergenSummary(MealieOutModel):
    """An allergen linked to a food."""

    id: UUID4
    name: str
    code: str | None = None
    model_config = ConfigDict(from_attributes=True)


class AllergenPagination(PaginationBase):
    items: list[AllergenOut]


class RecipeAllergen(MealieOutModel):
    """An allergen found in a recipe, with the ingredients that bring it."""

    allergen_id: UUID4
    code: str | None = None
    name: str
    ingredients: list[str] = []
