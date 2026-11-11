import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import RecipeDataNutritionReferenceDialog from "./RecipeDataNutritionReferenceDialog.vue";
import { i18n } from "~/tests/setup";
import type { IngredientFoodNutritionReference } from "~/lib/api/types/recipe";

const mocks = vi.hoisted(() => ({
  searchNutritionReferences: vi.fn(),
  searchOpenFoodFacts: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({
    foods: { searchNutritionReferences: mocks.searchNutritionReferences, searchOpenFoodFacts: mocks.searchOpenFoodFacts },
  }),
}));

const t = (key: string, values: Record<string, unknown> = {}) => i18n.global.t(key, values);

const lemon = {
  source: "ciqual",
  code: "13009",
  name: "Citron, pulpe, cru",
  nutrition: { calories: "35", proteinContent: "0.6", carbohydrateContent: "3.1", fatContent: "0.3" },
  averageWeight: 58,
} as IngredientFoodNutritionReference;

const usdaLemon = {
  source: "usda",
  code: "167746",
  name: "Lemons, raw, without peel",
  nutrition: { calories: "29" },
  averageWeight: null,
} as IngredientFoodNutritionReference;

const nutella = {
  source: "off",
  code: "3017620422003",
  name: "Nutella (Ferrero)",
  nutrition: { calories: "539" },
  averageWeight: null,
} as IngredientFoodNutritionReference;

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(RecipeDataNutritionReferenceDialog, {
    props: { "modelValue": true, "onUpdate:modelValue": () => {}, ...props },
    global: {
      mocks: { $globals: { icons: { database: "database", search: "search" } } },
      stubs: {
        BaseDialog: { props: ["modelValue", "title"], template: "<div class=\"dialog\"><slot /></div>" },
        VCardText: { template: "<div><slot /></div>" },
        VTextField: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template: "<input class=\"search\" :value=\"modelValue\" @input=\"$emit('update:modelValue', $event.target.value)\" />",
        },
        VAlert: { template: "<div class=\"alert\"><slot /></div>" },
        VList: { template: "<div class=\"list\"><slot /></div>" },
        VListItem: { emits: ["click"], template: "<div class=\"reference\" @click=\"$emit('click')\"><slot name=\"prepend\" /><slot /></div>" },
        VListItemTitle: { template: "<div class=\"title\"><slot /></div>" },
        VListItemSubtitle: { template: "<div class=\"subtitle\"><slot /></div>" },
        VChip: { template: "<span class=\"chip\"><slot /></span>" },
        VProgressCircular: { template: "<span />" },
      },
    },
  });
}

describe("RecipeDataNutritionReferenceDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mocks.searchNutritionReferences.mockResolvedValue({ data: [lemon, usdaLemon], error: null });
    mocks.searchOpenFoodFacts.mockResolvedValue({ data: [], error: null });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("searches the food's name when it opens", async () => {
    const wrapper = mountDialog({ query: "citron" });
    await flushPromises();

    expect(mocks.searchNutritionReferences).toHaveBeenCalledWith("citron", 20);
    const references = wrapper.findAll(".reference");
    expect(references).toHaveLength(2);
    expect(references[0]!.find(".chip").text()).toBe("Ciqual");
    expect(references[0]!.find(".title").text()).toBe("Citron, pulpe, cru");
    expect(references[0]!.find(".subtitle").text()).toContain("35 kcal");
    expect(references[0]!.find(".subtitle").text()).toContain(t("data-pages.foods.nutrition-search-piece-weight", { weight: 58 }));
    expect(references[1]!.find(".chip").text()).toBe("USDA FoodData Central");
  });

  test("does not search without a name", async () => {
    mountDialog();
    await flushPromises();

    expect(mocks.searchNutritionReferences).not.toHaveBeenCalled();
  });

  test("searches again once the user stops typing", async () => {
    const wrapper = mountDialog({ query: "citron" });
    await flushPromises();
    mocks.searchNutritionReferences.mockClear();

    await wrapper.find("input.search").setValue("lem");
    await wrapper.find("input.search").setValue("lemon");
    vi.advanceTimersByTime(299);
    expect(mocks.searchNutritionReferences).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    await flushPromises();

    expect(mocks.searchNutritionReferences).toHaveBeenCalledTimes(1);
    expect(mocks.searchNutritionReferences).toHaveBeenCalledWith("lemon", 20);
  });

  test("says when no food matches", async () => {
    mocks.searchNutritionReferences.mockResolvedValue({ data: [], error: null });
    const wrapper = mountDialog({ query: "xyz" });
    await flushPromises();

    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-search-no-results", { search: "xyz" }));
  });

  test("explains a technical error", async () => {
    mocks.searchNutritionReferences.mockResolvedValue({ data: null, error: { message: "Network Error" } });
    const wrapper = mountDialog({ query: "citron" });
    await flushPromises();

    expect(wrapper.find(".alert").text()).toBe(t("data-pages.foods.nutrition-search-failed", { error: "Network Error" }));
    expect(wrapper.findAll(".reference")).toHaveLength(0);
  });

  test("ignores the answer of an outdated search", async () => {
    let resolveFirst!: (value: unknown) => void;
    mocks.searchNutritionReferences
      .mockReturnValueOnce(new Promise(resolve => (resolveFirst = resolve)))
      .mockResolvedValueOnce({ data: [usdaLemon], error: null });
    const wrapper = mountDialog({ query: "citron" });

    await wrapper.find("input.search").setValue("lemon");
    vi.advanceTimersByTime(300);
    await flushPromises();
    resolveFirst({ data: [lemon], error: null });
    await flushPromises();

    const references = wrapper.findAll(".reference");
    expect(references).toHaveLength(1);
    expect(references[0]!.find(".title").text()).toBe("Lemons, raw, without peel");
  });

  test("selects a food and closes", async () => {
    const onClose = vi.fn();
    const wrapper = mountDialog({ "query": "citron", "onUpdate:modelValue": onClose });
    await flushPromises();

    await wrapper.findAll(".reference")[0]!.trigger("click");

    expect(wrapper.emitted("select")).toEqual([[lemon]]);
    expect(onClose).toHaveBeenCalledWith(false);
  });

  test("also searches Open Food Facts and lists its products after the tables", async () => {
    mocks.searchOpenFoodFacts.mockResolvedValue({ data: [nutella], error: null });
    const wrapper = mountDialog({ query: "nutella" });
    await flushPromises();

    expect(mocks.searchOpenFoodFacts).toHaveBeenCalledWith("nutella", 20);
    vi.advanceTimersByTime(2000);
    await flushPromises();
    expect(mocks.searchOpenFoodFacts).toHaveBeenCalledTimes(1);
    expect(mocks.searchNutritionReferences).toHaveBeenCalledTimes(1);
    const references = wrapper.findAll(".reference");
    expect(references).toHaveLength(3);
    expect(references[2]!.find(".chip").text()).toBe("Open Food Facts");
    expect(references[2]!.find(".title").text()).toBe("Nutella (Ferrero)");

    await references[2]!.trigger("click");
    expect(wrapper.emitted("select")).toEqual([[nutella]]);
  });

  test("waits longer before searching Open Food Facts while the user types", async () => {
    const wrapper = mountDialog({ query: "citron" });
    await flushPromises();
    mocks.searchOpenFoodFacts.mockClear();

    await wrapper.find("input.search").setValue("nutella");
    vi.advanceTimersByTime(999);
    expect(mocks.searchOpenFoodFacts).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    await flushPromises();

    expect(mocks.searchOpenFoodFacts).toHaveBeenCalledTimes(1);
    expect(mocks.searchOpenFoodFacts).toHaveBeenCalledWith("nutella", 20);
  });

  test("forgets the Open Food Facts products when the search changes", async () => {
    mocks.searchOpenFoodFacts.mockResolvedValueOnce({ data: [nutella], error: null });
    const wrapper = mountDialog({ query: "nutella" });
    await flushPromises();
    expect(wrapper.findAll(".reference")).toHaveLength(3);

    await wrapper.find("input.search").setValue("lemon");
    vi.advanceTimersByTime(300);
    await flushPromises();

    expect(wrapper.findAll(".reference")).toHaveLength(2);
  });

  test("does not search Open Food Facts without a name", async () => {
    mountDialog();
    await flushPromises();

    expect(mocks.searchOpenFoodFacts).not.toHaveBeenCalled();
  });

  test.each([
    [429, "data-pages.foods.nutrition-search-open-food-facts-rate-limited"],
    [503, "data-pages.foods.nutrition-search-open-food-facts-disabled"],
  ])("explains an Open Food Facts %i answer and keeps the tables' foods", async (status, key) => {
    mocks.searchOpenFoodFacts.mockResolvedValue({ data: null, error: { response: { status } } });
    const wrapper = mountDialog({ query: "nutella" });
    await flushPromises();

    expect(wrapper.find("[data-testid=nutrition-off-error]").text()).toBe(t(key));
    expect(wrapper.findAll(".reference")).toHaveLength(2);
  });

  test("explains an Open Food Facts outage", async () => {
    mocks.searchOpenFoodFacts.mockResolvedValue({
      data: null,
      error: { message: "Request failed", response: { status: 502, data: { detail: { message: "timeout" } } } },
    });
    const wrapper = mountDialog({ query: "nutella" });
    await flushPromises();

    expect(wrapper.find("[data-testid=nutrition-off-error]").text())
      .toBe(t("data-pages.foods.nutrition-search-open-food-facts-failed", { error: "timeout" }));
  });

  test("says when Open Food Facts has no product", async () => {
    const wrapper = mountDialog({ query: "xyz" });
    await flushPromises();

    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-search-open-food-facts-no-results", { search: "xyz" }));
  });
});
