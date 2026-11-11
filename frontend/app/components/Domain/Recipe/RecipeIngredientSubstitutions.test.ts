import { mount } from "@vue/test-utils";
import { describe, expect, test, vi } from "vitest";
import RecipeIngredientSubstitutions from "./RecipeIngredientSubstitutions.vue";
import type { RecipeIngredient } from "~/lib/api/types/recipe";

vi.mock("~/composables/recipes", async () => {
  const substitutions = await import("~/composables/recipes/use-ingredient-substitutions");
  return { ...substitutions, useFoodPlurality: () => ({ shouldPluralizeFood: () => false }) };
});
vi.mock("~/composables/recipes/use-recipe-ingredients", () => ({
  useFoodName: (food?: { name: string }) => food?.name ?? "",
}));

const butter = { id: "butter", name: "Butter" };
const oil = { id: "oil", name: "Oil" };
const flour = { id: "flour", name: "Flour" };
const milk = { id: "milk", name: "Milk" };

describe("RecipeIngredientSubstitutions", () => {
  test("lists every substitution, combinations included, under 'Can be replaced by'", () => {
    const ingredient = {
      referenceId: "1",
      food: {
        id: "cream",
        name: "Cream",
        substitutions: [
          { substituteFoodId: oil.id, substituteFood: oil },
          { substituteFoodId: butter.id, substituteFood: butter, additionalFoodIds: [flour.id, milk.id], additionalFoods: [flour, milk], note: "melt together" },
          { note: "yogurt" },
        ],
      },
    } as unknown as RecipeIngredient;

    const wrapper = mount(RecipeIngredientSubstitutions, {
      props: { ingredient },
      global: {
        mocks: { $globals: { icons: { swapHorizontal: "swap" } } },
        stubs: {
          VMenu: { template: "<div><slot name=\"activator\" :props=\"{}\" /><slot /></div>" },
          VBtn: true,
          VIcon: true,
          VCard: { template: "<div><slot /></div>" },
          VCardText: { template: "<div><slot /></div>" },
          SafeMarkdown: { props: ["source"], template: "<span>{{ source }}</span>" },
        },
      },
    });

    expect(wrapper.find(".substitution-header").text()).toBe("Can be replaced by");
    const items = wrapper.findAll(".substitution").map(node => node.text());
    expect(items).toStrictEqual(["Oil", "Butter + Flour + Milkmelt together", "yogurt"]);
  });
});
