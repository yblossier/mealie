from datetime import datetime
from typing import Annotated

from pydantic import StringConstraints, field_validator

from mealie.schema._mealie import MealieModel
from mealie.schema._mealie.mealie_model import MealieOutModel
from mealie.services.recipe.ciqual_import import CiqualImportError, parse_dataset_url


class FoodCompositionSourceCount(MealieOutModel):
    source: str
    imported_count: int = 0
    """The foods imported from the source's table, or bundled with Mealie when it was never imported"""
    api_count: int = 0
    """The foods found through the source's API and kept to enrich the referential"""
    bundled: bool = False
    """Whether the imported foods are the table bundled with Mealie, the source not being imported yet"""


class FoodCompositionStatus(MealieOutModel):
    ciqual_url: str
    ciqual_default_url: str
    ciqual_status: str = "idle"
    """idle, running, success or error"""
    ciqual_version: str | None = None
    """The version of the dataset, and the date of its files"""
    ciqual_release_time: str | None = None
    ciqual_imported_at: datetime | None = None
    ciqual_started_at: datetime | None = None
    ciqual_error: str | None = None
    sources: list[FoodCompositionSourceCount] = []


class FoodCompositionCiqualUpdate(MealieModel):
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        try:
            parse_dataset_url(v)
        except CiqualImportError as e:
            raise ValueError(str(e)) from e
        return v
