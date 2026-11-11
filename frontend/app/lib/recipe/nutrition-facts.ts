import { parseNutritionValue } from "~/composables/recipes/use-recipe-nutrition";
import type { Nutrition } from "~/lib/api/types/recipe";

export type NutritionFactKey = keyof Nutrition | "saltContent";

/**
 * Reference intakes of an average adult (8400 kJ / 2000 kcal), from Annex XIII of
 * regulation (EU) No 1169/2011, which French labels follow. Sodium uses the salt one (6 g = 2.4 g of sodium).
 */
export const REFERENCE_INTAKES: Partial<Record<NutritionFactKey, number>> = {
  calories: 2000,
  fatContent: 70,
  saturatedFatContent: 20,
  carbohydrateContent: 260,
  sugarContent: 90,
  proteinContent: 50,
  saltContent: 6,
  sodiumContent: 2400,
  calciumContent: 800,
  ironContent: 14,
  magnesiumContent: 375,
  potassiumContent: 2000,
  vitaminAContent: 800,
  vitaminCContent: 80,
  vitaminDContent: 5,
};

const KJ_PER_KCAL = 4.184;
/** Salt = sodium × 2.5, as required on EU labels */
const SALT_PER_SODIUM = 2.5;

export function kilojoules(kcal: number): number {
  return kcal * KJ_PER_KCAL;
}

/** Salt in grams, from sodium in milligrams */
export function saltGrams(nutrition: Nutrition | null | undefined): number | null {
  const sodium = parseNutritionValue(nutrition?.sodiumContent);
  return sodium === null ? null : (sodium * SALT_PER_SODIUM) / 1000;
}

export function nutritionFactValue(nutrition: Nutrition | null | undefined, key: NutritionFactKey): number | null {
  if (key === "saltContent") {
    return saltGrams(nutrition);
  }
  return parseNutritionValue(nutrition?.[key]);
}

/** Share of the reference intake, in percent, or null when the nutrient has none */
export function referenceIntakePercent(key: NutritionFactKey, value: number | null): number | null {
  const reference = REFERENCE_INTAKES[key];
  if (value === null || !reference) {
    return null;
  }
  return (value / reference) * 100;
}

export function formatNumber(value: number, locale: string, maximumFractionDigits = 1): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits }).format(value);
}

export function formatPercent(percent: number, locale: string): string {
  return `${formatNumber(percent, locale, percent < 10 ? 1 : 0)}%`;
}

/**
 * The five colors of the Nutri-Score, the front-of-pack label recommended by French health authorities
 * (Santé publique France), from dark green (A) to red (E).
 */
export const NUTRI_SCORE_COLORS = {
  A: "#038141",
  B: "#85BB2F",
  C: "#FECB02",
  D: "#EE8100",
  E: "#E63E11",
} as const;

export type NutriScoreGrade = keyof typeof NUTRI_SCORE_COLORS;

/**
 * Grades a serving by the share of the daily reference intake it brings. In France (PNNS), lunch and dinner
 * each bring about a third of the day's intake, so a serving above 30% is more than its share of a main meal.
 */
const GRADE_THRESHOLDS: [number, NutriScoreGrade][] = [
  [5, "A"],
  [10, "B"],
  [20, "C"],
  [30, "D"],
];

export function referenceIntakeGrade(percent: number): NutriScoreGrade {
  return GRADE_THRESHOLDS.find(([max]) => percent <= max)?.[1] ?? "E";
}
