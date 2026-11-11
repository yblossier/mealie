import { describe, expect, test } from "vitest";
import {
  amazonSearchUrl,
  dishSizeLabel,
  TOOL_CATEGORIES,
  toolsMentionedIn,
  toolCategoryIcon,
  toolFormPayload,
  toolImageUrl,
  toolHierarchy,
  toolSearchName,
  withToolAccessories,
} from "./tool-display";
import { icons } from "~/lib/icons/icons";

describe("toolCategoryIcon", () => {
  test("maps each category to its own icon", () => {
    const paths = TOOL_CATEGORIES.map(category => toolCategoryIcon(category));

    expect(new Set(paths).size).toBe(TOOL_CATEGORIES.length);
    expect(toolCategoryIcon("appliance")).toBe(icons.toolAppliance);
    expect(toolCategoryIcon("cutlery")).toBe(icons.toolCutlery);
  });

  test("falls back to the generic tools icon", () => {
    expect(toolCategoryIcon(null)).toBe(icons.tools);
    expect(toolCategoryIcon(undefined)).toBe(icons.tools);
    expect(toolCategoryIcon("unknown")).toBe(icons.tools);
  });
});

describe("dishSizeLabel", () => {
  test("shows length, width and height of a rectangular dish", () => {
    expect(dishSizeLabel({ dishShape: "rectangular", length: 30, width: 20, height: 6.5 })).toBe("30 × 20 × 6.5 cm");
  });

  test("shows the diameter of a round dish", () => {
    expect(dishSizeLabel({ dishShape: "round", diameter: 24, height: 5, length: 99 })).toBe("Ø 24 × 5 cm");
  });

  test("is empty without size", () => {
    expect(dishSizeLabel({ dishShape: "round" })).toBe("");
  });
});

describe("toolFormPayload", () => {
  test("keeps the size and usages of a dish", () => {
    expect(toolFormPayload({
      name: "Moule",
      category: "dishes",
      dishShape: "round",
      length: 10,
      diameter: "24,5" as unknown as number,
      height: 5,
      usages: ["oven"],
      parentId: "p1",
    })).toEqual({
      name: "Moule",
      category: "dishes",
      dishShape: "round",
      length: null,
      width: null,
      height: 5,
      diameter: 24.5,
      usages: ["oven"],
      parentId: null,
    });
  });

  test("keeps only the parent of an appliance", () => {
    const payload = toolFormPayload({ name: "Panier", category: "appliance", parentId: "p1", length: 3, usages: ["gas"] });

    expect(payload.parentId).toBe("p1");
    expect(payload.dishShape).toBeNull();
    expect(payload.length).toBeNull();
    expect(payload.usages).toEqual([]);
  });

  test("defaults to the utensils category and drops empty sizes", () => {
    const payload = toolFormPayload({ name: "Fouet", category: null });
    expect(payload.category).toBe("utensils");
    expect(toolFormPayload({ name: "Plat", category: "dishes", length: "" as unknown as number }).length).toBeNull();
  });
});

describe("withToolAccessories", () => {
  const thermomix = { id: "thermomix", parentId: null };
  const basket = { id: "basket", parentId: "thermomix" };
  const whisk = { id: "whisk", parentId: null };
  const all = [thermomix, basket, whisk];
  const ids = (tools: { id: string }[]) => tools.map(tool => tool.id);

  test("adding an accessory adds its appliance", () => {
    expect(ids(withToolAccessories([whisk], [whisk, basket], all))).toEqual(["whisk", "basket", "thermomix"]);
  });

  test("removing the appliance removes its accessories", () => {
    expect(ids(withToolAccessories([thermomix, basket, whisk], [basket, whisk], all))).toEqual(["whisk"]);
  });

  test("removing an accessory keeps the appliance", () => {
    expect(ids(withToolAccessories([thermomix, basket], [thermomix], all))).toEqual(["thermomix"]);
  });

  test("uses the known parent when the selected tool lacks it", () => {
    expect(ids(withToolAccessories([], [{ id: "basket" }], all))).toEqual(["basket", "thermomix"]);
  });
});
describe("toolSearchName", () => {
  test.each([
    ["Plats :: Moule à cake", "Moule à cake"],
    ["Cuisine > Plats > Cocotte", "Cocotte"],
    ["Linge | Torchon", "Torchon"],
    ["Fouet", "Fouet"],
    ["  Fouet  ", "Fouet"],
    ["Plats :: ", "Plats"],
  ])("%s -> %s", (name, expected) => {
    expect(toolSearchName(name)).toBe(expected);
  });
});

describe("amazonSearchUrl", () => {
  test("searches the last part of the name on amazon.fr", () => {
    expect(amazonSearchUrl("Plats :: Moule à cake")).toBe("https://www.amazon.fr/s?k=Moule%20%C3%A0%20cake");
  });

  test("encodes special characters", () => {
    expect(amazonSearchUrl("Couteau & planche")).toBe("https://www.amazon.fr/s?k=Couteau%20%26%20planche");
  });
});

describe("toolImageUrl", () => {
  test("versions the photo URL with its cache key", () => {
    expect(toolImageUrl({ id: "abc", image: "key1" })).toBe("/api/media/tools/abc/original.webp?version=key1");
  });

  test("is null without a photo", () => {
    expect(toolImageUrl({ id: "abc", image: null })).toBeNull();
    expect(toolImageUrl({ id: "", image: "key1" })).toBeNull();
  });
});

describe("toolHierarchy", () => {
  test("lists each accessory right after its appliance", () => {
    const tools = [
      { id: "basket", parentId: "thermomix" },
      { id: "whisk", parentId: null },
      { id: "thermomix", parentId: null },
      { id: "spatula", parentId: "thermomix" },
      { id: "lid", parentId: "absent" },
    ];

    expect(toolHierarchy(tools).map(row => [row.tool.id, row.index, row.child, row.last])).toEqual([
      ["whisk", 1, false, false],
      ["thermomix", 2, false, false],
      ["basket", 0, true, false],
      ["spatula", 3, true, true],
      ["lid", 4, false, false],
    ]);
  });
});

describe("toolsMentionedIn", () => {
  const tools = [
    { id: "1", name: "Plats :: Moule à cake" },
    { id: "2", name: "Fouet" },
    { id: "3", name: "Thermomix" },
    { id: null, name: "Four" },
  ];

  test("finds tools named in the text, ignoring case, accents and prefixes", () => {
    expect(toolsMentionedIn("Versez dans le MOULE A CAKE puis fouettez au fouet.", tools)).toEqual(["1", "2"]);
  });

  test("does not match a tool name inside another word", () => {
    expect(toolsMentionedIn("Ajoutez le préthermomixage", tools)).toEqual([]);
  });

  test("skips tools without an id", () => {
    expect(toolsMentionedIn("Préchauffez le four", tools)).toEqual([]);
  });
});
