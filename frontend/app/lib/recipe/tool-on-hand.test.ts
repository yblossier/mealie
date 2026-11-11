import { describe, expect, test } from "vitest";
import { toolOnHandUpdates } from "./tool-on-hand";
import type { RecipeToolWithOnHand } from "~/composables/store/use-tool-store";

const tool = (id: string, householdsWithTool: string[] | undefined): RecipeToolWithOnHand => ({
  id,
  groupId: "group",
  name: `tool ${id}`,
  slug: `tool-${id}`,
  recipeCount: 0,
  householdsWithTool: householdsWithTool as string[],
  onHand: (householdsWithTool || []).includes("home"),
});

describe("toolOnHandUpdates", () => {
  test("adds the household to the tools not on hand yet", () => {
    const updates = toolOnHandUpdates([tool("a", ["other"]), tool("b", ["home"]), tool("c", undefined)], "home", true);

    expect(updates.map(update => update.id)).toEqual(["a", "c"]);
    expect(updates[0]!.payload.householdsWithTool).toEqual(["other", "home"]);
    expect(updates[1]!.payload.householdsWithTool).toEqual(["home"]);
  });

  test("removes only the household from the tools on hand", () => {
    const updates = toolOnHandUpdates([tool("a", ["other", "home"]), tool("b", ["other"])], "home", false);

    expect(updates).toHaveLength(1);
    expect(updates[0]!.id).toBe("a");
    expect(updates[0]!.payload.householdsWithTool).toEqual(["other"]);
  });

  test("sends the tool without the computed onHand field", () => {
    const [update] = toolOnHandUpdates([tool("a", [])], "home", true);

    expect(update!.payload).toEqual({
      id: "a",
      groupId: "group",
      name: "tool a",
      slug: "tool-a",
      recipeCount: 0,
      householdsWithTool: ["home"],
    });
    expect(update!.payload).not.toHaveProperty("onHand");
  });

  test("does not modify the given tools", () => {
    const original = tool("a", ["home"]);
    toolOnHandUpdates([original], "home", false);

    expect(original.householdsWithTool).toEqual(["home"]);
    expect(original.onHand).toBe(true);
  });

  test("does nothing without a household or when nothing changes", () => {
    expect(toolOnHandUpdates([tool("a", [])], "", true)).toEqual([]);
    expect(toolOnHandUpdates([tool("a", ["home"])], "home", true)).toEqual([]);
    expect(toolOnHandUpdates([], "home", true)).toEqual([]);
  });
});
