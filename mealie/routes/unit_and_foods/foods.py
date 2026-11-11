from functools import cached_property

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4

from mealie.core import exceptions
from mealie.routes._base.base_controllers import BaseUserController
from mealie.routes._base.controller import controller
from mealie.routes._base.mixins import HttpRepo
from mealie.routes._base.permissions import Perm, require
from mealie.routes._base.routers import MealieCrudRoute
from mealie.schema import mapper
from mealie.schema.allergens.allergen import AllergenSummary
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFoodAllergenFillRequest,
    IngredientFoodAllergenSuggestRequest,
    IngredientFoodCreate,
    IngredientFoodMerge,
    IngredientFoodNutritionEstimate,
    IngredientFoodNutritionEstimateRequest,
    IngredientFoodNutritionFillRequest,
    IngredientFoodNutritionLogOut,
    IngredientFoodNutritionReference,
    IngredientFoodOut,
    IngredientFoodPagination,
    IngredientFoodSave,
)
from mealie.schema.response.pagination import PaginationQuery
from mealie.schema.response.responses import ErrorResponse, SuccessResponse
from mealie.services.openai import OpenAINotEnabledException
from mealie.services.recipe.food_allergen_service import FoodAllergenItem, FoodAllergenService
from mealie.services.recipe.food_nutrition_service import FoodNutritionService
from mealie.services.recipe.open_food_facts_service import OpenFoodFactsError, OpenFoodFactsRateLimited

router = APIRouter(prefix="/foods", tags=["Recipes: Foods"], route_class=MealieCrudRoute)


@controller(router)
class IngredientFoodsController(BaseUserController):
    AI_ERROR_MAX_LENGTH = 300

    @cached_property
    def repo(self):
        return self.repos.ingredient_foods

    @cached_property
    def mixins(self):
        return HttpRepo[IngredientFoodSave, IngredientFoodOut, IngredientFoodCreate](
            self.repo,
            self.logger,
            self.registered_exceptions,
        )

    @router.get("", response_model=IngredientFoodPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery), search: str | None = None):
        response = self.repo.page_all(
            pagination=q,
            override=IngredientFoodOut,
            search=search,
        )

        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=IngredientFoodOut, status_code=201, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def create_one(self, data: IngredientFoodCreate):
        save_data = mapper.cast(data, IngredientFoodSave, group_id=self.group_id)
        return self.mixins.create_one(save_data)

    @router.get("/empty", response_model=list[IngredientFoodOut])
    def get_all_empty(self):
        """Returns a list of foods that are not used by any recipe"""
        return self.repo.get_empty()

    @router.put("/merge", response_model=SuccessResponse, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def merge_one(self, data: IngredientFoodMerge):
        try:
            self.repo.merge(data.from_food, data.to_food)
            return SuccessResponse.respond("Successfully merged foods")
        except Exception as e:
            self.logger.error(e)
            raise HTTPException(500, "Failed to merge foods") from e

    @cached_property
    def nutrition_service(self):
        return FoodNutritionService(self.repos, self.group_id)

    def _ai_exception(self, ex: Exception) -> HTTPException:
        """
        OpenAIService wraps provider failures in a generic exception,
        so the cause chain is searched for the ones worth telling the user about.
        Any other failure is reported with its root cause, so the user can tell what went wrong.
        """

        cause: BaseException | None = ex
        root: BaseException = ex
        while cause is not None:
            if isinstance(cause, exceptions.RateLimitError):
                return HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    ErrorResponse.respond(self.t("exceptions.rate-limit-error")),
                )
            if isinstance(cause, OpenAINotEnabledException):
                return HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorResponse.respond(self.t("recipe.import-errors.ai-not-enabled")),
                )
            root = cause
            cause = cause.__cause__

        reason = f"{root.__class__.__name__}: {root}".strip().rstrip(":")
        if len(reason) > self.AI_ERROR_MAX_LENGTH:
            reason = reason[: self.AI_ERROR_MAX_LENGTH] + "…"

        return HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            ErrorResponse.respond(f"{self.t('recipe.import-errors.ai-request-failed')} ({reason})", exception=reason),
        )

    @router.post(
        "/nutrition/estimate",
        response_model=list[IngredientFoodNutritionEstimate],
        dependencies=[require(Perm.GROUP_ORGANIZE)],
    )
    async def estimate_nutrition(self, data: IngredientFoodNutritionEstimateRequest):
        """
        Finds the nutrition facts per 100 g and the average weight of each food, without saving them:
        in the Ciqual table, then the USDA one, with the AI choosing among their foods and estimating the others
        """
        try:
            return await self.nutrition_service.estimate(data.foods)
        except Exception as e:
            self.logger.exception(e)
            raise self._ai_exception(e) from e

    @router.post(
        "/nutrition/fill",
        response_model=list[IngredientFoodOut],
        dependencies=[require(Perm.GROUP_ORGANIZE)],
    )
    async def fill_nutrition(self, data: IngredientFoodNutritionFillRequest):
        """Finds the nutrition facts per 100 g and the average weight of the foods, like the estimate, and saves them"""
        try:
            return await self.nutrition_service.fill(data.food_ids, overwrite=data.overwrite)
        except Exception as e:
            self.logger.exception(e)
            raise self._ai_exception(e) from e

    @router.post(
        "/allergens/suggest",
        response_model=list[AllergenSummary],
        dependencies=[require(Perm.GROUP_ORGANIZE)],
    )
    async def suggest_allergens(self, data: IngredientFoodAllergenSuggestRequest):
        """Finds the allergens a food contains, with the allergen keywords then the AI, without saving the food"""
        item = FoodAllergenItem(data.name, data.plural_name, data.aliases, data.description)
        try:
            return (await FoodAllergenService(self.repos, self.group_id).suggest([item]))[0]
        except Exception as e:
            self.logger.exception(e)
            raise self._ai_exception(e) from e

    @router.post(
        "/allergens/fill",
        response_model=list[IngredientFoodOut],
        dependencies=[require(Perm.GROUP_ORGANIZE)],
    )
    async def fill_allergens(self, data: IngredientFoodAllergenFillRequest):
        """Links the foods with the allergens they contain, found with the allergen keywords then the AI"""
        try:
            return await FoodAllergenService(self.repos, self.group_id).match(data.food_ids, overwrite=data.overwrite)
        except Exception as e:
            self.logger.exception(e)
            raise self._ai_exception(e) from e

    @router.get("/nutrition/references", response_model=list[IngredientFoodNutritionReference])
    async def search_nutrition_references(
        self,
        search: str = Query(..., min_length=1, max_length=200),
        limit: int = Query(20, ge=1, le=50),
    ):
        """
        Searches the foods of the Ciqual and USDA composition tables, with their nutrition facts per 100 g, then USDA
        FoodData Central online when none is named like the search
        """
        return await self.nutrition_service.search_references(search, limit)

    @router.get("/nutrition/references/open-food-facts", response_model=list[IngredientFoodNutritionReference])
    async def search_open_food_facts(
        self,
        search: str = Query(..., min_length=1, max_length=200),
        limit: int = Query(20, ge=1, le=25),
    ):
        """
        Searches the packaged products of Open Food Facts by name, or by barcode, with their nutrition facts per
        100 g. Open Food Facts limits the requests, so this answers 429 when they're used up for the minute.
        """
        if not self.nutrition_service.open_food_facts.enabled():
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, ErrorResponse.respond("Open Food Facts is disabled")
            )
        try:
            return await self.nutrition_service.search_open_food_facts(search, limit)
        except OpenFoodFactsRateLimited as e:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, ErrorResponse.respond(str(e))) from e
        except OpenFoodFactsError as e:
            self.logger.warning(e)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, ErrorResponse.respond(str(e))) from e

    @router.get("/{item_id}/nutrition/logs", response_model=list[IngredientFoodNutritionLogOut])
    def get_nutrition_logs(self, item_id: UUID4):
        """Returns the history of the AI nutrition estimates of the food, most recent first"""
        self.mixins.get_one(item_id)
        return self.repos.ingredient_food_nutrition_logs.get_for_food(item_id)

    @router.get("/{item_id}", response_model=IngredientFoodOut)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=IngredientFoodOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def update_one(self, item_id: UUID4, data: IngredientFoodCreate):
        data = mapper.cast(data, IngredientFoodSave, group_id=self.group_id)
        return self.mixins.update_one(data, item_id)

    @router.delete("/{item_id}", response_model=IngredientFoodOut, dependencies=[require(Perm.GROUP_ORGANIZE)])
    def delete_one(self, item_id: UUID4):
        return self.mixins.delete_one(item_id)
