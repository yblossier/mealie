import { flushPromises, mount } from "@vue/test-utils";
import { createI18n } from "vue-i18n";
import { describe, expect, it, vi } from "vitest";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import messages from "@/lang/messages/en-US.json";
import RecipeAllergenNote from "./RecipeAllergenNote.vue";

const getAllergens = vi.fn();
vi.mock("~/composables/api", () => ({ useUserApi: () => ({ recipes: { getAllergens } }) }));

function mountNote() {
  return mount(RecipeAllergenNote, {
    props: { slug: "cake", revision: "1" },
    global: {
      plugins: [createVuetify({ components }), createI18n({ legacy: false, locale: "en-US", messages: { "en-US": messages } })],
      mocks: { $globals: { icons: { allergies: "allergies" } } },
    },
  });
}

describe("recipe allergen note", () => {
  it("names each detected allergen once, in bold", async () => {
    getAllergens.mockResolvedValue({
      data: [
        { allergenId: "1", code: "milk", name: "Milk", ingredients: ["Butter", "Cream"] },
        { allergenId: "2", code: "gluten", name: "Gluten", ingredients: ["Flour"] },
        { allergenId: "3", code: "milk", name: "Milk", ingredients: ["Cheese"] },
      ],
    });
    const wrapper = mountNote();
    await flushPromises();
    expect(getAllergens).toHaveBeenCalledWith("cake");
    const note = wrapper.find("[data-testid=recipe-allergen-note]");
    expect(note.text()).toContain("Allergy");
    expect(note.findAll("strong").map(item => item.text())).toStrictEqual(["Milk", "Gluten"]);
    expect(note.text()).toContain("Contains: Milk, Gluten.");
  });

  it("is hidden when no allergen is detected", async () => {
    getAllergens.mockResolvedValue({ data: [] });
    const wrapper = mountNote();
    await flushPromises();
    expect(wrapper.find("[data-testid=recipe-allergen-note]").exists()).toBe(false);
  });
});
