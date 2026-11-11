<template>
  <div class="nutrition-panel" data-testid="food-section-nutrition">
    <div class="d-flex align-center ga-2">
      <div class="pt-1">
        <v-card-title class="pl-0 pt-0 pb-0">
          {{ $t("recipe.nutrition") }}
        </v-card-title>
        <small class="text-medium-emphasis" data-testid="nutrition-per-100g">
          {{ $t("data-pages.foods.nutrition-per-100g") }}
        </small>
      </div>
      <div class="ml-auto d-flex align-center ga-2">
        <v-chip v-if="filledCount" size="x-small" color="success" variant="tonal">
          {{ filledCount }} / {{ fields.length }}
        </v-chip>
        <v-tooltip v-if="canFill" location="bottom" color="info" :text="$t('data-pages.foods.fill-nutrition')">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              v-bind="tooltipProps"
              icon
              variant="flat"
              rounded="circle"
              size="x-small"
              color="info"
              :loading="fillLoading"
              :disabled="!foodName"
              :aria-label="$t('data-pages.foods.fill-nutrition')"
              data-testid="fill-nutrition"
              @click.stop="emit('fill')"
            >
              <BaseNutritionAiIcon :size="20" background="info" />
            </v-btn>
          </template>
        </v-tooltip>
      </div>
    </div>
    <div class="d-flex align-center flex-wrap ga-2 py-2">
      <RecipeDataNutritionSource
        class="flex-grow-1"
        :source="source"
        :reference-code="referenceCode"
        :reference-name="referenceName"
      />
      <v-tooltip v-if="filledCount || source" location="bottom" :text="$t('recipe.clear-nutrition')">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            icon
            variant="text"
            size="small"
            color="error"
            class="ml-auto"
            :aria-label="$t('recipe.clear-nutrition')"
            data-testid="clear-nutrition"
            @click="clear"
          >
            <v-icon>{{ $globals.icons.eraser }}</v-icon>
          </v-btn>
        </template>
      </v-tooltip>
      <BaseButton
        size="small"
        color="info"
        :class="{ 'ml-auto': !(filledCount || source) }"
        data-testid="search-nutrition-tables"
        @click="searchDialog = true"
      >
        <template #icon>
          {{ $globals.icons.database }}
        </template>
        {{ $t("data-pages.foods.nutrition-fill-from-references") }}
      </BaseButton>
    </div>
    <v-row dense>
      <v-col v-for="field in fields" :key="field.key" cols="12" sm="6">
        <v-text-field
          :model-value="field.value"
          :label="field.label"
          :suffix="field.suffix"
          type="number"
          min="0"
          density="compact"
          variant="underlined"
          hide-details
          @update:model-value="update(field.key, $event)"
        />
      </v-col>
    </v-row>
  </div>
  <RecipeDataNutritionReferenceDialog v-model="searchDialog" :query="foodName" @select="selectReference" />
</template>

<script setup lang="ts">
import { filledNutritionFields, useNutritionLabels } from "~/composables/recipes/use-recipe-nutrition";
import type {
  IngredientFoodNutritionReference,
  IngredientFoodNutritionSource,
  Nutrition,
} from "~/lib/api/types/recipe";

withDefaults(defineProps<{
  /** Searched in the composition tables by default */
  foodName?: string | null;
  /** Shows the AI button filling the values in the title bar */
  canFill?: boolean;
  fillLoading?: boolean;
}>(), {
  foodName: null,
  canFill: false,
  fillLoading: false,
});

const emit = defineEmits<{
  /** The weight of one piece given by the chosen food of a composition table */
  "average-weight": [weight: number];
  /** The AI button of the title bar was clicked */
  "fill": [];
}>();

const nutrition = defineModel<Nutrition | null | undefined>();
const source = defineModel<IngredientFoodNutritionSource | null | undefined>("source");
const referenceCode = defineModel<string | null | undefined>("referenceCode");
const referenceName = defineModel<string | null | undefined>("referenceName");

const searchDialog = ref(false);

const { labels } = useNutritionLabels();

const fields = computed(() =>
  Object.entries(labels).map(([key, field]) => {
    const value = (nutrition.value as Record<string, string | null | undefined> | null | undefined)?.[key];
    return { key, label: field.label, suffix: field.suffix, value: value ?? "" };
  }),
);

const filledCount = computed(() => filledNutritionFields(nutrition.value, labels).length);

function update(key: string, value: string | number | null) {
  const text = value === null || value === undefined ? "" : String(value).trim();
  nutrition.value = { ...(nutrition.value || {}), [key]: text || null };
  // the values are no longer the ones of the source
  source.value = null;
  referenceCode.value = null;
  referenceName.value = null;
}

function clear() {
  nutrition.value = null;
  source.value = null;
  referenceCode.value = null;
  referenceName.value = null;
}

function selectReference(reference: IngredientFoodNutritionReference) {
  nutrition.value = { ...reference.nutrition };
  source.value = reference.source;
  referenceCode.value = reference.code;
  referenceName.value = reference.name;
  if (reference.averageWeight) {
    emit("average-weight", reference.averageWeight);
  }
}
</script>
