from pydantic import Field

from ._base import OpenAIBase


class OpenAIFoodAllergens(OpenAIBase):
    name: str = Field(..., description="The name of the food, as given in the input.")
    allergens: list[str] = Field(
        default_factory=list,
        description="The codes of the allergens the food contains, among the codes given in the instructions.",
    )


class OpenAIFoodsAllergens(OpenAIBase):
    foods: list[OpenAIFoodAllergens] = Field(
        default_factory=list, description="One entry per food of the input, in the same order."
    )
