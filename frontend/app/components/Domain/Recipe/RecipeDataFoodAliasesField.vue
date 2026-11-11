<template>
  <v-combobox
    :model-value="aliasNames"
    multiple
    chips
    closable-chips
    hide-no-data
    :delimiters="[',', ';']"
    :items="[]"
    variant="solo-filled"
    flat
    density="comfortable"
    :label="$t('data-pages.foods.aliases')"
    :hint="$t('data-pages.foods.aliases-hint')"
    persistent-hint
    data-testid="food-aliases"
    @update:model-value="update"
  />
</template>

<script setup lang="ts">
/** Edits the aliases of a food in place, one chip per alias */
const props = withDefaults(defineProps<{
  /** The names of the food itself, never kept as aliases */
  excludedNames?: (string | null | undefined)[];
}>(), {
  excludedNames: () => [],
});

const aliases = defineModel<{ name: string }[] | null | undefined>();

const aliasNames = computed(() => (aliases.value ?? []).map(alias => alias.name).filter(Boolean));

function update(values: unknown) {
  const excluded = new Set(props.excludedNames.filter(Boolean).map(name => name!.trim().toLowerCase()));
  const seen = new Set<string>();
  const names: string[] = [];
  for (const value of Array.isArray(values) ? values : []) {
    const name = String(value ?? "").trim();
    const key = name.toLowerCase();
    if (!name || excluded.has(key) || seen.has(key)) {
      continue;
    }
    seen.add(key);
    names.push(name);
  }
  aliases.value = names.map(name => ({ name }));
}
</script>
