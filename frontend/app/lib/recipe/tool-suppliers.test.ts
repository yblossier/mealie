import { describe, expect, test } from "vitest";
import {
  DEFAULT_TOOL_SUPPLIERS,
  isAmazonUrl,
  isValidSupplierUrl,
  supplierSearchUrl,
  toolSupplierLinks,
} from "./tool-suppliers";

describe("supplierSearchUrl", () => {
  test("replaces the {query} placeholder with the encoded tool name", () => {
    expect(supplierSearchUrl("https://shop.example/search?q={query}&sort=1", "Moule à cake"))
      .toBe("https://shop.example/search?q=Moule%20%C3%A0%20cake&sort=1");
  });

  test("replaces the %s placeholder", () => {
    expect(supplierSearchUrl("https://shop.example/s/%s/", "fouet")).toBe("https://shop.example/s/fouet/");
  });

  test("appends the name without placeholder", () => {
    expect(supplierSearchUrl(" https://shop.example/search?q= ", "a&b")).toBe("https://shop.example/search?q=a%26b");
  });

  test("searches only the last part of a categorized name", () => {
    expect(supplierSearchUrl(DEFAULT_TOOL_SUPPLIERS[0]!.url, "Plats :: Moule à cake"))
      .toBe("https://www.amazon.fr/s?k=Moule%20%C3%A0%20cake");
  });

  test("handles several placeholders and special replacement characters", () => {
    expect(supplierSearchUrl("https://x.example/{query}?q={query}", "$&")).toBe("https://x.example/%24%26?q=%24%26");
  });
});

describe("toolSupplierLinks", () => {
  test("keeps the enabled suppliers with a valid URL", () => {
    const links = toolSupplierLinks(
      [
        { name: "Amazon", url: "https://www.amazon.de/s?k={query}", enabled: true },
        { name: "Off", url: "https://off.example/{query}", enabled: false },
        { name: "Broken", url: "javascript:alert(1)", enabled: true },
        { name: " Shop ", url: "https://shop.example/?q=", enabled: true },
      ],
      "fouet",
    );

    expect(links).toEqual([
      { name: "Amazon", url: "https://www.amazon.de/s?k=fouet", amazon: true },
      { name: "Shop", url: "https://shop.example/?q=fouet", amazon: false },
    ]);
  });

  test("handles missing suppliers", () => {
    expect(toolSupplierLinks(null, "fouet")).toEqual([]);
  });
});

test("url helpers", () => {
  expect(isValidSupplierUrl("http://a.b")).toBe(true);
  expect(isValidSupplierUrl("ftp://a.b")).toBe(false);
  expect(isValidSupplierUrl("")).toBe(false);
  expect(isAmazonUrl("https://www.amazon.co.uk/s")).toBe(true);
  expect(isAmazonUrl("https://notamazon.example/")).toBe(false);
  expect(isAmazonUrl("not a url")).toBe(false);
});
