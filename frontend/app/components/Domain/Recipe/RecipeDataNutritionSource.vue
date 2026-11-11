<template>
  <div v-if="source" class="text-body-2" data-testid="nutrition-source">
    <div class="d-flex align-center flex-wrap ga-2">
      <v-chip
        size="small"
        variant="tonal"
        :color="table ? 'success' : 'info'"
        :prepend-icon="table ? $globals.icons.database : $globals.icons.robot"
      >
        {{ table ? table.name : $t("data-pages.foods.nutrition-source-ai") }}
      </v-chip>
      <a
        v-if="table && url"
        :href="url"
        target="_blank"
        rel="noopener noreferrer"
        class="text-decoration-underline"
        data-testid="nutrition-source-link"
      >
        {{ referenceName || referenceCode }}
      </a>
      <span v-else-if="table && referenceName">{{ referenceName }}</span>
    </div>
    <div v-if="table" class="pt-1 text-caption text-medium-emphasis" data-testid="nutrition-source-attribution">
      {{ $t("data-pages.foods.nutrition-source-attribution", { attribution: table.attribution }) }}
      (<a :href="table.licenseUrl" target="_blank" rel="noopener noreferrer">{{ table.license }}</a>)
    </div>
    <div v-else class="pt-1 text-caption text-medium-emphasis">
      {{ $t("data-pages.foods.nutrition-source-ai-hint") }}
    </div>
  </div>
</template>

<script setup lang="ts">
import type { IngredientFoodNutritionSource } from "~/lib/api/types/recipe";
import { nutritionReferenceUrl, nutritionTable } from "~/lib/recipe/nutrition-source";

const props = defineProps<{
  source?: IngredientFoodNutritionSource | null;
  referenceCode?: string | null;
  referenceName?: string | null;
}>();

const table = computed(() => nutritionTable(props.source));
const url = computed(() => nutritionReferenceUrl(props.source, props.referenceCode));
</script>
