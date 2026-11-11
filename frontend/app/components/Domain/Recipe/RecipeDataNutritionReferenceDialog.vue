<template>
  <BaseDialog
    v-model="dialog"
    :title="$t('data-pages.foods.nutrition-search-tables')"
    :icon="$globals.icons.database"
    :cancel-text="$t('general.close')"
    width="700"
  >
    <v-card-text>
      <v-text-field
        v-model="search"
        :label="$t('search.search')"
        :prepend-inner-icon="$globals.icons.search"
        :loading="loading"
        density="compact"
        variant="outlined"
        clearable
        autofocus
        hide-details
        data-testid="nutrition-reference-search"
      />
      <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3">
        {{ $t("data-pages.foods.nutrition-search-failed", { error }) }}
      </v-alert>
      <div v-else-if="searched && !references.length && !loading" class="pt-3 text-medium-emphasis">
        {{ $t("data-pages.foods.nutrition-search-no-results", { search: searched }) }}
      </div>
      <v-list v-if="shown.length" density="compact" class="mt-2 reference-list">
        <v-list-item
          v-for="reference in shown"
          :key="`${reference.source}:${reference.code}`"
          class="px-1"
          data-testid="nutrition-reference"
          @click="choose(reference)"
        >
          <template #prepend>
            <v-chip size="x-small" variant="tonal" :color="SOURCE_COLORS[reference.source] || 'info'" class="mr-2">
              {{ tableName(reference) }}
            </v-chip>
          </template>
          <v-list-item-title class="text-wrap">
            {{ reference.name }}
          </v-list-item-title>
          <v-list-item-subtitle>
            {{ summary(reference) }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>
      <div v-if="offLoading" class="d-flex align-center ga-2 pt-2 text-caption text-medium-emphasis" data-testid="nutrition-off-loading">
        <v-progress-circular indeterminate size="14" width="2" />
        {{ $t("data-pages.foods.nutrition-search-open-food-facts-loading") }}
      </div>
      <v-alert
        v-if="offError"
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-3"
        data-testid="nutrition-off-error"
      >
        {{ offError }}
      </v-alert>
      <div v-else-if="offSearched && !offReferences.length && !offLoading" class="pt-3 text-medium-emphasis">
        {{ $t("data-pages.foods.nutrition-search-open-food-facts-no-results", { search: offSearched }) }}
      </div>
      <div class="pt-2 text-caption text-medium-emphasis">
        {{ $t("data-pages.foods.nutrition-search-hint") }}
      </div>
    </v-card-text>
  </BaseDialog>
</template>

<script setup lang="ts">
import { useUserApi } from "~/composables/api";
import type { IngredientFoodNutritionReference, IngredientFoodNutritionSource } from "~/lib/api/types/recipe";
import { nutritionTable } from "~/lib/recipe/nutrition-source";

const props = defineProps<{
  /** Searched when the dialog opens */
  query?: string | null;
}>();

const emit = defineEmits<{
  select: [reference: IngredientFoodNutritionReference];
}>();

const dialog = defineModel<boolean>({ default: false });

const i18n = useI18n();
const api = useUserApi();

const SEARCH_DELAY = 300;
// Open Food Facts limits the requests per minute: it is searched once the user has really stopped typing
const OFF_SEARCH_DELAY = 1000;

const SOURCE_COLORS: Partial<Record<IngredientFoodNutritionSource, string>> = {
  ciqual: "success",
  usda: "info",
  off: "warning",
};

const search = ref("");
const searched = ref("");
const references = ref<IngredientFoodNutritionReference[]>([]);
const loading = ref(false);
const error = ref("");

// the packaged products of Open Food Facts are listed after the foods of the tables
const offSearched = ref("");
const offReferences = ref<IngredientFoodNutritionReference[]>([]);
const offLoading = ref(false);
const offError = ref("");

const shown = computed(() => [...references.value, ...offReferences.value]);

let timer: ReturnType<typeof setTimeout> | undefined;
let offTimer: ReturnType<typeof setTimeout> | undefined;
let requestId = 0;
let offRequestId = 0;
// the text already searched, so that filling the field when the dialog opens doesn't search it again
let scheduled = "";

function resetOpenFoodFacts() {
  clearTimeout(offTimer);
  offRequestId++;
  offSearched.value = "";
  offReferences.value = [];
  offLoading.value = false;
  offError.value = "";
}

function offErrorMessage(requestError: any) {
  switch (requestError?.response?.status) {
    case 429:
      return i18n.t("data-pages.foods.nutrition-search-open-food-facts-rate-limited");
    case 503:
      return i18n.t("data-pages.foods.nutrition-search-open-food-facts-disabled");
    default:
      return i18n.t("data-pages.foods.nutrition-search-open-food-facts-failed", {
        error: requestError?.response?.data?.detail?.message || requestError?.message || "HTTP error",
      });
  }
}

async function searchOpenFoodFacts(text: string) {
  const query = text.trim();
  if (!query) {
    return;
  }

  const id = ++offRequestId;
  offLoading.value = true;
  offError.value = "";
  const { data, error: requestError } = await api.foods.searchOpenFoodFacts(query, 20);
  if (id !== offRequestId) {
    return;
  }
  offLoading.value = false;
  offSearched.value = query;
  if (requestError || !data) {
    offReferences.value = [];
    offError.value = offErrorMessage(requestError);
    return;
  }
  offReferences.value = data;
}

async function runSearch(text: string) {
  const query = text.trim();
  error.value = "";
  if (!query) {
    references.value = [];
    searched.value = "";
    return;
  }

  const id = ++requestId;
  loading.value = true;
  const { data, error: requestError } = await api.foods.searchNutritionReferences(query, 20);
  // an answer to an older search is outdated
  if (id !== requestId) {
    return;
  }
  loading.value = false;
  searched.value = query;
  if (requestError || !data) {
    references.value = [];
    error.value = (requestError as any)?.message || "HTTP error";
    return;
  }
  references.value = data;
}

watch(search, (text) => {
  if ((text || "") === scheduled) {
    return;
  }
  scheduled = text || "";
  resetOpenFoodFacts();
  clearTimeout(timer);
  timer = setTimeout(() => runSearch(text || ""), SEARCH_DELAY);
  offTimer = setTimeout(() => searchOpenFoodFacts(text || ""), OFF_SEARCH_DELAY);
});

watch(dialog, (open) => {
  if (open) {
    search.value = props.query || "";
    scheduled = search.value;
    resetOpenFoodFacts();
    clearTimeout(timer);
    runSearch(search.value);
    searchOpenFoodFacts(search.value);
  }
}, { immediate: true });

onBeforeUnmount(() => {
  clearTimeout(timer);
  clearTimeout(offTimer);
});

function tableName(reference: IngredientFoodNutritionReference) {
  return nutritionTable(reference.source)?.name || reference.source;
}

function summary(reference: IngredientFoodNutritionReference) {
  const nutrition = reference.nutrition;
  const parts = [
    nutrition.calories ? `${nutrition.calories} kcal` : "",
    nutrition.proteinContent ? `${i18n.t("recipe.protein-content")} ${nutrition.proteinContent} g` : "",
    nutrition.carbohydrateContent ? `${i18n.t("recipe.carbohydrate-content")} ${nutrition.carbohydrateContent} g` : "",
    nutrition.fatContent ? `${i18n.t("recipe.fat-content")} ${nutrition.fatContent} g` : "",
    reference.averageWeight ? i18n.t("data-pages.foods.nutrition-search-piece-weight", { weight: reference.averageWeight }) : "",
  ];
  return parts.filter(Boolean).join(" · ");
}

function choose(reference: IngredientFoodNutritionReference) {
  emit("select", reference);
  dialog.value = false;
}
</script>

<style scoped>
.reference-list {
  max-height: 400px;
  overflow-y: auto;
}
</style>
