import type { IngredientFoodNutritionSource } from "~/lib/api/types/recipe";

export interface NutritionTable {
  name: string;
  /** Attribution required by the license of the table */
  attribution: string;
  license: string;
  licenseUrl: string;
  url: (code: string) => string;
}

/** The food composition tables and databases the nutrition facts can come from, in their order of priority */
export const NUTRITION_TABLES: Record<Exclude<IngredientFoodNutritionSource, "ai">, NutritionTable> = {
  ciqual: {
    name: "Ciqual",
    attribution: "Anses. Table de composition nutritionnelle des aliments Ciqual 2025",
    license: "Licence Ouverte / Etalab 2.0",
    licenseUrl: "https://www.etalab.gouv.fr/licence-ouverte-open-licence/",
    url: code => `https://ciqual.anses.fr/#/aliments/${encodeURIComponent(code)}`,
  },
  usda: {
    name: "USDA FoodData Central",
    attribution: "U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, SR Legacy (2018)",
    license: "Public domain (CC0 1.0)",
    licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/",
    url: code => `https://fdc.nal.usda.gov/food-details/${encodeURIComponent(code)}/nutrients`,
  },
  off: {
    name: "Open Food Facts",
    attribution: "Open Food Facts contributors (openfoodfacts.org)",
    license: "Open Database License (ODbL 1.0)",
    licenseUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
    url: code => `https://world.openfoodfacts.org/product/${encodeURIComponent(code)}`,
  },
};

export function nutritionTable(source: IngredientFoodNutritionSource | null | undefined): NutritionTable | null {
  return source && source !== "ai" ? NUTRITION_TABLES[source] : null;
}

/** Link to the food in its composition table, or null when it doesn't come from one */
export function nutritionReferenceUrl(
  source: IngredientFoodNutritionSource | null | undefined,
  code: string | null | undefined,
): string | null {
  const table = nutritionTable(source);
  return table && code ? table.url(code) : null;
}
