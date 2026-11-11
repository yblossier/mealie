import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import RecipeNutrition from "./RecipeNutrition.vue";
import { i18n } from "~/tests/setup";
import type { Nutrition, RecipeOut } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  alert: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

vi.mock("~/composables/use-toast", () => ({
  alert: mocks.alert,
}));

const wrappers: VueWrapper[] = [];

const recipe = { id: "recipe", slug: "recipe", recipeServings: 2, recipeIngredient: [] } as unknown as RecipeOut;

function mountNutrition(props: { edit: boolean; recipe?: RecipeOut | null; modelValue: Nutrition }) {
  const wrapper = mount(RecipeNutrition, {
    props: {
      ...props,
      "onUpdate:modelValue": (value: Nutrition) => wrapper.setProps({ modelValue: value }),
    },
    global: {
      mocks: { $globals: { icons: { delete: "delete-icon" } } },
      stubs: {
        RecipeNutritionFillButton: {
          props: ["recipe"],
          emits: ["fill"],
          template: "<button type=\"button\" class=\"fill-button\" :data-recipe=\"recipe?.id\" @click=\"$emit('fill', { calories: '250', proteinContent: '12' })\" />",
        },
        VCard: { template: "<div><slot /></div>" },
        VCardTitle: { template: "<div class=\"title\"><slot /></div>" },
        VCardText: { template: "<div><slot /></div>" },
        VDivider: { template: "<hr>" },
        VBtn: { emits: ["click"], template: "<button type=\"button\" v-bind=\"$attrs\" @click=\"$emit('click')\"><slot /></button>" },
        VIcon: { template: "<i><slot /></i>" },
        VNumberInput: { props: ["modelValue", "label"], template: "<input class=\"number\" :data-label=\"label\" :value=\"modelValue\">" },
        RecipeNutritionFactsLabel: {
          props: ["nutrition", "basis"],
          template: "<div class=\"facts-label\" :data-basis=\"basis\" :data-calories=\"nutrition?.calories\" />",
        },
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

describe("RecipeNutrition", () => {
  beforeEach(() => {
    mocks.alert.success.mockReset();
  });

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
  });

  test("shows the calculation button in the title while editing", () => {
    const wrapper = mountNutrition({ edit: true, recipe, modelValue: { calories: null } });

    expect(wrapper.get(".title").find(".fill-button").exists()).toBe(true);
    expect(wrapper.get(".fill-button").attributes("data-recipe")).toBe(recipe.id);
  });

  test("hides the calculation button outside of the editor, or without a recipe", () => {
    expect(mountNutrition({ edit: false, recipe, modelValue: { calories: "100" } }).find(".fill-button").exists()).toBe(false);
    expect(mountNutrition({ edit: true, modelValue: { calories: null } }).find(".fill-button").exists()).toBe(false);
  });

  test("fills the edited values with the calculated ones and keeps the others", async () => {
    const wrapper = mountNutrition({ edit: true, recipe, modelValue: { calories: "1", fiberContent: "3" } });

    await wrapper.get(".fill-button").trigger("click");

    expect(wrapper.props("modelValue")).toEqual({ calories: "250", proteinContent: "12", fiberContent: "3" });
    expect(mocks.alert.success).toHaveBeenCalledWith(i18n.global.t("recipe.nutrition-filled-from-ingredients"));
  });

  test("clears every value while editing", async () => {
    const wrapper = mountNutrition({ edit: true, recipe, modelValue: { calories: "250", fiberContent: "3", fatContent: null } });

    await wrapper.get("[data-testid='clear-recipe-nutrition']").trigger("click");

    expect(wrapper.props("modelValue")).toEqual({ calories: null, fiberContent: null, fatContent: null });
    expect(wrapper.find("[data-testid='clear-recipe-nutrition']").exists()).toBe(false);
  });

  test("shows the values as a product label, per serving", () => {
    const wrapper = mountNutrition({ edit: false, recipe, modelValue: { calories: "250", fatContent: null } });

    const label = wrapper.get(".facts-label");
    expect(label.attributes("data-basis")).toBe(i18n.global.t("recipe.nutrition-facts-per-serving"));
    expect(label.attributes("data-calories")).toBe("250");
    expect(wrapper.find(".number").exists()).toBe(false);
  });

  test("shows nothing outside of the editor when no value is filled", () => {
    const wrapper = mountNutrition({ edit: false, recipe, modelValue: { calories: null, fatContent: " " } });

    expect(wrapper.find(".facts-label").exists()).toBe(false);
    expect(wrapper.find(".title").exists()).toBe(false);
  });
});
