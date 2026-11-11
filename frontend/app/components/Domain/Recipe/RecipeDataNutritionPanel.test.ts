import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeDataNutritionPanel from "./RecipeDataNutritionPanel.vue";
import { i18n } from "~/tests/setup";
import type { IngredientFoodNutritionReference, Nutrition } from "~/lib/api/types/recipe";

const t = (key: string) => i18n.global.t(key);

function mountPanel(nutrition: Nutrition | null, props: Record<string, unknown> = {}) {
  return mount(RecipeDataNutritionPanel, {
    props: { "modelValue": nutrition, "onUpdate:modelValue": () => {}, ...props },
    global: {
      mocks: { $globals: { icons: { foods: "foods", eraser: "eraser", database: "database", robot: "robot" } } },
      stubs: {
        BaseNutritionAiIcon: { template: "<span class=\"ai-icon\" />" },
        VTooltip: { props: ["text"], template: "<div :data-tooltip=\"text\"><slot name=\"activator\" :props=\"{}\" /></div>" },
        VBtn: { emits: ["click"], template: "<button v-bind=\"$attrs\" @click=\"$emit('click', $event)\"><slot /></button>" },
        RecipeDataNutritionSource: {
          props: ["source", "referenceCode", "referenceName"],
          template: "<div class=\"source\" :data-source=\"source\" :data-code=\"referenceCode\" />",
        },
        RecipeDataNutritionReferenceDialog: {
          props: ["modelValue", "query"],
          emits: ["update:modelValue", "select"],
          template: "<div class=\"reference-dialog\" :data-open=\"modelValue\" :data-query=\"query\" />",
        },
        BaseButton: { emits: ["click"], template: "<button v-bind=\"$attrs\" @click=\"$emit('click')\"><slot name=\"icon\" /><slot /></button>" },
        VCardTitle: { template: "<div class=\"title\"><slot /></div>" },
        VRow: { template: "<div><slot /></div>" },
        VCol: { template: "<div><slot /></div>" },
        VIcon: { template: "<i><slot /></i>" },
        VChip: { template: "<span class=\"filled-count\"><slot /></span>" },
        VTextField: {
          props: ["modelValue", "label", "suffix"],
          emits: ["update:modelValue"],
          template: "<input class=\"nutrition-field\" :data-label=\"label\" :data-suffix=\"suffix\" :value=\"modelValue\" @input=\"$emit('update:modelValue', $event.target.value)\" />",
        },
      },
    },
  });
}

describe("RecipeDataNutritionPanel", () => {
  test("is a plain section showing its values per 100 g under its title", () => {
    const wrapper = mountPanel(null);

    expect(wrapper.find(".title").text()).toBe(t("recipe.nutrition"));
    expect(wrapper.get("[data-testid=nutrition-per-100g]").element.tagName).toBe("SMALL");
    expect(wrapper.get("[data-testid=nutrition-per-100g]").text()).toBe(t("data-pages.foods.nutrition-per-100g"));
    expect(wrapper.findAll(".nutrition-field").length).toBeGreaterThan(0);
    expect(wrapper.get("[data-testid=search-nutrition-tables]").text())
      .toContain(t("data-pages.foods.nutrition-fill-from-references"));
  });

  test("lists every nutrient, including the minerals and vitamins", () => {
    const wrapper = mountPanel({ calories: "52", calciumContent: "6" });

    const fields = wrapper.findAll(".nutrition-field");
    const labels = fields.map(field => field.attributes("data-label"));
    expect(labels).toContain(t("recipe.calories"));
    expect(labels).toContain(t("recipe.calcium-content"));
    expect(labels).toContain(t("recipe.vitamin-d-content"));
    expect(fields.find(field => field.attributes("data-label") === t("recipe.calcium-content"))!.element.value).toBe("6");
    expect(fields.find(field => field.attributes("data-label") === t("recipe.vitamin-d-content"))!.attributes("data-suffix"))
      .toBe(t("recipe.micrograms"));
    expect(wrapper.find(".filled-count").text()).toBe(`2 / ${fields.length}`);
  });

  test("updates the nutrition, emptying a cleared field", async () => {
    const wrapper = mountPanel({ calories: "52", fatContent: "0.2" });

    const field = (label: string) => wrapper.findAll(".nutrition-field").find(f => f.attributes("data-label") === t(label))!;
    await field("recipe.calcium-content").setValue("6");
    await wrapper.setProps({ modelValue: wrapper.emitted("update:modelValue")!.at(-1)![0] as Nutrition });
    await field("recipe.fat-content").setValue(" ");

    expect(wrapper.emitted("update:modelValue")!.at(-1)![0]).toEqual({ calories: "52", fatContent: null, calciumContent: "6" });
  });

  test("starts the nutrition when the food had none", async () => {
    const wrapper = mountPanel(null);

    await wrapper.find(".nutrition-field").setValue("52");

    expect(wrapper.emitted("update:modelValue")![0]).toEqual([{ calories: "52" }]);
  });

  test("shows where the values come from", () => {
    const wrapper = mountPanel({ calories: "35" }, { source: "ciqual", referenceCode: "13009" });

    expect(wrapper.find(".source").attributes("data-source")).toBe("ciqual");
    expect(wrapper.find(".source").attributes("data-code")).toBe("13009");
  });

  test("searches the composition tables with the food's name", async () => {
    const wrapper = mountPanel(null, { foodName: "citron" });

    expect(wrapper.find(".reference-dialog").attributes("data-open")).toBe("false");
    await wrapper.find("[data-testid=search-nutrition-tables]").trigger("click");

    expect(wrapper.find(".reference-dialog").attributes("data-open")).toBe("true");
    expect(wrapper.find(".reference-dialog").attributes("data-query")).toBe("citron");
  });

  test("replaces the nutrition with the chosen food of the tables", async () => {
    const wrapper = mountPanel({ calories: "52", fatContent: "1" });
    const reference = {
      source: "ciqual",
      code: "13009",
      name: "Citron, pulpe, cru",
      nutrition: { calories: "35" },
      averageWeight: 58,
    } as IngredientFoodNutritionReference;

    wrapper.findComponent(".reference-dialog").vm.$emit("select", reference);
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual([{ calories: "35" }]);
    expect(wrapper.emitted("update:source")!.at(-1)).toEqual(["ciqual"]);
    expect(wrapper.emitted("update:referenceCode")!.at(-1)).toEqual(["13009"]);
    expect(wrapper.emitted("update:referenceName")!.at(-1)).toEqual(["Citron, pulpe, cru"]);
    expect(wrapper.emitted("average-weight")).toEqual([[58]]);
  });

  test("clears the values with the red eraser icon button", async () => {
    const wrapper = mountPanel({ calories: "35" });

    const clear = wrapper.get("[data-testid=clear-nutrition]");
    expect(clear.text()).toBe("eraser");
    expect(clear.attributes("aria-label")).toBe(t("recipe.clear-nutrition"));
    await clear.trigger("click");

    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual([null]);
  });

  test("shows the AI fill button in the title bar only when asked", async () => {
    expect(mountPanel(null).find("[data-testid=fill-nutrition]").exists()).toBe(false);

    const wrapper = mountPanel(null, { canFill: true, foodName: "citron" });
    await wrapper.get("[data-testid=fill-nutrition]").trigger("click");

    expect(wrapper.emitted("fill")).toHaveLength(1);
  });

  test("forgets the source once a value is edited by hand", async () => {
    const wrapper = mountPanel({ calories: "35" }, { source: "ciqual", referenceCode: "13009", referenceName: "Citron" });

    await wrapper.find(".nutrition-field").setValue("40");

    expect(wrapper.emitted("update:source")!.at(-1)).toEqual([null]);
    expect(wrapper.emitted("update:referenceCode")!.at(-1)).toEqual([null]);
    expect(wrapper.emitted("update:referenceName")!.at(-1)).toEqual([null]);
  });
});
