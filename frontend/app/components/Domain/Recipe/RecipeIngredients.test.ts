import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";
import RecipeIngredients from "./RecipeIngredients.vue";
import type { RecipeIngredient } from "~/lib/api/types/recipe";
import { useLocales } from "~/composables/use-locales";

vi.mock("~/composables/use-locales");

vi.stubGlobal("useMealieAuth", () => ({ user: { value: { householdSlug: "home" } } }));
vi.mock("~/composables/use-logged-in-state", () => ({ useLoggedInState: () => ({ isOwnGroup: { value: true } }) }));

const ingredients = {
  curryPaste: {
    referenceId: "ingredient-curry-paste",
    quantity: 1,
    food: { id: "food-1", name: "curry paste" },
  },
  coconutMilk: {
    referenceId: "ingredient-coconut-milk",
    quantity: 1,
    food: { id: "food-2", name: "coconut milk" },
  },
} satisfies Record<string, RecipeIngredient>;

function mountIngredients(value: RecipeIngredient[], storageKey = "recipe-ingredients:test-recipe:checked") {
  return mount(RecipeIngredients, {
    props: {
      value,
      storageKey,
    },
    global: {
      mocks: {
        $globals: { icons: { informationOutline: "info-icon" } },
      },
      stubs: {
        AppButtonCopy: true,
        RecipeIngredientAddToListMenu: true,
        RecipeIngredientListItem: true,
        VCheckbox: {
          props: ["modelValue"],
          emits: ["update:modelValue"],
          template: `
            <button
              class="checkbox"
              type="button"
              :aria-pressed="modelValue ? 'true' : 'false'"
              @click="$emit('update:modelValue', !modelValue)"
            />
          `,
        },
        VDivider: true,
        VListItem: {
          template: "<div class=\"list-item\" @click=\"$emit('click', $event)\"><slot name=\"prepend\" /><slot /><slot name=\"append\" /></div>",
        },
        VTooltip: {
          template: "<div class=\"tooltip\"><slot name=\"activator\" :props=\"{}\" /><span class=\"tooltip-text\"><slot /></span></div>",
        },
        VIcon: {
          template: "<i v-bind=\"$attrs\"><slot /></i>",
        },
        VListItemTitle: {
          template: "<div><slot /></div>",
        },
      },
    },
  });
}

describe("RecipeIngredients", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(useLocales).mockReturnValue({
      locales: [{ value: "en-US", pluralFoodHandling: "always" }],
      locale: { value: "en-US", pluralFoodHandling: "always" },
    } as any);
  });

  test("restores checked ingredients from session storage by reference id", async () => {
    const firstWrapper = mountIngredients([ingredients.curryPaste, ingredients.coconutMilk]);
    await firstWrapper.findAll(".checkbox")[0].trigger("click");
    await nextTick();

    expect(firstWrapper.findAll(".checkbox")[0].attributes("aria-pressed")).toBe("true");
    firstWrapper.unmount();

    const secondWrapper = mountIngredients([ingredients.coconutMilk, ingredients.curryPaste]);

    expect(secondWrapper.findAll(".checkbox")[0].attributes("aria-pressed")).toBe("false");
    expect(secondWrapper.findAll(".checkbox")[1].attributes("aria-pressed")).toBe("true");
  });

  test("shows the allergens of a food linked to allergens in an info bubble", () => {
    const wrapper = mountIngredients([
      {
        ...ingredients.curryPaste,
        food: { ...ingredients.curryPaste.food, allergens: [{ id: "a1", name: "Mustard" }, { id: "a2", name: "Celery" }] },
      } as RecipeIngredient,
      ingredients.coconutMilk,
    ]);

    expect(wrapper.findAll("[data-testid='ingredient-allergen-info']")).toHaveLength(1);
    expect(wrapper.find(".tooltip-text").text()).toBe("Allergens: Mustard, Celery");
  });

  test("shows no info bubble when no food is linked to an allergen", () => {
    const wrapper = mountIngredients([ingredients.curryPaste, ingredients.coconutMilk]);

    expect(wrapper.find("[data-testid='ingredient-allergen-info']").exists()).toBe(false);
  });
});
