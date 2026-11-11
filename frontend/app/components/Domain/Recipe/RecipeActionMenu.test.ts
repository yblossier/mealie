import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import RecipeActionMenu from "./RecipeActionMenu.vue";
import type { RecipeOut } from "~/lib/api/types/recipe";

vi.mock("./RecipeContextMenu/RecipeContextMenu.vue", () => ({ default: { template: "<div />" } }));
vi.mock("./RecipeFavoriteBadge.vue", () => ({ default: { template: "<div />" } }));
vi.mock("./RecipeTimelineBadge.vue", () => ({ default: { template: "<div />" } }));
vi.mock("./RecipeNutritionFillButton.vue", () => ({
  default: {
    props: { recipe: Object, fab: Boolean },
    emits: ["fill"],
    template: "<button type=\"button\" class=\"fill-button\" :data-recipe=\"recipe?.id\" :data-fab=\"String(fab)\" @click=\"$emit('fill', { calories: '250' })\" />",
  },
}));

const wrappers: VueWrapper[] = [];

const recipe = { id: "recipe", slug: "recipe", name: "Recipe", recipeServings: 2, recipeIngredient: [] } as unknown as RecipeOut;

function mountMenu(props: { loggedIn?: boolean; canEdit?: boolean; open?: boolean }) {
  const wrapper = mount(RecipeActionMenu, {
    props: { recipe, slug: recipe.slug, name: recipe.name, recipeId: recipe.id, open: false, ...props },
    global: {
      mocks: {
        $globals: { icons: {} },
        $vuetify: { display: { xs: false } },
      },
      stubs: {
        VToolbar: { template: "<div><slot /></div>" },
        VSpacer: true,
        VTooltip: { template: "<div><slot name=\"activator\" :props=\"{}\" /></div>" },
        VBtn: { emits: ["click"], template: "<button type=\"button\" class=\"btn\" @click=\"$emit('click')\"><slot /></button>" },
        VIcon: { template: "<i><slot /></i>" },
        BaseDialog: true,
      },
    },
  });

  wrappers.push(wrapper);
  return wrapper;
}

describe("RecipeActionMenu", () => {
  beforeEach(() => {
    vi.stubGlobal("useNuxtApp", () => ({ $globals: { icons: {} } }));
  });

  afterEach(() => {
    wrappers.forEach(wrapper => wrapper.unmount());
    wrappers.length = 0;
    vi.unstubAllGlobals();
  });

  test("shows the nutrition calculation next to the edit button and forwards its values", async () => {
    const wrapper = mountMenu({ loggedIn: true, canEdit: true });

    const button = wrapper.get(".fill-button");
    expect(button.attributes("data-recipe")).toBe(recipe.id);
    expect(button.attributes("data-fab")).toBe("true");

    await wrapper.get(".fill-button").trigger("click");
    expect(wrapper.emitted("fill-nutrition")).toEqual([[{ calories: "250" }]]);
  });

  test.each([
    { loggedIn: false, canEdit: true },
    { loggedIn: true, canEdit: false },
    { loggedIn: true, canEdit: true, open: true },
  ])("hides the nutrition calculation when the recipe can't be edited from here (%j)", (props) => {
    expect(mountMenu(props).find(".fill-button").exists()).toBe(false);
  });
});
