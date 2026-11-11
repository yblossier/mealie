import { describe, expect, test } from "vitest";
import { ingredientAllergenNames } from "./ingredient-allergens";

type Ingredient = Parameters<typeof ingredientAllergenNames>[0];

function withAllergens(allergens: { name: string }[] | null | undefined): Ingredient {
  return { food: { id: "food", name: "Brioche", allergens } } as unknown as Ingredient;
}

describe("ingredientAllergenNames", () => {
  test("lists the allergens of the food once each, trimmed", () => {
    expect(ingredientAllergenNames(withAllergens([{ name: " Gluten " }, { name: "Milk" }, { name: "Gluten" }]))).toEqual([
      "Gluten",
      "Milk",
    ]);
  });

  test("skips allergens without a name", () => {
    expect(ingredientAllergenNames(withAllergens([{ name: "  " }, { name: "" }, { name: "Egg" }]))).toEqual(["Egg"]);
  });

  test("has none without a food or without allergens", () => {
    expect(ingredientAllergenNames({ food: null } as Ingredient)).toEqual([]);
    expect(ingredientAllergenNames({} as Ingredient)).toEqual([]);
    expect(ingredientAllergenNames(withAllergens(null))).toEqual([]);
    expect(ingredientAllergenNames(withAllergens(undefined))).toEqual([]);
  });
});
