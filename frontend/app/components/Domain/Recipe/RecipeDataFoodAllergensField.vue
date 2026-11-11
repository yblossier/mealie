<template>
  <div class="d-flex align-start ga-2">
    <v-autocomplete
      v-model="selectedIds"
      :items="allergenItems"
      item-title="name"
      item-value="id"
      :label="$t('data-pages.foods.allergens')"
      :hint="$t('data-pages.foods.allergens-hint')"
      persistent-hint
      :prepend-inner-icon="$globals.icons.allergies"
      multiple
      chips
      closable-chips
      clearable
      density="comfortable"
      data-testid="food-allergens"
    />
    <v-tooltip location="top" :text="$t('data-pages.foods.suggest-allergens')">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          icon
          color="info"
          variant="tonal"
          class="mt-1"
          :loading="loading"
          :disabled="!food.name || !allergenItems.length"
          data-testid="suggest-food-allergens"
          @click="suggest"
        >
          <v-icon>{{ $globals.icons.robot }}</v-icon>
        </v-btn>
      </template>
    </v-tooltip>
  </div>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import { useAllergenStore } from "~/composables/store";
import { alert } from "~/composables/use-toast";
import type { AllergenSummary } from "~/lib/api/types/allergens";

const props = defineProps<{
  food: {
    name?: string | null;
    pluralName?: string | null;
    description?: string | null;
    aliases?: { name: string }[] | null;
  };
}>();

const allergens = defineModel<AllergenSummary[] | null | undefined>({ default: () => [] });

const i18n = useI18n();
const api = useUserApi();
const { store: allergenStore } = useAllergenStore();
const loading = ref(false);

const allergenItems = computed<AllergenSummary[]>(() =>
  allergenStore.value.map(allergen => ({ id: allergen.id, name: allergen.name, code: allergen.code })),
);

const selectedIds = computed<string[]>({
  get: () => (allergens.value ?? []).map(allergen => allergen.id),
  set: (ids) => {
    const known = new Map([...(allergens.value ?? []), ...allergenItems.value].map(allergen => [allergen.id, allergen]));
    allergens.value = (ids ?? []).map(id => known.get(id)).filter((allergen): allergen is AllergenSummary => !!allergen);
  },
});

/** Adds what the AI finds to the allergens already chosen, which are kept */
async function suggest() {
  if (!props.food.name) {
    return;
  }
  loading.value = true;
  try {
    const { data } = await api.foods.suggestAllergens({
      name: props.food.name,
      pluralName: props.food.pluralName,
      description: props.food.description,
      aliases: (props.food.aliases ?? []).map(alias => alias.name).filter(Boolean),
    });
    if (!data) {
      return;
    }
    const current = allergens.value ?? [];
    const added = data.filter(allergen => !current.some(existing => existing.id === allergen.id));
    allergens.value = [...current, ...added];
    if (added.length) {
      alert.success(i18n.t("data-pages.foods.allergens-suggested", { count: added.length }, added.length));
    }
    else {
      alert.info(i18n.t("data-pages.foods.no-allergen-suggested"));
    }
  }
  finally {
    loading.value = false;
  }
}
</script>
