import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeDataFoodFormSections from "./RecipeDataFoodFormSections.vue";

function mountSections(props: Record<string, unknown>) {
  return mount(RecipeDataFoodFormSections, {
    props,
    global: {
      mocks: { $globals: { icons: { edit: "edit", informationOutline: "info" } } },
      stubs: {
        RecipeDataFoodAllergensField: { template: "<div class=\"allergens-field\" />" },
        RecipeDataNutritionPanel: {
          emits: ["fill", "average-weight"],
          template: "<button class=\"nutrition-panel\" @click=\"$emit('fill')\" />",
        },
        VBtn: { emits: ["click"], template: "<button v-bind=\"$attrs\" @click=\"$emit('click')\"><slot /></button>" },
        VTooltip: {
          props: ["text"],
          template: "<span class=\"tooltip\" :data-text=\"text\"><slot name=\"activator\" :props=\"{}\" /></span>",
        },
        VIcon: { template: "<i v-bind=\"$attrs\"><slot /></i>" },
        VDivider: { template: "<hr />" },
        VCardTitle: { template: "<div v-bind=\"$attrs\"><slot /></div>" },
        VChip: { template: "<span class=\"chip\"><slot /></span>" },
      },
    },
  });
}

describe("RecipeDataFoodFormSections", () => {
  test("hides the substitutions for a food that is not saved yet", () => {
    const wrapper = mountSections({ food: { name: "Milk" } });
    expect(wrapper.find("[data-testid='food-section-substitutions']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='food-section-allergens']").exists()).toBe(true);
    expect(wrapper.find(".nutrition-panel").exists()).toBe(true);
  });

  test("lists the named substitutions of a saved food as tags, without its aliases", async () => {
    const wrapper = mountSections({
      food: {
        name: "Butter",
        aliases: [{ name: "Beurre" }],
        substitutions: [{ substituteFoodId: "1", additionalFoodIds: ["2"] }],
      },
      foodNames: { 1: "Margarine", 2: "Salt" },
      manageLinks: true,
    });
    expect(wrapper.findAll(".chip").map(chip => chip.text())).toEqual(["Margarine + Salt"]);
    expect(wrapper.find("[data-testid='substitution-note']").exists()).toBe(false);

    const manage = wrapper.get("[data-testid='manage-substitutions']");
    // an icon-only button, named for screen readers
    expect(manage.text()).toBe("edit");
    expect(manage.attributes("aria-label")).toBeTruthy();
    await manage.trigger("click");
    await wrapper.find(".nutrition-panel").trigger("click");
    expect(wrapper.emitted("manage-substitutions")).toHaveLength(1);
    expect(wrapper.emitted("fill-nutrition")).toHaveLength(1);
  });

  test("reveals the instruction of a substitution behind an information icon", () => {
    const wrapper = mountSections({
      food: {
        name: "Butter",
        substitutions: [
          { substituteFoodId: "1", substituteFood: { id: "1", name: "Margarine", pluralName: null }, note: "Use 80 %" },
          { substituteFoodId: "1", additionalFoodIds: ["2"] },
          { substituteFoodId: "3" },
          { note: "Oil" },
        ],
      },
      foodNames: { 2: "Salt" },
      manageLinks: true,
    });
    expect(wrapper.findAll(".chip").map(chip => chip.text())).toEqual(["Margarine info", "Salt", "Oil"]);
    const notes = wrapper.findAll("[data-testid='substitution-note']");
    expect(notes).toHaveLength(1);
    expect(notes[0]!.attributes("aria-label")).toBe("Use 80 %");
    expect(wrapper.findAll(".chip .tooltip").map(tooltip => tooltip.attributes("data-text"))).toEqual(["Use 80 %"]);
  });

  test("says so when the food has no substitution", () => {
    const wrapper = mountSections({ food: { name: "Butter", substitutions: [] }, manageLinks: true });
    expect(wrapper.find(".chip").exists()).toBe(false);
    expect(wrapper.find("[data-testid='food-substitutions-empty']").exists()).toBe(true);
  });
});
