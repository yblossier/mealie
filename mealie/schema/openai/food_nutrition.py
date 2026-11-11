from pydantic import Field

from ._base import OpenAIBase


class OpenAIFoodNutrition(OpenAIBase):
    name: str | None = Field(None, description="The name of the food, as given in the input.")
    calories: float | None = Field(None, description="Energy per 100 g, in kcal.")
    carbohydrate_content: float | None = Field(None, description="Carbohydrates per 100 g, in grams.")
    cholesterol_content: float | None = Field(None, description="Cholesterol per 100 g, in milligrams.")
    fat_content: float | None = Field(None, description="Total fat per 100 g, in grams.")
    fiber_content: float | None = Field(None, description="Fiber per 100 g, in grams.")
    protein_content: float | None = Field(None, description="Protein per 100 g, in grams.")
    saturated_fat_content: float | None = Field(None, description="Saturated fat per 100 g, in grams.")
    sodium_content: float | None = Field(None, description="Sodium per 100 g, in milligrams.")
    sugar_content: float | None = Field(None, description="Sugar per 100 g, in grams.")
    trans_fat_content: float | None = Field(None, description="Trans fat per 100 g, in grams.")
    unsaturated_fat_content: float | None = Field(None, description="Unsaturated fat per 100 g, in grams.")
    calcium_content: float | None = Field(None, description="Calcium per 100 g, in milligrams.")
    iron_content: float | None = Field(None, description="Iron per 100 g, in milligrams.")
    magnesium_content: float | None = Field(None, description="Magnesium per 100 g, in milligrams.")
    potassium_content: float | None = Field(None, description="Potassium per 100 g, in milligrams.")
    vitamin_a_content: float | None = Field(
        None, description="Vitamin A (retinol activity equivalents) per 100 g, in micrograms."
    )
    vitamin_c_content: float | None = Field(None, description="Vitamin C per 100 g, in milligrams.")
    vitamin_d_content: float | None = Field(None, description="Vitamin D per 100 g, in micrograms.")
    average_weight: float | None = Field(
        None,
        description="Average weight of one piece of the food as counted in recipes (one lemon, one egg), in grams.",
    )


class OpenAIFoodsNutrition(OpenAIBase):
    foods: list[OpenAIFoodNutrition] = Field(
        [],
        description="The nutrition facts of each food, in the same order as the input.",
    )


class OpenAIFoodNutritionMatch(OpenAIBase):
    name: str | None = Field(None, description="The name of the food, as given in the input.")
    reference: str | None = Field(
        None,
        description="The id of the candidate that is the same food, or null when none of them is.",
    )
    average_weight: float | None = Field(
        None,
        description="Average weight of one piece of the food as counted in recipes (one lemon, one egg), in grams.",
    )


class OpenAIFoodNutritionMatches(OpenAIBase):
    foods: list[OpenAIFoodNutritionMatch] = Field(
        [],
        description="The chosen candidate of each food, in the same order as the input.",
    )
