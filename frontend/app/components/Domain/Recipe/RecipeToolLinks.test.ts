import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import RecipeToolLinks from "./RecipeToolLinks.vue";
import { AMAZON_COLOR, AMAZON_LOGO_PATH } from "~/lib/recipe/tool-display";
import type { ToolSupplier } from "~/lib/api/types/group";

const passthrough = (tag: string) => ({ template: `<${tag}><slot /></${tag}>` });

function mountLinks(
  tool: { id: string; name: string; image: string | null },
  onHand: boolean,
  extra: { suppliers?: ToolSupplier[] | null; showSuppliers?: boolean } = {},
) {
  return mount(RecipeToolLinks, {
    props: { tool, onHand, ...extra },
    global: {
      mocks: { $globals: { icons: { informationOutline: "info", cartPlus: "cart" } } },
      stubs: {
        VMenu: { template: "<div class=\"menu\"><slot name=\"activator\" :props=\"{}\" /><slot /></div>" },
        VBtn: {
          props: ["href", "target", "rel"],
          template: "<a class=\"btn\" :href=\"href\" :target=\"target\" :rel=\"rel\"><slot /></a>",
        },
        VIcon: { props: ["color"], template: "<i :data-color=\"color\"><slot /></i>" },
        VImg: { props: ["src"], template: "<img :src=\"src\">" },
        VCard: passthrough("div"),
        VCardText: passthrough("div"),
        VList: passthrough("div"),
        VListItem: {
          props: ["href", "title"],
          template: "<a class=\"item\" :href=\"href\"><slot name=\"prepend\" />{{ title }}</a>",
        },
      },
    },
  });
}

const tool = { id: "t1", name: "Plats :: Moule à cake", image: null as string | null };

describe("RecipeToolLinks", () => {
  test("renders nothing for an owned tool without photo", () => {
    const wrapper = mountLinks(tool, true);

    expect(wrapper.find("[data-testid=tool-photo]").exists()).toBe(false);
    expect(wrapper.find("[data-testid=tool-amazon]").exists()).toBe(false);
  });

  test("links a missing tool to an Amazon search with the Amazon logo", () => {
    const amazon = mountLinks(tool, false).find("[data-testid=tool-amazon]");

    expect(amazon.attributes("href")).toBe("https://www.amazon.fr/s?k=Moule%20%C3%A0%20cake");
    expect(amazon.attributes("target")).toBe("_blank");
    expect(amazon.attributes("rel")).toContain("noopener");
    expect(amazon.find("i").text()).toBe(AMAZON_LOGO_PATH);
    expect(amazon.find("i").attributes("data-color")).toBe(AMAZON_COLOR);
  });

  test("shows the photo bubble and the Amazon link side by side", () => {
    const wrapper = mountLinks({ ...tool, image: "key" }, false);

    expect(wrapper.find("[data-testid=tool-photo]").exists()).toBe(true);
    expect(wrapper.find("img").attributes("src")).toBe("/api/media/tools/t1/original.webp?version=key");
    expect(wrapper.find("[data-testid=tool-amazon]").exists()).toBe(true);
  });

  test("links a missing tool to the group's enabled suppliers", () => {
    const wrapper = mountLinks(tool, false, {
      suppliers: [
        { name: "Amazon", url: "https://www.amazon.de/s?k={query}", enabled: true },
        { name: "Shop", url: "https://shop.example/search?q=", enabled: true },
        { name: "Off", url: "https://off.example/{query}", enabled: false },
      ],
    });

    expect(wrapper.find("[data-testid=tool-amazon]").attributes("href")).toBe("https://www.amazon.de/s?k=Moule%20%C3%A0%20cake");
    const shop = wrapper.find("[data-testid=tool-supplier]");
    expect(shop.attributes("href")).toBe("https://shop.example/search?q=Moule%20%C3%A0%20cake");
    expect(shop.find("i").text()).toBe("cart");
    expect(wrapper.findAll("a.btn")).toHaveLength(2);
  });

  test("groups many suppliers in a menu", () => {
    const suppliers = ["a", "b", "c"].map(name => ({ name, url: `https://${name}.example/?q=`, enabled: true }));
    const wrapper = mountLinks(tool, false, { suppliers });

    expect(wrapper.find("[data-testid=tool-suppliers]").exists()).toBe(true);
    expect(wrapper.findAll("[data-testid=tool-supplier]").map(item => item.attributes("href"))).toEqual([
      "https://a.example/?q=Moule%20%C3%A0%20cake",
      "https://b.example/?q=Moule%20%C3%A0%20cake",
      "https://c.example/?q=Moule%20%C3%A0%20cake",
    ]);
  });

  test("hides the supplier links when the group turned them off or has none", () => {
    expect(mountLinks(tool, false, { showSuppliers: false }).html()).not.toContain("btn");
    expect(mountLinks(tool, false, { suppliers: [] }).find("[data-testid=tool-amazon]").exists()).toBe(false);
  });
});
