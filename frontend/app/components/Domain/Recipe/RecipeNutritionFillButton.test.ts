import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import RecipeNutritionFillButton from "./RecipeNutritionFillButton.vue";
import BaseNutritionAiIcon from "~/components/global/BaseNutritionAiIcon.vue";
import { i18n } from "~/tests/setup";
import type { Nutrition, RecipeIngredient, RecipeOut } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  getOne: vi.fn(),
  alert: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ foods: { getOne: mocks.getOne } }),
}));

vi.mock("~/composables/use-toast", () => ({
  alert: mocks.alert,
}));

const t = (key: string, values: Record<string, unknown> = {}) => i18n.global.t(key, values);

const wrappers: VueWrapper[] = [];

const grams = { name: "gram", standardUnit: "gram", standardQuantity: 1 };

function ingredient(foodId: string, quantity: number, overrides: Partial<RecipeIngredient> = {}): RecipeIngredient {
  return {
    quantity,
    unit: grams,
    food: { id: foodId, name: `food ${foodId}` },
    display: `${quantity} g food ${foodId}`,
    ...overrides,
  } as RecipeIngredient;
}

function recipe(recipeIngredient: RecipeIngredient[], recipeServings = 2): RecipeOut {
  return { id: "recipe", slug: "recipe", name: "Recipe", recipeServings, recipeIngredient } as RecipeOut;
}

function foodResponse(id: string, nutrition: Partial<Nutrition> | null, averageWeight: number | null = null) {
  return { data: { id, name: `food ${id}`, nutrition, averageWeight }, error: null };
}

function mountButton(value: RecipeOut, fab = false) {
  const wrapper = mount(RecipeNutritionFillButton, {
    props: { recipe: value, fab },
    global: {
      components: { BaseNutritionAiIcon },
      mocks: {
        $globals: { icons: { calculator: "calculator", alertCircle: "alert", foods: "foods", robot: "robot" } },
      },
      stubs: {
        VTooltip: { template: "<div><slot name=\"activator\" :props=\"{}\" /><slot /></div>" },
        VBtn: {
          props: ["loading", "color", "variant"],
          emits: ["click"],
          template: "<button type=\"button\" class=\"fill-btn\" :data-color=\"color\" :data-variant=\"variant\" @click=\"$emit('click')\"><slot /></button>",
        },
        VIcon: { template: "<i><slot /></i>" },
        BaseDialog: {
          props: ["modelValue", "canSubmit", "submitText", "cancelText"],
          template: `
            <div v-if="modelValue" class="problems-dialog" :data-can-submit="canSubmit">
              <slot />
              <button v-if="canSubmit" class="dialog-submit" type="button" @click="$emit('submit')">{{ submitText }}</button>
              <span class="dialog-cancel">{{ cancelText }}</span>
            </div>
          `,
        },
        VCardText: { template: "<div><slot /></div>" },
        VList: { template: "<ul><slot /></ul>" },
        VListItem: { template: "<li class=\"problem\"><slot /></li>" },
        VListItemTitle: { template: "<strong><slot /></strong>" },
        VListItemSubtitle: { template: "<span class=\"reason\"><slot /></span>" },
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

async function click(wrapper: VueWrapper) {
  await wrapper.get(".fill-btn").trigger("click");
  await flushPromises();
}

describe("RecipeNutritionFillButton", () => {
  beforeEach(() => {
    mocks.getOne.mockReset();
    Object.values(mocks.alert).forEach(fn => fn.mockReset());
  });

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
  });

  test("emits the nutrition per serving from the up-to-date foods", async () => {
    mocks.getOne.mockImplementation(async (id: string) =>
      foodResponse(id, id === "a" ? { calories: "100", proteinContent: "10" } : { calories: "50" }),
    );
    const wrapper = mountButton(recipe([ingredient("a", 200), ingredient("b", 400), ingredient("a", 100)]));

    await click(wrapper);

    // each food is only read once
    expect(mocks.getOne).toHaveBeenCalledTimes(2);
    expect(mocks.getOne).toHaveBeenCalledWith("a");
    expect(mocks.getOne).toHaveBeenCalledWith("b");
    const [[nutrition]] = wrapper.emitted("fill") as [[Nutrition]];
    // (300 g x 100 + 400 g x 50) / 100 / 2 servings
    expect(nutrition.calories).toBe("250");
    expect(nutrition.proteinContent).toBe("15");
    expect(nutrition.fatContent).toBeNull();
    expect(wrapper.find(".problems-dialog").exists()).toBe(false);
    expect(mocks.alert.error).not.toHaveBeenCalled();
  });

  test("weighs the ingredients without a unit with the up-to-date average weight of their food", async () => {
    mocks.getOne.mockImplementation(async (id: string) => foodResponse(id, { calories: "30" }, 110));
    const wrapper = mountButton(recipe([ingredient("lemon", 2, { unit: null, display: "2 lemons" })]));

    await click(wrapper);

    const [[nutrition]] = wrapper.emitted("fill") as [[Nutrition]];
    // 2 x 110 g x 30 / 100 / 2 servings
    expect(nutrition.calories).toBe("33");
    expect(wrapper.find(".problems-dialog").exists()).toBe(false);
  });

  test("asks for the servings before calculating", async () => {
    const wrapper = mountButton(recipe([ingredient("a", 200)], 0));

    await click(wrapper);

    expect(mocks.alert.error).toHaveBeenCalledWith(t("recipe.nutrition-no-servings"));
    expect(mocks.getOne).not.toHaveBeenCalled();
    expect(wrapper.emitted("fill")).toBeUndefined();
  });

  test("lists the ingredients that can't be used and calculates without them on request", async () => {
    mocks.getOne.mockImplementation(async (id: string) =>
      foodResponse(id, id === "a" ? { calories: "100" } : null),
    );
    const wrapper = mountButton(recipe([
      ingredient("a", 200),
      ingredient("b", 100),
      ingredient("a", 2, { unit: { name: "bunch", standardUnit: null, standardQuantity: null }, display: "2 bunch food a" }),
      { quantity: 1, unit: grams, note: "salt", display: "1 g salt" } as RecipeIngredient,
    ]));

    await click(wrapper);

    expect(wrapper.emitted("fill")).toBeUndefined();
    const dialog = wrapper.get(".problems-dialog");
    expect(dialog.attributes("data-can-submit")).toBe("true");
    expect(dialog.text()).toContain(t("recipe.nutrition-calculation-problems"));
    const problems = wrapper.findAll(".problem").map(problem => problem.text());
    expect(problems).toEqual([
      `100 g food b${t("recipe.nutrition-ingredient-food-no-nutrition", { food: "food b" })}`,
      `2 bunch food a${t("recipe.nutrition-ingredient-unit-not-convertible", { unit: "bunch" })}`,
      `1 g salt${t("recipe.nutrition-ingredient-no-food")}`,
    ]);

    await wrapper.get(".dialog-submit").trigger("click");

    const [[nutrition]] = wrapper.emitted("fill") as [[Nutrition]];
    expect(nutrition.calories).toBe("100");
  });

  test("can't calculate when no ingredient is usable", async () => {
    mocks.getOne.mockImplementation(async (id: string) => foodResponse(id, null));
    const wrapper = mountButton(recipe([ingredient("a", 200)]));

    await click(wrapper);

    const dialog = wrapper.get(".problems-dialog");
    expect(dialog.text()).toContain(t("recipe.nutrition-no-usable-ingredient"));
    expect(dialog.text()).toContain(t("recipe.nutrition-ingredient-food-no-nutrition", { food: "food a" }));
    expect(dialog.attributes("data-can-submit")).toBe("false");
    expect(wrapper.find(".dialog-submit").exists()).toBe(false);
    expect(wrapper.emitted("fill")).toBeUndefined();
  });

  test("explains a technical failure while loading the foods", async () => {
    mocks.getOne.mockResolvedValue({ data: null, error: { message: "Network Error", response: { status: 503 } } });
    const wrapper = mountButton(recipe([ingredient("a", 200)]));

    await click(wrapper);

    expect(mocks.alert.error).toHaveBeenCalledWith(
      t("recipe.nutrition-calculation-failed", { error: "HTTP 503 - Network Error" }),
    );
    expect(wrapper.find(".problems-dialog").exists()).toBe(false);
    expect(wrapper.emitted("fill")).toBeUndefined();
  });

  test("matches the recipe action buttons when used as a fab", () => {
    const button = mountButton(recipe([]), true).get(".fill-btn");
    expect(button.attributes("data-color")).toBe("info");
    expect(button.attributes("data-variant")).toBe("flat");

    const inline = mountButton(recipe([])).get(".fill-btn");
    expect(inline.attributes("data-variant")).toBe("text");
  });

  test("shows the AI robot icon", () => {
    const icon = mountButton(recipe([]), true).get("[data-testid='nutrition-ai-icon']");
    expect(icon.find("path").exists()).toBe(true);
    expect(icon.find("text").exists()).toBe(false);
  });
});
