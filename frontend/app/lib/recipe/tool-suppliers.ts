import type { ToolSupplier } from "~/lib/api/types/group";
import { toolSearchName } from "~/lib/recipe/tool-display";

/** The supplier of the groups that never configured theirs. */
export const DEFAULT_TOOL_SUPPLIERS: ToolSupplier[] = [
  { name: "Amazon", url: "https://www.amazon.fr/s?k={query}", enabled: true },
];

const QUERY_PLACEHOLDER = /\{query\}|%s/g;

export interface ToolSupplierLink {
  name: string;
  url: string;
  amazon: boolean;
}

export function isValidSupplierUrl(url: string | null | undefined): boolean {
  return /^https?:\/\/\S+$/i.test((url ?? "").trim());
}

export function isAmazonUrl(url: string): boolean {
  try {
    return /(^|\.)amazon\.[a-z.]+$/i.test(new URL(url).hostname);
  }
  catch {
    return false;
  }
}

/**
 * The supplier's search URL for a tool: `{query}` (or `%s`) is replaced by the URL-encoded tool name,
 * which is appended when the URL has no placeholder.
 */
export function supplierSearchUrl(url: string, toolName: string): string {
  const query = encodeURIComponent(toolSearchName(toolName));
  const template = url.trim();
  if (template.match(QUERY_PLACEHOLDER)) {
    return template.replace(QUERY_PLACEHOLDER, () => query);
  }
  return template + query;
}

/** The search links of the enabled suppliers for a tool. */
export function toolSupplierLinks(suppliers: ToolSupplier[] | null | undefined, toolName: string): ToolSupplierLink[] {
  return (suppliers ?? [])
    .filter(supplier => supplier.enabled !== false && supplier.name?.trim() && isValidSupplierUrl(supplier.url))
    .map((supplier) => {
      const url = supplierSearchUrl(supplier.url, toolName);
      return { name: supplier.name.trim(), url, amazon: isAmazonUrl(url) };
    });
}
