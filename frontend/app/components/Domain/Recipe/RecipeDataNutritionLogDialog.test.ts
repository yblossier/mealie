import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import RecipeDataNutritionLogDialog from "./RecipeDataNutritionLogDialog.vue";
import { i18n } from "~/tests/setup";
import type { IngredientFoodNutritionLogOut } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  getNutritionLogs: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ foods: { getNutritionLogs: mocks.getNutritionLogs } }),
}));

const t = (key: string, values: Record<string, unknown> = {}) => i18n.global.t(key, values);

const lemon = { id: "lemon-id", name: "citron" };

function log(overrides: Partial<IngredientFoodNutritionLogOut> = {}): IngredientFoodNutritionLogOut {
  return {
    id: "log-1",
    groupId: "group",
    foodId: lemon.id,
    origin: "fill",
    aiModel: "gpt-4o",
    createdAt: "2026-11-09T10:00:00Z",
    steps: [
      {
        kind: "batch",
        foodsCount: 2,
        response: { name: "citron" },
        issues: [{ code: "missing-values", params: { fields: "calories,fat_content" } }],
        error: null,
        kept: false,
      },
      { kind: "retry", foodsCount: 1, response: { name: "citron", calories: 37 }, issues: [], error: null, kept: true },
    ],
    corrections: [{ field: "sugar_content", before: 9, after: 3.1 }, { field: "average_weight", before: -1, after: null }],
    result: { nutrition: { calories: "37", sugarContent: "3.1" }, averageWeight: 110 },
    error: null,
    ...overrides,
  } as IngredientFoodNutritionLogOut;
}

function mountDialog(food: typeof lemon | null = lemon, open = true) {
  return mount(RecipeDataNutritionLogDialog, {
    props: { "food": food, "modelValue": open, "onUpdate:modelValue": () => {} },
    global: {
      mocks: { $globals: { icons: { history: "history", alertCircle: "alert", check: "check", close: "close" } } },
      stubs: {
        BaseDialog: { props: ["modelValue", "title"], template: "<div class=\"dialog\" :data-title=\"title\"><slot /></div>" },
        VCardText: { template: "<div><slot /></div>" },
        VAlert: { template: "<div class=\"alert\"><slot /></div>" },
        VProgressCircular: { template: "<div class=\"loading\" />" },
        VExpansionPanels: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template: "<div class=\"panels\" :data-open=\"(modelValue || []).join(',')\"><slot /></div>",
        },
        VExpansionPanel: { template: "<div><slot /></div>" },
        VExpansionPanelTitle: { template: "<div class=\"panel-title\"><slot /></div>" },
        VExpansionPanelText: { template: "<div class=\"panel-text\"><slot /></div>" },
        VIcon: { template: "<i><slot /></i>" },
        VChip: { template: "<span class=\"chip\"><slot /></span>" },
      },
    },
  });
}

describe("RecipeDataNutritionLogDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("loads the history of the food when it opens", async () => {
    mocks.getNutritionLogs.mockResolvedValue({ data: [], error: null });

    mountDialog(lemon, false);
    await flushPromises();
    expect(mocks.getNutritionLogs).not.toHaveBeenCalled();

    mountDialog();
    await flushPromises();
    expect(mocks.getNutritionLogs).toHaveBeenCalledWith("lemon-id");
  });

  test("says when the food has no history", async () => {
    mocks.getNutritionLogs.mockResolvedValue({ data: [], error: null });

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.find("[data-testid='nutrition-history-empty']").text()).toBe(
      t("data-pages.foods.nutrition-history-empty", { food: "citron" }),
    );
  });

  test("shows each step with its issues and whether its answer was kept", async () => {
    mocks.getNutritionLogs.mockResolvedValue({ data: [log()], error: null });

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-history-origin-fill"));
    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-history-model", { model: "gpt-4o" }));

    const [batch, retry] = wrapper.findAll("[data-testid='nutrition-history-step']");
    expect(batch!.text()).toContain(t("data-pages.foods.nutrition-history-step-batch", { count: 2 }));
    expect(batch!.text()).toContain(t("data-pages.foods.nutrition-history-discarded"));
    expect(batch!.text()).toContain(
      t("data-pages.foods.nutrition-issue-missing-values", { fields: `${t("recipe.calories")}, ${t("recipe.fat-content")}` }),
    );
    expect(retry!.text()).toContain(t("data-pages.foods.nutrition-history-step-retry"));
    expect(retry!.text()).toContain(t("data-pages.foods.nutrition-history-kept"));
    expect(retry!.text()).toContain(t("data-pages.foods.nutrition-history-no-issues"));
    expect(retry!.text()).toContain("\"calories\": 37");
  });

  test("shows the corrections and the result with the nutrient labels", async () => {
    mocks.getNutritionLogs.mockResolvedValue({ data: [log()], error: null });

    const wrapper = mountDialog();
    await flushPromises();

    const corrections = wrapper.find("[data-testid='nutrition-history-corrections']").text();
    expect(corrections).toContain(`${t("recipe.sugar-content")} : 9 → 3.1`);
    expect(corrections).toContain(`${t("data-pages.foods.average-weight")} : -1 → —`);

    const result = wrapper.find("[data-testid='nutrition-history-result']").text();
    expect(result).toContain(t("recipe.calories"));
    expect(result).toContain("37");
    expect(result).toContain("110");
  });

  test("shows the error of a failed estimate", async () => {
    mocks.getNutritionLogs.mockResolvedValue({
      data: [log({
        steps: [{ kind: "single", foodsCount: 1, response: null, issues: [], error: "Connection refused", kept: false }],
        corrections: [],
        result: null,
        error: "Connection refused",
      })],
      error: null,
    });

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-history-error", { error: "Connection refused" }));
    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-history-no-result"));
    expect(wrapper.text()).not.toContain(t("data-pages.foods.nutrition-history-kept"));
  });

  test("opens the latest estimate only", async () => {
    mocks.getNutritionLogs.mockResolvedValue({ data: [log(), log({ id: "log-0" })], error: null });

    const wrapper = mountDialog();
    await flushPromises();

    expect(wrapper.findAll("[data-testid='nutrition-history-log']")).toHaveLength(2);
    expect(wrapper.find(".panels").attributes("data-open")).toBe("log-1");
  });
});
