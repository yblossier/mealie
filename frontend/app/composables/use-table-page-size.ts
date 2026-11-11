import { useGroupSelf } from "~/composables/use-groups";

export const DEFAULT_TABLE_PAGE_SIZE = 15;

/** The user's own page size wins over the group default. */
export function resolveTablePageSize(userSize?: number | null, groupSize?: number | null): number {
  for (const size of [userSize, groupSize]) {
    if (typeof size === "number" && Number.isFinite(size) && size > 0) {
      return Math.round(size);
    }
  }
  return DEFAULT_TABLE_PAGE_SIZE;
}

/** The default number of rows of the configuration tables (foods, tools, allergens...). */
export function useTablePageSize() {
  const auth = useMealieAuth();
  const { group } = useGroupSelf();
  return computed(() => resolveTablePageSize(auth.user.value?.tablePageSize, group.value?.preferences?.defaultTablePageSize));
}
