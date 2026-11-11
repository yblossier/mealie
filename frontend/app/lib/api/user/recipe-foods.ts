import { BaseCRUDAPI } from "../base/base-clients";
import type { AllergenSummary } from "~/lib/api/types/allergens";
import type {
  IngredientFoodAllergenFillRequest,
  IngredientFoodAllergenSuggestRequest,
  IngredientFoodCreate,
  IngredientFoodNutritionEstimate,
  IngredientFoodNutritionEstimateRequest,
  IngredientFoodNutritionFillRequest,
  IngredientFoodNutritionLogOut,
  IngredientFoodNutritionReference,
  IngredientFoodOut,
} from "~/lib/api/types/recipe";

const prefix = "/api";

const routes = {
  food: `${prefix}/foods`,
  foodsFood: (tag: string) => `${prefix}/foods/${tag}`,
  foodsEmpty: `${prefix}/foods/empty`,
  merge: `${prefix}/foods/merge`,
  nutritionEstimate: `${prefix}/foods/nutrition/estimate`,
  nutritionFill: `${prefix}/foods/nutrition/fill`,
  nutritionReferences: `${prefix}/foods/nutrition/references`,
  nutritionOpenFoodFacts: `${prefix}/foods/nutrition/references/open-food-facts`,
  nutritionLogs: (id: string) => `${prefix}/foods/${id}/nutrition/logs`,
  allergensSuggest: `${prefix}/foods/allergens/suggest`,
  allergensFill: `${prefix}/foods/allergens/fill`,
};

export class FoodAPI extends BaseCRUDAPI<IngredientFoodCreate, IngredientFoodOut> {
  baseRoute: string = routes.food;
  itemRoute = routes.foodsFood;

  async getEmpty() {
    return await this.requests.get<IngredientFoodOut[]>(routes.foodsEmpty);
  }

  merge(fromId: string, toId: string) {
    return this.requests.put<IngredientFoodOut>(routes.merge, { fromFood: fromId, toFood: toId });
  }

  estimateNutrition(payload: IngredientFoodNutritionEstimateRequest) {
    return this.requests.post<IngredientFoodNutritionEstimate[]>(routes.nutritionEstimate, payload);
  }

  fillNutrition(payload: IngredientFoodNutritionFillRequest) {
    return this.requests.post<IngredientFoodOut[]>(routes.nutritionFill, payload);
  }

  /** Searches the foods of the Ciqual and USDA composition tables, Ciqual first */
  searchNutritionReferences(search: string, limit = 20) {
    return this.requests.get<IngredientFoodNutritionReference[]>(routes.nutritionReferences, { search, limit });
  }

  /** Searches the packaged products of Open Food Facts by name or barcode; its requests per minute are limited */
  searchOpenFoodFacts(search: string, limit = 20) {
    return this.requests.get<IngredientFoodNutritionReference[]>(routes.nutritionOpenFoodFacts, { search, limit });
  }

  /** Asks the AI which of the group's allergens a food contains, without saving anything */
  suggestAllergens(payload: IngredientFoodAllergenSuggestRequest) {
    return this.requests.post<AllergenSummary[]>(routes.allergensSuggest, payload);
  }

  /** Links foods to the allergens the AI finds in them, returning the updated foods */
  fillAllergens(payload: IngredientFoodAllergenFillRequest) {
    return this.requests.post<IngredientFoodOut[]>(routes.allergensFill, payload);
  }

  getNutritionLogs(id: string) {
    return this.requests.get<IngredientFoodNutritionLogOut[]>(routes.nutritionLogs(id));
  }
}
