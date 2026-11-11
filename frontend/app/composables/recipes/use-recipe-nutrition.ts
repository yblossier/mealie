import type { Nutrition } from "~/lib/api/types/recipe";

export interface NutritionLabelType {
  [key: string]: {
    label: string;
    suffix: string;
    value?: string;
  };
};

export function parseNutritionValue(value: string | null | undefined): number | null {
  if (!value) {
    return null;
  }

  const parsedValue = Number.parseFloat(value);
  return Number.isFinite(parsedValue) ? parsedValue : null;
}

type NutritionValues = Nutrition | Record<string, string | null | undefined> | null | undefined;

export interface NutritionField {
  key: string;
  label: string;
  suffix: string;
  value: string;
}

function nutritionValue(nutrition: NutritionValues, key: string): string {
  const value = (nutrition as Record<string, unknown> | null | undefined)?.[key];
  return value === null || value === undefined ? "" : String(value).trim();
}

export function hasNutritionValues(nutrition: NutritionValues): boolean {
  return !!nutrition && Object.keys(nutrition).some(key => nutritionValue(nutrition, key) !== "");
}

/** Only the filled values, for read-only display */
export function filledNutritionFields(nutrition: NutritionValues, labels: NutritionLabelType): NutritionField[] {
  return Object.entries(labels)
    .map(([key, field]) => ({ key, label: field.label, suffix: field.suffix, value: nutritionValue(nutrition, key) }))
    .filter(field => field.value !== "");
}

export function useNutritionLabels() {
  const i18n = useI18n();
  const labels = <NutritionLabelType>{
    calories: {
      label: i18n.t("recipe.calories"),
      suffix: i18n.t("recipe.calories-suffix"),
    },
    carbohydrateContent: {
      label: i18n.t("recipe.carbohydrate-content"),
      suffix: i18n.t("recipe.grams"),
    },
    cholesterolContent: {
      label: i18n.t("recipe.cholesterol-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    fatContent: {
      label: i18n.t("recipe.fat-content"),
      suffix: i18n.t("recipe.grams"),
    },
    fiberContent: {
      label: i18n.t("recipe.fiber-content"),
      suffix: i18n.t("recipe.grams"),
    },
    proteinContent: {
      label: i18n.t("recipe.protein-content"),
      suffix: i18n.t("recipe.grams"),
    },
    saturatedFatContent: {
      label: i18n.t("recipe.saturated-fat-content"),
      suffix: i18n.t("recipe.grams"),
    },
    sodiumContent: {
      label: i18n.t("recipe.sodium-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    sugarContent: {
      label: i18n.t("recipe.sugar-content"),
      suffix: i18n.t("recipe.grams"),
    },
    transFatContent: {
      label: i18n.t("recipe.trans-fat-content"),
      suffix: i18n.t("recipe.grams"),
    },
    unsaturatedFatContent: {
      label: i18n.t("recipe.unsaturated-fat-content"),
      suffix: i18n.t("recipe.grams"),
    },
    calciumContent: {
      label: i18n.t("recipe.calcium-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    ironContent: {
      label: i18n.t("recipe.iron-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    magnesiumContent: {
      label: i18n.t("recipe.magnesium-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    potassiumContent: {
      label: i18n.t("recipe.potassium-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    vitaminAContent: {
      label: i18n.t("recipe.vitamin-a-content"),
      suffix: i18n.t("recipe.micrograms"),
    },
    vitaminCContent: {
      label: i18n.t("recipe.vitamin-c-content"),
      suffix: i18n.t("recipe.milligrams"),
    },
    vitaminDContent: {
      label: i18n.t("recipe.vitamin-d-content"),
      suffix: i18n.t("recipe.micrograms"),
    },
  };

  return { labels };
}
