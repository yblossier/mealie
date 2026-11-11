import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";
import type { IngredientFoodNutritionSource, IngredientFoodOut, Nutrition } from "~/lib/api/types/recipe";

type FoodDescription = Pick<IngredientFoodOut, "name" | "pluralName" | "description"> & { id?: string | null };

export interface FoodNutritionEstimate {
  /** Nutrition facts per 100 g, without the empty values; null when there are none */
  nutrition: Nutrition | null;
  /** Weight in grams of one piece of the food */
  averageWeight: number | null;
  /** Where the nutrition facts come from: a composition table, or the AI */
  source: IngredientFoodNutritionSource | null;
  referenceCode: string | null;
  referenceName: string | null;
}

/**
 * Finds the nutrition facts of foods in the Ciqual and USDA composition tables, with the group's AI provider
 * choosing among their foods and estimating the others when it's set up, with explicit error messages
 */
export function useFoodNutritionAI() {
  const i18n = useI18n();
  const api = useUserApi();
  const { group } = useGroupSelf();

  const aiEnabled = computed(() => !!group.value?.aiProviderSettings?.aiEnabled);
  const loading = ref(false);

  function alertNotFound(food: string) {
    alert.warning(aiEnabled.value
      ? i18n.t("data-pages.foods.nutrition-ai-no-values", { food })
      : i18n.t("data-pages.foods.nutrition-not-found-in-tables", { food }));
  }

  /**
   * The API interceptor already shows the server's own message when there is one,
   * so this only covers failures that never got one, like a timeout or a lost connection.
   */
  function alertTechnicalError(error: any) {
    if (error?.response?.data?.detail?.message) {
      return;
    }

    const status = error?.response?.status;
    const reason = [status ? `HTTP ${status}` : "", error?.message || ""].filter(Boolean).join(" - ");
    alert.error(reason
      ? i18n.t("data-pages.foods.nutrition-ai-technical-error", { error: reason })
      : i18n.t("data-pages.foods.nutrition-ai-failed"));
  }

  /**
   * Returns the estimated values, without saving them, or null when there are none.
   * The estimate is kept in the history of the food when it has an id.
   */
  async function estimate(food: FoodDescription): Promise<FoodNutritionEstimate | null> {
    loading.value = true;
    const { data, error } = await api.foods.estimateNutrition({
      foods: [{ id: food.id || null, name: food.name, pluralName: food.pluralName, description: food.description }],
    });
    loading.value = false;

    if (error || !data) {
      alertTechnicalError(error);
      return null;
    }

    const result = data[0];
    const values = Object.entries(result?.nutrition || {}).filter(([, value]) => value !== null && value !== undefined && value !== "");
    const averageWeight = result?.averageWeight || null;
    const reference = {
      source: result?.source || null,
      referenceCode: result?.referenceCode || null,
      referenceName: result?.referenceName || null,
    };
    if (!values.length) {
      alertNotFound(food.name);
      return averageWeight ? { nutrition: null, averageWeight, source: null, referenceCode: null, referenceName: null } : null;
    }

    return { nutrition: Object.fromEntries(values) as Nutrition, averageWeight, ...reference };
  }

  /** Estimates and saves the values of a food that has none, returning the updated food */
  async function generate(food: IngredientFoodOut): Promise<IngredientFoodOut | null> {
    loading.value = true;
    const { data, error } = await api.foods.fillNutrition({ foodIds: [food.id], overwrite: false });
    loading.value = false;

    if (error || !data) {
      alertTechnicalError(error);
      return null;
    }

    if (!data.length) {
      alertNotFound(food.name);
      return null;
    }

    alert.success(i18n.t("data-pages.foods.nutrition-generated", { food: food.name }));
    return data[0]!;
  }

  return { aiEnabled, loading, estimate, generate };
}
