import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import RecipePrintView from "./RecipePrintView.vue";
import type { Recipe } from "~/lib/api/types/recipe";

vi.mock("~/composables/use-locales", () => ({
  useLocales: () => ({ locales: [{ value: "en-US", pluralFoodHandling: "always" }], locale: { value: "en-US" } }),
}));

vi.mock("~/composables/use-logged-in-state", () => ({
  useLoggedInState: () => ({ isOwnGroup: { value: false } }),
}));

vi.mock("~/composables/api", () => ({
  useStaticRoutes: () => ({ recipeImage: (id: string) => `/images/${id}` }),
}));

vi.mock("~/composables/recipe-page/shared-state", () => ({
  usePageState: () => ({ imageKey: { value: 1 } }),
}));

const recipe = {
  id: "recipe-id",
  slug: "cake",
  name: "Cake",
  image: "image-key",
  recipeIngredient: [],
  recipeInstructions: [
    { id: "s1", title: "Batter", summary: "", text: "Mix", ingredientReferences: [] },
    { id: "s2", title: "", summary: "", text: "Bake", ingredientReferences: [] },
  ],
  tools: [{ id: "t1", name: "Whisk", slug: "whisk", category: "utensils" }],
  settings: { showNutrition: true },
  nutrition: { calories: "254", fatContent: "15" },
} as unknown as Recipe;

function setPreferences(overrides: Record<string, boolean>) {
  localStorage.setItem("recipe-print-preferences", JSON.stringify({ showNutrition: true, ...overrides }));
}

function mountView() {
  return mount(RecipePrintView, {
    props: { recipe },
    global: {
      stubs: { SafeMarkdown: true, RecipeTimeCard: true, RecipeAllergenNote: true },
      mocks: { $globals: { icons: new Proxy({}, { get: (_, key) => String(key) }) } },
    },
  });
}

describe("RecipePrintView", () => {
  beforeEach(() => {
    setPreferences({});
  });

  test("shows the image and tools by default", () => {
    const wrapper = mountView();

    expect(wrapper.find("img").exists()).toBe(true);
    expect(wrapper.find("[data-testid='print-tools']").text()).toContain("Whisk");
  });

  test("leaves out the image and tools when turned off", () => {
    setPreferences({ showImage: false, showTools: false });

    const wrapper = mountView();

    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.find("[data-testid='print-tools']").exists()).toBe(false);
  });

  test("puts group titles on a medium grey band and steps on a lighter one", () => {
    const wrapper = mountView();

    expect(wrapper.findAll(".print-banner--group").map(el => el.text())).toContain("Batter");
    expect(wrapper.findAll(".print-banner--step")).toHaveLength(2);
  });

  test("prints the nutrition as on the recipe page", () => {
    const wrapper = mountView();

    const nutrition = wrapper.find("[data-testid='print-nutrition']");
    expect(nutrition.findAll(".nutrition-badge").length).toBeGreaterThan(0);
    expect(nutrition.findComponent({ name: "RecipeNutritionFactsLabel" }).exists()).toBe(true);
  });
});
