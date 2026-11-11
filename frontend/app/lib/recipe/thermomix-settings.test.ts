import { describe, expect, test } from "vitest";
import { isThermomixRecipe, isThermomixSiteUrl, tagThermomixSettings } from "./thermomix-settings";

const tag = (settings: string) => `<span class="thermomix-setting">${settings}</span>`;

describe("tagThermomixSettings", () => {
  test.each([
    ["Mélanger 5 min/30°C/vitesse 3.", `Mélanger ${tag("5 min/30°C/Vitesse 3")}.`],
    ["Cuire 10 min/100 °C/sens inverse/vitesse 1.", `Cuire ${tag("10 min/100°C/sens inverse/Vitesse 1")}.`],
    ["Hacher 5 sec/vitesse 5, puis racler.", `Hacher ${tag("5 sec/Vitesse 5")}, puis racler.`],
    ["Cuire 20 min/varoma/vitesse mijotage.", `Cuire ${tag("20 min/Varoma/Vitesse mijotage")}.`],
    ["Mixer 30 sec/turbo.", `Mixer ${tag("30 sec/Turbo")}.`],
    ["Chop 10 sec/speed 7.5.", `Chop ${tag("10 sec/Vitesse 7.5")}.`],
    ["Mixer **30 sec/vitesse 10**.", `Mixer ${tag("30 sec/Vitesse 10")}.`],
  ])("tags the settings of %s", (text, expected) => {
    expect(tagThermomixSettings(text)).toBe(expected);
  });

  test("leaves text without settings untouched", () => {
    expect(tagThermomixSettings("Cuire 45 minutes à 170°C.")).toBe("Cuire 45 minutes à 170°C.");
  });
});

describe("isThermomixRecipe", () => {
  test.each([
    ["https://www.cookomix.com/recettes/risotto-thermomix/", true],
    ["https://cookomix.com/recettes/risotto-thermomix/", true],
    ["http://www.cookomix.com/recettes/risotto-thermomix/", true],
    ["HTTPS://WWW.COOKOMIX.COM/recettes/", true],
    ["https://www.marmiton.org/recettes/risotto.aspx", false],
    ["https://cookomix.com.example.org/recettes/", false],
    ["https://notcookomix.com/recettes/", false],
    ["ftp://cookomix.com/recettes/", false],
    ["not a url", false],
    ["", false],
    [null, false],
  ])("detects the Cookomix recipes from %s", (url, expected) => {
    expect(isThermomixSiteUrl(url)).toBe(expected);
    expect(isThermomixRecipe({ orgURL: url })).toBe(expected);
  });

  test("follows the Thermomix setting of the recipe", () => {
    expect(isThermomixRecipe({ orgURL: null, settings: { thermomix: true } })).toBe(true);
    expect(isThermomixRecipe({ orgURL: "https://www.marmiton.org/", settings: { thermomix: false } })).toBe(false);
    expect(isThermomixRecipe({ orgURL: "https://www.cookomix.com/r/", settings: { thermomix: false } })).toBe(true);
    expect(isThermomixRecipe({})).toBe(false);
  });
});
