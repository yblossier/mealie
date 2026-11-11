import type { RecipeToolWithOnHand } from "~/composables/store/use-tool-store";
import type { ToolOut } from "~/lib/api/types/recipe";

export interface ToolOnHandUpdate {
  id: string;
  payload: ToolOut;
}

/**
 * Builds the updates marking the tools as on hand (or not) for a household.
 * Tools already in the requested state are skipped.
 */
export function toolOnHandUpdates(
  tools: RecipeToolWithOnHand[],
  household: string,
  onHand: boolean,
): ToolOnHandUpdate[] {
  if (!household) {
    return [];
  }

  return tools
    .filter(tool => onHand !== (tool.householdsWithTool || []).includes(household))
    .map((tool) => {
      const { onHand: _onHand, ...data } = tool;
      const others = (tool.householdsWithTool || []).filter(slug => slug !== household);
      return {
        id: tool.id,
        payload: { ...data, householdsWithTool: onHand ? [...others, household] : others },
      };
    });
}
