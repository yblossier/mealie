import { mount } from "@vue/test-utils";
import { describe, expect, test, vi } from "vitest";
import RecipeIngredientListItem from "./RecipeIngredientListItem.vue";
import type { RecipeIngredient } from "~/lib/api/types/recipe";
import { ingredientAllergenNames } from "~/lib/recipe/ingredient-allergens";

vi.stubGlobal("useRoute", () => ({ params: { groupSlug: "home" } }));
vi.stubGlobal("useMealieAuth", () => ({ user: { value: { groupSlug: "home" } } }));
vi.mock("~/composables/recipes", () => ({
  useIngredientTextParser: () => ({
    useParsedIngredientText: (ingredient: RecipeIngredient) => ({
      quantity: "1",
      unit: "",
      name: ingredient.food?.name ?? "",
      note: ingredient.note ?? "",
    }),
  }),
}));

const butter = { referenceId: "1", quantity: 1, food: { id: "f1", name: "butter", allergens: [{ id: "a1", name: "Milk" }] } };
const salt = { referenceId: "2", quantity: 1, food: { id: "f2", name: "salt", allergens: [] } };

function mountItem(ingredient: RecipeIngredient, highlightAllergens = true) {
  return mount(RecipeIngredientListItem, {
    props: { ingredient, highlightAllergens },
    global: {
      stubs: {
        RecipeIngredientSubstitutions: true,
        SafeMarkdown: { props: ["source"], template: "<span class=\"md\">{{ source }}</span>" },
      },
    },
  });
}

function nameOf(wrapper: ReturnType<typeof mountItem>) {
  return wrapper.findAll(".md").find(node => node.classes("text-bold"))!;
}

describe("RecipeIngredientListItem", () => {
  test("puts in bold the ingredients whose food is linked to an allergen", () => {
    expect(nameOf(mountItem(butter as RecipeIngredient)).classes()).toContain("ingredient-allergen");
    expect(nameOf(mountItem(salt as RecipeIngredient)).classes()).toContain("ingredient-plain");
  });

  test("keeps the usual style when allergens are not highlighted", () => {
    const classes = nameOf(mountItem(butter as RecipeIngredient, false)).classes();
    expect(classes).not.toContain("ingredient-allergen");
    expect(classes).not.toContain("ingredient-plain");
  });
});

describe("ingredientAllergenNames", () => {
  test("lists the allergen names of the food without repeats", () => {
    const food = { id: "f", name: "x", allergens: [{ id: "1", name: "Milk" }, { id: "2", name: "Milk" }, { id: "3", name: "Eggs" }] };
    expect(ingredientAllergenNames({ food } as RecipeIngredient)).toStrictEqual(["Milk", "Eggs"]);
    expect(ingredientAllergenNames({ food: null } as RecipeIngredient)).toStrictEqual([]);
  });
});
