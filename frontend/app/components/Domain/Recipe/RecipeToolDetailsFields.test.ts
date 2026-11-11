import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, test } from "vitest";
import RecipeToolDetailsFields from "./RecipeToolDetailsFields.vue";
import type { ToolFormData } from "~/lib/recipe/tool-display";

const field = (name: string) => ({
  name,
  props: ["items", "modelValue", "label", "disabled", "hint"],
  emits: ["update:modelValue"],
  template: `<div class="${name}" :data-label="label" :data-disabled="disabled"><slot /></div>`,
});

const tools = [
  { id: "thermomix", name: "Thermomix", category: "appliance", parentId: null },
  { id: "basket", name: "Panier", category: "appliance", parentId: "thermomix" },
  { id: "robot", name: "Robot", category: "appliance", parentId: null },
  { id: "pan", name: "Poêle", category: "dishes", parentId: null },
];

function mountFields(data: ToolFormData, toolId: string | null = null) {
  const model = { ...data };
  const wrapper = mount(RecipeToolDetailsFields, {
    props: { "modelValue": model, "onUpdate:modelValue": () => {}, tools, toolId },
    global: {
      stubs: {
        VSelect: field("VSelect"),
        VAutocomplete: field("VAutocomplete"),
        VTextField: field("VTextField"),
        VBtnToggle: field("VBtnToggle"),
        VBtn: { template: "<button><slot /></button>" },
        VListItem: true,
        VIcon: true,
      },
    },
  });
  return { wrapper, model };
}

describe("RecipeToolDetailsFields", () => {
  test("shows the size and usages of a rectangular dish", () => {
    const { wrapper, model } = mountFields({ name: "Plat", category: "dishes" });

    expect(model.dishShape).toBe("rectangular");
    expect(wrapper.find("[data-testid=tool-length]").exists()).toBe(true);
    expect(wrapper.find("[data-testid=tool-width]").exists()).toBe(true);
    expect(wrapper.find("[data-testid=tool-diameter]").exists()).toBe(false);
    expect(wrapper.find("[data-testid=tool-usages]").exists()).toBe(true);
    expect(wrapper.find("[data-testid=tool-parent]").exists()).toBe(false);
  });

  test("shows the diameter of a round dish", () => {
    const { wrapper } = mountFields({ name: "Moule", category: "dishes", dishShape: "round" });

    expect(wrapper.find("[data-testid=tool-diameter]").exists()).toBe(true);
    expect(wrapper.find("[data-testid=tool-length]").exists()).toBe(false);
    expect(wrapper.find("[data-testid=tool-height]").exists()).toBe(true);
  });

  test("offers the standalone appliances as parent of an accessory", async () => {
    const { wrapper } = mountFields({ name: "Fouet", category: "appliance" }, "robot");
    await nextTick();

    const parent = wrapper.findComponent({ name: "VAutocomplete" });
    expect(parent.props("items").map((tool: { id: string }) => tool.id)).toEqual(["thermomix"]);
    expect(parent.props("disabled")).toBe(false);
    expect(wrapper.find("[data-testid=tool-length]").exists()).toBe(false);
  });

  test("an appliance with accessories cannot become an accessory", () => {
    const { wrapper } = mountFields({ name: "Thermomix", category: "appliance" }, "thermomix");

    expect(wrapper.findComponent({ name: "VAutocomplete" }).props("disabled")).toBe(true);
  });

  test("hides the dish and appliance fields for other categories", () => {
    const { wrapper } = mountFields({ name: "Torchon", category: "linen" });

    expect(wrapper.find("[data-testid=tool-usages]").exists()).toBe(false);
    expect(wrapper.find("[data-testid=tool-parent]").exists()).toBe(false);
  });
});
