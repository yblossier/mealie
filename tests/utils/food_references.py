from sqlalchemy import delete

from mealie.db.db_setup import session_context
from mealie.db.models.server.food_composition import FoodCompositionFoodModel, FoodCompositionSourceModel
from mealie.services.recipe.food_reference_service import invalidate_tables


def clear_food_references() -> None:
    """Empties the nutrition referential, shared by all the groups, so that a test doesn't see the foods of another"""
    with session_context() as session:
        session.execute(delete(FoodCompositionFoodModel))
        session.execute(delete(FoodCompositionSourceModel))
        session.commit()
    invalidate_tables()
