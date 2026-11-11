import { describe, expect, test } from "vitest";
import {
  formatNumber,
  formatPercent,
  kilojoules,
  NUTRI_SCORE_COLORS,
  nutritionFactValue,
  referenceIntakeGrade,
  referenceIntakePercent,
  saltGrams,
} from "./nutrition-facts";

describe("saltGrams", () => {
  test("converts sodium in mg to salt in g", () => {
    expect(saltGrams({ sodiumContent: "400" })).toBe(1);
  });

  test("is null without sodium", () => {
    expect(saltGrams({ sodiumContent: "" })).toBeNull();
    expect(saltGrams(null)).toBeNull();
  });
});

describe("nutritionFactValue", () => {
  test("reads a stored value, or derives the salt", () => {
    const nutrition = { calories: "254", sodiumContent: "100" };
    expect(nutritionFactValue(nutrition, "calories")).toBe(254);
    expect(nutritionFactValue(nutrition, "saltContent")).toBe(0.25);
    expect(nutritionFactValue(nutrition, "calciumContent")).toBeNull();
  });
});

describe("referenceIntakePercent", () => {
  test("uses the EU reference intakes", () => {
    expect(referenceIntakePercent("calories", 200)).toBe(10);
    expect(referenceIntakePercent("saltContent", 3)).toBe(50);
    expect(referenceIntakePercent("calciumContent", 80)).toBe(10);
    expect(referenceIntakePercent("vitaminDContent", 5)).toBe(100);
  });

  test("is null without a value or a reference intake", () => {
    expect(referenceIntakePercent("calories", null)).toBeNull();
    expect(referenceIntakePercent("fiberContent", 10)).toBeNull();
  });
});

describe("referenceIntakeGrade", () => {
  test.each([
    [0, "A"],
    [5, "A"],
    [5.1, "B"],
    [10, "B"],
    [20, "C"],
    [30, "D"],
    [30.1, "E"],
    [150, "E"],
  ] as const)("%s%% is graded %s", (percent, grade) => {
    expect(referenceIntakeGrade(percent)).toBe(grade);
  });

  test("uses the Nutri-Score colors", () => {
    expect(NUTRI_SCORE_COLORS.A).toBe("#038141");
    expect(NUTRI_SCORE_COLORS.E).toBe("#E63E11");
  });
});

describe("formatting", () => {
  test("converts kcal to kJ", () => {
    expect(Math.round(kilojoules(100))).toBe(418);
  });

  test("formats with the locale", () => {
    expect(formatNumber(1.25, "fr-FR", 1)).toBe("1,3");
    expect(formatNumber(1.25, "en-US", 2)).toBe("1.25");
    expect(formatPercent(0.7, "fr-FR")).toBe("0,7%");
    expect(formatPercent(18.4, "en-US")).toBe("18%");
  });
});
