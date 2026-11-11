import sqlalchemy as sa
from sqlalchemy.orm import mapped_column

from mealie.db.models._model_base import FilterableColumn, SqlAlchemyBase
from mealie.db.models._model_utils.guid import GUID


class Nutrition(SqlAlchemyBase):
    __tablename__ = "recipe_nutrition"
    id: FilterableColumn[int] = mapped_column(sa.Integer, primary_key=True)
    recipe_id: FilterableColumn[GUID | None] = mapped_column(GUID, sa.ForeignKey("recipes.id"), index=True)

    calories: FilterableColumn[str | None] = mapped_column(sa.String)
    carbohydrate_content: FilterableColumn[str | None] = mapped_column(sa.String)
    cholesterol_content: FilterableColumn[str | None] = mapped_column(sa.String)
    fat_content: FilterableColumn[str | None] = mapped_column(sa.String)
    fiber_content: FilterableColumn[str | None] = mapped_column(sa.String)
    protein_content: FilterableColumn[str | None] = mapped_column(sa.String)
    saturated_fat_content: FilterableColumn[str | None] = mapped_column(sa.String)

    # `serving_size` is not a scaling factor, but a per-serving volume or mass
    # according to schema.org. E.g., "2 L", "500 g", "5 cups", etc.
    #
    # Ignoring for now because it's too difficult to work around variable units
    # in translation for the frontend. Also, it causes cognitive dissonance wrt
    # "servings" (i.e., "serves 2" etc.), which is an unrelated concept that
    # might cause confusion.
    #
    # serving_size: Mapped[str | None] = mapped_column(sa.String)

    sodium_content: FilterableColumn[str | None] = mapped_column(sa.String)
    sugar_content: FilterableColumn[str | None] = mapped_column(sa.String)
    trans_fat_content: FilterableColumn[str | None] = mapped_column(sa.String)
    unsaturated_fat_content: FilterableColumn[str | None] = mapped_column(sa.String)
    calcium_content: FilterableColumn[str | None] = mapped_column(sa.String)
    iron_content: FilterableColumn[str | None] = mapped_column(sa.String)
    magnesium_content: FilterableColumn[str | None] = mapped_column(sa.String)
    potassium_content: FilterableColumn[str | None] = mapped_column(sa.String)
    vitamin_a_content: FilterableColumn[str | None] = mapped_column(sa.String)
    vitamin_c_content: FilterableColumn[str | None] = mapped_column(sa.String)
    vitamin_d_content: FilterableColumn[str | None] = mapped_column(sa.String)

    def __init__(
        self,
        calories=None,
        carbohydrate_content=None,
        cholesterol_content=None,
        fat_content=None,
        fiber_content=None,
        protein_content=None,
        saturated_fat_content=None,
        sodium_content=None,
        sugar_content=None,
        trans_fat_content=None,
        unsaturated_fat_content=None,
        calcium_content=None,
        iron_content=None,
        magnesium_content=None,
        potassium_content=None,
        vitamin_a_content=None,
        vitamin_c_content=None,
        vitamin_d_content=None,
    ) -> None:
        self.calories = calories
        self.carbohydrate_content = carbohydrate_content
        self.cholesterol_content = cholesterol_content
        self.fat_content = fat_content
        self.fiber_content = fiber_content
        self.protein_content = protein_content
        self.saturated_fat_content = saturated_fat_content
        self.sodium_content = sodium_content
        self.sugar_content = sugar_content
        self.trans_fat_content = trans_fat_content
        self.unsaturated_fat_content = unsaturated_fat_content
        self.calcium_content = calcium_content
        self.iron_content = iron_content
        self.magnesium_content = magnesium_content
        self.potassium_content = potassium_content
        self.vitamin_a_content = vitamin_a_content
        self.vitamin_c_content = vitamin_c_content
        self.vitamin_d_content = vitamin_d_content
