from pydantic import ConfigDict

from mealie.schema._mealie import MealieModel


class RecipeSettings(MealieModel):
    public: bool = False
    show_nutrition: bool = False
    show_assets: bool = False
    show_allergens: bool = True
    landscape_view: bool = False
    disable_comments: bool = True
    locked: bool = False
    thermomix: bool = False
    """The recipe is written for the Thermomix, e.g. imported from Cookomix"""
    model_config = ConfigDict(from_attributes=True)
