import { icons } from "~/lib/icons/icons";
import type { DishShape, DishUsage, ToolCategory, ToolCreate } from "~/lib/api/types/recipe";

export const TOOL_CATEGORIES: ToolCategory[] = ["dishes", "linen", "appliance", "utensils", "tableware", "cutlery"];
export const DISH_SHAPES: DishShape[] = ["rectangular", "round"];
export const DISH_USAGES: DishUsage[] = ["induction", "gas", "oven", "microwave"];
export const DEFAULT_TOOL_CATEGORY: ToolCategory = "utensils";

const CATEGORY_ICONS: Record<ToolCategory, string> = {
  dishes: icons.toolDishes,
  linen: icons.toolLinen,
  appliance: icons.toolAppliance,
  utensils: icons.toolUtensils,
  tableware: icons.toolTableware,
  cutlery: icons.toolCutlery,
};

/** The icon of a tool category, or the generic tools icon when unset or unknown. */
export function toolCategoryIcon(category?: string | null): string {
  return CATEGORY_ICONS[category as ToolCategory] ?? icons.tools;
}

/** The Amazon logo (Simple Icons, CC0), drawn like any other icon path on a 24x24 grid. */
export const AMAZON_LOGO_PATH = "M.045 18.02c.072-.116.187-.124.348-.022 3.636 2.11 7.594 3.166 11.87 3.166 2.852 0 5.668-.533 8.447-1.595l.315-.14c.138-.06.234-.1.293-.13.226-.088.39-.046.525.13.12.174.09.336-.12.48-.256.19-.6.41-1.006.654-1.244.743-2.64 1.316-4.185 1.726a17.617 17.617 0 01-10.951-.577 17.88 17.88 0 01-5.43-3.35c-.1-.074-.151-.15-.151-.22 0-.047.021-.09.051-.13zm6.565-6.218c0-1.005.247-1.863.743-2.577.495-.71 1.17-1.25 2.04-1.615.796-.335 1.756-.575 2.912-.72.39-.046 1.033-.103 1.92-.174v-.37c0-.93-.105-1.558-.3-1.875-.302-.43-.78-.65-1.44-.65h-.182c-.48.046-.896.196-1.246.46-.35.27-.575.63-.675 1.096-.06.3-.206.465-.435.51l-2.52-.315c-.248-.06-.372-.18-.372-.39 0-.046.007-.09.022-.15.247-1.29.855-2.25 1.82-2.88.976-.616 2.1-.975 3.39-1.05h.54c1.65 0 2.957.434 3.888 1.29.135.15.27.3.405.48.12.165.224.314.283.45.075.134.15.33.195.57.06.254.105.42.135.51.03.104.062.3.076.615.01.313.02.493.02.553v5.28c0 .376.06.72.165 1.036.105.313.21.54.315.674l.51.674c.09.136.136.256.136.36 0 .12-.06.226-.18.314-1.2 1.05-1.86 1.62-1.963 1.71-.165.135-.375.15-.63.045a6.062 6.062 0 01-.526-.496l-.31-.347a9.391 9.391 0 01-.317-.42l-.3-.435c-.81.886-1.603 1.44-2.4 1.665-.494.15-1.093.227-1.83.227-1.11 0-2.04-.343-2.76-1.034-.72-.69-1.08-1.665-1.08-2.94l-.05-.076zm3.753-.438c0 .566.14 1.02.425 1.364.285.34.675.512 1.155.512.045 0 .106-.007.195-.02.09-.016.134-.023.166-.023.614-.16 1.08-.553 1.424-1.178.165-.28.285-.58.36-.91.09-.32.12-.59.135-.8.015-.195.015-.54.015-1.005v-.54c-.84 0-1.484.06-1.92.18-1.275.36-1.92 1.17-1.92 2.43l-.035-.02zm9.162 7.027c.03-.06.075-.11.132-.17.362-.243.714-.41 1.05-.5a8.094 8.094 0 011.612-.24c.14-.012.28 0 .41.03.65.06 1.05.168 1.172.33.063.09.099.228.099.39v.15c0 .51-.149 1.11-.424 1.8-.278.69-.664 1.248-1.156 1.68-.073.06-.14.09-.197.09-.03 0-.06 0-.09-.012-.09-.044-.107-.12-.064-.24.54-1.26.806-2.143.806-2.64 0-.15-.03-.27-.087-.344-.145-.166-.55-.257-1.224-.257-.243 0-.533.016-.87.046-.363.045-.7.09-1 .135-.09 0-.148-.014-.18-.044-.03-.03-.036-.047-.02-.077 0-.017.006-.03.02-.063v-.06z";

export const AMAZON_COLOR = "#FF9900";

// Tools are often named with a category prefix, such as "Dishes :: Cake tin".
const NAME_SEPARATORS = /::|>|\||»|→/;

/** The part of a tool name worth searching for: the last part after a category separator. */
export function toolSearchName(name: string): string {
  const parts = name.split(NAME_SEPARATORS).map(part => part.trim()).filter(Boolean);
  return parts.length ? parts[parts.length - 1]! : name.trim();
}

export function amazonSearchUrl(name: string): string {
  return `https://www.amazon.fr/s?k=${encodeURIComponent(toolSearchName(name))}`;
}

/** The URL of a tool photo, versioned by its cache key so a new photo is not served from cache. */
export function toolImageUrl(tool: { id?: string | null; image?: string | null }): string | null {
  if (!tool.id || !tool.image) {
    return null;
  }
  return `/api/media/tools/${tool.id}/original.webp?version=${encodeURIComponent(tool.image)}`;
}

type ToolSizeFields = Pick<ToolCreate, "dishShape" | "length" | "width" | "height" | "diameter">;

function formatCentimeters(value: number): string {
  return Number.isInteger(value) ? `${value}` : value.toFixed(1).replace(/\.0$/, "");
}

/** A short size such as "30 × 20 × 6 cm" or "Ø 24 × 5 cm", empty when no size is set. */
export function dishSizeLabel(tool: ToolSizeFields): string {
  const parts: string[] = [];
  if (tool.dishShape === "round") {
    if (tool.diameter) parts.push(`Ø ${formatCentimeters(tool.diameter)}`);
  }
  else {
    if (tool.length) parts.push(formatCentimeters(tool.length));
    if (tool.width) parts.push(formatCentimeters(tool.width));
  }
  if (tool.height) parts.push(formatCentimeters(tool.height));
  return parts.length ? `${parts.join(" × ")} cm` : "";
}

/** A number typed in a form, or null when the field is empty or not a positive number. */
function toCentimeters(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const number = typeof value === "number" ? value : Number(String(value).replace(",", "."));
  return Number.isFinite(number) && number > 0 ? number : null;
}

export interface ToolFormData extends Partial<ToolSizeFields> {
  name: string;
  category?: ToolCategory | null;
  usages?: DishUsage[] | null;
  parentId?: string | null;
}

/** The fields of the tool form as the API expects them, keeping only those of the chosen category. */
export function toolFormPayload(data: ToolFormData): Omit<ToolCreate, "householdsWithTool"> {
  const category = data.category ?? DEFAULT_TOOL_CATEGORY;
  const isDish = category === "dishes";
  const round = data.dishShape === "round";
  return {
    name: data.name,
    category,
    dishShape: isDish ? (data.dishShape ?? "rectangular") : null,
    length: isDish && !round ? toCentimeters(data.length) : null,
    width: isDish && !round ? toCentimeters(data.width) : null,
    height: isDish ? toCentimeters(data.height) : null,
    diameter: isDish && round ? toCentimeters(data.diameter) : null,
    usages: isDish ? [...(data.usages ?? [])] : [],
    parentId: category === "appliance" ? (data.parentId ?? null) : null,
  };
}

interface LinkedTool {
  id: string;
  parentId?: string | null;
}

/**
 * Applies the accessory rules to the tools of a recipe after the selection changed:
 * an accessory brings its appliance along, and removing an appliance removes its accessories.
 * Removing an accessory leaves its appliance in place.
 */
export function withToolAccessories<T extends LinkedTool>(previous: T[], next: T[], allTools: T[]): T[] {
  const parentOf = (tool: T) => (allTools.find(known => known.id === tool.id) ?? tool).parentId ?? null;
  const nextIds = new Set(next.map(tool => tool.id));
  const removedIds = new Set(previous.filter(tool => !nextIds.has(tool.id)).map(tool => tool.id));

  const kept = next.filter((tool) => {
    const parentId = parentOf(tool);
    return !(parentId && removedIds.has(parentId));
  });

  const keptIds = new Set(kept.map(tool => tool.id));
  for (const tool of [...kept]) {
    const parentId = parentOf(tool);
    if (!parentId || keptIds.has(parentId)) {
      continue;
    }
    const parent = allTools.find(known => known.id === parentId);
    if (parent) {
      kept.push(parent);
      keptIds.add(parent.id);
    }
  }
  return kept;
}

export interface ToolRow<T> {
  tool: T;
  /** Position of the tool in the recipe list. */
  index: number;
  /** An accessory listed under its appliance. */
  child: boolean;
  /** The last accessory of its appliance. */
  last: boolean;
}

/** The tools of a recipe ordered so each accessory comes right after its appliance. */
export function toolHierarchy<T extends LinkedTool>(tools: T[]): ToolRow<T>[] {
  const ids = new Set(tools.map(tool => tool.id));
  const isChild = (tool: T) => !!tool.parentId && ids.has(tool.parentId);
  const rows: ToolRow<T>[] = [];
  tools.forEach((tool, index) => {
    if (isChild(tool)) {
      return;
    }
    rows.push({ tool, index, child: false, last: false });
    const children = tools
      .map((child, childIndex) => ({ child, childIndex }))
      .filter(({ child }) => child.parentId === tool.id);
    children.forEach(({ child, childIndex }, position) => {
      rows.push({ tool: child, index: childIndex, child: true, last: position === children.length - 1 });
    });
  });
  return rows;
}

function normalizeForSearch(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036F]/g, "").toLowerCase();
}

/** The ids of the tools whose name appears in a step's text, ignoring case, accents and category prefixes. */
export function toolsMentionedIn(text: string, tools: { id?: string | null; name: string }[]): string[] {
  const haystack = normalizeForSearch(text);
  return tools
    .filter((tool): tool is { id: string; name: string } => !!tool.id)
    .filter((tool) => {
      const name = normalizeForSearch(toolSearchName(tool.name));
      return name.length > 1 && new RegExp(`(^|[^a-z0-9])${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`).test(haystack);
    })
    .map(tool => tool.id);
}
