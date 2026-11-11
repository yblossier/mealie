import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeDataNutritionSource from "./RecipeDataNutritionSource.vue";
import { i18n } from "~/tests/setup";
import { NUTRITION_TABLES } from "~/lib/recipe/nutrition-source";

const t = (key: string, values: Record<string, unknown> = {}) => i18n.global.t(key, values);

function mountSource(props: Record<string, unknown>) {
  return mount(RecipeDataNutritionSource, {
    props,
    global: {
      mocks: { $globals: { icons: { database: "database", robot: "robot" } } },
      stubs: { VChip: { props: ["prependIcon"], template: "<span class=\"chip\" :data-icon=\"prependIcon\"><slot /></span>" } },
    },
  });
}

describe("RecipeDataNutritionSource", () => {
  test("renders nothing without a source", () => {
    expect(mountSource({ source: null }).find("[data-testid=nutrition-source]").exists()).toBe(false);
  });

  test("links to the Ciqual food and credits the table", () => {
    const wrapper = mountSource({ source: "ciqual", referenceCode: "13009", referenceName: "Citron, pulpe, cru" });

    expect(wrapper.find(".chip").text()).toBe("Ciqual");
    expect(wrapper.find(".chip").attributes("data-icon")).toBe("database");
    const link = wrapper.find("[data-testid=nutrition-source-link]");
    expect(link.text()).toBe("Citron, pulpe, cru");
    expect(link.attributes("href")).toBe("https://ciqual.anses.fr/#/aliments/13009");
    expect(link.attributes("rel")).toContain("noopener");
    const attribution = wrapper.find("[data-testid=nutrition-source-attribution]");
    expect(attribution.text()).toContain(t("data-pages.foods.nutrition-source-attribution", { attribution: NUTRITION_TABLES.ciqual.attribution }));
    expect(attribution.text()).toContain(NUTRITION_TABLES.ciqual.license);
  });

  test("shows the code when the food has no name", () => {
    const wrapper = mountSource({ source: "usda", referenceCode: "167746" });

    expect(wrapper.find(".chip").text()).toBe("USDA FoodData Central");
    expect(wrapper.find("[data-testid=nutrition-source-link]").text()).toBe("167746");
  });

  test("tells the values are an AI estimate to check", () => {
    const wrapper = mountSource({ source: "ai" });

    expect(wrapper.find(".chip").text()).toBe(t("data-pages.foods.nutrition-source-ai"));
    expect(wrapper.find(".chip").attributes("data-icon")).toBe("robot");
    expect(wrapper.find("[data-testid=nutrition-source-link]").exists()).toBe(false);
    expect(wrapper.text()).toContain(t("data-pages.foods.nutrition-source-ai-hint"));
  });
});
