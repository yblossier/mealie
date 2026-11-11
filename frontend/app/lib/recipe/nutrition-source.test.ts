import { describe, expect, test } from "vitest";
import { NUTRITION_TABLES, nutritionReferenceUrl, nutritionTable } from "./nutrition-source";

describe("nutritionTable", () => {
  test("returns the composition table of a source", () => {
    expect(nutritionTable("ciqual")).toBe(NUTRITION_TABLES.ciqual);
    expect(nutritionTable("usda")).toBe(NUTRITION_TABLES.usda);
  });

  test("returns null for AI estimates and missing sources", () => {
    expect(nutritionTable("ai")).toBeNull();
    expect(nutritionTable(null)).toBeNull();
    expect(nutritionTable(undefined)).toBeNull();
  });

  test("credits each table with its license", () => {
    expect(NUTRITION_TABLES.ciqual.attribution).toContain("Anses");
    expect(NUTRITION_TABLES.ciqual.license).toContain("Etalab");
    expect(NUTRITION_TABLES.usda.license).toContain("CC0");
    expect(NUTRITION_TABLES.off.license).toContain("ODbL");
  });
});

describe("nutritionReferenceUrl", () => {
  test("links to the food in its table", () => {
    expect(nutritionReferenceUrl("ciqual", "13009")).toBe("https://ciqual.anses.fr/#/aliments/13009");
    expect(nutritionReferenceUrl("usda", "167746")).toBe("https://fdc.nal.usda.gov/food-details/167746/nutrients");
    expect(nutritionReferenceUrl("off", "3017620422003")).toBe("https://world.openfoodfacts.org/product/3017620422003");
  });

  test("encodes the code", () => {
    expect(nutritionReferenceUrl("ciqual", "a/b")).toBe("https://ciqual.anses.fr/#/aliments/a%2Fb");
  });

  test("has no link without a table or a code", () => {
    expect(nutritionReferenceUrl("ai", "13009")).toBeNull();
    expect(nutritionReferenceUrl("ciqual", null)).toBeNull();
    expect(nutritionReferenceUrl(null, "13009")).toBeNull();
  });
});
