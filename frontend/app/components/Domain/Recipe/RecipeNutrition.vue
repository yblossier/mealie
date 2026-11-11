<template>
  <div v-if="valueNotNull || edit">
    <v-card class="mt-2">
      <v-card-title class="pt-2 pb-0 d-flex align-center">
        {{ $t("recipe.nutrition") }}
        <div v-if="edit" class="ml-auto d-flex align-center ga-1">
          <v-btn
            v-if="valueNotNull"
            icon
            size="small"
            variant="text"
            color="error"
            data-testid="clear-recipe-nutrition"
            :title="$t('recipe.clear-nutrition')"
            :aria-label="$t('recipe.clear-nutrition')"
            @click="clearValues"
          >
            <v-icon>{{ $globals.icons.eraser }}</v-icon>
          </v-btn>
          <RecipeNutritionFillButton
            v-if="recipe"
            fab
            compact
            :recipe="recipe"
            @fill="fillValues"
          />
        </div>
      </v-card-title>
      <v-card-subtitle class="pb-1">
        {{ $t("recipe.per-serving") }}
      </v-card-subtitle>
      <v-divider class="mx-2 my-1" />
      <v-card-text v-if="edit">
        <div
          v-for="(item, key, index) in modelValue"
          :key="index"
        >
          <v-number-input
            :model-value="parseNutritionValue(modelValue[key])"
            :label="labels[key].label"
            :suffix="labels[key].suffix"
            density="compact"
            autocomplete="off"
            variant="underlined"
            inset
            :precision="null"
            :min="0"
            @update:model-value="updateValue(key, $event)"
          />
        </div>
      </v-card-text>
      <v-card-text v-if="showViewer" class="pt-1">
        <RecipeNutritionFactsLabel
          :nutrition="modelValue"
          :basis="$t('recipe.nutrition-facts-per-serving')"
        />
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { parseNutritionValue, useNutritionLabels } from "~/composables/recipes";
import type { Nutrition, RecipeOut } from "~/lib/api/types/recipe";
import { alert } from "~/composables/use-toast";
import RecipeNutritionFillButton from "./RecipeNutritionFillButton.vue";
import RecipeNutritionFactsLabel from "./RecipeNutritionFactsLabel.vue";

interface Props {
  edit?: boolean;
  /** Enables computing the values from the ingredients while editing */
  recipe?: RecipeOut | null;
}
const props = withDefaults(defineProps<Props>(), {
  edit: true,
  recipe: null,
});

const modelValue = defineModel<Nutrition>({ required: true });

const i18n = useI18n();

function fillValues(nutrition: Nutrition) {
  modelValue.value = { ...modelValue.value, ...nutrition };
  alert.success(i18n.t("recipe.nutrition-filled-from-ingredients"));
}

const { labels } = useNutritionLabels();
const valueNotNull = computed(() => {
  let key: keyof Nutrition;
  for (key in modelValue.value) {
    if (modelValue.value[key] !== null && modelValue.value[key] !== undefined && String(modelValue.value[key]).trim() !== "") {
      return true;
    }
  }
  return false;
});

const showViewer = computed(() => !props.edit && valueNotNull.value);

function clearValues() {
  modelValue.value = Object.fromEntries(Object.keys(modelValue.value).map(key => [key, null])) as Nutrition;
}

function updateValue(key: number | string, value: number | null) {
  modelValue.value = { ...modelValue.value, [key]: value?.toString() ?? null };
}
</script>

<style lang="scss" scoped></style>
