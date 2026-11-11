import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeNutritionBadges from "./RecipeNutritionBadges.vue";
import { i18n } from "~/tests/setup";
import type { Nutrition } from "~/lib/api/types/recipe";

const t = (key: string) => i18n.global.t(key);

function mountBadges(nutrition: Nutrition | null) {
  return mount(RecipeNutritionBadges, { props: { nutrition } });
}

describe("RecipeNutritionBadges", () => {
  test("shows a badge per known value, with its share of the reference intake", () => {
    const wrapper = mountBadges({ calories: "254", sodiumContent: "400", sugarContent: "5", fatContent: "15" });

    const badges = wrapper.findAll(".nutrition-badge");
    expect(badges.map(badge => badge.find(".nutrition-badge__label").text())).toEqual([
      t("recipe.calories"),
      t("recipe.sodium-content"),
      t("recipe.sugar-content"),
      t("recipe.fat-content"),
      t("recipe.nutrition-facts-salt"),
    ]);
    expect(badges.map(badge => badge.find(".nutrition-badge__number").text())).toEqual(["254", "400", "5", "15", "1"]);
    expect(badges.map(badge => badge.find(".nutrition-badge__unit").text())).toEqual(["kcal", "mg", "g", "g", "g"]);
    expect(badges.map(badge => badge.find(".nutrition-badge__percent").text())).toEqual(["13%", "17%", "5.6%", "21%", "17%"]);
    expect(wrapper.text()).toContain(t("recipe.nutrition-badges-caption"));
  });

  test("colors each badge with the Nutri-Score palette", () => {
    const wrapper = mountBadges({ calories: "60", sugarContent: "9", fatContent: "14", sodiumContent: "600" });

    const grades = wrapper.findAll(".nutrition-badge").map(badge => badge.attributes("data-grade"));
    expect(grades).toEqual(["A", "D", "B", "C", "D"]);
    expect(wrapper.find(".nutrition-badge__percent").attributes("style")).toContain("background-color: rgb(3, 129, 65)");
  });

  test("only shows the known values", () => {
    const wrapper = mountBadges({ calories: "100", fatContent: "" });

    expect(wrapper.findAll(".nutrition-badge")).toHaveLength(1);
  });

  test("renders nothing without values", () => {
    expect(mountBadges(null).find(".nutrition-badges").exists()).toBe(false);
    expect(mountBadges({ proteinContent: "10" }).find(".nutrition-badges").exists()).toBe(false);
  });
});
