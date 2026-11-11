"""
The shape shared by the nutrition references: the rows of the bundled composition tables and the foods found online
through the Open Food Facts and USDA FoodData Central APIs. The API clients only return these, they never write them.
"""

from dataclasses import dataclass, field
from typing import Literal

FoodReferenceSource = Literal["ciqual", "usda", "off"]

NUTRIENT_KEYS: tuple[str, ...] = (
    "calories",
    "carbohydrate_content",
    "sugar_content",
    "fiber_content",
    "fat_content",
    "saturated_fat_content",
    "unsaturated_fat_content",
    "trans_fat_content",
    "protein_content",
    "cholesterol_content",
    "sodium_content",
    "calcium_content",
    "iron_content",
    "magnesium_content",
    "potassium_content",
    "vitamin_a_content",
    "vitamin_c_content",
    "vitamin_d_content",
)
"""The nutrients of a reference food, per 100 g, with the keys and units of the bundled composition tables"""


@dataclass(frozen=True)
class FoodReferenceResult:
    source: FoodReferenceSource
    code: str
    """The barcode for Open Food Facts, the FDC id for USDA, the food code for Ciqual"""
    name: str
    nutrients: dict[str, float | None] = field(default_factory=dict)
    name_en: str | None = None
    brand: str | None = None
    url: str | None = None
    """The page of the food on the source's website"""
    average_weight: float | None = None
