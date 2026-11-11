from pydantic import UUID4
from sqlalchemy import delete, select

from mealie.db.models.recipe.ingredient import IngredientFoodNutritionLogModel
from mealie.schema.recipe.recipe_ingredient import IngredientFoodNutritionLogOut, IngredientFoodNutritionLogSave

from .repository_generic import GroupRepositoryGeneric


class RepositoryFoodNutritionLogs(
    GroupRepositoryGeneric[IngredientFoodNutritionLogOut, IngredientFoodNutritionLogModel]
):
    JSON_FIELDS = {"steps", "corrections", "result"}

    def add(self, log: IngredientFoodNutritionLogSave, keep: int) -> IngredientFoodNutritionLogOut:
        """Saves a log, deleting the oldest logs of the food beyond the `keep` most recent ones"""
        data = log.model_dump(exclude=self.JSON_FIELDS)
        data.update(log.model_dump(mode="json", include=self.JSON_FIELDS))
        created = self.create(data)

        kept = (
            select(IngredientFoodNutritionLogModel.id)
            .filter_by(**self._filter_builder(food_id=log.food_id))
            .order_by(IngredientFoodNutritionLogModel.created_at.desc(), IngredientFoodNutritionLogModel.id)
            .limit(keep)
        )
        self.session.execute(
            delete(IngredientFoodNutritionLogModel)
            .filter_by(**self._filter_builder(food_id=log.food_id))
            .where(IngredientFoodNutritionLogModel.id.not_in(kept))
        )
        self.session.commit()

        return created

    def get_for_food(self, food_id: UUID4) -> list[IngredientFoodNutritionLogOut]:
        """Logs of the food, most recent first"""
        stmt = (
            select(IngredientFoodNutritionLogModel)
            .filter_by(**self._filter_builder(food_id=food_id))
            .order_by(IngredientFoodNutritionLogModel.created_at.desc())
        )
        return [self.schema.model_validate(log) for log in self.session.execute(stmt).scalars().all()]
