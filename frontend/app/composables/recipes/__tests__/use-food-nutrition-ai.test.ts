import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent } from "vue";
import { useFoodNutritionAI } from "../use-food-nutrition-ai";
import { i18n } from "~/tests/setup";
import type { IngredientFoodOut } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  estimateNutrition: vi.fn(),
  fillNutrition: vi.fn(),
  alert: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
  aiEnabled: true,
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ foods: { estimateNutrition: mocks.estimateNutrition, fillNutrition: mocks.fillNutrition } }),
}));

vi.mock("~/composables/use-toast", () => ({
  alert: mocks.alert,
}));

vi.stubGlobal("useGroupSelf", () => ({
  group: computed(() => ({ aiProviderSettings: { aiEnabled: mocks.aiEnabled } })),
}));

const t = (key: string, values: Record<string, unknown> = {}) => i18n.global.t(key, values);

const food = { id: "apple", name: "apple", pluralName: "apples", description: "" } as IngredientFoodOut;

function setup() {
  let api!: ReturnType<typeof useFoodNutritionAI>;
  mount(defineComponent({
    setup() {
      api = useFoodNutritionAI();
      return () => null;
    },
  }));
  return api;
}

describe("useFoodNutritionAI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.aiEnabled = true;
  });

  test("tells whether the group's AI is enabled", () => {
    expect(setup().aiEnabled.value).toBe(true);
    mocks.aiEnabled = false;
    expect(setup().aiEnabled.value).toBe(false);
  });

  describe("estimate", () => {
    test("returns the estimated values only", async () => {
      mocks.estimateNutrition.mockResolvedValue({
        data: [{ nutrition: { calories: "52", calciumContent: "6", fatContent: null }, averageWeight: 150 }],
        error: null,
      });

      const estimate = await setup().estimate(food);

      expect(mocks.estimateNutrition).toHaveBeenCalledWith({ foods: [{ id: "apple", name: "apple", pluralName: "apples", description: "" }] });
      expect(estimate).toEqual({
        nutrition: { calories: "52", calciumContent: "6" },
        averageWeight: 150,
        source: null,
        referenceCode: null,
        referenceName: null,
      });
    });

    test("sends no id for a food that is not saved yet, so no history is kept", async () => {
      mocks.estimateNutrition.mockResolvedValue({ data: [{ nutrition: { calories: "52" }, averageWeight: null }], error: null });

      await setup().estimate({ name: "apple", pluralName: null, description: "" });

      expect(mocks.estimateNutrition).toHaveBeenCalledWith({ foods: [{ id: null, name: "apple", pluralName: null, description: "" }] });
    });

    test("returns the composition table the values come from", async () => {
      mocks.estimateNutrition.mockResolvedValue({
        data: [{
          nutrition: { calories: "35" },
          averageWeight: 58,
          source: "ciqual",
          referenceCode: "13009",
          referenceName: "Citron, pulpe, cru",
        }],
        error: null,
      });

      expect(await setup().estimate(food)).toEqual({
        nutrition: { calories: "35" },
        averageWeight: 58,
        source: "ciqual",
        referenceCode: "13009",
        referenceName: "Citron, pulpe, cru",
      });
    });

    test("says the food is missing from the tables when the AI is disabled", async () => {
      mocks.aiEnabled = false;
      mocks.estimateNutrition.mockResolvedValue({ data: [{ nutrition: {}, averageWeight: null, source: null }], error: null });

      expect(await setup().estimate(food)).toBeNull();
      expect(mocks.alert.warning).toHaveBeenCalledWith(t("data-pages.foods.nutrition-not-found-in-tables", { food: "apple" }));
    });

    test("warns when the AI found no value", async () => {
      mocks.estimateNutrition.mockResolvedValue({ data: [{ nutrition: { calories: null }, averageWeight: null }], error: null });

      expect(await setup().estimate(food)).toBeNull();
      expect(mocks.alert.warning).toHaveBeenCalledWith(t("data-pages.foods.nutrition-ai-no-values", { food: "apple" }));
    });

    test("still returns the average weight when the AI found no nutrition facts", async () => {
      mocks.estimateNutrition.mockResolvedValue({ data: [{ nutrition: { calories: null }, averageWeight: 110 }], error: null });

      expect(await setup().estimate(food)).toEqual({
        nutrition: null,
        averageWeight: 110,
        source: null,
        referenceCode: null,
        referenceName: null,
      });
      expect(mocks.alert.warning).toHaveBeenCalled();
    });

    test("explains a technical error", async () => {
      mocks.estimateNutrition.mockResolvedValue({ data: null, error: { message: "timeout of 120000ms exceeded" } });

      expect(await setup().estimate(food)).toBeNull();
      expect(mocks.alert.error).toHaveBeenCalledWith(
        t("data-pages.foods.nutrition-ai-technical-error", { error: "timeout of 120000ms exceeded" }),
      );
    });

    test("leaves the server's own message to the API client", async () => {
      mocks.estimateNutrition.mockResolvedValue({ data: null, error: { response: { status: 400, data: { detail: { message: "AI disabled" } } } } });

      expect(await setup().estimate(food)).toBeNull();
      expect(mocks.alert.error).not.toHaveBeenCalled();
    });
  });

  describe("generate", () => {
    test("saves the values of a food without any and returns it", async () => {
      const updated = { ...food, nutrition: { calories: "52" } };
      mocks.fillNutrition.mockResolvedValue({ data: [updated], error: null });

      expect(await setup().generate(food)).toEqual(updated);
      expect(mocks.fillNutrition).toHaveBeenCalledWith({ foodIds: ["apple"], overwrite: false });
      expect(mocks.alert.success).toHaveBeenCalledWith(t("data-pages.foods.nutrition-generated", { food: "apple" }));
    });

    test("warns when nothing was generated", async () => {
      mocks.fillNutrition.mockResolvedValue({ data: [], error: null });

      expect(await setup().generate(food)).toBeNull();
      expect(mocks.alert.warning).toHaveBeenCalledWith(t("data-pages.foods.nutrition-ai-no-values", { food: "apple" }));
    });

    test("explains a technical error with its status", async () => {
      mocks.fillNutrition.mockResolvedValue({ data: null, error: { response: { status: 502 }, message: "Bad Gateway" } });

      expect(await setup().generate(food)).toBeNull();
      expect(mocks.alert.error).toHaveBeenCalledWith(
        t("data-pages.foods.nutrition-ai-technical-error", { error: "HTTP 502 - Bad Gateway" }),
      );
    });
  });
});
