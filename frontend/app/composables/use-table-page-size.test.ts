import { describe, expect, test } from "vitest";
import { DEFAULT_TABLE_PAGE_SIZE, resolveTablePageSize } from "./use-table-page-size";

describe("resolveTablePageSize", () => {
  test("prefers the user's page size", () => {
    expect(resolveTablePageSize(50, 25)).toBe(50);
  });

  test("falls back on the group default", () => {
    expect(resolveTablePageSize(null, 25)).toBe(25);
    expect(resolveTablePageSize(undefined, 25)).toBe(25);
  });

  test("falls back on the built-in default", () => {
    expect(resolveTablePageSize(null, null)).toBe(DEFAULT_TABLE_PAGE_SIZE);
    expect(resolveTablePageSize(0, Number.NaN)).toBe(DEFAULT_TABLE_PAGE_SIZE);
  });
});
