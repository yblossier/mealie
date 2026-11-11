import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import { nextTick, reactive } from "vue";
import RecipeIngredientSubstitutionEditor, { type EditableSubstitution } from "./RecipeIngredientSubstitutionEditor.vue";

const foods = [
  { id: "butter", name: "Butter" },
  { id: "flour", name: "Flour" },
  { id: "oil", name: "Oil" },
];

function mountEditor(substitutions: EditableSubstitution[], framed = false) {
  return mount(RecipeIngredientSubstitutionEditor, {
    props: { substitutions, foods: foods as any, framed },
    global: {
      mocks: {
        $globals: { icons: { swapHorizontal: "swap", create: "plus", delete: "delete", close: "close" } },
        $vuetify: { display: { mdAndDown: false } },
      },
      stubs: {
        VBtnToggle: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template: "<div class=\"kind\" :data-kind=\"modelValue\"><button class=\"to-combination\" @click=\"$emit('update:modelValue', 'combination')\" /><button class=\"to-single\" @click=\"$emit('update:modelValue', 'single')\" /></div>",
        },
        VAutocomplete: {
          props: ["modelValue", "items"],
          template: "<div class=\"autocomplete\" :data-items=\"(items || []).map(i => i.id).join(',')\" />",
        },
        VBtn: { template: "<button v-bind=\"$attrs\"><slot /></button>" },
        VIcon: true,
        VTextField: true,
      },
    },
  });
}

describe("RecipeIngredientSubstitutionEditor", () => {
  test("frames each substitution only when asked", () => {
    const rows = [{ substituteFoodId: "butter", note: "" }, { substituteFoodId: "oil", note: "" }];

    expect(mountEditor(rows).findAll("[data-testid=substitution-row]").every(row => !row.classes("border-thin"))).toBe(true);
    const framed = mountEditor(rows, true).findAll("[data-testid=substitution-row]");
    expect(framed).toHaveLength(2);
    expect(framed.every(row => row.classes("border-thin") && row.classes("rounded-lg"))).toBe(true);
  });

  test("a combination starts with two foods and takes as many more as needed", async () => {
    const substitution = reactive<EditableSubstitution>({ substituteFoodId: "butter", note: "" });
    const wrapper = mountEditor([substitution]);

    await wrapper.find(".to-combination").trigger("click");
    await nextTick();
    expect(substitution.additionalFoodIds).toStrictEqual([""]);
    expect(wrapper.findAll("[data-testid='substitution-combination-food']")).toHaveLength(1);

    await wrapper.find("[data-testid='substitution-combination-add']").trigger("click");
    await wrapper.find("[data-testid='substitution-combination-add']").trigger("click");
    await nextTick();
    expect(wrapper.findAll("[data-testid='substitution-combination-food']")).toHaveLength(3);
  });

  test("a food used in the combination is not offered again", async () => {
    const substitution = reactive<EditableSubstitution>({ substituteFoodId: "butter", additionalFoodIds: ["flour", ""], note: "" });
    const wrapper = mountEditor([substitution]);
    await nextTick();

    const rows = wrapper.findAll("[data-testid='substitution-combination-food'] .autocomplete");
    expect(rows[0].attributes("data-items")).toBe("flour,oil");
    expect(rows[1].attributes("data-items")).toBe("oil");
  });

  test("removing foods keeps at least two in the combination", async () => {
    const substitution = reactive<EditableSubstitution>({ substituteFoodId: "butter", additionalFoodIds: ["flour", "oil"], note: "" });
    const wrapper = mountEditor([substitution]);

    await wrapper.findAll("[data-testid='substitution-combination-remove']")[0].trigger("click");
    await nextTick();
    expect(substitution.additionalFoodIds).toStrictEqual(["oil"]);
    expect(wrapper.find("[data-testid='substitution-combination-remove']").attributes("disabled")).toBeDefined();
    expect(wrapper.emitted("food-changed")).toStrictEqual([[0]]);
  });

  test("switching back to a single food drops the other foods", async () => {
    const substitution = reactive<EditableSubstitution>({ substituteFoodId: "butter", additionalFoodIds: ["flour"], note: "" });
    const wrapper = mountEditor([substitution]);

    await wrapper.find(".to-single").trigger("click");
    await nextTick();
    expect(substitution.additionalFoodIds).toStrictEqual([]);
    expect(wrapper.find("[data-testid='substitution-combination-food']").exists()).toBe(false);
  });
});
