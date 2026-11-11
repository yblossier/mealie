import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeNutritionFactsLabel from "./RecipeNutritionFactsLabel.vue";
import { i18n } from "~/tests/setup";
import type { Nutrition } from "~/lib/api/types/recipe";

const t = (key: string) => i18n.global.t(key);

function rows(nutrition: Nutrition | null, basis?: string) {
  const wrapper = mount(RecipeNutritionFactsLabel, { props: { nutrition, basis } });
  return {
    wrapper,
    rows: wrapper.findAll("tbody tr").map(row => row.findAll("td").map(cell => cell.text())),
  };
}

describe("RecipeNutritionFactsLabel", () => {
  test("lists the mandatory rows like a product label, even when unknown", () => {
    const { wrapper, rows: table } = rows({ calories: "100", fatContent: "3.5", sodiumContent: "400" });

    expect(table).toEqual([
      [t("recipe.nutrition-facts-energy"), "418 kJ / 100 kcal", "5%"],
      [t("recipe.fat-content"), "3.5 g", "5%"],
      [t("recipe.nutrition-facts-of-which-saturates"), "—", ""],
      [t("recipe.carbohydrate-content"), "—", ""],
      [t("recipe.nutrition-facts-of-which-sugars"), "—", ""],
      [t("recipe.protein-content"), "—", ""],
      [t("recipe.nutrition-facts-salt"), "1 g", "17%"],
    ]);
    expect(wrapper.find("thead").text()).toContain(t("recipe.nutrition-facts-per-100g"));
    expect(wrapper.text()).toContain(t("recipe.nutrition-facts-ri-footnote"));
  });

  test("adds the optional rows and the vitamins and minerals when known", () => {
    const { rows: table } = rows({ calories: "52", fiberContent: "2.4", calciumContent: "6", vitaminCContent: "4" });

    expect(table).toContainEqual([t("recipe.fiber-content"), "2.4 g", ""]);
    expect(table).toContainEqual([t("recipe.nutrition-facts-vitamins-minerals")]);
    expect(table).toContainEqual([t("recipe.calcium-content"), "6 mg", "0.8%"]);
    expect(table).toContainEqual([t("recipe.vitamin-c-content"), "4 mg", "5%"]);
    expect(table).not.toContainEqual(expect.arrayContaining([t("recipe.iron-content")]));
  });

  test("uses the given basis as the values header", () => {
    const { wrapper } = rows({ calories: "52" }, "Per serving");

    expect(wrapper.find("thead").text()).toContain("Per serving");
  });
});
