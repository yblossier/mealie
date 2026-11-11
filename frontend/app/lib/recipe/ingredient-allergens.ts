import type { RecipeIngredient } from "~/lib/api/types/recipe";

/**
 * The names of the allergens linked to the food of an ingredient, without repeats. An ingredient
 * without a food, or whose food is linked to no allergen, has none.
 */
export function ingredientAllergenNames(ingredient: Pick<RecipeIngredient, "food">): string[] {
  const food = ingredient.food as { allergens?: { name: string }[] | null } | null | undefined;
  return [...new Set((food?.allergens ?? []).map(allergen => allergen.name?.trim()).filter((name): name is string => !!name))];
}
