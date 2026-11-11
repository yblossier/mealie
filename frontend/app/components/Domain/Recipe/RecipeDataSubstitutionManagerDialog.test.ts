import { mount } from "@vue/test-utils";
import { describe, expect, test, vi } from "vitest";
import { ref } from "vue";
import RecipeDataSubstitutionManagerDialog from "./RecipeDataSubstitutionManagerDialog.vue";

const foods = [
  { id: "food", name: "Roux", pluralName: null, substitutions: [] },
  { id: "butter", name: "Butter", pluralName: null, substitutions: [] },
  { id: "flour", name: "Flour", pluralName: null, substitutions: [] },
  { id: "oil", name: "Oil", pluralName: null, substitutions: [] },
];

vi.mock("~/composables/store", () => ({
  useFoodStore: () => ({ store: ref(foods) }),
}));

function mountDialog(substitutions: Record<string, unknown>[]) {
  return mount(RecipeDataSubstitutionManagerDialog, {
    props: { data: { id: "food", name: "Roux", substitutions } as never, modelValue: true },
    global: {
      mocks: { $globals: { icons: {} } },
      stubs: {
        BaseDialog: { emits: ["submit"], template: "<div><button class=\"submit\" @click=\"$emit('submit')\" /><slot /></div>" },
        RecipeIngredientSubstitutionEditor: { template: "<div />" },
        VCardText: { template: "<div><slot /></div>" },
      },
    },
  });
}

describe("RecipeDataSubstitutionManagerDialog", () => {
  test("keeps several substitutions, combinations sharing their first food included", async () => {
    const wrapper = mountDialog([
      { substituteFoodId: "butter", additionalFoodIds: [] },
      { substituteFoodId: "butter", additionalFoodIds: ["flour"], note: "roux" },
      { substituteFoodId: "butter", additionalFoodIds: ["oil"] },
      { substituteFoodId: "flour", additionalFoodIds: ["butter"] },
      { substituteFoodId: "oil", additionalFoodIds: [] },
      { note: "water" },
    ]);

    await wrapper.find(".submit").trigger("click");

    const [saved] = wrapper.emitted("submit")![0] as [Record<string, unknown>[]];
    expect(saved.map(sub => [sub.substituteFoodId, sub.additionalFoodIds, sub.note])).toEqual([
      ["butter", [], null],
      ["butter", ["flour"], "roux"],
      ["butter", ["oil"], null],
      ["oil", [], null],
      [null, [], "water"],
    ]);
    // the foods come back expanded, so the edit form can name them before the food is saved
    expect(saved[1]!.substituteFood).toEqual({ id: "butter", name: "Butter", pluralName: null });
    expect(saved[1]!.additionalFoods).toEqual([{ id: "flour", name: "Flour", pluralName: null }]);
  });
});
