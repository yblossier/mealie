import { STANDARDIZED_UNITS } from "./unit-systems";
import { parseNutritionValue } from "./use-recipe-nutrition";
import type { Nutrition, RecipeIngredient } from "~/lib/api/types/recipe";

export const NUTRITION_KEYS = [
  "calories",
  "carbohydrateContent",
  "cholesterolContent",
  "fatContent",
  "fiberContent",
  "proteinContent",
  "saturatedFatContent",
  "sodiumContent",
  "sugarContent",
  "transFatContent",
  "unsaturatedFatContent",
  "calciumContent",
  "ironContent",
  "magnesiumContent",
  "potassiumContent",
  "vitaminAContent",
  "vitaminCContent",
  "vitaminDContent",
] as const;

export type NutritionProblemReason
  = | "sub-recipe"
    | "no-food"
    | "no-quantity"
    | "no-unit"
    | "unit-not-convertible"
    | "food-no-nutrition";

export interface NutritionProblem {
  ingredient: RecipeIngredient;
  reason: NutritionProblemReason;
}

export interface RecipeNutritionResult {
  /** Per serving, with every key present; null when no usable ingredient had a value for it */
  nutrition: Nutrition;
  /** Ingredients that were left out of the calculation, and why */
  problems: NutritionProblem[];
  /** Number of ingredients that went into the calculation */
  usedCount: number;
}

/**
 * Volumes are counted as 1 ml = 1 g: Mealie stores no density per food, and this is right for
 * water-based ingredients (water, milk, stock) and close enough for most others.
 */
const GRAMS_PER_MILLILITER = 1;

/** A pinch (of salt, spices...) has no standard measure: it's counted as 1 g */
export const GRAMS_PER_PINCH = 1;

/** Names of the pinch unit in the languages of Mealie's seed data, singular and plural */
const PINCH_NAMES = new Set([
  "pinch", "pinches", "pincée", "pincées", "prise", "prisen", "pizzico", "pizzichi", "pellizco", "pellizcos",
  "pitada", "pitadas", "pessic", "pessics", "areiña", "areiñas", "snufje", "snufjes", "knivspids", "knivspidser",
  "klype", "klyper", "nypa", "nypor", "klípa", "klípur", "hyppysellinen", "hyppysellistä", "näpuotsatäis",
  "näpuotsatäit", "szczypta", "szczypty", "špetka", "špetky", "štipka", "štipky", "ščepec", "ščepcev", "prstohvat",
  "prstohvati", "csipet", "praf", "prafuri", "žiupsnelis", "žiupsneliai", "šķipsniņa", "šķipsnas", "tutam",
  "щипка", "щипки", "щепотка", "щепотки", "дрібка", "дрібки", "прстохват", "прстохвата", "πρέζα", "πρέζες",
  "رشه", "رشاة", "קמצוץ", "קמצוצים", "撮", "小さじ1/16",
]);

/** A sachet of baker's yeast weighs 7 g */
export const GRAMS_PER_YEAST_SACHET = 7;

/** A sachet of baking powder ("levure chimique") weighs 11 g */
export const GRAMS_PER_BAKING_POWDER_SACHET = 11;

const SACHET_NAMES = new Set([
  "sachet", "sachets", "packet", "packets", "envelope", "envelopes", "päckchen", "tütchen", "beutel", "bustina",
  "bustine", "sobre", "sobres", "sobrecito", "sobrecitos", "zakje", "zakjes", "sachê", "sachês", "saqueta", "saquetas",
  "saquinho", "saquinhos", "torebka", "torebki", "sáček", "sáčky", "brev", "påse", "påsar",
]);

/** Words found in the names of yeasts, in the languages of Mealie's seed data */
const YEAST_WORDS = ["levure", "yeast", "hefe", "lievito", "levadura", "fermento", "gist", "drożdż", "droždí", "jäst", "gjær"];

type Unit = NonNullable<RecipeIngredient["unit"]>;

function normalize(name: string | null | undefined): string {
  return (name || "").trim().toLocaleLowerCase().normalize("NFC");
}

function unitIs(unit: Unit, names: Set<string>): boolean {
  return [unit.name, unit.pluralName, unit.abbreviation, unit.pluralAbbreviation].some(name => names.has(normalize(name)));
}

/** Words found in the names of baking powders, in the languages of Mealie's seed data */
const BAKING_POWDER_WORDS = [
  "levure chimique", "baking powder", "backpulver", "lievito per dolci", "lievito chimico", "levadura química",
  "polvo de hornear", "fermento químico", "bakpoeder", "proszek do pieczenia", "prášek do pečiva", "bakpulver",
];

function foodNameContains(food: RecipeIngredient["food"], words: string[]): boolean {
  const names = [food?.name, food?.pluralName].map(normalize);
  return names.some(name => words.some(word => name.includes(word)));
}

/** Weight of one unit that has no standard measure but a customary weight: a pinch, a sachet of yeast or baking powder */
function customaryUnitGrams(unit: Unit, food: RecipeIngredient["food"]): number | null {
  if (unitIs(unit, PINCH_NAMES)) {
    return GRAMS_PER_PINCH;
  }
  if (unitIs(unit, SACHET_NAMES)) {
    if (foodNameContains(food, BAKING_POWDER_WORDS)) {
      return GRAMS_PER_BAKING_POWDER_SACHET;
    }
    if (foodNameContains(food, YEAST_WORDS)) {
      return GRAMS_PER_YEAST_SACHET;
    }
  }
  return null;
}

/**
 * Converts an ingredient's quantity into grams, or returns why it can't be done.
 * A quantity without a unit counts pieces of the food ("2 lemons"), weighed with the food's average weight,
 * a pinch without a standard measure counts as 1 g, a sachet of baker's yeast as 7 g and of baking powder as 11 g.
 */
export function ingredientGrams(ingredient: RecipeIngredient, averageWeight?: number | null): number | NutritionProblemReason {
  if (!ingredient.quantity || ingredient.quantity <= 0) {
    return "no-quantity";
  }

  const unit = ingredient.unit;
  if (!unit) {
    return averageWeight && averageWeight > 0 ? ingredient.quantity * averageWeight : "no-unit";
  }

  const standard = unit.standardUnit ? STANDARDIZED_UNITS[unit.standardUnit] : undefined;
  if (!standard || !unit.standardQuantity) {
    const grams = customaryUnitGrams(unit, ingredient.food);
    return grams ? ingredient.quantity * grams : "unit-not-convertible";
  }

  const amount = ingredient.quantity * unit.standardQuantity * standard.base;
  return standard.dimension === "mass" ? amount : amount * GRAMS_PER_MILLILITER;
}

function isBlank(ingredient: RecipeIngredient): boolean {
  return !ingredient.quantity && !ingredient.unit && !ingredient.food && !ingredient.note?.trim();
}

function roundValue(key: string, value: number): string {
  const decimals = key === "calories" ? 0 : 1;
  const factor = 10 ** decimals;
  return String(Math.round(value * factor) / factor);
}

/**
 * Sums the nutrition facts of the ingredients, from their food's values per 100 g, and divides them by the servings.
 *
 * `foods` maps a food id to its up-to-date nutrition facts, and `averageWeights` to its up-to-date weight of
 * one piece; foods missing from them fall back to the values embedded in the ingredient.
 */
export function calculateRecipeNutrition(
  ingredients: RecipeIngredient[],
  servings: number,
  foods: Record<string, Nutrition | null | undefined> = {},
  averageWeights: Record<string, number | null | undefined> = {},
): RecipeNutritionResult {
  const totals: Record<string, number | null> = Object.fromEntries(NUTRITION_KEYS.map(key => [key, null]));
  const problems: NutritionProblem[] = [];
  let usedCount = 0;

  for (const ingredient of ingredients) {
    if (isBlank(ingredient)) {
      continue;
    }
    if (ingredient.referencedRecipe) {
      problems.push({ ingredient, reason: "sub-recipe" });
      continue;
    }
    if (!ingredient.food) {
      problems.push({ ingredient, reason: "no-food" });
      continue;
    }

    const foodId = "id" in ingredient.food ? ingredient.food.id : undefined;
    const averageWeight = foodId && foodId in averageWeights ? averageWeights[foodId] : ingredient.food.averageWeight;
    const grams = ingredientGrams(ingredient, averageWeight);
    if (typeof grams === "string") {
      problems.push({ ingredient, reason: grams });
      continue;
    }

    const nutrition = (foodId && foodId in foods ? foods[foodId] : ingredient.food.nutrition) as Record<string, string | null> | null | undefined;
    const values = NUTRITION_KEYS.map(key => [key, parseNutritionValue(nutrition?.[key])] as const);
    if (!values.some(([, value]) => value !== null)) {
      problems.push({ ingredient, reason: "food-no-nutrition" });
      continue;
    }

    for (const [key, value] of values) {
      if (value !== null) {
        totals[key] = (totals[key] ?? 0) + (value * grams) / 100;
      }
    }
    usedCount++;
  }

  const divisor = servings > 0 ? servings : 1;
  const nutrition = Object.fromEntries(
    NUTRITION_KEYS.map((key) => {
      const total = totals[key];
      return [key, total === null || usedCount === 0 ? null : roundValue(key, total / divisor)];
    }),
  ) as Nutrition;

  return { nutrition, problems, usedCount };
}
