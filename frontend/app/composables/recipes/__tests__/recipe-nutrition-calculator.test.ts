import { describe, expect, test } from "vitest";
import type { IngredientUnitCreate, Nutrition, RecipeIngredient } from "~/lib/api/types/recipe";
import { calculateRecipeNutrition, ingredientGrams } from "../recipe-nutrition-calculator";

const unit = (standardUnit: string | null, standardQuantity = 1): IngredientUnitCreate => ({
  name: standardUnit || "piece",
  standardUnit,
  standardQuantity: standardUnit ? standardQuantity : null,
});

const ingredient = (
  quantity: number,
  unitValue: IngredientUnitCreate | null,
  nutrition: Partial<Nutrition> | null,
  id = "food-1",
): RecipeIngredient => ({
  quantity,
  unit: unitValue,
  food: { id, name: `food ${id}`, nutrition: nutrition as Nutrition | null },
});

describe("ingredientGrams", () => {
  test("converts mass units", () => {
    expect(ingredientGrams(ingredient(2, unit("kilogram"), null))).toBe(2000);
    expect(ingredientGrams(ingredient(1, unit("ounce"), null))).toBeCloseTo(28.35, 2);
  });

  test("converts volumes as 1 ml = 1 g, through the unit's standard quantity", () => {
    expect(ingredientGrams(ingredient(3, unit("milliliter", 15), null))).toBe(45);
    expect(ingredientGrams(ingredient(0.5, unit("liter"), null))).toBe(500);
  });

  test("explains what can't be converted", () => {
    expect(ingredientGrams(ingredient(0, unit("gram"), null))).toBe("no-quantity");
    expect(ingredientGrams(ingredient(2, null, null))).toBe("no-unit");
    expect(ingredientGrams(ingredient(2, unit(null), null))).toBe("unit-not-convertible");
    expect(ingredientGrams(ingredient(2, unit("furlong"), null))).toBe("unit-not-convertible");
  });

  test("counts a pinch as 1 g, in any language", () => {
    const pinch = (name: string, pluralName: string | null = null): IngredientUnitCreate => (
      { name, pluralName, standardUnit: null, standardQuantity: null }
    );
    expect(ingredientGrams(ingredient(1, pinch("pinch"), null))).toBe(1);
    expect(ingredientGrams(ingredient(2, pinch("Pincée"), null))).toBe(2);
    expect(ingredientGrams(ingredient(3, pinch("whatever", "pincées"), null))).toBe(3);
    expect(ingredientGrams(ingredient(1, pinch("Prise"), null))).toBe(1);
    expect(ingredientGrams(ingredient(1, pinch("bunch"), null))).toBe("unit-not-convertible");
    // a standard measure set on the unit wins
    expect(ingredientGrams(ingredient(1, { ...pinch("pinch"), standardUnit: "gram", standardQuantity: 0.5 }, null))).toBe(0.5);
  });

  test("counts a sachet of baker's yeast as 7 g and of baking powder as 11 g", () => {
    const sachet = (name: string): IngredientUnitCreate => ({ name, standardUnit: null, standardQuantity: null });
    const withFood = (quantity: number, unitValue: IngredientUnitCreate, name: string): RecipeIngredient => (
      { quantity, unit: unitValue, food: { id: "yeast", name } }
    );
    expect(ingredientGrams(withFood(1, sachet("sachet"), "levure boulangère"))).toBe(7);
    expect(ingredientGrams(withFood(2, sachet("Sachets"), "Levure chimique"))).toBe(22);
    expect(ingredientGrams(withFood(1, sachet("packet"), "baking powder"))).toBe(11);
    expect(ingredientGrams(withFood(1, sachet("Päckchen"), "Backpulver"))).toBe(11);
    expect(ingredientGrams(withFood(1, sachet("packet"), "dry yeast"))).toBe(7);
    expect(ingredientGrams(withFood(1, sachet("Päckchen"), "Trockenhefe"))).toBe(7);
    // a sachet of something else has no known weight
    expect(ingredientGrams(withFood(1, sachet("sachet"), "sucre vanillé"))).toBe("unit-not-convertible");
  });

  test("weighs a quantity without a unit with the food's average weight", () => {
    expect(ingredientGrams(ingredient(2, null, null), 110)).toBe(220);
    expect(ingredientGrams(ingredient(2, null, null), 0)).toBe("no-unit");
    expect(ingredientGrams(ingredient(2, null, null), null)).toBe("no-unit");
    // the average weight is only for pieces, a unit always wins
    expect(ingredientGrams(ingredient(2, unit("kilogram"), null), 110)).toBe(2000);
  });
});

describe("calculateRecipeNutrition", () => {
  test("sums the foods' values per 100 g and divides by the servings", () => {
    const result = calculateRecipeNutrition(
      [
        ingredient(200, unit("gram"), { calories: "100", proteinContent: "10" }, "a"),
        ingredient(1, unit("liter"), { calories: "40", fatContent: "3.6" }, "b"),
      ],
      4,
    );

    expect(result.problems).toEqual([]);
    expect(result.usedCount).toBe(2);
    expect(result.nutrition.calories).toBe("150");
    expect(result.nutrition.proteinContent).toBe("5");
    expect(result.nutrition.fatContent).toBe("9");
    expect(result.nutrition.sugarContent).toBeNull();
  });

  test("prefers the up-to-date food values over the ones embedded in the recipe", () => {
    const result = calculateRecipeNutrition(
      [ingredient(100, unit("gram"), { calories: "1" }, "a")],
      1,
      { a: { calories: "250" } },
    );
    expect(result.nutrition.calories).toBe("250");
  });

  test("counts the pieces of a food with its average weight", () => {
    const lemon: RecipeIngredient = {
      quantity: 2,
      unit: null,
      food: { id: "lemon", name: "lemon", averageWeight: 100, nutrition: { calories: "30" } as Nutrition },
    };
    expect(calculateRecipeNutrition([lemon], 2).nutrition.calories).toBe("30");

    // the up-to-date weight of the food wins over the one embedded in the recipe
    const result = calculateRecipeNutrition([lemon], 2, {}, { lemon: 150 });
    expect(result.problems).toEqual([]);
    expect(result.nutrition.calories).toBe("45");

    expect(calculateRecipeNutrition([lemon], 2, {}, { lemon: null }).problems[0]?.reason).toBe("no-unit");
  });

  test("reports every ingredient that can't be used, and skips blank lines", () => {
    const noFood: RecipeIngredient = { quantity: 1, unit: unit("gram"), note: "salt" };
    const subRecipe: RecipeIngredient = { quantity: 1, referencedRecipe: { name: "sauce" } };
    const blank: RecipeIngredient = { quantity: 0, note: "" };
    const result = calculateRecipeNutrition(
      [
        noFood,
        subRecipe,
        blank,
        ingredient(2, null, { calories: "10" }),
        ingredient(100, unit("gram"), null),
        ingredient(100, unit("gram"), { calories: "10" }),
      ],
      1,
    );

    expect(result.problems.map(problem => problem.reason)).toEqual([
      "no-food",
      "sub-recipe",
      "no-unit",
      "food-no-nutrition",
    ]);
    expect(result.usedCount).toBe(1);
    expect(result.nutrition.calories).toBe("10");
  });

  test("returns no values when nothing could be used", () => {
    const result = calculateRecipeNutrition([ingredient(2, null, null)], 2);
    expect(result.usedCount).toBe(0);
    expect(Object.values(result.nutrition).every(value => value === null)).toBe(true);
  });
});
