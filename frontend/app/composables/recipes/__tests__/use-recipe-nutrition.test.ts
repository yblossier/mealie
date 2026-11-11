import { describe, expect, test } from "vitest";
import { filledNutritionFields, hasNutritionValues, parseNutritionValue, type NutritionLabelType } from "../use-recipe-nutrition";

describe("parseNutritionValue", () => {
  test.each([
    ["18g", 18],
    ["450 mg", 450],
    ["320 calories", 320],
    ["4.5 g", 4.5],
    ["0", 0],
    ["", null],
    [null, null],
    [undefined, null],
    ["unknown", null],
    ["Infinity", null],
  ])("parses %j as %j", (value, expected) => {
    expect(parseNutritionValue(value)).toBe(expected);
  });
});

const labels: NutritionLabelType = {
  calories: { label: "Calories", suffix: "kcal" },
  proteinContent: { label: "Protein", suffix: "g" },
  sugarContent: { label: "Sugar", suffix: "g" },
};

describe("hasNutritionValues", () => {
  test.each([
    [null, false],
    [undefined, false],
    [{}, false],
    [{ calories: null, proteinContent: "" }, false],
    [{ calories: "   " }, false],
    [{ calories: "0" }, true],
    [{ calories: null, sugarContent: "4" }, true],
  ])("%j has values: %j", (nutrition, expected) => {
    expect(hasNutritionValues(nutrition)).toBe(expected);
  });
});

describe("filledNutritionFields", () => {
  test("lists only the filled values, in the labels' order", () => {
    expect(filledNutritionFields({ sugarContent: " 4 ", calories: "52", proteinContent: null }, labels)).toEqual([
      { key: "calories", label: "Calories", suffix: "kcal", value: "52" },
      { key: "sugarContent", label: "Sugar", suffix: "g", value: "4" },
    ]);
  });

  test("is empty without nutrition facts", () => {
    expect(filledNutritionFields(null, labels)).toEqual([]);
  });
});
