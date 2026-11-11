import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeDataFoodAliasesField from "./RecipeDataFoodAliasesField.vue";

function mountField(aliases: { name: string }[] | null, excludedNames: (string | null)[] = []) {
  return mount(RecipeDataFoodAliasesField, {
    props: { "modelValue": aliases, excludedNames, "onUpdate:modelValue": () => {} },
    global: {
      stubs: {
        VCombobox: {
          props: ["modelValue", "label"],
          emits: ["update:modelValue"],
          template: "<div class=\"combobox\" :data-values=\"modelValue.join('|')\" :data-label=\"label\" />",
        },
      },
    },
  });
}

describe("RecipeDataFoodAliasesField", () => {
  test("shows one chip per alias", () => {
    const wrapper = mountField([{ name: "Beurre" }, { name: "Butter fat" }]);
    expect(wrapper.find(".combobox").attributes("data-values")).toBe("Beurre|Butter fat");
  });

  test("keeps trimmed, unique aliases that are not the food's own names", async () => {
    const wrapper = mountField([], ["Butter", "Butters"]);

    wrapper.findComponent(".combobox").vm.$emit("update:modelValue", [" Beurre ", "beurre", "", "butter", "Butters", "Ghee"]);
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual([[{ name: "Beurre" }, { name: "Ghee" }]]);
  });

  test("empties the aliases when every chip is removed", async () => {
    const wrapper = mountField([{ name: "Beurre" }]);

    wrapper.findComponent(".combobox").vm.$emit("update:modelValue", null);
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual([[]]);
  });
});
